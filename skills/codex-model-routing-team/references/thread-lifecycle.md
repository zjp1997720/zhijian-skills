# App Thread 生命周期

本文件只负责 `app_thread` Surface 的创建前预检、运行读取和故障/归档入口。原生路径见 [原生 Subagent 生命周期](native-subagent-lifecycle.md)。Thread 控制状态、排队恢复、稳定观察、断点续跑与收尾门统一遵守 [Thread 监督协议](thread-supervision-protocol.md)。

## 创建前检查

- 确认 `codex_app__list_projects`、`codex_app__create_thread`、`codex_app__list_threads`、`codex_app__read_thread`、`codex_app__send_message_to_thread` 和 `codex_app__set_thread_archived` 可用。
- 从 `model-registry.json`、`routing-policy.md` 和 `provider-policy.md` 取得精确 `model`、`thinking`、`speed`、候选链与 Provider 门。
- live `create_thread` 工具元数据只验证当前 host 接受性，不能覆盖 registry 的 automatic/manual-only 策略。没有显式速度参数时 App Thread 只能按 Standard 路由；Fast 必须有 `speed_evidence`。
- App `create_thread` 必须使用 registry 的 `surface_runtime_models.app_thread` 精确 ID。Sol 一律传原生 `gpt-5.6-sol`；`gpt-5.6-sol-standard` / `gpt-5.6-sol-fast` 仅属于原生 Subagent Surface。
- 任务包声明任何工作区输出路径时，先用 `list_projects` 取得匹配 `projectId` 并使用 project local；纯聊天交付才可 projectless。
- 为每次 creation attempt 生成唯一 `task_id`，写入 ledger 和任务包。

## 分层预检

### Registry 与 runtime

Skill 包提供无依赖静态检查器：

```bash
python3 scripts/model_preflight.py \
  --surface app_thread \
  --model grok-4.6 \
  --thinking high \
  --runtime-confirmed \
  --tool-probe-confirmed \
  --proxy-version 7.2.130 \
  --explicit-user-request \
  --host <host> \
  --provider-status allowed \
  --data-allowed
```

`--runtime-confirmed` 只能在主 Agent 已从当前 host 的 live 工具元数据确认精确组合后传入。Fast 还必须传 `--speed fast --service-tier-confirmed --host <host>`。原生 Surface 会输出绑定 host/model/thinking/speed/checked_at 的 `runtime_evidence`；App Fast 输出 `speed_evidence`。Responses 语义 probe 不能替代 live schema 证据。缺少 live/provider/data 任一证据时，脚本返回 `unknown` 或 `manual_review`。

本地 catalog 只作诊断；registry 决定策略允许范围，live runtime 决定当前 host 是否接受组合。Gemini Antigravity 当前 terms blocked，显式点名也不能覆盖 Provider 门。

### 可选语义 canary

只有环境提供兼容 Responses API 的 loopback 地址与专用凭证环境变量时才运行：

```bash
python3 scripts/model_preflight.py \
  --surface app_thread \
  --model grok-4.6 \
  --thinking high \
  --provider-status allowed \
  --data-allowed \
  --probe-url http://127.0.0.1:8317/v1/responses \
  --auth-env CLI_PROXY_API_KEY
```

脚本只允许 loopback endpoint、禁止重定向、限制响应体，并且不打印凭证或模型正文。没有专用凭证或 endpoint 时跳过；禁止读取、复制或猜测 Codex 内部认证材料。

首次语义不匹配只记 transient，原组合复测一次；连续两次失败才按 `recovery-policy.md` 打开短期熔断。

### 首个真实业务 Worker

禁止创建空 Thread 探针。每个新 `host/model/thinking/speed/tool-signature` 的第一个有业务价值 Worker 兼作最终数据面探针；它达到 `DATA_READY` 后，才释放同组合后续任务。一个模型或速度组合的健康不能外推到另一个组合。

concrete RoutePlan 在派遣前写成 JSON 并验证：

```bash
python3 scripts/validate_route_plan.py /path/to/route-plan.json
```

## 创建与实体化

1. 调用 `create_thread` 前递增 root worker attempt、兼容字段 creation attempt 与 subtask attempt，写入 `surface: app_thread`、`thread_id: null`、`pending_worktree_id: null`、`control_state: PLANNED` 的完整审计记录。
2. 调用开始时更新为 `CREATION_PENDING`，显式传入任务包、runtime model、thinking 和目标环境；只有 live schema 已证明速度参数时才传 Fast，否则使用 Standard。
3. `create_thread` 若拒绝显式模型或 thinking，把它分类为该精确组合失败；只能进入派遣前声明的下一候选或由主 Agent 接管。绝对不能删掉 `model/thinking` 重试，因为省略字段会继承用户默认模型，可能把 Sol 任务静默变成 DeepSeek。
4. 返回 `threadId`、`pendingWorktreeId`、超时或未知形状时，严格按 `thread-supervision-protocol.md` 分类和恢复。
5. `pendingWorktreeId` 不是正式 Thread id；只有唯一 task id 查询、正式读取和稳定观察通过后才进入 `CONTROL_READY`。
6. 当前 turn 出现首个 assistant-originated reasoning/message 或模型工具调用时进入 `DATA_READY`。user message、Thread 元数据、客户端提示和 MCP 初始化错误不计入。
7. 同组合探针通过后按 TeamPlan 档位新增任务：`standard` 每波最多 3 个，具备扩容理由且 live host 容量允许的 `expanded` 每波最多 6 个，防止新会话同时初始化 MCP 造成拥塞。

`DATA_READY` 与模型/速度身份分开；没有真实回显时，`observed_runtime_model` 与 `observed_runtime_speed` 保持 `unknown`。

零/多匹配、读取失败和创建结果歧义进入 `UNKNOWN`。`UNKNOWN` 不 follow-up、不归档、不 fallback、不重复创建；先继续官方查证或由主 Agent 接管。

## 运行与读取

- 优先使用可用的 wait 工具做有界等待；需要完整身份、cwd、turn 和故障证据时使用 `read_thread`。
- 每个检查点更新 `thread_status / turn_status / last_observed_at / control_state`。
- 最新官方读取覆盖旧 `status` 摘要和 Worker 文本。
- 看到完整 final answer 后确认 turn completed，再由主 Agent 验证工作区产物。
- 完整输出质量不足时只在同一个正式 Thread 追问一次；切换模型或 thinking 时创建候选链中的第二 Worker。
- 恢复耐久任务时先重建官方当前状态，再决定是否创建；详见监督协议的断点续跑顺序。

## 归档

- 只归档正式 Thread，且必须满足 `COMPLETED`、turn completed、产物已验证、结果已采纳、归档前 completed/idle。
- 逐个调用 `set_thread_archived` 并等待成功，禁止并行连发。
- 归档失败时先 `read_thread`；Thread 仍存在且 idle 时只重试一次。
- pending id、未实体化和 `UNKNOWN` 记录禁止归档；禁止直接修改 Codex 数据库。

## 已知启动阻塞

新任务会初始化当前启用的 MCP。某个 MCP 的鉴权或启动持续失败时，按 workspace/tool signature 处理；先修复、禁用故障 MCP 或走预声明无 MCP 路径，不通过连续换模型验证运气。
