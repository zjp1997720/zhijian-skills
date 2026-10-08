# 默认原生协作

用于新建的 `standard` 团队、原生 Worker、Standard 速度，以及所有单元可共用的工作负载、决策状态和风险路由。权限、模型范围、并发上限与正式生命周期不变。不同路由、Fast、App、CLI、expanded 或 revision 恢复使用对应完整分支。

## 一次准备

主 Agent 判断净收益后，在内存或临时文件准备一个对象：

- `task_prefix`：本任务唯一标识。
- `team_plan`：按 [TeamPlan](team-plan.md) 的最小契约写目标、unit、依赖、精确所有权和完成条件。每个 unit 另写 `task_intent: inspect|verify|mutate` 与匹配的 `mutation_authority`；只读为 `none`，写入仅声明范围。
- `routing`：按 [编译器输入](route-compiler.md) 声明 workload/risk、`task_contract`（`decision_state: specified|unresolved` 和具体验收方法 `acceptance`）、已获准 Provider/数据边界与当前 live tuple 证据；不伪造授权、accepted 或实际运行身份。

首次需要输入结构时读取上述两份接口；同一任务已知结构则不重读。registry、Provider、路由和 Surface 的完整说明只在特殊条件或校验失败时读取，脚本仍执行现有机器校验。

```bash
python3 scripts/prepare_native_team.py /tmp/team-input.json --output /tmp/prepared-team.json
```

脚本一次验证 TeamPlan、编译并验证共用 RoutePlan，返回派遣波次、候选参数和 `PLANNED` 账本。它不创建 Worker；输出路径须是本任务允许的临时文件，不能覆盖已有任务证据。共用路由必须覆盖每个单元的决策状态、复杂度与风险；`acceptance` 对应 TeamPlan 各单元的 `done_when`。混合明确执行和未决判断时分开编译 RoutePlan，不把整个团队抬到 Sol，也不能以简单单元降低审查强度。

## 执行与收口

1. 简报人数、精确模型/强度/速度及职责；Task Packet 包含工作目录、unit 目标、输入、精确写入范围、完成标准、Provider/数据边界，以及禁止下级派遣和外部/破坏性动作。写任务提醒保留他人改动。
2. 按波次派遣，主 Agent 同时推进独立工作。每次调用前写 `SPAWN_PENDING` 并计入真实 attempt；正式回执后记录身份，requested/accepted/observed 分开。
3. 只在需要结果时等待；输出不足最多追问一次，失败仅沿已编译候选链。主 Agent 验证产物后采纳。
4. 依 [原生生命周期](native-subagent-lifecycle.md) 完成释放；无 close 工具时，必须由正式状态确认 completed/idle 才用 `completed_idle`。把 prepared 数据内的 ledger 单独交 `validate_team_ledger.py` 校验，记录实际输出与采纳结果。

所有权或依赖变化、身份不明、跨 Provider、持久任务需求或简单路径被拒绝时，转对应完整合同；不自动放宽边界，也不重复创建不明状态的 Worker。
