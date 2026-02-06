# PRD: Agent 执行计划 (Execution Plan)

## 背景与问题
目前 Agno 模式可调用工具并流式输出，但缺少“可执行的多步计划”与稳定编排能力：
- 复杂任务只能单轮对话驱动，难以跨多步稳定执行
- 缺少依赖/并行管理，无法可控地扩展复杂流程
- 缺少执行状态持久化与恢复，失败后不可复盘

我们需要一个“给 Agent 执行用的计划”，强调结构化、可执行、可恢复，不是给人阅读的任务计划。

## 目标
- 生成结构化的 Agent 执行计划（Plan Spec），包含步骤、依赖、并行、执行类型
- 提供稳定的多步执行编排（基于 Agno Workflow）
- 支持步骤级重试与可恢复执行
- 执行状态持久化，便于复盘与后续自动化

## 非目标
- 分布式任务调度与队列系统
- 多 Agent 团队编排与复杂权限治理
- 多 Agent 团队编排与复杂权限治理
- 分布式任务调度与队列系统

## 用户与场景
- 用户输入复杂目标（如“规划并创建本周任务+提醒”）
- Agent 先生成可执行计划，再按步骤自动执行
- 步骤执行失败可重试或跳过

## 关键成功指标
- 计划生成成功率
- 计划执行完成率
- 单步骤失败后的恢复成功率
- 执行总时长（P50/P90）

## 核心需求
### 1) 计划生成
- 输出机器可读的 Plan Spec（JSON）
- 包含步骤类型、依赖关系、并行标记与重试策略
- 支持工具执行与 LLM 推理步骤混合

### 2) 执行编排
- 根据依赖关系构建可执行 DAG
- 对无依赖步骤并行执行
- 记录每步输入、输出、状态与耗时

### 3) 失败处理
- 支持步骤级重试
- 超过重试次数后可跳过或终止计划

### 4) 状态持久化
- 持久化 Plan、Run、Step 执行记录
- 支持恢复执行（从最后成功步骤继续）

### 5) 回滚与补偿（必须）
- 有副作用的步骤必须写入回滚日志（journal）
- 支持文件写入/删除/移动的可逆补偿
- 回滚按已完成步骤的逆拓扑顺序执行

## Plan Spec（草案）
```json
{
  "plan_id": "pln_123",
  "title": "Plan my week",
  "steps": [
    {
      "step_id": "s1",
      "name": "Collect existing todos",
      "type": "tool",
      "tool": "list_todos",
      "inputs": {"status": "active"},
      "depends_on": [],
      "retry": {"max_retries": 3}
    },
    {
      "step_id": "s2",
      "name": "Break down project tasks",
      "type": "llm",
      "inputs": {"prompt": "..."},
      "depends_on": ["s1"]
    },
    {
      "step_id": "s3",
      "name": "Create new todos",
      "type": "tool",
      "tool": "create_todo",
      "inputs": {"name": "..."},
      "depends_on": ["s2"]
    }
  ]
}
```

## 回滚策略（概述）
文件操作需要硬性回滚策略，最低要求：
- 写入/修改文件：写入前备份旧内容，回滚时恢复；若新建文件，回滚时删除
- 删除文件/目录：改为移动到回收目录，回滚时移回
- 移动/重命名：记录 from/to，回滚时反向移动

回滚日志需要持久化，确保崩溃后可恢复执行回滚。

## 依赖与参考
- Agno Workflow API: https://docs.agno.com/introduction
- 现有 Agno 集成：`lifetrace/llm/agno_agent.py`
