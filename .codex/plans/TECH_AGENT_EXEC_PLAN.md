# 技术方案: Agent 执行计划 (Execution Plan)

## 目标
实现“可执行计划”的生成与执行编排，面向 Agno Agent，提供：
- 多步计划生成（机器可读 JSON）
- 依赖/并行执行
- 步骤级重试
- 执行状态持久化与恢复

## 架构概览
1) **Plan Builder**: LLM 生成 Plan Spec  
2) **Plan Runner**: Plan Spec -> Agno Workflow 执行  
3) **Persistence**: Plan/Run/Step 状态与产出存储  
4) **Streaming**: 执行事件流向前端

## Plan Builder（新 Prompt）
### 触发
新增 API（示例）：`POST /api/agent/plan`

### 输入
- 用户目标、可选上下文（todos、历史对话、workspace）

### 输出
Plan Spec JSON，字段如下：
```json
{
  "plan_id": "pln_123",
  "title": "string",
  "steps": [
    {
      "step_id": "s1",
      "name": "string",
      "type": "tool|llm|condition",
      "tool": "tool_name_if_any",
      "inputs": {},
      "depends_on": ["s0"],
      "parallel_group": "optional_group_id",
      "retry": {"max_retries": 3, "backoff_ms": 500},
      "on_fail": "stop|skip"
    }
  ]
}
```

### Prompt 建议（示意）
目标：产出可执行的 JSON，强调依赖与可执行性。
```
你是执行计划生成器，输出一个 JSON 对象 {plan_id, title, steps}。
每个 step 必须包含: step_id, name, type, inputs, depends_on。
只输出 JSON，不要自然语言。
```

## Plan Runner（Agno Workflow 映射）
### 映射规则
- `PlanStep` -> `agno.workflow.Step`
- 同层且无依赖的 step -> `Parallel(...)`
- 条件分支 -> `Condition/Router`
- 重试 -> `Step(max_retries=...)`

### 执行流程
1) 校验 Plan Spec（DAG 无环、依赖存在）
2) 拓扑排序 + 分组并行
3) 生成 Agno Workflow 并执行
4) 将 `WorkflowRunEvent` 转换为前端事件流

### 关键实现点
新增模块示例：
- `lifetrace/llm/agno_plan/plan_builder.py`
- `lifetrace/llm/agno_plan/plan_runner.py`

## Persistence 设计
新增表（示例）：
- `agent_plans`
  - plan_id (pk), title, spec_json, created_at, updated_at
- `agent_plan_runs`
  - run_id (pk), plan_id (fk), status, started_at, ended_at, session_id
  - error, rollback_status, rollback_error
- `agent_plan_steps`
  - run_id (fk), step_id, step_name, status, retry_count
  - input_json, output_json, error, started_at, ended_at
  - is_side_effect, rollback_required
- `agent_plan_journals` (回滚日志)
  - journal_id (pk), run_id (fk), step_id
  - op_type (write/delete/move)
  - target_path, backup_path, trash_path, from_path, to_path
  - created_paths_json
  - status (applied/rolled_back/failed), error, created_at, updated_at

恢复逻辑：
- run 状态为 `running` 且中断 -> 从最后成功步骤继续

## API 设计（建议）
### 计划生成
`POST /api/agent/plan`  
输入：`{message, context}`  
输出：Plan Spec JSON

### 计划执行（流式）
`POST /api/agent/plan/run`  
输入：`{plan_id, session_id}`  
输出：事件流（StepStarted/StepCompleted/StepError）

### 控制
`POST /api/agent/plan/run/{run_id}/cancel|resume|retry`

## 事件流与前端
利用 Agno `WorkflowRunEvent`：
- `step_started`
- `step_completed`
- `step_error`

前端可复用现有 Agno TOOL_EVENT 格式，新增 `PLAN_EVENT` 或扩展现有事件类型字段。

## 与现有模块对齐
- 现有 Agno Agent: `lifetrace/llm/agno_agent.py`
- 现有流式入口: `lifetrace/routers/chat/modes/agno.py`
- 新增计划执行入口可与 `mode="agno"` 并存或新增 `mode="agno_plan"`

## 回滚策略（文件操作优先）
### 约束
- 有副作用的 step 必须写 journal
- `shell` 默认不可回滚，除非显式提供 rollback 脚本

### 文件操作回滚
- 写入/修改：执行前备份原文件到 `workspace/.agno/rollback/<run_id>/files/`，回滚时恢复
- 删除：改为移动到 `workspace/.agno/rollback/<run_id>/trash/`，回滚时移回
- 移动/重命名：记录 from/to，回滚时反向移动

### 执行顺序
- 失败时，按已完成步骤的**逆拓扑顺序**执行回滚
- 并行步骤按完成时间倒序回滚

## 实施步骤（建议）
1) 定义 Plan Spec + Prompt
2) 实现 Plan Builder（LLM JSON 输出）
3) 实现 Plan Runner（Agno Workflow 映射 + 执行）
4) 接入 API + Streaming 事件
5) 增加持久化与恢复
6) 增加回滚日志与回滚执行

## Runner 伪代码（含回滚）
```python
def run_plan(plan, run_id):
    journal = []
    completed_steps = []
    for step in topo_sort(plan.steps):
        try:
            if step.is_side_effect:
                j = prepare_journal(step, run_id)
                journal.append(j)
            output = execute_step(step)
            record_step_success(step, output)
            completed_steps.append(step)
        except Exception as exc:
            record_step_error(step, exc)
            rollback(completed_steps, journal)
            raise

def rollback(completed_steps, journal):
    for step in reversed(completed_steps):
        j = find_journal_for_step(step, journal)
        if not j:
            continue
        try:
            execute_rollback(j)
            mark_journal_rolled_back(j)
        except Exception as exc:
            mark_journal_failed(j, exc)
```
