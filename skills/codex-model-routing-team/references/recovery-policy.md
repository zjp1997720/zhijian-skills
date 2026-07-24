# 路由恢复策略

fallback 的目标是让任务可恢复，同时保持模型、数据边界和尝试次数可审计。主 Agent 在派遣前固定 RoutePlan；运行时只能沿有序候选链前进。

## RoutePlan

每个子任务在首次创建前记录：

```json
{
  "task_class": "DEEP_AGENTIC_CODE",
  "risk": "medium",
  "minimum_thinking": "high",
  "provider_allowlist": ["xai", "openai"],
  "provider_status": {"xai": "allowed", "openai": "allowed"},
  "data_allowed_providers": ["xai", "openai"],
  "explicit_user_request": false,
  "risk_acknowledged": false,
  "candidates": [
    {"model": "xai/grok-4.5", "thinking": "high"},
    {"model": "gpt-5.6-sol", "thinking": "high"}
  ],
  "max_worker_threads": 2,
  "max_followups_per_thread": 1
}
```

候选链不能包含循环、Ultra、低于 `minimum_thinking` 的降级，或 Provider 策略不允许的目标。非 blocked 的 manual-only 模型只能出现在用户明确点名的 RoutePlan 首项，不能作为静默 fallback；当前 Gemini Antigravity registry entry 因 terms blocked 会被 validator 拒绝。

concrete RoutePlan 必须通过 `scripts/validate_route_plan.py`。画像名不是执行依据；真正派遣使用验证后的有序 `candidates` 数组。

每次 Worker creation attempt 另外生成唯一 `task_id`。RoutePlan 可以复用，task id 不能复用；fallback Worker 使用新 task id 和递增的 `subtask_attempt`。

## 分层健康

健康判断分为五层：

1. `STATIC_READY`：registry、live runtime、`thinking` 和 Provider 门通过。
2. `PROBE_READY`：可选语义 canary 在当前 provider/model 上精确回显 nonce。
3. `CREATION_PENDING`：调用已发起，或只返回 `pendingWorktreeId`，尚未取得稳定正式 Thread。
4. `CONTROL_READY`：正式 ID 通过 `read_thread`；排队 worktree 还需两次连续官方观察的 thread id/cwd 一致。
5. `DATA_READY`：当前 turn 出现首个 assistant-originated 输出项（reasoning/assistant message）或模型发起的工具调用；用户消息、Thread 元数据和 MCP 初始化错误不计入。完整交付通过验收后才进入 `COMPLETED`。

`DATA_READY` 只证明数据面开始响应，不证明实际模型身份。`read_thread` 没有模型回显时，`observed_runtime_model` 必须保持 `unknown`。

成功缓存只参与候选排序，不保证下一次调用成功。建议在当前 run ledger 中对精确 `account-scope/host/model/thinking/tool-signature/App-version` 保存 10 分钟正向证据；不要为此创建新的全局状态事实源。

## 错误分类

| 类别 | 作用域 | 当前任务动作 | 熔断 |
| --- | --- | --- | --- |
| unsupported model / thinking | 精确 host/model/thinking | 不重试原组合，进入预声明下一候选 | 立即打开，直到目录、App 或策略版本变化 |
| 认证/授权失败 | provider + account | 不在同 provider 重试；进入已授权 provider 或主 Agent 接管 | 立即打开，凭证变化后解除 |
| 429 / 配额不足 | provider/model/account | 遵守 `Retry-After`；当前任务进入下一候选 | 按 `Retry-After`；缺失时初始 10 分钟 |
| 创建超时/实体化歧义 | host + App 初始化链 | 用唯一 task id 有界查询；唯一稳定匹配则恢复，零/多匹配则进入 `UNKNOWN` | 两次近期故障后短暂隔离 |
| MCP 初始化失败 | workspace + tool signature | 必需 MCP 失败时主 Agent 接管或阻塞；可选 MCP 只走预声明无 MCP 路径 | 按工具签名隔离，不归咎全部模型 |
| 代理协议错误 | host/model/protocol version | 不重打同协议路径；进入预声明下一 provider | 立即隔离该协议组合，版本变化后复验 |
| 语义 canary 不匹配 | provider/model/protocol | 原组合复测一次；第二次仍不匹配才进入下一候选 | 连续两次失败后 10 分钟 |
| 完整输出质量不足 | model/thinking/task class | 原 Thread 定向追问一次；仍失败才创建第二 Worker | 不触发基础设施熔断，进入任务类质量隔离 |

质量判断只能发生在获得完整、可解析输出之后。传输、协议、MCP 和会话串线不能记成模型能力失败。

## 两次机会

- 每次调用 `create_thread` 前同时递增 root `creation_attempt` 与 subtask attempt。即使调用超时、没有正式 ID 或 Thread 未实体化，也消耗一次机会。
- 返回正式 ID 后立即写入 ledger；返回 `pendingWorktreeId` 时只写 pending 字段。实体化只更新观察与派生状态，不改变 attempt 计数。
- 每个子任务最多发起两次 Worker creation attempt，替换任务也计入根任务上限 8。
- `UNKNOWN` 记录先按 `thread-supervision-protocol.md` 继续官方查证；查证完成前禁止 fallback 或第二次创建。
- 同一精确组合在同一子任务中最多创建一次；语义 canary 的一次复测不占 App Thread 槽位，但消耗 provider 配额并记录在审计中。
- 完整输出需要纠正时复用原 Thread，最多发送一次 follow-up。
- 模型、provider 或 `thinking` 改变时创建新 Thread，并使用候选链中的下一项。
- 第二 Worker 仍失败时由主 Agent 接管或明确报告阻塞，禁止继续试第三个模型。

## 禁止行为

- 失败后临时选择“当前看起来最健康”的任意模型。
- 对同一组合进行无界重试。
- 静默降低 `thinking` 或扩大 provider allowlist。
- MCP 初始化失败后连续更换模型。
- 为每个候选创建空 App Thread canary。
- 把 `pendingWorktreeId` 传给 read/send/archive，或在零/多匹配时按列表位置挑 Thread。
- 在 `UNKNOWN` 状态继续 fallback、重复创建、追问或归档。
- 把一次成功缓存当作实时配额保证。
