# Thread 监督协议

本文件是 Codex App Thread 控制状态、排队恢复、断点续跑和归档门的唯一事实源。模型选择、Provider 门与 fallback 仍由 `routing-policy.md`、`provider-policy.md` 和 `recovery-policy.md` 负责。

## 目录

- [事实模型](#事实模型)
- [控制状态](#控制状态)
- [任务身份](#任务身份)
- [创建与排队恢复](#创建与排队恢复)
- [读取与检查点](#读取与检查点)
- [断点续跑](#断点续跑)
- [结果、追问与归档](#结果追问与归档)
- [收尾门](#收尾门)

## 事实模型

把官方工具观察和派生判断分开：

```text
Observed：create_thread 返回值、thread_id、pending_worktree_id、thread_status、turn_status、cwd、last_observed_at
Derived：control_state、materialized、data_ready、adopted、archived
Legacy：status 只作兼容摘要，不是当前状态真相
```

当前状态只由最新成功的 `create_thread`、`list_threads` 和 `read_thread` 观察推导。Worker 文本、旧 ledger 摘要、事件日志、聊天记忆和 pending id 都不能覆盖较新的官方读取。

`DATA_READY` 证明数据面已经开始响应，不证明模型身份、结果质量或任务完成。平台没有回显实际模型时，`observed_runtime_model` 保持 `unknown`。

## 控制状态

| `control_state` | 含义 | 允许动作 |
| --- | --- | --- |
| `PLANNED` | 已写 ledger，尚未调用创建 | 调用一次预声明候选 |
| `CREATION_PENDING` | 调用已发起，或只拿到 `pendingWorktreeId` | 有界查找正式 Thread |
| `CONTROL_READY` | 正式 `thread_id` 可读，实体身份稳定 | 读取、等待 |
| `DATA_READY` | 出现首个 assistant-originated 输出或模型工具调用 | 读取、等待、验收 |
| `COMPLETED` | 官方 turn completed，完整输出已取得 | 主 Agent 验收、采纳、归档 |
| `UNKNOWN` | 创建或恢复结果存在歧义 | 继续官方查证或主 Agent 接管 |
| `FAILED` | 已分类的确定失败 | 沿预声明候选链恢复或主 Agent 接管 |

硬门：

- `UNKNOWN` 禁止 follow-up、归档、fallback 和重复创建。
- `pendingWorktreeId` 不是 `thread_id`，禁止传给 `read_thread`、`send_message_to_thread` 或 `set_thread_archived`。
- 只有正式 `thread_id` 通过读取后才能设置 `materialized=true`。
- 只有 `materialized=true` 才能设置 `data_ready=true`。

## 任务身份

每次 Worker creation attempt 生成唯一 `task_id`，并把它放入：

- ledger Worker 记录；
- 初始任务包首屏；
- `list_threads` 的精确查询；
- 可选 `result_correlation_id`。

同一子任务的 fallback Worker 使用新的 `task_id`，保留相同的子任务语义和递增的 `subtask_attempt`。禁止复用 task id，否则超时恢复可能匹配到旧 Thread。

`result_correlation_id` 只证明结果与任务的关联，不能代替产物、测试和事实核验。

## 创建与排队恢复

调用 `create_thread` 前先递增 root `creation_attempt` 和 subtask attempt，并写入 `PLANNED` 记录。调用开始后更新为 `CREATION_PENDING`。

### 返回正式 `threadId`

1. 立即写回 `thread_id`。
2. 调用 `read_thread`。
3. 能读取 thread、cwd 和 turn 状态后标记 `CONTROL_READY` 与 `materialized=true`。

### 返回 `pendingWorktreeId`

1. 只写入 `pending_worktree_id`，保持 `CREATION_PENDING`。
2. 用唯一 `task_id` 调用 `list_threads(query=task_id)`，不得用 pending id 充当 Thread id。
3. 零匹配：在有界等待窗口内再查；窗口结束仍为零则标记 `UNKNOWN`。
4. 多匹配：立即标记 `UNKNOWN`，禁止按位置挑选。
5. 唯一匹配：调用 `read_thread`，确认初始用户消息含相同 `task_id`。
6. worktree 排队任务要求两次连续官方观察的 `thread_id` 与 `cwd` 一致，再进入 `CONTROL_READY`；任一次变化都重新开始稳定计数。

### 工具调用超时或无返回值

创建可能已经产生外部副作用。用唯一 `task_id` 执行同一套有界 `list_threads` 查找：

- 唯一且稳定的正式 Thread 可以恢复；
- 零匹配或多匹配在窗口结束后保持 `UNKNOWN`；
- 不把“未收到返回值”写成“确定未创建”。

创建歧义已经消耗 creation attempt。`list_threads` 与 `read_thread` 查证不新增 creation attempt。

## 读取与检查点

优先使用可用的 wait 工具做有界等待；需要身份、cwd、turn 或故障证据时使用 `read_thread`。没有 wait 工具时，以克制频率读取，不运行常驻 watcher 或 daemon。

每个检查点至少更新：

```text
thread_status
turn_status
last_observed_at
control_state
```

判断顺序：

1. 最新官方 Thread/turn 状态。
2. 当前 assistant-originated 输出或工具调用。
3. 已验证的工作区产物。
4. 旧状态摘要与 Worker 文本只作诊断。

读取到 active/inProgress 时保持等待。读取到 completed 后提取完整 assistant turn，再由主 Agent 检查产物。读取失败时保留上一次观察并把当前状态标为 `UNKNOWN`，不能用旧的 `done` 文本继续归档。

## 断点续跑

恢复耐久任务时严格按以下顺序：

1. 读取上游账本或 `state.json`，核对 creation attempt、task id、pending id 和正式 thread id。
2. 对 `CREATION_PENDING` 或 `UNKNOWN` 记录按 task id 运行排队恢复；禁止先创建替代 Worker。
3. 对每个正式 thread id 调用 `read_thread`，以最新官方状态重建 `control_state`。
4. 已在 inProgress/active 的 Thread 继续监督，不重复创建。
5. completed 的 Thread 重新提取完整输出并验收。
6. 只有官方证据确认失败后，才沿原 RoutePlan 的下一候选恢复。

无法完成官方查证时保留 `UNKNOWN` 并由主 Agent 接管可继续的本地工作。禁止通过切换 project/projectless、模型或 thinking 猜测性碰撞。

## 结果、追问与归档

完整结果必须来自正式 Thread 的 assistant turn 或任务包声明的工作区产物。`result_correlation_id` 缺失只影响关联可信度，不自动证明结果失败；主 Agent 仍需核对 task id、目标与产物。

完整输出质量不足时，在同一正式 Thread 最多追问一次。`UNKNOWN`、未实体化或只有 pending id 的记录禁止追问。

归档前同时满足：

- `control_state=COMPLETED`；
- `thread_id` 正式且可管理；
- `turn_status=completed`；
- 任务包声明的产物已经主 Agent 验证；
- `adopted=true`；
- Thread 在归档前处于 completed/idle。

归档后可以记录平台返回的 `notLoaded`，但不得用 `notLoaded` 反推归档前状态。归档失败按 `thread-lifecycle.md` 有界重试一次。

## 收尾门

主 Agent 结束当前 turn 前检查：

- 所有 in-flight Worker 都有最新检查点或明确的官方等待机制；
- 没有 `UNKNOWN` 记录被 follow-up、fallback、重复创建或归档；
- completed 结果已经读取完整 assistant turn；
- 已采纳结果完成本地产物验证；
- 未完成、失败与歧义状态已写入可恢复账本；
- 最终汇报区分 requested、platform accepted 与 observed runtime model。

本门是 Codex 的有界前台监督协议，不安装 hook，不创建后台 watcher，也不依赖模型记忆自动重启监督。
