# 耐久 App Thread 模式

## 进入条件

只有任务需要独立 worktree、侧栏可见、跨任务恢复、长期监督、项目级 Thread 历史，或严格 App Thread 审计时，才选择 `surface_intent=durable_app`。外部/生产/账户/成本审批仍由主 Agent 执行，不能因为风险高就下放给 Worker。

预计超过 30 分钟、四个以上 Worker 或四个以上正式交付物只是耐久信号，不单独触发状态目录。短时、回到父任务集成的工作按 registry 画像走原生 Worker，TeamPlan/RoutePlan/ledger 从 stdin 校验。

## 状态目录

先复用上游 Skill 已有的 plan、task ledger 或 run summary；禁止创建第二套状态事实源。只有没有上游恢复机制且命中耐久条件时，才在项目根目录创建：

```text
agent_team/
  state.json
  task-board.md
  packets/
  handoffs/
```

`state.json` 记录根目标、策略版本、TeamPlan revision、attempt、RoutePlan、Provider allowlist、Thread 正式 id、pending id、控制状态、官方观察、采纳和归档。声明工作区输出路径的任务必须绑定匹配 project；projectless 只用于纯聊天交付。

## 风险与恢复门

Worker 只能准备发布、发送、付款、删除、账户和生产变更材料。恢复时先读已有账本，再按 task id 解析 `CREATION_PENDING/UNKNOWN`，随后读取正式 Thread，最后才决定预声明 fallback。active/inProgress、排队未决和歧义记录不能被重复创建覆盖。

```bash
python3 scripts/validate_team_ledger.py /path/to/state.json
```

validator 只检查确定性状态不变量，不把本地 ledger 当作实时 Thread 真相。TeamPlan revision 只能在当前波全部收口后新增。

## rollback boundary

回滚只包含本 Skill 新建的 App Thread、`agent_team/` 协调文件和未集成 Worker 变更。不得删除用户既有工作；撤销文件变更必须按项目版本控制与所有权逐项执行。
