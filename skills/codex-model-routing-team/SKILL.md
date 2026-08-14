---
name: codex-model-routing-team
description: 编译 Codex TeamPlan，默认创建 Luna App Thread，并在 live schema 支持时使用原生 fallback。用于两个以上独立交付物、独立验证，或用户明确要求模型路由、后台 Worker、Agents Team、Grok Worker；简单任务不触发。
---

# 模型路由

主 Agent 保持模型并负责规划、所有权、集成和验收。两个以上 Worker 先编译 TeamPlan；默认 `app_thread/gpt-5.6-luna/xhigh/fast`，高风险升 `max`，无 live 证据则 Standard；`native_subagent` 仅显式或 fallback。

## 不使用

简单问答、状态查询、单文件小改、强顺序任务和不可逆操作留在主任务；Worker 只能准备外部动作材料。

## 执行模式

- `governed`（默认）：编译 2–3 unit 微型 TeamPlan，Luna App 从 XHigh 起步；三类 JSON 从 stdin 校验，需要恢复/worktree/审计时按 [耐久模式](references/durable-mode.md) 留状态。
- `native-light`（显式/回退）：App 不可用时须预声明；Luna 不可走原生，Sol 最低 High。
- 上游 Skill 已定义拆分、阶段和产物时，遵守 [适配协议](references/upstream-skill-adapter.md)，不重做 Scale、阶段门或第二套账本。

## 执行流程

1. 确认用户显式或 `AGENTS.md` 长期授权；至少两个独立交付物且有净收益才派遣，否则 `lead_only`。
2. 两个以上 Worker 按 [TeamPlan 协议](references/team-plan.md) 编译 unit、依赖、所有权、交付物、验收和集成顺序，并运行 `scripts/validate_team_plan.py`；已有上游计划时只编译、不重写。
3. 读取 [模型注册表](references/model-registry.json)、[Provider 策略](references/provider-policy.md) 和 [路由策略](references/routing-policy.md)，固定数据边界与 `surface/model/runtime_model/thinking/speed`；有歧义时读 [选择策略](references/surface-selection-policy.md)。
4. 每个 unit 生成 `schema_version: "2.1"` RoutePlan 并运行 `scripts/validate_route_plan.py`。原生组合必须有 live `runtime_evidence`；App Fast 必须有 live `speed_evidence`。
5. 按 [任务包](references/task-packet.md) 写 `unit_id/team_plan_revision`、唯一 `task_id`、权限、验收和禁止下级派遣；派遣前简报 Worker 数、精确路由、职责、fallback 与 reserved slots。
6. 原生路径遵守 [生命周期](references/native-subagent-lifecycle.md)；App 路径遵守 [Thread 生命周期](references/thread-lifecycle.md) 与 [监督协议](references/thread-supervision-protocol.md)。
7. TeamPlan 默认 `standard` 6/8/3；独立产物足够多且扩容收益、隔离与 host 容量明确时可用 `expanded` 12/16/6，并留至少 2 个 reserved slots。每 unit 最多 2 次 attempt、一次 follow-up，保持单写者；更窄 live 上限优先。
8. 失败只按 [恢复策略](references/recovery-policy.md) 沿预声明链前进；只有依赖、所有权、交付物、范围或验收发生结构变化时，才在当前波收口后修订 TeamPlan。
9. 主 Agent 验证并集成交付，关闭已采纳原生 Worker，仅归档满足收尾门的 App Thread；运行 `scripts/validate_team_ledger.py` 后汇报 TeamPlan、路由、尝试、fallback、采纳与收尾状态。

## 硬门

- registry 决定策略允许范围；live schema 只证明当前 host 接受精确组合。逻辑模型、Surface runtime model、平台接受与 observed 模型/速度必须分开记录，未回显保持 `unknown`。App Sol 使用 `gpt-5.6-sol`，原生 Sol 才使用 Standard/Fast 别名。
- 官方原生 V2 live schema 未开放 Luna；Luna 仅走 App Thread，XHigh 起步，高难/高风险 Max。Sol 无论 Surface 均最低 High；Medium/Low 静态拒绝。
- Fast 即 `service_tier=priority`。Luna 默认 Fast；Sol/Terra 默认 Standard，仅在用户明确要求且 live schema 接受精确组合时用 Fast。无证据一律 Standard。
- Terra 与 Grok 4.6 仅在用户点名时作为首项；Grok 还须通过 runtime/provider/工具序列门。AntiGravity 已从 registry 移除。禁止自动使用旧模型、Ultra 或低于最低 `thinking` 的 fallback。
- Worker 不得继续派生任务，也不得执行发布、发送、付款、删除、账户或生产变更。主 Agent 不切换自身模型。
- TeamPlan 默认不创建 Planner、不调用重型计划、不落持久文件；`expanded` 必须写 `scale_reason` 并保留故障位；同波写冲突、依赖环、超预算、计划外 Worker 或下放最终验收必须拒绝。
- `pendingWorktreeId`/未知返回值不可管理；零或多匹配进入 `UNKNOWN`，禁止追问、归档、fallback、重复创建或修改 Codex 数据库。上游阶段门始终优先。

## 输出契约

交付必须完整、自洽并经主 Agent 验证，包含可审计的 Surface、模型、推理强度、速度、Provider 门、尝试、fallback、采纳及收尾状态。行为边界见 [验证案例](references/validation-cases.md) 与 [`evals/`](evals/)。
