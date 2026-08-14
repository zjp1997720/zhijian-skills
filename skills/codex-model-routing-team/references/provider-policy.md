# Provider 策略

模型能力与接入资格是两件事。模型注册表回答“这个模型擅长什么”；本文件回答“当前任务的数据能否发给这个 provider，以及当前凭证路径是否允许自动使用”。Provider 门先于速度、质量和配额排序。

## 通用硬门

创建 RoutePlan 前记录：

- `data_class`：`public`、`internal`、`confidential` 或项目自定义等级。
- `provider_allowlist`：当前任务允许使用的 provider。
- `credential_path`：官方 API、官方客户端、受支持 OAuth 集成或未知代理。
- `terms_status`：`allowed`、`manual_review`、`blocked`、`unknown`。
- `quota_signal`：已知余额/重置时间，或 `unknown`。

出现以下任一情况时，候选不得进入自动路由：

- provider 不在任务 allowlist。
- 项目规则禁止把当前数据发给该 provider。
- 凭证来源或条款状态为 `blocked`。blocked 永远不能由用户确认覆盖。
- 条款状态为 `unknown` 时尚未完成核验；必须先解析成 `allowed` 或 `manual_review`。
- 订阅账号只证明产品可登录，没有证明第三方代理或 API 路径被授权。

跨 provider fallback 必须在派遣前写入候选链。运行时不得因为某个模型更快而临时扩大数据发送范围。

## OpenAI 基线

`gpt-5.6-luna` 与 `gpt-5.6-sol` 使用当前 Codex App 已配置的 OpenAI 路径。自动路由默认创建 Luna XHigh App Thread，高难/高风险升 Luna Max；当前官方原生 V2 live schema 不开放 Luna。Sol 仅作为 High 以上的显式原生路径、fallback 或专项审查。Luna 默认请求 Fast；Sol/Terra 默认 Standard。App Fast 需要 live schema 接受 `service_tier=priority`，原生 Sol Fast 需要 live schema 接受 `gpt-5.6-sol-fast` runtime model。当前项目若有更窄的数据规则，以项目规则为准。

## xAI / Grok 4.6

`grok-4.6` 是显式 opt-in 候选，不进入自动候选或静默 fallback：

- live runtime 必须列出精确 ID 与所选 `thinking`。
- 当前 host 必须使用 CLIProxyAPI `7.2.130` 或更新版本，并同时通过 `probe-multi-agent` 与有序双命令工具探针；旧版 Responses 工具状态故障不能归因为 Grok 不会用工具。
- 当前 xAI 凭证或订阅路径必须允许该客户端使用；某些官方支持的第三方集成不能外推为“任意代理都被授权”。
- 订阅周池、API rate limit 和瞬时容量不能视为 SLA。没有余额接口时，把 quota 记为 `unknown`，依靠首个业务 Worker 和 429 分类处理。
- confidential 数据只有在项目 allowlist 明确包含 xAI 时才能发送。

官方参考：[xAI 模型目录](https://docs.x.ai/developers/models)、[xAI Responses API 发布说明](https://docs.x.ai/developers/release-notes)。本地 `grok-4.6` 路由能力以 live `/models` 与 Codex 探针为准，不把订阅产品名称外推成公开 API 保证。

## 审计字段

每次跨 provider 路由至少记录：

```text
model
requested_model
runtime_model
platform_accepted_model
observed_runtime_model
requested_speed
platform_accepted_speed
observed_runtime_speed
provider
credential_path
terms_status
data_class
provider_allowlist
quota_signal
```

`model` 保持为 `requested_model` 的兼容别名。平台没有回显真实运行模型或速度时，对应 observed 字段记为 `unknown`，不能用请求值代填。
