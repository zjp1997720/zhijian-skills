# RoutePlan 编译器接口

`scripts/compile_route_plan.py` 是只读的 stdlib 辅助。它不调用 `spawn_agent`、`create_thread` 或任何外部服务；只把紧凑输入展开为 RoutePlan，调用现有 `scripts/validate_route_plan.py`，并返回可供主 Agent 审核的 dispatch 参数。

## 输入

默认从 stdin 读取一个 JSON 对象，也可把 JSON 文件作为唯一位置参数。最小输入要明确数据边界和当前 live 能力：

```json
{
  "workload": "routine",
  "risk": "normal",
  "surface_intent": "parent_integrated",
  "provider_allowlist": ["openai"],
  "provider_status": {"openai": "allowed"},
  "data_allowed_providers": ["openai"],
  "explicit_user_request": false,
  "risk_acknowledged": false,
  "live_evidence": [
    {"kind": "live_spawn_schema", "surface": "native_subagent", "model": "gpt-5.6-sol", "thinking": "medium", "fork_turns": "none", "accepted": true, "host": "current-host", "checked_at": "<当前 ISO-8601>"},
    {"kind": "live_spawn_schema", "surface": "native_subagent", "model": "gpt-5.6-sol", "thinking": "high", "fork_turns": "none", "accepted": true, "host": "current-host", "checked_at": "<当前 ISO-8601>"}
  ]
}
```

`workload`、`risk` 通过 registry 的 `route_selection` 选择 `openai_route_profiles`；当前 routine 为 Sol Medium，complex/high risk 为 Sol High，critical review 为 Sol XHigh，mechanical 为 Luna XHigh。profile 的 fallback 最多再加一项。需要精确覆盖时可传 `route_profile` 或 `routes`，编译器不会替换调用者写明的 model、thinking、surface、speed 或 Provider。

`live_evidence` 可按候选顺序传数组，也可传 `{ "primary": ..., "fallback": ... }` 或在候选项内传 `runtime_evidence`/`speed_evidence`。证据会原样进入对应 RoutePlan 字段。Native 证据由现有 validator 校验；App Standard 也必须有 `live_create_schema`、`accepted=true`、host 和新鲜时间戳，表示 Surface schema 支持该请求。所有 App 候选还必须有独立的 `host_authorization`：`surface=app_thread`、`authorized=true`、host、来源和新鲜时间戳；schema 支持不等于用户/宿主已授权创建 Task。缺少任一证据、证据过期或 `accepted` 不为 true 都会失败，不会补写 accepted、observed、capacity 或 service tier。

请求 Fast 但没有精确的 `service_tier=priority` live 证据时，候选降为 Standard 并给出 warning；证据带有 Fast 标记但不完整或不匹配时直接交由 validator 拒绝。Fast 只在 registry 与显式授权门都通过时保留。

## 输出

输出包含 `route_plan`、`validation`、`warnings`、`errors` 和：

```json
"dispatch": {
  "auto_dispatch": false,
  "ready": true,
  "candidates": [{"surface": "native_subagent", "model": "gpt-5.6-sol", "reasoning_effort": "medium", "speed": "standard", "fork_turns": "none"}]
}
```

`dispatch.candidates` 是参数草案，不是已接受或已观测的身份。`ready=true` 只表示现有 RoutePlan validator 通过；主 Agent 仍负责 TeamPlan、Task Packet、授权、实际派遣、结果采纳和收尾。退出码为 0（通过）、3（validator 要求人工复核）或 2（输入、编译或校验失败）。
