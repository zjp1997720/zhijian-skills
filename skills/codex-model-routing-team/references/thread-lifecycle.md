# 后台任务生命周期

## 创建前检查

- 确认 `codex_app__list_projects`、`codex_app__create_thread`、`codex_app__read_thread`、`codex_app__send_message_to_thread` 和 `codex_app__set_thread_archived` 可用。
- 从 `model-registry.json`、`routing-policy.md` 和 `provider-policy.md` 取得精确 `model`、`thinking`、候选链与 Provider 门。
- live `create_thread` 工具元数据是当前 host 对模型/`thinking` 的运行声明；它用于验证 RoutePlan，不能覆盖 registry 的 automatic/manual-only 策略。
- `${CODEX_HOME:-$HOME/.codex}/models_cache.json` 常只覆盖 OpenAI catalog。自定义 Provider 可检查 `${CODEX_HOME:-$HOME/.codex}/cliproxyapi-catalog.json`；其他 catalog 只作诊断，不能替代 live runtime。
- 任务包声明任何工作区输出路径时，先用 `codex_app__list_projects` 取得匹配 `projectId` 并使用 project local。只有纯聊天交付才能 projectless。

## 分层预检

### 1. Registry 与 runtime

Skill 包提供无依赖静态检查器：

```bash
python3 scripts/model_preflight.py \
  --model xai/grok-4.5 \
  --thinking high \
  --catalog "${CODEX_HOME:-$HOME/.codex}/cliproxyapi-catalog.json" \
  --runtime-confirmed \
  --provider-status allowed \
  --data-allowed
```

`--runtime-confirmed` 只能在主 Agent 已从当前 host 的 live 工具元数据确认精确组合后传入。缺少 live/provider/data 任一证据时，脚本返回 `route_status: unknown` 或 `manual_review`，不会把 registry/catalog 局部检查误报为最终可路由。

Gemini Antigravity 的 manual review 需要 `--explicit-user-request --risk-acknowledged`，但其 registry `terms_default` 当前为 blocked，脚本仍会拒绝；显式点名不能覆盖 Provider 硬门。

如果本地 catalog 不存在，使用 registry + live 工具元数据完成静态检查，不因缺少诊断文件自动判失败。catalog 与 live 元数据冲突时，以 live runtime 的当前 host 接受性决定“能否创建”，以 registry 决定“是否允许自动创建”。

### 2. 可选语义 canary

环境提供兼容 Responses API 的本地代理地址与专用凭证环境变量时，可在创建 App Thread 前运行：

```bash
python3 scripts/model_preflight.py \
  --model xai/grok-4.5 \
  --thinking high \
  --provider-status allowed \
  --data-allowed \
  --probe-url http://127.0.0.1:8317/v1/responses \
  --auth-env CLI_PROXY_API_KEY
```

脚本只允许 loopback endpoint，禁止 HTTP 重定向，把响应体限制为 64 KiB；它发送随机 nonce，并只返回哈希与匹配结果，不打印凭证或模型正文。语义 canary 消耗 provider 配额，但不占后台 Thread 的 8 个 creation-attempt 槽位；同一精确组合在 10 分钟健康窗口内不重复运行。没有专用凭证或 endpoint 时跳过，不读取、复制或猜测 Codex 内部认证材料。

首次语义不匹配只记为 transient，并原组合复测一次。连续两次失败才按 `recovery-policy.md` 打开短期熔断。HTTP 成功但 nonce 不匹配不能标记为健康。

### 3. 首个真实业务 Worker

禁止为每个候选创建空 App Thread。每个新 `host/model/thinking/tool-signature` 的第一个有业务价值的 Worker 兼作最终探针；它通过 `DATA_READY` 后，才释放同组合后续任务。一个 Luna 探针不能证明 Grok 或 Gemini 可用。

concrete RoutePlan 在派遣前写成 JSON，并运行：

```bash
python3 scripts/validate_route_plan.py /path/to/route-plan.json
```

## 实体化与数据面门

1. 调用 `create_thread` 前递增 root `creation_attempt` 和 subtask attempt，检查仍不超过 8/2，并按 `audit-schema.json` 写入 `thread_id: null` 的 ledger 记录。
2. 调用 `create_thread`，显式传入完整任务包、RoutePlan 当前候选的 `model` / `thinking` 和目标环境。
3. 工具返回正式 `threadId` 后立即写入 ledger；调用超时或无 ID 也保留 attempt 记录。
4. 立即调用 `read_thread`。能读到 thread、cwd 和 turn 状态，即进入 `CONTROL_READY` 并标记 `materialized=true`；turn 仍为 inProgress 或 items 暂时为空可以继续有界等待。
5. 当前 turn 出现首个 assistant-originated reasoning/assistant message，或模型发起的工具调用时进入 `DATA_READY`。user message、Thread 元数据、客户端提示和 MCP 初始化错误不计入；先工具调用可以计入。
6. `DATA_READY` 与模型身份分开：没有真实模型回显时，`observed_runtime_model` 保持 `unknown`。只有到达 DATA_READY，才把近期正向数据面证据用于同组合后续任务。
7. 同组合探针通过后，每波最多新增 3 个任务，防止多个新会话同时初始化 MCP 导致启动拥塞。

以下响应都视为创建失败：工具超时且没有正式 `threadId`；`read_thread` 返回 `not materialized yet`；恢复时报 `no rollout found`；任务不在正常列表且没有 rollout。

首个组合创建失败时停止该组合的批量释放。项目模式与 projectless 会经过相同的新会话初始化链，禁止把切换目标类型当作重试。无 ID、未实体化和 fallback 都已消耗 creation attempt；按恢复策略判断是进入预声明下一候选，还是由主 Agent 接管，不得随机换模型。

健康组合中的单个后续 Worker 失败不取消其他已实体化 Worker。保留成功结果，把失败项写入上游账本，再按错误类别处理。

## 运行与读取

- 优先使用 `wait_threads` 做有界状态等待；实体化门和故障诊断需要完整状态时使用 `read_thread`。轮询保持克制。
- 看到 final answer 后再确认 turn 为 completed、thread 为 idle。
- 完整输出质量不足时只在同一个正式 `threadId` 追问一次，并保持原模型与推理强度。
- 需要切换模型或 `thinking` 时创建候选链中的第二 Worker；不把模型切换伪装成同 Thread 追问。
- 不把未实体化 ID 交给 `send_message_to_thread`。

## 归档

- 只归档已实体化、completed/idle、输出文件已由主 Agent 验证且结果已采纳的轻量任务。
- 逐个调用 `set_thread_archived` 并等待成功响应，禁止并行连发归档请求。
- 归档失败时先 `read_thread`：任务仍存在且 idle 时仅重试一次；不存在 rollout 时停止，不再制造错误弹窗。
- 未实体化 ID 只存在于客户端临时状态，后端没有可删除或归档的任务。禁止直接写 SQLite；它会在 Codex 窗口重新加载或应用重启后消失。

## fork 应急路径

`fork_thread` 可以创建有真实 rollout 的子任务，再用 `send_message_to_thread` 显式切换模型与 thinking。它会复制源任务的已完成历史，可能显著放大上下文和 Token 成本。仅当源历史很短、继承上下文有明确收益、且 `create_thread` 暂时不可用时使用；否则由主 Agent 接管。

## 已知启动阻塞

新任务会初始化当前启用的 MCP。某个 MCP 的鉴权发现或启动持续失败时，`create_thread` 可能在首条消息写入前超时并留下客户端空壳。MCP 故障以 workspace/tool signature 为作用域；先修复、禁用故障 MCP 或走预声明的无 MCP 路径，不通过连续换模型验证运气。
