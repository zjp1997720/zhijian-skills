# RoutePlan 编译器接口

`scripts/compile_route_plan.py` 是只读的 stdlib 辅助。它不调用 `spawn_agent`、`create_thread` 或任何外部服务；只把紧凑输入展开为 RoutePlan，调用现有 `scripts/validate_route_plan.py`，并返回可供主 Agent 审核的 dispatch 参数。

编译结果使用 `schema_version: "3.0"`，包含 `surface_intent`、候选精确组合与原样保留的 live evidence。

## 输入

默认从 stdin 读取一个 JSON 对象，也可把 JSON 文件作为唯一位置参数。最小输入要明确数据边界和当前 live 能力：

```json
{
  "workload": "routine",
  "risk": "normal",
  "task_contract": {"decision_state": "specified", "acceptance": "按指定来源逐项核对输出，并运行目标模块测试"},
  "surface_intent": "parent_integrated",
  "provider_allowlist": ["openai"],
  "provider_status": {"openai": "allowed"},
  "data_allowed_providers": ["openai"],
  "explicit_user_request": false,
  "risk_acknowledged": false,
  "live_evidence": [
    {"kind": "live_spawn_schema", "surface": "native_subagent", "model": "gpt-6-luna", "thinking": "xhigh", "fork_turns": "none", "accepted": true, "host": "current-host", "checked_at": "<当前 ISO-8601>"},
    {"kind": "live_spawn_schema", "surface": "native_subagent", "model": "gpt-6.1-sol", "thinking": "medium", "fork_turns": "none", "accepted": true, "host": "current-host", "checked_at": "<当前 ISO-8601>"}
  ]
}
```

`task_contract.decision_state` 表示关键方案和判断是否已确定；`acceptance` 必须是非空的具体验收方法。自动选路缺少合同即拒绝；新 v3 Luna 候选（含显式 routes、App 和 fallback）必须为 `specified` 且有验收方法。字段证明调用者已声明边界，实际是否充分仍由主 Agent 负责。

| workload / risk | specified | unresolved |
| --- | --- | --- |
| routine / mechanical | Luna XHigh | Sol Medium |
| complex | Luna Max | Sol High |
| judgment / exploratory / review | Sol Medium / High / High | 同左 |
| high risk | Sol High | Sol High |
| critical risk / critical_review | Sol XHigh | Sol XHigh |

critical_review 不因 risk=high 被降档。profile 的 fallback 最多一项：routine/mechanical → Sol Medium，complex → Sol High，judgment → Sol High，exploratory/high_risk → Sol XHigh，critical 无自动 fallback。每任务最多两次 attempt。已知主要风险是执行深度不足时，可预先用 `fallback: "complex"` 将 routine 的唯一 fallback 改为 Luna Max；不得随后再接 Sol。

`route_profile` 或 `routes` 可精确覆盖，但仍受风险、Luna 合同、逐模型下限与 live 证据校验；不能以显式覆盖给未决判断或高风险/关键审查套 Luna。

用户明确点名 Astra 时，使用 `gpt-6-astra`，设 `explicit_user_request=true` 并作为首项；支持原生子 Agent 和具备宿主授权的 App Task，推理档位为 Low／Medium／High／XHigh／Max。仍须提供当前 live schema 的精确组合证据；不开放 Ultra，不加入默认自动路由或 fallback，也不登记未经验证的 Fast 能力。例如 Astra High 使用 `model=gpt-6-astra`、`thinking=high`、`speed=standard`。

`live_evidence` 可按候选顺序传数组，也可传 `{ "primary": ..., "fallback": ... }` 或在候选项内传 `runtime_evidence`/`speed_evidence`。证据会原样进入对应 RoutePlan 字段。Native 证据由现有 validator 校验；App Standard 也必须有 `live_create_schema`、`accepted=true`、host 和新鲜时间戳，表示 Surface schema 支持该请求。所有 App 候选还必须有独立的 `host_authorization`：`surface=app_thread`、`authorized=true`、host、来源和新鲜时间戳；schema 支持不等于用户/宿主已授权创建 Task。缺少任一证据、证据过期或 `accepted` 不为 true 都会失败，不会补写 accepted、observed、capacity 或 service tier。

用户点名 exact CLI model 时，传 `surface_intent=ephemeral_cli`、单条 `routes` 和 [`ephemeral_codex_cli` 合同](ephemeral-cli-surface.md)。候选固定 `fresh_context=true`、`speed=standard`，证据 `kind=live_codex_cli_help_catalog` 并绑定 exact tuple；另传新鲜 `cli_authorization`。DeepSeek 4.1 的本轮 Provider state 是 `manual_authorized`，Gemini 3.8 是 `experimental_authorized`。它们不是 Provider 条款 `allowed`。

请求 Fast 但没有精确的 `service_tier=priority` live 证据时，候选降为 Standard 并给出 warning；证据带有 Fast 标记但不完整或不匹配时直接交由 validator 拒绝。Fast 只在 registry 与显式授权门都通过时保留。

## 输出

输出包含 `route_plan`、`validation`、`warnings`、`errors` 和：

```json
"dispatch": {
  "auto_dispatch": false,
  "ready": true,
  "candidates": [{"surface": "native_subagent", "model": "gpt-6-luna", "reasoning_effort": "xhigh", "speed": "standard", "fork_turns": "none"}]
}
```

`dispatch.candidates` 是参数草案，不是已接受或已观测的身份。`ready=true` 只表示现有 RoutePlan validator 通过；主 Agent 仍负责 TeamPlan、Task Packet、授权、实际派遣、结果采纳和收尾。退出码为 0（通过）、3（validator 要求人工复核）或 2（输入、编译或校验失败）。
