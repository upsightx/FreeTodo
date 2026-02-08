"""
Token使用量记录器
记录LLM API调用的token使用情况，便于后续统计分析
"""

from datetime import timedelta
from functools import lru_cache
from typing import Any

try:
    import litellm
except Exception:  # pragma: no cover - 仅在依赖缺失时触发
    litellm = None

from lifetrace.storage import get_session
from lifetrace.storage.models import TokenUsage
from lifetrace.storage.sql_utils import col
from lifetrace.util.logging_config import get_logger
from lifetrace.util.settings import settings
from lifetrace.util.time_utils import get_utc_now

logger = get_logger()

INVALID_LLM_VALUES = [
    "",
    "xxx",
    "YOUR_API_KEY_HERE",
    "YOUR_BASE_URL_HERE",
    "YOUR_LLM_KEY_HERE",
]


def _is_valid_value(value: str | None) -> bool:
    return bool(value) and value not in INVALID_LLM_VALUES


def _resolve_litellm_model(model: str | None, base_url: str | None) -> str:
    """将模型名转换为 LiteLLM 可识别的格式。"""
    if not model:
        return ""
    if "/" in model:
        return model
    if _is_valid_value(base_url):
        return f"openai/{model}"
    return model


def _get_litellm_model_cost_entry(model: str) -> dict[str, Any] | None:
    if litellm is None:
        return None
    cost_map = getattr(litellm, "model_cost", {}) or {}
    if not cost_map:
        return None

    base_url = settings.get("llm.base_url")
    resolved_model = _resolve_litellm_model(model, base_url)
    model_keys = []
    if resolved_model:
        model_keys.append(resolved_model)
        if "/" in resolved_model:
            model_keys.append(resolved_model.split("/", 1)[1])
    if model and model not in model_keys:
        model_keys.append(model)

    for key in model_keys:
        if key in cost_map:
            return cost_map[key]
    return None


def _normalize_price_per_1k(cost_entry: dict[str, Any]) -> tuple[float, float]:
    input_per_token = cost_entry.get("input_cost_per_token")
    output_per_token = cost_entry.get("output_cost_per_token")
    if input_per_token is not None and output_per_token is not None:
        return float(input_per_token) * 1000, float(output_per_token) * 1000

    input_per_1k = cost_entry.get("input_cost_per_1k_tokens")
    output_per_1k = cost_entry.get("output_cost_per_1k_tokens")
    if input_per_1k is not None and output_per_1k is not None:
        return float(input_per_1k), float(output_per_1k)

    return 0.0, 0.0


class TokenUsageLogger:
    """Token使用量记录器"""

    def __init__(self):
        pass

    def _get_model_price(self, model: str, input_tokens: int | None = None) -> tuple[float, float]:
        """获取模型价格（USD/千token，来自 LiteLLM 的模型价格表）

        Args:
            model: 模型名称
            input_tokens: 输入token数量，用于选择分层价格（可选）

        Returns:
            (input_price, output_price) 元组
        """
        _ = input_tokens
        if litellm is None:
            return 0.0, 0.0

        cost_entry = _get_litellm_model_cost_entry(model)
        if not cost_entry:
            return 0.0, 0.0
        return _normalize_price_per_1k(cost_entry)

    def log_token_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: dict[str, Any] | None = None,
    ):
        """
        记录token使用量

        Args:
            model: 使用的模型名称
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            metadata: 元数据字典，可包含以下键：
                - endpoint: API端点（如 /api/chat, /api/chat/stream）
                - user_query: 用户查询内容（可选，用于分析）
                - response_type: 响应类型（如 chat, search, classify）
                - feature_type: 功能类型（如 event_assistant, project_assistant）
                - additional_info: 额外信息字典
        """
        max_query_preview_length = 200

        if metadata is None:
            metadata = {}

        endpoint = metadata.get("endpoint") or "unknown"
        user_query = metadata.get("user_query")
        response_type = metadata.get("response_type")
        feature_type = metadata.get("feature_type") or endpoint

        try:
            # 计算成本
            input_price, output_price = self._get_model_price(model, input_tokens)
            input_cost = (input_tokens / 1000) * input_price
            output_cost = (output_tokens / 1000) * output_price
            total_cost = input_cost + output_cost

            # 准备用户查询预览
            user_query_preview = None
            query_length = None
            if user_query:
                # 只记录查询的前N个字符
                user_query_preview = user_query[:max_query_preview_length] + (
                    "..." if len(user_query) > max_query_preview_length else ""
                )
                query_length = len(user_query)

            # 写入数据库
            with get_session() as session:
                token_usage = TokenUsage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    endpoint=endpoint,
                    response_type=response_type,
                    feature_type=feature_type,
                    user_query_preview=user_query_preview,
                    query_length=query_length,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    total_cost=total_cost,
                    created_at=get_utc_now(),
                )
                session.add(token_usage)
                session.flush()

            # 记录到标准日志
            logger.info(
                "Token usage - Model: %s, Input: %s, Output: %s, Total: %s, Cost: %.4f USD",
                model,
                input_tokens,
                output_tokens,
                input_tokens + output_tokens,
                total_cost,
            )

        except Exception as e:
            # 记录错误但不影响主流程
            logger.error(f"Failed to log token usage: {e}")

    def get_usage_stats(self, days: int = 30) -> dict[str, Any]:
        """
        获取token使用统计

        Args:
            days: 统计最近多少天的数据

        Returns:
            统计结果字典
        """
        try:
            stats = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_requests": 0,
                "total_cost": 0.0,
                "model_stats": {},
                "endpoint_stats": {},
                "feature_stats": {},
                "daily_stats": {},
            }

            end_date = get_utc_now()
            start_date = end_date - timedelta(days=days)

            # 从数据库查询
            with get_session() as session:
                # 查询时间范围内的所有记录
                records = (
                    session.query(TokenUsage)
                    .filter(col(TokenUsage.created_at) >= start_date)
                    .filter(col(TokenUsage.created_at) <= end_date)
                    .all()
                )

                for record in records:
                    # 更新总计
                    stats["total_input_tokens"] += record.input_tokens
                    stats["total_output_tokens"] += record.output_tokens
                    stats["total_tokens"] += record.total_tokens
                    stats["total_cost"] += record.total_cost
                    stats["total_requests"] += 1

                    # 按模型统计
                    model = record.model
                    if model not in stats["model_stats"]:
                        stats["model_stats"][model] = {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "requests": 0,
                            "input_cost": 0.0,
                            "output_cost": 0.0,
                            "total_cost": 0.0,
                        }
                    stats["model_stats"][model]["input_tokens"] += record.input_tokens
                    stats["model_stats"][model]["output_tokens"] += record.output_tokens
                    stats["model_stats"][model]["total_tokens"] += record.total_tokens
                    stats["model_stats"][model]["input_cost"] += record.input_cost
                    stats["model_stats"][model]["output_cost"] += record.output_cost
                    stats["model_stats"][model]["total_cost"] += record.total_cost
                    stats["model_stats"][model]["requests"] += 1

                    # 按端点统计
                    endpoint = record.endpoint or "unknown"
                    if endpoint not in stats["endpoint_stats"]:
                        stats["endpoint_stats"][endpoint] = {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "requests": 0,
                            "total_cost": 0.0,
                        }
                    stats["endpoint_stats"][endpoint]["input_tokens"] += record.input_tokens
                    stats["endpoint_stats"][endpoint]["output_tokens"] += record.output_tokens
                    stats["endpoint_stats"][endpoint]["total_tokens"] += record.total_tokens
                    stats["endpoint_stats"][endpoint]["total_cost"] += record.total_cost
                    stats["endpoint_stats"][endpoint]["requests"] += 1

                    # 按功能类型统计
                    feature_type = record.feature_type or "unknown"
                    if feature_type not in stats["feature_stats"]:
                        stats["feature_stats"][feature_type] = {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "requests": 0,
                            "total_cost": 0.0,
                        }
                    stats["feature_stats"][feature_type]["input_tokens"] += record.input_tokens
                    stats["feature_stats"][feature_type]["output_tokens"] += record.output_tokens
                    stats["feature_stats"][feature_type]["total_tokens"] += record.total_tokens
                    stats["feature_stats"][feature_type]["total_cost"] += record.total_cost
                    stats["feature_stats"][feature_type]["requests"] += 1

                    # 按日期统计
                    date_str = record.created_at.strftime("%Y-%m-%d")
                    if date_str not in stats["daily_stats"]:
                        stats["daily_stats"][date_str] = {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "requests": 0,
                            "total_cost": 0.0,
                        }
                    stats["daily_stats"][date_str]["input_tokens"] += record.input_tokens
                    stats["daily_stats"][date_str]["output_tokens"] += record.output_tokens
                    stats["daily_stats"][date_str]["total_tokens"] += record.total_tokens
                    stats["daily_stats"][date_str]["total_cost"] += record.total_cost
                    stats["daily_stats"][date_str]["requests"] += 1

            return stats

        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}


# 全局token使用量记录器实例


@lru_cache(maxsize=1)
def get_token_logger() -> TokenUsageLogger:
    """获取token使用量记录器实例"""
    return TokenUsageLogger()


def setup_token_logger() -> TokenUsageLogger:
    """设置token使用量记录器"""
    return get_token_logger()


def log_token_usage(model: str, input_tokens: int, output_tokens: int, **kwargs):
    """便捷函数：记录token使用量

    Args:
        model: 模型名称
        input_tokens: 输入token数量
        output_tokens: 输出token数量
        **kwargs: 传递给 metadata 字典的其他参数
    """
    token_logger = get_token_logger()
    return token_logger.log_token_usage(model, input_tokens, output_tokens, metadata=kwargs)
