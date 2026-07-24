---
name: codex-model-routing-team
description: 在 Codex App 中为复杂、可并行的知识工作或编程任务创建可指定模型与推理强度的后台任务，并以确定性状态恢复和审计 Thread 生命周期；由主 Agent 负责规划、provider 数据边界、分工、集成和验收。用于多来源调研、多章节内容、复杂 Skill/PPT、跨模块开发、独立验证或 2 个以上互不依赖工作流；也用于用户明确要求模型路由、后台 Worker、Agents Team、Grok/Gemini Worker 或持久项目协作。简单问答、状态查询、单文件小改、强顺序任务和发布/付款/删除/账户操作不得自动触发。
---

# Codex 模型路由团队

主 Agent 始终是任务总负责人。后台 Worker 通过 Codex App 独立 Thread 获得真实的 `model` 与 `thinking` 路由；本 Skill 不使用原生 `spawn_agent` 冒充模型路由。

## Do not use

简单问答、状态查询、单文件小改、强顺序任务，以及发布、付款、删除、账户或生产操作不得自动派遣。外部或不可逆动作只能由主 Agent 在用户授权范围内执行，Worker 只准备材料。

## 上游 Skill 模式

当 Deep Research、PPT、课程生产或其他上游 Skill 已经定义任务拆分、阶段顺序、文件路径和验收标准时，读取 [上游 Skill 适配协议](references/upstream-skill-adapter.md)。上游 Skill 保持业务流程主权；本 Skill 只负责模型路由、provider 门、Thread 创建、并发额度、运行读取和归档。

禁止重复执行 Scale、改写上游阶段依赖或创建第二套事实源。安全上限仍然生效；预算不足时收敛 Worker 数量并明确报告。

## 执行流程

1. 检查当前指令中是否存在用户对后台任务和模型路由的明确授权。全局 `AGENTS.md` 的长期授权有效；没有授权就留在主任务内完成。
2. 读取 [模型注册表](references/model-registry.json)、[路由策略](references/routing-policy.md) 与 [Provider 策略](references/provider-policy.md)。先固定任务画像、数据边界、有序候选链和最低 `thinking`，再创建任何 Thread。
3. 独立任务由本 Skill 判断并行收益；上游 Skill 模式直接采用上游 Scale 和任务包，只施加安全上限。预计超过 30 分钟、正式交付物达到 4 个、需要恢复或涉及高风险审批时，读取 [耐久模式](references/durable-mode.md)。
4. 按 [任务生命周期](references/thread-lifecycle.md) 做分层预检，并按 [Thread 监督协议](references/thread-supervision-protocol.md) 管理创建、pending setup、稳定观察、断点续跑和收尾门。缺少 registry、runtime、Provider 或数据任一层证据时不得写成 `route_eligible=true`。
5. 派遣前显示一条简短通知：任务数、每个任务的精确模型、`thinking`、职责、预声明 fallback，以及为后续阶段和重试预留的累计额度。Gemini Antigravity 路径必须说明 manual-only 状态和账号风险。
6. 读取 [任务包模板](references/task-packet.md)，为每个 Worker 写唯一 `task_id`、权限导向的 `task_intent / mutation_authority` 和独立可执行提示词。提示词必须包含“禁止创建任何后台任务、线程或子 Agent”。
7. 用 `codex_app__list_projects` 定位项目；任何声明工作区输出路径的任务都使用匹配 project local，只有纯聊天交付才能 projectless。调用 `create_thread` 前消耗一次 root `creation_attempt` 和 subtask attempt，并按 [审计 schema](references/audit-schema.json) 建立 `PLANNED` ledger 记录；调用开始后更新为 `CREATION_PENDING`。
8. 分别处理 `threadId`、`pendingWorktreeId`、超时和未知返回形状。pending id 只用于审计；用唯一 task id 通过 `codex_app__list_threads` 查找正式 Thread，零/多匹配进入 `UNKNOWN`。正式 Thread 经 `read_thread` 后进入 `CONTROL_READY`；首个 assistant-originated 输出或模型工具调用进入 `DATA_READY`。
9. 每波最多再创建 3 个；运行并发最多 6 个，单个根任务最多发起 8 次 `creation_attempt`，未实体化、超时歧义和 fallback 尝试都计数。创建前扣除上游后续阶段和失败恢复的 reserved slots。按文件、模块、章节或主题分配互斥所有权；同一文件同一时刻只允许一个写入者。
10. 按 [恢复策略](references/recovery-policy.md) 分类失败。完整输出质量不足时只在原 Thread 追问一次；仍失败才创建预声明 fallback Worker。每个子任务最多创建两个 Worker Thread，禁止运行时随机选模、循环回退或静默降低 `thinking`。
11. 主 Agent 亲自核对事实、运行验证、处理冲突并整合最终交付。只对正式 Thread 且 `COMPLETED`、turn completed、输出已验证、结果已采纳的轻量任务逐个归档；失败、争议、待审和 `UNKNOWN` 任务保留。
12. 所有 Worker 记录遵守 [审计 schema](references/audit-schema.json)，把 task id、正式/pending id、官方 thread/turn 观察与派生 `control_state` 分开记录。运行 `scripts/validate_team_ledger.py` 检查确定性不变量；平台没有回显真实模型时，`observed_runtime_model` 保持 `unknown`。最终汇报模型分布、预检、重试、升级、采纳、归档和未解决风险。

## 硬性边界

- 自动候选、manual-only 候选、精确模型 ID 与支持的 `thinking` 以 [模型注册表](references/model-registry.json) 为策略事实源；Codex App live 工具元数据只验证当前 host 是否接受该组合，不能静默扩张策略。
- `gpt-5.6-luna` 与 `gpt-5.6-sol` 是稳定基线；`xai/grok-4.5` 通过 runtime/provider 预检后可作为条件自动候选。
- `antigravity/gemini-3.6-flash` 默认 manual-only，不进入自动路由或静默 fallback。显式点名、风险确认和数据允许仍不能覆盖 `terms_status: blocked`；当前第三方 Antigravity 登录路径不得创建，正式 API 路径必须作为新的 registry entry 接入。
- 禁止自动回退到 `gpt-5.5`、`gpt-5.4`、`gpt-5.4-mini` 或 `gpt-5.3-codex-spark`。Terra 默认关闭；只有用户明确要求或有任务证据时才可使用。
- Worker 永不使用 Ultra，永不继续派生任务。fallback 不得低于任务声明的最低 `thinking`。
- 主 Agent 不切换自己的模型，不把后台任务伪称为原生 Subagent 或预制 Agent Type。
- App 后台任务工具不可用、项目无法安全定位、Provider 数据边界不允许或文件所有权无法隔离时，停止委派并在主任务内完成。
- `pendingWorktreeId` 和未确认返回值都不是可管理 Thread。只允许按唯一 task id 通过官方 `list_threads/read_thread` 有界恢复；零/多匹配进入 `UNKNOWN`，禁止追问、归档、fallback、重复创建或直接修改 Codex 数据库。
- MCP 初始化错误按 workspace/tool signature 处理，不通过连续换模型掩盖环境故障。
- `fork_thread` 会复制已完成历史，可能显著增加上下文成本。只有源任务历史很短且继承上下文确有价值时才能作为应急路径；其他情况由主 Agent 接管。
- 上游 Skill 的阶段门优先于并行收益；存在 verifier → reviewer 等依赖时必须串行创建。

## 输出契约

交付必须完整、自洽、经过主 Agent 验证，并包含可审计的模型路由摘要。结束前通过 Thread 监督协议的收尾门；上游 Skill 模式另外报告 reserved slots、阶段门、输出采纳和归档状态。触发、并发、provider、恢复和归档边界见 [验证案例](references/validation-cases.md)。
