# 路由恢复策略

fallback 的目标是让任务可恢复，同时保持模型、数据边界和尝试次数可审计。主 Agent 在派遣前固定 RoutePlan；运行时只能沿有序候选链前进。

## RoutePlan

每个子任务在首次创建前记录：

```json
{
  "schema_version": "2.1",
  "task_class": "DEFAULT_GENERAL",
  "risk": "medium",
  "minimum_thinking": "high",
  "provider_allowlist": ["openai"],
  "provider_status": {"openai": "allowed"},
  "data_allowed_providers": ["openai"],
  "explicit_user_request": false,
  "risk_acknowledged": false,
  "candidates": [
    {"surface": "app_thread", "model": "gpt-5.6-luna", "thinking": "xhigh", "speed": "standard"},
    {"surface": "app_thread", "model": "gpt-5.6-sol", "thinking": "high", "speed": "standard"}
  ],
  "max_worker_threads": 2,
  "max_followups_per_thread": 1
}
```

`max_worker_threads` 必须等于已声明候选数：只有一个候选且失败后由主 Agent 接管时写 `1`；声明一个 fallback 候选时写 `2`。它不能为未来未声明的模型预留空位。旧计划省略版本/`surface/speed` 时兼容解释为 legacy App Thread Standard；新计划必须显式写 `schema_version: "2.1"`、Surface 和 speed。

候选链不能包含循环、Ultra、低于 `minimum_thinking` 的降级，或 Provider 策略不允许的目标。opt-in 模型只能出现在用户明确点名的 RoutePlan 首项，不能作为静默 fallback；AntiGravity 已从 registry 删除。

concrete RoutePlan 必须通过 `scripts/validate_route_plan.py`。画像名不是执行依据；真正派遣使用验证后的有序 `candidates` 数组。

每次 Worker attempt 另外生成唯一 `task_id`。RoutePlan 可以复用，task id 不能复用；fallback Worker 使用新 task id、递增的 `subtask_attempt` 和新的 Surface 生命周期记录。

## 分层健康

App Thread 健康判断分为五层：

1. `STATIC_READY`：registry、live runtime、`thinking`、`speed` 和 Provider 门通过。
2. `PROBE_READY`：可选语义 canary 在当前 provider/model 上精确回显 nonce。
3. `CREATION_PENDING`：调用已发起，或只返回 `pendingWorktreeId`，尚未取得稳定正式 Thread。
4. `CONTROL_READY`：正式 ID 通过 `read_thread`；排队 worktree 还需两次连续官方观察的 thread id/cwd 一致。
5. `DATA_READY`：当前 turn 出现首个 assistant-originated 输出项（reasoning/assistant message）或模型发起的工具调用；用户消息、Thread 元数据和 MCP 初始化错误不计入。完整交付通过验收后才进入 `COMPLETED`。

`DATA_READY` 只证明数据面开始响应，不证明实际模型或速度身份。`read_thread` 没有对应回显时，`observed_runtime_model` 与 `observed_runtime_speed` 必须保持 `unknown`。

成功缓存只参与候选排序，不保证下一次调用成功。建议在当前 run ledger 中对精确 `account-scope/host/surface/model/thinking/speed/tool-signature/App-version` 保存 10 分钟正向证据；不要为此创建新的全局状态事实源。

原生 Subagent 使用更短的控制面：`PLANNED → SPAWN_PENDING → RUNNING → COMPLETED/FAILED → CLOSED`。它只用于显式请求或预声明 fallback，live spawn schema 必须接受精确 `runtime_model/reasoning_effort/speed`。当前 Luna 不在官方原生 V2 live schema 中；Sol 必须 High 以上，Standard/Fast 分别使用 registry 的原生别名。Grok 4.6 必须显式请求且通过工具序列门。V1 使用 `fork_context=false`，V2 使用 `fork_turns="none"`。返回 agent id 只证明 Worker 已创建；平台未回显实际模型或速度时，对应 observed 字段仍写 `unknown`。详见 [原生 Subagent 生命周期](native-subagent-lifecycle.md)。

## 错误分类

| 类别 | 作用域 | 当前任务动作 | 熔断 |
| --- | --- | --- | --- |
| unsupported model / thinking / speed | 精确 host/surface/model/thinking/speed | 不重试原组合，进入预声明下一候选 | 立即打开，直到目录、App 或策略版本变化 |
| 认证/授权失败 | provider + account | 不在同 provider 重试；进入已授权 provider 或主 Agent 接管 | 立即打开，凭证变化后解除 |
| 429 / 配额不足 | provider/model/account | 遵守 `Retry-After`；当前任务进入下一候选 | 按 `Retry-After`；缺失时初始 10 分钟 |
| 创建超时/实体化歧义 | host + App 初始化链 | 用唯一 task id 有界查询；唯一稳定匹配则恢复，零/多匹配则进入 `UNKNOWN` | 两次近期故障后短暂隔离 |
| MCP 初始化失败 | workspace + tool signature | 必需 MCP 失败时主 Agent 接管或阻塞；可选 MCP 只走预声明无 MCP 路径 | 按工具签名隔离，不归咎全部模型 |
| 代理协议错误 | host/model/protocol version | 不重打同协议路径；进入预声明下一 provider | 立即隔离该协议组合，版本变化后复验 |
| 工具参数/类型错误 | host/model/proxy version/tool signature | 先升级或回退代理版本并重跑有序工具探针；仍失败则进入下一候选 | 版本变化或完整工具探针通过后解除 |
| 语义 canary 不匹配 | provider/model/protocol | 原组合复测一次；第二次仍不匹配才进入下一候选 | 连续两次失败后 10 分钟 |
| 完整输出质量不足 | model/thinking/task class | 原 Thread 定向追问一次；仍失败才创建第二 Worker | 不触发基础设施熔断，进入任务类质量隔离 |

原生 spawn 返回 `Unknown model`、不接受 `reasoning_effort` 或缺少显式模型字段时，归入第一类。它证明当前精确原生组合不可用，不证明同模型的 App Thread 组合不可用。跨 Surface fallback 必须已经出现在 RoutePlan 中。

质量判断只能发生在获得完整、可解析输出之后。传输、协议、MCP 和会话串线不能记成模型能力失败。

## 两次机会

- 每次创建 Worker 前同时递增 root `worker_attempt` 与 subtask attempt。原生 spawn 使用自己的 attempt 记录；每次调用 `create_thread` 前还递增兼容字段 `creation_attempt`。即使调用超时、没有正式 ID、Thread 未实体化或原生 spawn 被拒绝，也消耗一次机会。
- 返回正式 ID 后立即写入 ledger；返回 `pendingWorktreeId` 时只写 pending 字段。实体化只更新观察与派生状态，不改变 attempt 计数。
- 每个子任务最多发起两次 Worker attempt，跨 Surface 替换也计入根任务上限 8。
- `UNKNOWN` 记录先按 `thread-supervision-protocol.md` 继续官方查证；查证完成前禁止 fallback 或第二次创建。
- 同一精确 `surface/model/thinking/speed` 组合在同一子任务中最多创建一次；语义 canary 的一次复测不占 Worker 槽位，但消耗 Provider 配额并记录在审计中。
- 完整输出需要纠正时复用原 Worker，最多发送一次 follow-up。
- Surface、模型、Provider、`thinking` 或 `speed` 改变时创建新 Worker，并使用候选链中的下一项。
- 第二 Worker 仍失败时由主 Agent 接管或明确报告阻塞，禁止继续试第三个模型。
- 原生结果被采纳前必须确认完整输出；采纳后必须关闭 agent 并写 `CLOSED`。App Thread 的采纳、保留与归档仍遵守 Thread 监督协议。

## 禁止行为

- 失败后临时选择“当前看起来最健康”的任意模型。
- `create_thread` 拒绝显式模型或 thinking 后删掉字段重试；省略会继承用户默认模型，造成不可审计的静默换模。
- 对同一组合进行无界重试。
- 静默降低 `thinking` 或扩大 provider allowlist。
- 绕过 RoutePlan 临时打开 Fast，或把请求/接受的 Fast 冒充 observed Fast。
- MCP 初始化失败后连续更换模型。
- 为每个候选创建空 App Thread canary。
- 原生 spawn 不支持精确组合后静默继承父 Agent 的模型或推理强度。
- 把 `gpt-5.6-terra` 放在 fallback 位置，或在没有用户明确点名时自动使用。
- 把 `pendingWorktreeId` 传给 read/send/archive，或在零/多匹配时按列表位置挑 Thread。
- 在 `UNKNOWN` 状态继续 fallback、重复创建、追问或归档。
- 把一次成功缓存当作实时配额保证。
