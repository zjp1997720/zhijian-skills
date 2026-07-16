# 耐久项目模式

## 进入条件

满足任一条件时使用：预计超过 30 分钟；有 4 个以上正式交付物；涉及外部/生产/账户/成本审批；需要跨任务恢复；用户明确要求 Agents Team、项目管理或持续执行。

## 状态目录

先检查上游 Skill 是否已经提供可恢复的 plan、task ledger 或 run summary。存在上游账本时直接复用，并在其中增加 Thread id、model、thinking、尝试次数、采纳和归档字段；禁止再创建第二套状态事实源。

只有没有上游状态系统时，才在项目根目录创建：

```text
agent_team/
  state.json
  task-board.md
  packets/
  handoffs/
```

`state.json` 至少记录：根任务目标、模式、并发/累计计数、每个 thread id、模型、thinking、职责、所有权、状态、尝试次数、输出路径、是否采纳、是否归档、审批与阻塞项。

`task-board.md` 展示待办、执行中、待集成、完成、阻塞。`packets/` 保存正式任务包，`handoffs/` 保存可恢复的交接摘要。

## 风险门

Worker 可以准备外部或高风险动作所需的材料。发布、发送、付款、删除、账户、生产变更和不可逆操作必须回到主 Agent，并遵守当前用户授权。恢复任务时先读取 `state.json` 与交接文件，禁止重复创建已完成任务。

## rollback boundary

回滚范围只包括本 Skill 新建的后台任务、`agent_team/` 协调文件和未集成的 Worker 变更。不得删除用户既有工作；撤销文件变更必须按项目版本控制与所有权逐项执行。
