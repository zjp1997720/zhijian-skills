# 原生 Subagent 生命周期

本文件负责 `native_subagent` Surface 的预检、创建、等待、追问和关闭。Thread 生命周期继续由 `thread-lifecycle.md` 与 `thread-supervision-protocol.md` 管理。

## 创建前预检

- 当前 host 必须暴露原生 spawn、wait、send 和 close 能力。
- live `spawn_agent` schema 必须暴露 `model` 与 `reasoning_effort`，并接受 RoutePlan 的精确组合。派遣参数使用 registry 的 `surface_runtime_models.native_subagent`，而 RoutePlan 继续保留逻辑模型 ID；例如逻辑 `gpt-5.6-sol` 在原生 Standard/Fast 分别传 `gpt-5.6-sol-standard` / `gpt-5.6-sol-fast`。禁止静默继承父模型，也禁止把原生别名写进 App `create_thread`。
- Grok 4.6 还必须在当前 host 上通过工具序列探针，且 CLIProxyAPI 不低于 registry 的兼容版本；只通过文本 canary、单次 `pwd` 或 `agent_message` 200 不能证明其适合多工具任务。
- V1 新鲜上下文映射为 `fork_context=false`；V2 新鲜上下文映射为 `fork_turns="none"`。不要仅凭 `multi_agent_v2=true` 推断模型白名单可用。
- 每个任务包包含唯一 task id、完整约束、输出契约、Provider 数据边界和“禁止创建任何后台任务、线程或子 Agent”。

## 控制状态

`PLANNED → SPAWN_PENDING → RUNNING → COMPLETED → CLOSED` 是正常路径。确定失败进入 `FAILED`；返回值、身份或状态无法确认时进入 `UNKNOWN`。

1. 调用 spawn 前递增 root `worker_attempt` 和 `subtask_attempt`，写 `SPAWN_PENDING`。
2. 返回正式 `agent_id` 后把实际派遣参数记为 `runtime_model` 与 `platform_accepted_model`，逻辑模型仍记为 `requested_model/model`；同时记录 `platform_accepted_speed`。这不等于观测到真实运行模型或速度。
3. 只在主流程需要结果时有界等待。完整输出质量不足时，同一正式 Agent 最多追问一次。
4. 主 Agent 验证输出并设置 `adopted=true`。
5. 已完成且已采纳的 Agent 调用 close，成功后进入 `CLOSED` 并释放并发位。

`Unknown model`、reasoning 不支持、Fast tier 被拒绝或白名单为空属于精确组合失败。若 RoutePlan 预声明下一候选，可以沿链继续；否则主 Agent 接管。禁止在失败后临时换 Surface、模型、强度、速度或 Provider。

## 审计

记录遵守 `native-audit-schema.json`。模型使用 `requested_model/runtime_model/platform_accepted_model/observed_runtime_model`，速度使用 `requested_speed/platform_accepted_speed/observed_runtime_speed`；没有可信运行时回显时，对应 observed 字段必须保持 `unknown`。完整结果来自正式 Agent 的 completed message，不能用 task 文本或创建回执代替。
