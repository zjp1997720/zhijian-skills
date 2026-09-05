---
name: codex-model-routing-team
description: 为有明确净并行收益的任务编译 TeamPlan，按 registry 与 live schema 固定 Worker 路由。用于两个以上独立交付物、独立验证，或明确要求模型路由、后台 Worker、Agents Team、Grok/Gemini Worker。简单问答、状态查询、单文件小改、强顺序、不可逆操作不触发。
---

# Codex 模型路由团队

主 Agent 保持当前模型，只做必要规划、所有权、集成和最终验收。独立的批量或复杂执行交给 1–3 个 Luna/Sol Worker，不重复已委派工作。两个以上 Worker 先编译 TeamPlan；registry 按风险/工作负载选路：常规 Sol Medium，复杂/高风险 Sol High，关键审查 Sol XHigh，机械批量 Luna XHigh。

## 不使用

简单问答、状态查询、单文件小改、强顺序和不可逆操作留在主任务；Worker 只能准备外部动作材料。

## 执行模式

- `native-v2`（默认）：按 registry 选 `native_subagent` Sol/Luna Worker；fresh context 使用 `fork_turns="none"`，少量上下文写正整数。JSON 默认从 stdin 校验。
- `durable-app`：仅当前 live 能力与宿主授权都通过时使用 App Thread；worktree 需求本身不授权创建用户可见 Task。
- 上游 Skill 已定义拆分、阶段和产物时，遵守 [适配协议](references/upstream-skill-adapter.md)，不重做阶段门或业务账本。
- `python3 scripts/compile_route_plan.py -` 把紧凑 JSON 编译为 RoutePlan 并校验；只返回 dispatch 参数，永不派遣。

## 执行流程

1. 自动派遣需 2+ 独立交付物且净收益为正；用户明确点名单 Worker 可执行，否则 `lead_only`。
2. 两个以上 Worker 按 [TeamPlan 协议](references/team-plan.md) 编译 unit、依赖、所有权、交付物和集成顺序，并运行 `scripts/validate_team_plan.py`；上游计划只编译。
3. 按 [registry](references/model-registry.json)、[Provider](references/provider-policy.md)、[路由](references/routing-policy.md) 与 [Surface](references/surface-selection-policy.md) 固定候选链；编译器降低手写成本。
4. 每个 unit 生成 `schema_version: "3.0"` RoutePlan，写 `surface_intent` 并运行 `scripts/validate_route_plan.py`。原生候选须写 `fork_turns`、tuple-bound `runtime_evidence`；Fast 还须有 live `service_tier=priority` 证据。
5. [任务包](references/task-packet.md) 写 unit、唯一 `task_id`、权限、验收和禁止下级派遣；简报路由、fallback 与 reserved slots。
6. 原生路径遵守 [生命周期](references/native-subagent-lifecycle.md)；App 路径遵守 [Thread 生命周期](references/thread-lifecycle.md) 与 [监督协议](references/thread-supervision-protocol.md)。
7. TeamPlan 默认 `standard` 6/8/3；`expanded` 12/16/6 需 live 容量门、2 个 reserved slots；按 child slots 切波，更严的宿主/用户限制优先。
8. 每 unit 最多 2 次 attempt、一次 follow-up；失败只沿 [预声明链](references/recovery-policy.md)。结构变化才修订 TeamPlan。
9. 主 Agent 验证集成；原生 Worker close 或 completed-idle 后写 `RELEASED`，App Thread 过门后归档；运行 `scripts/validate_team_ledger.py`。

## 硬门

- registry 决定范围；live schema 只证明当前 host 接受精确组合。requested/accepted/observed 分开记录，未回显为 `unknown`。
- V2 父 Agent 可创建 picker 可见且未禁用的 V1 leaf model；Luna 可走原生 V2但不获协作工具，Sol/Terra 也禁止下级派遣。
- 不加 `model: luna` frontmatter；编排入口留在协作父 Agent，Luna 只做 Worker。
- Luna 最低 XHigh；Sol 最低 Medium，按工作负载与风险提升到 High/XHigh；Terra 仅显式首项；Grok 过门；Gemini blocked。禁止旧模型、Ultra 和低强度 fallback。
- Fast 即 `service_tier=priority`；live schema 无字段时一律 Standard，不把 catalog 或请求值冒充 observed Fast。
- `app_thread` 只用于 worktree、侧栏、跨任务恢复、耐久监督或预声明 fallback，并且必须有 live 能力与宿主授权证据。
- Worker 不得继续派生或执行发布、发送、付款、删除、账户、生产变更；主 Agent 不切换模型。
- TeamPlan 不创建 Planner、不调用重型计划、不落持久文件；同波写冲突、依赖环、超预算、计划外 Worker、下放验收必须拒绝。
- 未确认返回值或 `pendingWorktreeId` 不得当正式身份；`UNKNOWN` 禁止追问、归档、fallback、重复创建、改库。

## 输出契约

交付须经主 Agent 验证，包含可审计的 Surface、模型、推理、速度、上下文、Provider 门、尝试、fallback、采纳及收尾状态。编译器见 [RoutePlan 编译器接口](references/route-compiler.md)；边界见 [验证案例](references/validation-cases.md) 与 [`evals/`](evals/)。
