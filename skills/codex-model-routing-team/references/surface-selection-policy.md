# 执行 Surface 选择策略

本 Skill 在模型候选之前先选择执行 Surface。`native_subagent` 与 `app_thread` 都是真实模型路由；它们解决不同的生命周期问题。

## 确定性选择顺序

1. 简单问答、状态查询、单文件小改、强顺序任务和不可逆操作留在主 Agent。
2. 自动路由默认 `app_thread`，优先使用 `gpt-5.6-luna/xhigh/fast`；高难或高风险任务使用 Luna Max Fast。当前 Surface 无 Fast live 证据时改写为 Standard。短时和文件数量不改变模型默认值。
3. 只有用户明确要求原生 Subagent，或 App Thread 路径不可用且 RoutePlan 已预声明 fallback 时，才使用 `native_subagent`。当前官方原生 V2 live schema 不开放 Luna；原生 OpenAI 自动候选只能使用 live schema 接受的 Sol High/XHigh/Max，Terra 仍须用户点名。
4. Surface 缺少精确 live 能力、Provider 门不通过或所有权无法隔离时，进入预声明的下一候选；没有下一候选时由主 Agent 接管。

旧 RoutePlan 候选没有 `surface/speed` 时按 `app_thread/standard` 解释。`schema_version: "2.1"` 的候选规范形状为：

```json
{"surface": "app_thread", "model": "gpt-5.6-luna", "thinking": "xhigh", "speed": "standard"}
```

`thinking` 是策略字段：原生工具映射为 `reasoning_effort`，App Thread 映射为 `thinking`。逻辑模型 ID 先通过 registry 的 `surface_runtime_models` 编译为 Surface 实参；App Sol 是 `gpt-5.6-sol`，原生 Sol Standard/Fast 才是对应别名。Luna 最低 XHigh，Sol 最低 High。`speed=fast` 在 App 映射为 `service_tier=priority`，在原生 Sol 映射为 Fast runtime alias。Luna 默认 Fast，Sol/Terra 默认 Standard，后两者只有用户明确要求时才候选 Fast。所有 Fast 都必须有 live Surface 证据。跨 Surface fallback 必须在 `candidates` 中预声明；`surface + model + thinking + speed` 才是唯一组合。

## 额度

- 一个子任务最多两个候选，`max_worker_threads` 等于候选数。
- 任何已开始的 `spawn_agent` 或 `create_thread` 都消耗一次 root Worker attempt；静态门排除不消耗。
- 默认 `standard` 档跨 Surface 并发 6、root attempts 8、每波 3；有扩容理由、隔离所有权和至少 2 个 reserved slots 的 `expanded` 档上限为 12/16/6。实际 host 更窄时以 live 上限为准。
- 原生 V2 没有 live 上限证据时按“协调者 + 3 个 child”执行；任何更窄 host 上限优先。
- Worker 永不使用 Ultra，永不继续派生 Agent、Thread 或后台任务。

## 模型身份

feature flag、模型 catalog 和文档只提供候选证据。原生候选的 `runtime_evidence` 必须来自当前会话 live spawn schema，与 host/Surface/逻辑模型/runtime model/thinking/speed 绑定并在 10 分钟后失效；Grok 还要包含工具序列探针。App Fast 使用同样期限的 `speed_evidence`。它们是协调器审计证据，不是防篡改凭证。成功调用分别写 `runtime_model/platform_accepted_model/platform_accepted_speed`，平台未回显真实身份或速度时对应 observed 字段保持 `unknown`。
