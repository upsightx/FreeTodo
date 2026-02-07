# -*- coding: utf-8 -*-
"""
视频音频提取与语音识别脚本

功能：
1. 读取今天爬取的所有平台的 CSV 文件
2. 从视频帖子中提取视频 URL
3. 下载视频
4. 从视频中提取音频
5. 使用 faster-whisper 进行语音识别
6. 保存文本到指定目录
"""

import asyncio
import csv
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

# 配置路径
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "transcripts"

# 各平台视频URL字段映射
PLATFORM_VIDEO_FIELDS = {
    "douyin": "video_download_url",
    "xhs": "video_url",
    "bilibili": "video_url",
    "kuaishou": "video_url",
}

# 各平台ID字段映射
PLATFORM_ID_FIELDS = {
    "douyin": "aweme_id",
    "xhs": "note_id",
    "bilibili": "video_id",
    "kuaishou": "video_id",
}

# 各平台标题字段映射
PLATFORM_TITLE_FIELDS = {
    "douyin": "title",
    "xhs": "title",
    "bilibili": "title",
    "kuaishou": "title",
}


class VideoTranscriber:
    """视频转文字处理器"""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
    ):
        """
        初始化转写器

        Args:
            model_size: Whisper模型大小 (tiny, base, small, medium, large-v2, large-v3)
            device: 设备类型 (auto, cpu, cuda)
            compute_type: 计算类型 (auto, int8, float16, float32)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._http_client = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=15.0),  # 更短的超时
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._http_client:
            await self._http_client.aclose()

    def _load_model(self):
        """延迟加载Whisper模型"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info(f"正在加载 Whisper 模型: {self.model_size}")
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("Whisper 模型加载完成")
            except ImportError:
                logger.error("faster-whisper 未安装，请运行: pip install faster-whisper")
                raise
            except Exception as e:
                logger.error(f"加载 Whisper 模型失败: {e}")
                raise
        return self._model

    async def download_video(
        self, url: str, output_path: Path, platform: str = ""
    ) -> bool:
        """
        下载视频文件

        Args:
            url: 视频URL
            output_path: 输出路径
            platform: 平台名称

        Returns:
            是否下载成功
        """
        if not url or not url.startswith("http"):
            logger.warning(f"无效的视频URL: {url}")
            return False

        try:
            logger.info(f"正在下载视频: {url[:100]}...")

            # 根据平台设置不同的请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            if platform == "douyin" or "douyin" in url:
                headers["Referer"] = "https://www.douyin.com/"
            elif platform == "xhs" or "xhscdn" in url:
                headers["Referer"] = "https://www.xiaohongshu.com/"
            elif platform == "kuaishou" or "kuaishou" in url:
                headers["Referer"] = "https://www.kuaishou.com/"

            # 使用流式下载
            async with self._http_client.stream(
                "GET", url, headers=headers
            ) as response:
                if response.status_code != 200:
                    logger.error(
                        f"下载失败，状态码: {response.status_code}, URL: {url[:80]}"
                    )
                    return False

                # 检查内容类型
                content_type = response.headers.get("content-type", "")
                if "video" not in content_type and "octet-stream" not in content_type:
                    logger.warning(f"响应不是视频类型: {content_type}")
                    # 仍然尝试下载

                total_size = 0
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        total_size += len(chunk)

            if total_size < 1000:  # 小于1KB可能是错误响应
                logger.warning(f"下载的文件太小 ({total_size} bytes)，可能不是有效视频")
                return False

            logger.info(f"视频下载完成: {output_path} ({total_size / 1024 / 1024:.2f} MB)")
            return True

        except httpx.TimeoutException:
            logger.error(f"下载超时: {url[:80]}")
            return False
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            return False

    def extract_audio_from_video(
        self, video_path: Path, audio_path: Path
    ) -> bool:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径
            audio_path: 输出音频路径

        Returns:
            是否提取成功
        """
        try:
            import av

            logger.info(f"正在从视频中提取音频...")

            # 打开视频文件
            container = av.open(str(video_path))

            # 检查是否有音频流
            audio_streams = [s for s in container.streams if s.type == "audio"]
            if not audio_streams:
                logger.warning("视频没有音频流")
                container.close()
                return False

            # 创建输出容器
            output_container = av.open(str(audio_path), mode="w")
            output_stream = output_container.add_stream("pcm_s16le", rate=16000)
            output_stream.layout = "mono"

            # 重采样器
            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=16000,
            )

            # 处理音频帧
            for frame in container.decode(audio=0):
                # 重采样
                resampled_frames = resampler.resample(frame)
                for resampled_frame in resampled_frames:
                    for packet in output_stream.encode(resampled_frame):
                        output_container.mux(packet)

            # 刷新编码器
            for packet in output_stream.encode():
                output_container.mux(packet)

            output_container.close()
            container.close()

            logger.info(f"音频提取完成: {audio_path}")
            return True

        except Exception as e:
            logger.error(f"提取音频失败: {e}")
            return False

    def transcribe_audio(self, audio_path: Path) -> Optional[str]:
        """
        对音频进行语音识别

        Args:
            audio_path: 音频文件路径

        Returns:
            识别出的文本
        """
        try:
            model = self._load_model()

            logger.info(f"正在进行语音识别...")

            # 执行转写
            segments, info = model.transcribe(
                str(audio_path),
                language="zh",  # 中文
                beam_size=5,
                vad_filter=True,  # 启用VAD过滤静音
            )

            # 合并所有文本片段
            texts = []
            for segment in segments:
                texts.append(segment.text.strip())

            full_text = "\n".join(texts)
            logger.info(f"语音识别完成，文本长度: {len(full_text)}")
            return full_text

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return None

    async def process_video(
        self, video_url: str, content_id: str, title: str, platform: str
    ) -> Optional[dict]:
        """
        处理单个视频：下载 -> 提取音频 -> 语音识别

        Args:
            video_url: 视频URL
            content_id: 内容ID
            title: 标题
            platform: 平台名称

        Returns:
            处理结果字典
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # 使用安全的文件名
            safe_id = re.sub(r'[\\/*?:"<>|]', "_", content_id)[:50]
            video_path = temp_path / f"{safe_id}.mp4"
            audio_path = temp_path / f"{safe_id}.wav"

            # 1. 下载视频
            if not await self.download_video(video_url, video_path, platform):
                return None

            # 2. 提取音频
            if not self.extract_audio_from_video(video_path, audio_path):
                return None

            # 3. 语音识别
            transcript = self.transcribe_audio(audio_path)
            if not transcript:
                return None

            return {
                "content_id": content_id,
                "title": title,
                "platform": platform,
                "transcript": transcript,
                "video_url": video_url,
            }


def get_today_csv_files() -> list[tuple[str, Path]]:
    """
    获取今天的所有CSV文件

    Returns:
        [(platform, file_path), ...]
    """
    today = datetime.now().strftime("%Y-%m-%d")
    files = []

    for platform in PLATFORM_VIDEO_FIELDS.keys():
        platform_dir = DATA_DIR / platform
        if not platform_dir.exists():
            continue

        for csv_file in platform_dir.glob(f"*_search_contents_{today}.csv"):
            files.append((platform, csv_file))
            logger.info(f"找到数据文件: {csv_file}")

    return files


def read_video_contents(platform: str, csv_path: Path) -> list[dict]:
    """
    读取CSV文件中的视频内容

    Args:
        platform: 平台名称
        csv_path: CSV文件路径

    Returns:
        视频内容列表
    """
    video_field = PLATFORM_VIDEO_FIELDS.get(platform)
    id_field = PLATFORM_ID_FIELDS.get(platform)
    title_field = PLATFORM_TITLE_FIELDS.get(platform)

    if not video_field:
        logger.warning(f"未配置平台 {platform} 的视频字段")
        return []

    contents = []
    try:
        # 使用 utf-8-sig 编码来自动处理 BOM
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # 打印列名以便调试
            fieldnames = reader.fieldnames
            logger.debug(f"CSV 列名: {fieldnames}")

            for row in reader:
                video_url = row.get(video_field, "").strip()
                content_id = row.get(id_field, "").strip()
                title = row.get(title_field, "").strip() or row.get("desc", "").strip()

                # 跳过 bilibili（网页链接，需要额外解析）
                if platform == "bilibili":
                    logger.debug(f"跳过 bilibili 视频（需要额外解析）: {content_id}")
                    continue

                # 只处理有视频URL的内容，并且是直接下载链接
                if video_url and video_url.startswith("http"):
                    # 跳过网页链接
                    if "/video/" in video_url and "bilibili" in video_url:
                        continue

                    contents.append({
                        "video_url": video_url,
                        "content_id": content_id or f"unknown_{hash(video_url) % 10000}",
                        "title": title[:100] if title else "无标题",
                        "platform": platform,
                    })

        logger.info(f"从 {csv_path.name} 读取到 {len(contents)} 个可下载视频")
    except Exception as e:
        logger.error(f"读取CSV文件失败 {csv_path}: {e}")
        import traceback
        traceback.print_exc()

    return contents


def save_transcript(result: dict, output_dir: Path):
    """
    保存转写结果

    Args:
        result: 转写结果
        output_dir: 输出目录
    """
    platform = result["platform"]
    content_id = result["content_id"]
    title = result["title"]
    transcript = result["transcript"]

    # 创建平台子目录
    platform_dir = output_dir / platform
    platform_dir.mkdir(parents=True, exist_ok=True)

    # 清理标题作为文件名的一部分
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50]

    # 保存为txt文件
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{content_id}_{safe_title}_{today}.txt"
    output_path = platform_dir / filename

    content = f"""标题: {title}
平台: {platform}
内容ID: {content_id}
视频URL: {result['video_url']}
转写时间: {datetime.now().isoformat()}

========== 转写文本 ==========

{transcript}
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"转写结果已保存: {output_path}")


async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("视频音频提取与语音识别脚本")
    logger.info("=" * 50)

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"输出目录: {OUTPUT_DIR}")

    # 获取今天的CSV文件
    csv_files = get_today_csv_files()
    if not csv_files:
        logger.warning("没有找到今天的数据文件")
        return

    # 收集所有视频内容，按平台分组（优先处理小红书和快手）
    all_contents = []
    platform_order = ["xhs", "kuaishou", "douyin"]  # 优先顺序

    for priority_platform in platform_order:
        for platform, csv_path in csv_files:
            if platform == priority_platform:
                contents = read_video_contents(platform, csv_path)
                all_contents.extend(contents)

    logger.info(f"共找到 {len(all_contents)} 个视频需要处理")
    logger.info("处理顺序: 小红书 -> 快手 -> 抖音")

    if not all_contents:
        logger.warning("没有找到需要处理的视频")
        return

    # 处理视频 (使用CPU模式避免CUDA兼容性问题)
    async with VideoTranscriber(
        model_size="base",  # 使用base模型，平衡速度和准确性
        device="cpu",  # 强制使用CPU
        compute_type="int8",  # 使用int8量化提高CPU性能
    ) as transcriber:
        success_count = 0
        fail_count = 0

        for i, content in enumerate(all_contents, 1):
            logger.info(f"\n[{i}/{len(all_contents)}] 处理: {content['title'][:50]}...")
            logger.info(f"平台: {content['platform']}, ID: {content['content_id']}")

            try:
                result = await transcriber.process_video(
                    video_url=content["video_url"],
                    content_id=content["content_id"],
                    title=content["title"],
                    platform=content["platform"],
                )

                if result:
                    save_transcript(result, OUTPUT_DIR)
                    success_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                logger.error(f"处理视频时出错: {e}")
                fail_count += 1

    logger.info("\n" + "=" * 50)
    logger.info(f"处理完成! 成功: {success_count}, 失败: {fail_count}")
    logger.info(f"转写结果保存在: {OUTPUT_DIR}")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
