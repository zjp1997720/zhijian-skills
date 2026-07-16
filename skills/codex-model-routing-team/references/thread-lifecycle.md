# 后台任务生命周期

## 创建前检查

- 确认 `codex_app__create_thread`、`codex_app__read_thread` 和 `codex_app__set_thread_archived` 可用。
- 从 `references/routing-policy.md` 取得精确 `model` 与 `thinking`。如需核对本地目录，读取 `${CODEX_HOME:-~/.codex}/models_cache.json`，不要写死用户名路径。
- 工具描述中的模型列表属于接口元数据；路由策略是本 Skill 的模型事实源。
- 用第一个真实 Worker 兼作健康探针，禁止先批量创建空测试任务。
- 任务包声明任何工作区输出路径时，先用 `codex_app__list_projects` 取得匹配的 `projectId` 并使用 project local。只有纯聊天交付才能 projectless。

## 实体化门

1. 调用 `create_thread`，显式传入任务包、路由策略规定的 `gpt-5.6-luna` / `gpt-5.6-sol`、对应 `thinking` 和目标环境。
2. 必须等工具返回正式 `threadId`。
3. 立即调用 `read_thread`。能读到 thread、cwd 和 turn 状态，即视为已实体化；turn 仍为 inProgress 或 items 暂时为空均可继续等待。
4. 只有通过实体化门后，才把该任务计入 Worker 清单、累计创建数和耐久模式 `state.json`。
5. 健康探针通过后，每波最多新增 3 个任务，防止多个新会话同时初始化 MCP 导致启动拥塞。

以下响应都视为创建失败：工具超时且没有正式 `threadId`；`read_thread` 返回 `not materialized yet`；恢复时报 `no rollout found`；任务不在正常列表且没有 rollout。

创建失败后立即停止同一批次。项目模式与 projectless 会经过相同的新会话初始化链，禁止把切换目标类型当作重试。主 Agent 本地接管并报告启动故障。

如果错误明确指向 Luna / Sol 模型不可用或推理强度不兼容，报告本地模型目录与 App 运行时不一致。禁止换成旧模型继续派遣。

健康探针通过后，单个后续 Worker 失败不取消已经实体化的健康 Worker。保留成功结果，把失败项记录到上游任务账本，再按一次追问、一次升级或主 Agent 接管处理。

## 运行与读取

- 轮询频率保持克制；看到 final answer 后再确认 turn 为 completed、thread 为 idle。
- 追问只使用同一个正式 `threadId`，并保持原模型与推理强度；确需升级时显式传入新值。
- 不把未实体化 ID 交给 `send_message_to_thread`。

## 归档

- 只归档已实体化、completed/idle、输出文件已由主 Agent 验证且结果已采纳的轻量任务。
- 逐个调用 `set_thread_archived` 并等待成功响应，禁止并行连发归档请求。
- 归档失败时先 `read_thread`：任务仍存在且 idle 时仅重试一次；不存在 rollout 时停止，不再制造错误弹窗。
- 未实体化 ID 只存在于客户端临时状态，后端没有可删除或归档的任务。禁止直接写 SQLite；它会在 Codex 窗口重新加载或应用重启后消失。

## fork 应急路径

`fork_thread` 可以创建有真实 rollout 的子任务，再用 `send_message_to_thread` 显式切换模型与 thinking。它会复制源任务的已完成历史，可能显著放大上下文和 Token 成本。仅当源历史很短、继承上下文有明确收益、且 `create_thread` 暂时不可用时使用；否则由主 Agent 接管。

## 已知启动阻塞

新任务会初始化当前启用的 MCP。某个 MCP 的鉴权发现或启动持续失败时，`create_thread` 可能在首条消息写入前超时并留下客户端空壳。先修复或禁用故障 MCP，再恢复路由；不要通过重复创建验证运气。
