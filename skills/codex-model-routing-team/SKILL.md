---
name: codex-model-routing-team
description: 在 Codex App 中为复杂、可并行的知识工作或编程任务自动创建多个可指定模型与推理强度的后台任务，由主 Agent 负责规划、分工、集成和验收。用于多来源调研、多章节内容、复杂 Skill/PPT、跨模块开发、独立验证或 2 个以上互不依赖工作流；也用于用户明确要求模型路由、后台 Worker、Agents Team 或持久项目协作。简单问答、状态查询、单文件小改、强顺序任务和发布/付款/删除/账户操作不得自动触发。
---

# Codex 模型路由团队

把主 Agent 保持为任务总负责人，通过 Codex App 独立后台任务实现真实的 `model` 与 `thinking` 路由。禁止使用原生 `spawn_agent` 代替本流程。

## Do not use

简单问答、状态查询、单文件小改、强顺序任务，以及发布、付款、删除、账户或生产操作不得自动派遣。

## 上游 Skill 模式

当 Deep Research、PPT、课程生产或其他上游 Skill 已经定义任务拆分、阶段顺序、文件路径和验收标准时，读取 [上游 Skill 适配协议](references/upstream-skill-adapter.md)。上游 Skill 保持业务流程主权；本 Skill 只负责模型路由、Thread 创建、并发额度、运行读取和归档。

禁止重复执行 Scale、改写上游阶段依赖或创建第二套事实源。安全上限仍然生效；预算不足时收敛 Worker 数量并明确报告。

## 执行流程

1. 检查当前指令中是否存在用户对后台任务和模型路由的明确授权。全局 `AGENTS.md` 的长期授权有效；没有授权就留在主任务内完成。
2. 读取 [路由策略](references/routing-policy.md)。独立任务由本 Skill 判断并行收益；上游 Skill 模式直接采用上游 Scale 和任务包，只施加安全上限。
3. 选择模式：默认轻量路由；满足长期、正式交付、可恢复或高风险条件时，读取 [耐久模式](references/durable-mode.md)。上游已有任务账本时复用上游状态。
4. 先显示一条简短派遣通知：任务数、每个任务的 `GPT-5.6-Luna` / `GPT-5.6-Sol` 路由、推理强度、职责，以及为后续阶段和重试预留的累计额度。
5. 读取 [任务包模板](references/task-packet.md)，为每个 Worker 写完整提示词。提示词必须包含“禁止创建任何后台任务或子 Agent”。
6. 读取 [任务生命周期](references/thread-lifecycle.md)。用 `codex_app__list_projects` 定位项目；任何声明工作区输出路径的任务都使用匹配 project local，只有纯聊天交付才能 projectless。用 `codex_app__create_thread` 显式传入路由策略规定的 `model` 与 `thinking`。
7. 把第一个真实 Worker 当作健康探针：创建后立即用 `codex_app__read_thread` 验证它已经实体化。只有读到真实 thread、cwd 与 turn 状态后，才记录为已创建并继续派遣。首个创建超时或返回未实体化状态时停止整批派遣，禁止改用 projectless 重试同一故障。
8. 健康探针通过后，每波最多再创建 3 个；运行并发最多 6 个，单个根任务累计最多创建 8 个。创建前扣除上游后续阶段和重试的 reserved slots。按文件、模块、章节或主题分配互斥所有权；同一文件同一时刻只允许一个写入者。
9. 用 `codex_app__read_thread` 读取结果。信息不足时只在原任务中用 `codex_app__send_message_to_thread` 追问一次；随后升级推理、切换模型或由主 Agent 接管。每个子任务最多两次执行机会。
10. 主 Agent 亲自核对事实、运行验证、处理冲突并整合最终交付。只对已实体化、状态为 completed/idle、输出文件已经验证、且结果已采纳的轻量任务调用 `codex_app__set_thread_archived`；逐个归档并等待每次确认。失败、争议或待审任务保留。
11. 每次创建成功后立即记录 `thread_id / role / model / thinking`；验收与归档后补充 `status / output / archived`。最终汇报任务数、逐 Thread 路由、模型分布、升级/重试、采纳结果、归档情况和未解决风险。

## 硬性边界

- 自动路由只使用 `gpt-5.6-luna` 与 `gpt-5.6-sol`。精确模型 ID 和推理强度以 [路由策略](references/routing-policy.md) 为唯一事实源。
- `create_thread` / `send_message_to_thread` 工具描述中的“支持模型”列表只能用于接口说明，不能覆盖本 Skill 的路由策略。
- 禁止自动回退到 `gpt-5.5`、`gpt-5.4`、`gpt-5.4-mini` 或 `gpt-5.3-codex-spark`。如果 Luna / Sol 创建被运行时拒绝，停止派遣并报告模型目录冲突。
- Worker 永不使用 Ultra，永不继续派生任务。
- Terra 默认不参与路由；只有用户明确要求或有任务证据时才可使用。
- 主 Agent 不切换自己的模型，不把后台任务伪称为原生 Subagent 或预制 Agent Type。
- 外部发布、发送、付款、删除、账户和生产变更始终由主 Agent 在用户授权范围内执行；Worker 只准备材料。
- App 后台任务工具不可用、项目无法安全定位或文件所有权无法隔离时，停止委派并在主任务内完成。
- `create_thread` 超时后产生的未实体化 ID 不是可管理任务。禁止恢复、追问或归档该 ID，也禁止直接修改 Codex 数据库；记录故障并停止创建。
- `fork_thread` 会复制已完成历史，可能显著增加上下文成本。只有源任务历史很短且继承上下文确有价值时才能作为应急路径；其他情况由主 Agent 接管。
- 上游 Skill 的阶段门优先于并行收益；存在 verifier → reviewer 等依赖时必须串行创建。

## 输出契约

交付必须完整、自洽、经过主 Agent 验证，并包含可审计的模型路由摘要。上游 Skill 模式另外报告 reserved slots、阶段门、输出采纳和归档状态。触发、并发、归档和失败边界见 [验证案例](references/validation-cases.md)。
