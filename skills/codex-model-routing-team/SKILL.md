---
name: codex-model-routing-team
description: "为有净收益的独立子任务安排多模型协作；简单或强顺序任务直接执行。"
---

# Codex 模型路由团队

主 Agent 保持模型并负责集成验收；独立执行交给 1–3 个 Worker。两个以上 Worker 先编译 TeamPlan；边界明确且可验收的执行默认 GPT-6 Luna XHigh，复杂执行 Luna Max；未决判断 Sol Medium/High，高风险 Sol High，关键独立审查 Sol XHigh。派遣前声明 `task_contract`：决策是否已定、如何验收；提示词长或文件多不单独触发 Sol。

## 按需选择路径

- 默认原生 Standard、新 standard 团队且单元可共用风险路由：读 [原生简洁路径](references/native-quick-path.md)，用 `scripts/prepare_native_team.py` 一次生成已校验派遣参数和初始账本。
- 路由不同、Fast、单 Worker 或已有团队恢复：读 [编译器接口](references/route-compiler.md)；两个以上 Worker 按 [TeamPlan](references/team-plan.md) 校验，原生执行读 [生命周期](references/native-subagent-lifecycle.md)。
- 需要用户明确要求的持久 Task：核对宿主授权后读 [Thread 生命周期](references/thread-lifecycle.md) 与 [监督协议](references/thread-supervision-protocol.md)。worktree 需求本身不授权创建 Task。
- 用户点名 exact CLI model：读 [CLI Surface](references/ephemeral-cli-surface.md)，核对 help/catalog、授权与 fresh context。
- 上游 Skill 已定义拆分、阶段和产物时，遵守 [适配协议](references/upstream-skill-adapter.md)，不重做阶段门或业务账本。

## 所有路径共用

1. 自动派遣需 2+ 独立交付物且净收益为正；点名单 Worker 可执行，否则主 Agent 直接完成。
2. 编译器读取 registry 并执行 RoutePlan 校验，不省略 Provider、live schema 或数据边界。特殊 Provider/覆盖或失败诊断才展开 [Provider](references/provider-policy.md)、[路由](references/routing-policy.md)、[Surface](references/surface-selection-policy.md)；不用每次先读齐。
3. 派遣前明确 unit、唯一 task_id、权限、精确所有权和验收；完整 [任务包](references/task-packet.md) 仅在输入/上下文/权限复杂时展开。主 Agent 保持集成和最终验收。
4. 默认 `standard` 6/8/3，实际受 live child slots 及更严的用户上限约束；`expanded` 12/16/6 仅按 TeamPlan 容量门启用。每 unit 最多 2 次 attempt、一次 follow-up；失败只沿 [预声明链](references/recovery-policy.md)。
5. 结果经主 Agent 验证后采纳，正式状态确认收口并运行 `scripts/validate_team_ledger.py`。编译准备不等于已执行，不把创建回执当完成。

## 硬门

- registry 决定范围；live schema 只证明当前 host 接受精确组合。requested/accepted/observed 分开记录，未回显为 `unknown`。
- GPT-6.1 Sol / GPT-6 Luna 的官方 catalog 均为 V2；本 Skill 将所有 Worker 限制为叶子执行角色，禁止继续派遣。当前 host 必须接受精确模型组合。
- 不加 `model: luna` frontmatter；编排入口留在协作父 Agent，Luna 只做 Worker。
- Luna 最低 XHigh；Sol 最低 Medium；Terra 仅显式首项；Grok 过门；Gemini 3.6 blocked。DeepSeek 4.1/Gemini 3.8 仅走 manual/experimental CLI。禁止 Ultra。
- Fast 即 `service_tier=priority`；live schema 无字段时一律 Standard，不把 catalog 或请求值冒充 observed Fast。
- `app_thread` 只用于 worktree、侧栏、跨任务恢复、耐久监督或预声明 fallback，并且必须有 live 能力与宿主授权证据。
- Worker 不得继续派生或执行发布、发送、付款、删除、账户、生产变更；主 Agent 不切换模型。
- TeamPlan 不创建 Planner、不调用重型计划、不落持久文件；同波写冲突、依赖环、超预算、计划外 Worker、下放验收必须拒绝。
- 未确认返回值或 `pendingWorktreeId` 不得当正式身份；`UNKNOWN` 禁止追问、归档、fallback、重复创建、改库。

## 输出契约

交付须经主 Agent 验证，包含可审计的 Surface、模型、推理、速度、上下文、Provider 门、尝试、fallback、采纳及收尾状态。编译器见 [RoutePlan 编译器接口](references/route-compiler.md)；边界见 [验证案例](references/validation-cases.md) 与 [`evals/`](evals/)。
