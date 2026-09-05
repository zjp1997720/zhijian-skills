# 上游 Skill 适配协议

当 Deep Research、课程生产、PPT 或其他 Skill 已经定义工作流时，本 Skill 作为双 Surface 路由 Orchestrator 执行。

## 决策边界

上游 Skill 拥有：

- 任务目标与 Scale
- 子任务划分
- 阶段顺序与依赖
- 产出路径与文件格式
- 业务验收与质量门

本 Skill 拥有：

- 把上游单元编译成轻量 TeamPlan 的 Worker、依赖、所有权、预算与集成顺序；不重写业务语义
- Worker Surface、`model`、`thinking` 与 `speed`
- RoutePlan、Provider allowlist、模型预检与 deterministic fallback
- 原生 Subagent 的 context-scoped spawn、等待、follow-up 与释放
- App Thread 的 project / projectless 选择、创建、实体化、读取、追问与归档
- TeamPlan 默认 6/8/3，或经扩容理由、所有权隔离和 live host 容量门启用 12/16/6；同时保留 reserved slots 与升级次数
- 单写者和禁止下级派遣等安全边界

遇到冲突时，上游业务流程优先，路由安全上限保持强制。预算不足时收敛 Worker 数量并报告，禁止跳过上游验证阶段。

## 调用流程

1. 读取上游计划、任务账本、阶段门和输出路径。
2. 接受上游已经完成的 Scale 和业务单元，不重新拆分任务；按 [TeamPlan 协议](team-plan.md) 编译来源 ID、依赖、所有权、交付物和验收。
3. 两个及以上 Worker 时从 stdin 运行 `scripts/validate_team_plan.py`；失败则修正一次、串行化或由主 Agent 接管，禁止调用第二套重型计划。
4. 计算当前阶段 Worker、后续阶段和重试的 reserved slots。
5. 输出派遣通知，列明当前 Worker 的 Surface、模型、thinking、speed 与保留额度。
6. 把验证后的 unit 转换成 `references/task-packet.md`，保留原始验收标准与 `unit_id/team_plan_revision`。
7. 自动路由按 registry 风险与工作负载画像选择 Native Sol/Luna Worker；需要 worktree、侧栏、跨任务恢复或耐久监督时，RoutePlan 写 `surface_intent=durable_app`，并通过 live 能力与宿主授权门后留在 App Thread。
8. 原生候选按 `references/native-subagent-lifecycle.md` 执行；App Thread 有工作区输出时绑定匹配 project local，并按 `references/thread-lifecycle.md` 与 `references/thread-supervision-protocol.md` 执行。
9. 主 Agent 验证输出文件并更新上游账本。
10. 只有上游阶段完成且结果采纳后，才按 live 能力 close 或 completed-idle 释放原生 Worker；App Thread 满足收尾门后才归档。

上游 run summary 的 Worker 记录按 Surface 分别遵守 [原生审计 schema](native-audit-schema.json) 或 [Thread 审计 schema](audit-schema.json)。每次创建使用唯一 task id 并递增 worker/subtask attempt；每次调用 `create_thread` 前另外写兼容字段 creation attempt，返回正式 id 或 pending id 后写入对应字段。`model` 继续作为 `requested_model` 的兼容别名。平台视图不保证返回模型字段，禁止依赖事后反查恢复路由信息。

## Deep Research 预设

```text
standard: researcher_count + 1 verifier + 1 reviewer + retry_reserve <= 8
```

- researcher：按 registry 画像使用 Native Sol Medium/High；规则明确、可机械验收的批量材料可用 Luna XHigh。live spawn schema 接受 priority 时可用 Fast，否则保持 Standard。公开技术研究可在 Provider 门通过后使用 Grok Medium。
- verifier：1 个 Native Sol High，在 draft 存在后创建；关键核验升 XHigh。
- reviewer：1 个 Native Sol High，在 cited 存在并通过检查后创建；需要异构工程复核时可按 RoutePlan 使用 Grok High。
- FATAL 复审：最多一次 Sol X High，使用 retry reserve。
- 所有任务绑定包含 `01_项目/调研` 的 vault project。
- 每个 researcher 写唯一的 T1/T2/T3/T4 文件。

## 状态复用

上游已经维护 plan 或 task ledger 时，在原账本增加以下字段：

```json
{
  "worker_attempt": 1,
  "subtask_attempt": 1,
  "task_id": "deepresearch-topic-t1-a1",
  "unit_id": "U1",
  "team_plan_revision": 1,
  "surface": "app_thread",
  "creation_attempt": 1,
  "thread_id": null,
  "pending_worktree_id": null,
  "control_state": "PLANNED",
  "thread_status": null,
  "turn_status": null,
  "last_observed_at": null,
  "role": "researcher",
  "model": "gpt-5.6-sol",
  "requested_model": "gpt-5.6-sol",
  "platform_accepted_model": null,
  "observed_runtime_model": "unknown",
  "thinking": "xhigh",
  "requested_speed": "standard",
  "platform_accepted_speed": null,
  "observed_runtime_speed": "unknown",
  "route_plan": {"schema_version": "3.0", "surface_intent": "durable_app", "candidates": [{"surface": "app_thread", "model": "gpt-5.6-sol", "thinking": "medium", "speed": "standard"}]},
  "provider_policy": {},
  "materialized": false,
  "data_ready": false,
  "status": "planned",
  "output": null,
  "fallback_reason": null,
  "adopted": false,
  "archived": false
}
```

不要额外创建 `agent_team/state.json`。只有上游没有恢复机制且任务满足耐久模式条件时，才使用本 Skill 的独立状态目录。
