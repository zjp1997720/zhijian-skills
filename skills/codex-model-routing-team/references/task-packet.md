# Worker 任务包

每个后台任务的初始提示词必须独立可执行，不能依赖完整聊天记录。包含以下字段：

```markdown
# 任务身份
你是本任务的独立执行 Worker。禁止创建任何后台任务、线程或子 Agent。

- task_id：
- task_intent：`mutate | inspect | verify`
- mutation_authority：`none | declared-output-only | declared-workspace | isolated-worktree`
- result_correlation_id（可选）：

## 目标与位置
- 总目标：
- 你负责的子目标：
- 该子目标在整体方案中的位置：
- 上游 Skill（如有）：
- 上游阶段：
- 前置阶段门：

## 交付物
- 产物：
- 写入路径（如有）：
- 返回格式：先回显 task_id；再给结论、证据/变更、验证、风险；有 result_correlation_id 时在最终回复中原样返回

## 边界
- 可读取：
- 可写入：
- 禁止触碰：
- 文件所有权：
- 数据等级：
- Provider allowlist：
- reserved slots（由主 Agent 记录，Worker 不修改）：

## 背景与约束
- 已知事实：
- 用户偏好：
- 关键约束：
- 与其他 Worker 的接口：

## 验收
- 完成标准：
- 必须运行的验证：
- 缺失信息时的处理：报告缺口，不猜测
```

`task_intent` 表达权限语义：`mutate` 可以在声明范围内修改；`inspect` 只研究、诊断或写声明的报告；`verify` 只验证既有产物。`mutation_authority` 是实际写入硬门，不能由 Worker 扩大。`declared-output-only` 只允许写交付物路径，不允许顺手修改源文件。

每次 Worker creation attempt 使用唯一 task id。fallback Worker 使用新 task id，避免 `list_threads(query=task_id)` 匹配旧 Thread。`result_correlation_id` 只用于结果关联，不代表任务正确完成。

主 Agent 另外记录所选 `model`、`thinking` 与选择理由。任务包中严禁声称 Worker 已加载某个预制 Agent Type。

主 Agent 还要在任务包之外保存 RoutePlan：任务画像、精确候选链、最低 `thinking`、Provider 策略、健康证据和 fallback 条件。Worker 不自行选择或切换模型，也不需要看到其他候选的凭证与配额信息。

上游 Skill 模式下，任务包必须原样保留上游定义的输出路径、阶段依赖和验收标准。路由层可以收紧安全边界，不能扩大写入范围或跳过质量门。
