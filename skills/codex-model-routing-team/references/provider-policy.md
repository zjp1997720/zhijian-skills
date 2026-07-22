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

`gpt-5.6-luna` 与 `gpt-5.6-sol` 使用当前 Codex App 已配置的 OpenAI 路径。它们是本 Skill 的默认基线，但仍需通过 live runtime 的模型/`thinking` 接受性检查。当前项目若有更窄的数据规则，以项目规则为准。

## xAI / Grok 4.5

`xai/grok-4.5` 是条件自动候选：

- live runtime 必须列出精确 ID 与所选 `thinking`。
- 当前 xAI 凭证或订阅路径必须允许该客户端使用；某些官方支持的第三方集成不能外推为“任意代理都被授权”。
- 订阅周池、API rate limit 和瞬时容量不能视为 SLA。没有余额接口时，把 quota 记为 `unknown`，依靠首个业务 Worker 和 429 分类处理。
- confidential 数据只有在项目 allowlist 明确包含 xAI 时才能发送。

官方参考：[Grok 4.5 文档](https://docs.x.ai/developers/grok-4-5)、[Grok 使用与周配额说明](https://docs.x.ai/grok/faq)。

## Google Antigravity / Gemini 3.6 Flash

`antigravity/gemini-3.6-flash` 默认 `manual_only`，不进入自动候选或 fallback。Google Antigravity 官方 FAQ 明确表示，通过第三方软件、工具或服务使用 Antigravity 登录违反其服务条款，并可能导致账号暂停或终止，因此第三方登录路径的 `terms_status` 应记为 `blocked`，不能靠风险确认改成 allowed。

因此：

- 模型在 Codex App 中可运行，不代表该第三方登录路径适合自动化或生产使用。
- 用户点名、单独确认风险和当前任务数据允许发送只是 manual review 的必要条件；若实际 credential path 属于官方明确禁止的第三方登录，仍不得创建。
- 对未来非 blocked 的 manual-only Gemini 路径，显式请求也只适用于本次 RoutePlan，不建立长期健康或合规结论。当前 blocked Antigravity 路径不会因此解锁。
- 更稳的自动化路径是使用 AI Studio、Gemini API 或 Vertex 的正式凭证。新增正式路径时，为其建立新的精确 registry entry，不覆盖或伪装现有 `antigravity/...` ID。

官方参考：[Google Antigravity FAQ](https://antigravity.google/docs/faq)、[Gemini 3.6 Flash 模型页](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash)、[Antigravity Plans](https://antigravity.google/docs/plans)。

## 审计字段

每次跨 provider 路由至少记录：

```text
model
requested_model
platform_accepted_model
observed_runtime_model
provider
credential_path
terms_status
data_class
provider_allowlist
quota_signal
```

`model` 保持为 `requested_model` 的兼容别名。平台没有回显真实运行模型时，`observed_runtime_model` 记为 `unknown`，不能用请求值代填。
