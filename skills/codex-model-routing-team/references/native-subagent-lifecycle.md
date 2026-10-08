# 原生 Subagent 生命周期

本文件负责 `native_subagent` Surface 的预检、创建、等待、追问和释放。App Thread 生命周期由 `thread-lifecycle.md` 与 `thread-supervision-protocol.md` 管理。

## 创建前预检

- 当前 host 必须暴露 `spawn_agent`、`wait_agent`、`send_message`/follow-up 与 `list_agents`；close/interrupt 只按 live schema 使用。
- live `spawn_agent` schema 必须接受 RoutePlan 的精确 `model`、`reasoning_effort` 与 `fork_turns`。Fast 还必须接受 `service_tier=priority`。禁止静默继承父模型、默认 reasoning 或默认速度来冒充路由成功。
- 新 v3 任务的 fresh context 写 `fork_turns="none"`；少量上下文写正整数字符串。显式模型覆盖禁止 `fork_turns="all"`。旧 V1 工具若仍使用 `fork_context`，只作为 v2.1 run 的兼容映射。
- GPT-6 Luna 的官方能力为 V2；本 Skill 仍将它限制为 leaf Worker，禁止下级派遣。任务包必须独立包含工作目录、目标、约束、输出、Provider 数据边界和“禁止创建任何后台任务、线程或子 Agent”。

## 控制状态

`PLANNED → SPAWN_PENDING → RUNNING → COMPLETED → RELEASED` 是 v3 正常路径。确定失败进入 `FAILED`；返回值、身份或状态无法确认时进入 `UNKNOWN`。旧 ledger 的 `CLOSED` 只作兼容终态。

1. 调用 spawn 前递增 root `worker_attempt` 与 `subtask_attempt`，写 `SPAWN_PENDING`。
2. 返回正式 `agent_id` 后记录 `platform_accepted_model` 与 `platform_accepted_speed`；这不等于观测到真实运行模型或速度。
3. 只在主流程需要结果时有界等待。完整输出质量不足时，对同一正式 Agent 最多追问一次。
4. 主 Agent 验证输出并设置 `adopted=true`。
5. live schema 有正式 close 能力时关闭 Agent；没有 close 时，只有官方状态确认该 turn 已完成且 Agent 为 completed/idle，才用 `release_method: completed_idle` 标记 `RELEASED`。`interrupt` 只能停止仍在运行的 turn，不能伪装成 close。

完成但尚未释放的 Worker 仍占用协调预算。`RELEASED` 记录必须写 `released=true` 与 `release_method=close|completed_idle`。未完成、状态不明或仍有活动 turn 时不得标记释放。

`Unknown model`、reasoning 不支持、fork 范围不支持、Fast tier 被拒绝或白名单为空属于精确组合失败。只有 RoutePlan 预声明下一候选时才能沿链继续；否则由主 Agent 接管。禁止失败后临时换 Surface、模型、强度、速度、上下文范围或 Provider。

## 审计

记录遵守 `native-audit-schema.json`。模型使用 `requested_model/platform_accepted_model/observed_runtime_model`，速度使用 `requested_speed/platform_accepted_speed/observed_runtime_speed`；没有可信回显时 observed 字段保持 `unknown`。完整结果来自正式 Agent 的 completed message，不能用 task 文本、创建回执或 commentary 代替。
