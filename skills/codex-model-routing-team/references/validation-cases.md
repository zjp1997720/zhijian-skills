# 验证案例

## 应触发

- “调研 6 个来源，分别验证后写成一篇完整文章。”
- “这个 Skill 涉及路由、脚本、评测和文档，直接实现并验证。”
- “并行检查三个模块的回归，再由主 Agent 修复和验收。”
- “用 Deep Research 调研四个子主题，研究文件写入 vault，最后串行做引用核查和对抗审查。”
- “明确把复杂编码 Worker 交给 Grok 4.6，失败时由 Sol 接管。”
- “明确让两个 Sol High 原生 Subagent 分别检查实现和测试，结果回到父任务集成。”
- “默认用 Luna XHigh App Thread 完成三个边界清晰的实现，高风险任务升 Luna Max。”
- “把耐久调研放到 App Thread；原生精确组合不可用时按预声明链切换 Surface。”

## 不应触发

- “解释一下这段报错是什么意思。”
- “把这个标题改短一点。”
- “查看当前 Git 状态。”
- “帮我发布、付款或删除账号。”
- “没有点名 Grok，把所有低风险任务自动发给 Grok 4.6。”

## 最小行为回归

### Net-positive TeamPlan

Prompt：同时核对三个独立来源并汇总，任务不大，但 Luna Worker 并行预计更快且不降低验收质量。

应出现：不以“任务不够复杂”为由拒绝；主 Agent 生成 3-unit 微型 TeamPlan，从 stdin 校验，计算单波派遣；每个 unit 有独立 output、ownership 和 done_when，再生成 Luna XHigh App RoutePlan 与 Task Packet；不创建 Planner 或持久文件。

### TeamPlan write collision

Prompt：两个实现 Worker 都计划修改 `scripts/router.py`，没有依赖关系。

应出现：TeamPlan validator 拒绝同一就绪层写入冲突；主 Agent 增加依赖、重分所有权或串行执行，不能靠不同模型掩盖冲突。

### Existing plan compiles, not rewrites

Prompt：CE Plan 已定义 U1/U2、Dependencies、Files 和 Verification，请按模型路由团队执行。

应出现：保留上游 U-ID 和业务质量门，只编译 TeamPlan 的 Worker、所有权、预算和集成顺序；不调用 `ce-work`，不重新写一份领域计划。

### Happy path

Prompt：明确使用 Grok 4.6 实现复杂模块，再让另一个模型独立审查，最后由主 Agent 集成。

应出现：`DEEP_AGENTIC_CODE_EXPLICIT`；Grok High → Sol High 的固定候选链；Grok 先通过 CLIProxyAPI 版本、多智能体协议和有序工具序列探针；不同 provider 的审查；单写者；默认 6/8/3，满足扩容门时可用 12/16/6；主 Agent 最终验收。

### Native exact-model happy path

Prompt：明确要求并行派两个原生 Sol Worker，一个 High 做扫描，一个 XHigh 做实现，完成后回到主任务集成。

应出现：`native-light` 与两个 `native_subagent` 候选；live spawn schema 分别确认 `gpt-5.6-sol / high` 与 `gpt-5.6-sol / xhigh`；RoutePlan/ledger 可从 stdin 校验且不创建 `agent_team/`；V1 传 `fork_context=false` 或 V2 传 `fork_turns="none"`；requested/platform/observed identity 分开记录；采纳后关闭 agent。

### Default App Luna happy path

Prompt：并行完成三个普通复杂子任务，没有点名 Surface 或模型。

应出现：默认首项为 `app_thread/gpt-5.6-luna/xhigh`，高风险子任务升 `max`；若 live create schema 接受 priority 可写 Fast，否则显式写 Standard；fallback 为 Sol High App Standard。

### Native Luna rejected

Prompt：要求用官方原生 MultiAgent V2 创建 Luna XHigh Worker。

应出现：registry 静态拒绝 `native_subagent/gpt-5.6-luna`；不得用代理 catalog 或请求字段冒充官方 live schema 支持；改用 Luna App Thread，或沿预声明链进入 Sol High Standard。

### Sol Medium rejected

Prompt：创建 Sol Medium Worker，用户认为 Medium 足够。

应出现：无论 App 还是原生都静态拒绝；Sol 的质量下限是 High，不以显式请求绕过。

### App Luna Fast without speed schema

Prompt：创建 Luna XHigh App Thread，当前 `create_thread` schema 只有 model/thinking，没有速度参数。

应出现：App 路由保持 Standard；不得声称 Fast。若 RoutePlan 强制 App Fast，则因缺少 `speed_evidence` 被拒绝。

### Sol Fast requires explicit request

Prompt：使用 Sol XHigh 并打开 Fast。

应出现：自动 RoutePlan 被静态拒绝；Sol 默认 Standard。只有用户明确要求且 live schema 接受 `service_tier=priority` 时，精确 Sol Fast 候选才通过。

### Four short outputs stay lightweight

Prompt：四个互斥的小文件预计十分钟完成，明确交给三个 Sol High 原生 Worker，结果回到父任务集成，不需要恢复或独立历史。

应出现：因用户明确点名原生而选择 `native-light`；不创建持久协调文件；Provider、Sol High 下限、默认 6/8/3、单写者、fresh-context、身份和关闭门保持不变。

### Expanded TeamPlan

Prompt：12 个互不依赖的审核对象，各自产出独立报告，主 Agent 统一汇总；live host 可承载 6 个并发 Worker。

应出现：主 Agent 记录明确 `scale_reason`，验证所有权无重叠，使用 `expanded` 12/16/6 并保留至少 2 个 reserved slots；若 live host 更窄则降低每波数量。

### Native model rejection

Prompt：用户明确要求 Terra low 原生 Worker，但当前 V2 spawn 返回 `Unknown model gpt-5.6-terra`。

应出现：该精确 `native_subagent/gpt-5.6-terra/low` 组合立即失败；不得静默继承父模型；只进入预声明的 Sol 或 App Thread fallback。若 RoutePlan 没有下一候选则由主 Agent 接管。

### Surface selection

Prompt：一个 5 分钟只读代码检查和一个需要独立 worktree、跨会话恢复的实现任务并行执行。

应出现：两个任务默认都选择 `app_thread`，普通只读检查用 Luna XHigh，独立 worktree 实现按风险用 Luna XHigh/Max；只有显式请求或 App fallback 才使用原生。

### Ambiguous

Prompt：并行处理三份包含图片的长文档，其中一份含内部客户信息，速度优先。

应出现：先做数据分类和 Provider allowlist；不能只因 Gemini 快就发送内部数据；允许公开材料与敏感材料使用不同 RoutePlan。

### Adjacent non-goal

Prompt：告诉我当前模型列表里有哪些模型。

应出现：主任务内读取并回答；不创建后台任务或语义 canary。

### Regression

Prompt：Deep Research 的 researcher 已完成，但 draft/cited 不存在，请同时创建 verifier 和 reviewer。

应出现：保留上游阶段门；先由主 Agent 产生 draft，再创建 verifier；cited 通过后才能创建 reviewer。

### Pending worktree

Prompt：`create_thread` 只返回 `pendingWorktreeId`，稍后 `list_threads(task_id)` 唯一匹配到一个 worktree Thread。

应出现：pending id 只进审计；用唯一 task id 查询；两次连续观察的正式 thread id/cwd 一致后进入 `CONTROL_READY`；pending id 不传给 read/send/archive。

### Ambiguous recovery

Prompt：创建调用超时，按 task id 查询得到零个或两个匹配。

应出现：标记 `UNKNOWN`；不写成确定未创建；不 follow-up、不归档、不 fallback、不重复创建，由主 Agent 接管可继续工作。

### Resume

Prompt：耐久任务恢复时 ledger 已有正式 thread id，最新 `read_thread` 显示 turn inProgress。

应出现：以最新官方读取覆盖旧 `status=done` 摘要，继续监督原 Thread，禁止创建替代 Worker。

### Permission intent

Prompt：一个 `task_intent=inspect` Worker 想顺手修改源文件，mutation authority 只有 `declared-output-only`。

应出现：拒绝源文件写入，只允许声明的报告路径。

## 运行断言

- 派遣前显示 Worker 数量、Surface、精确模型、thinking、speed、职责、有序 fallback 和 reserved slots。
- `governed` App Thread 是自动默认；`native-light` 仅用于显式原生或预声明 fallback，RoutePlan 与 ledger 可从 stdin 校验且不创建 `agent_team/`。
- registry 决定策略允许范围；live runtime 只验证当前 host 接受性。
- AntiGravity 不在 registry，不进入候选或 fallback。
- Grok 4.6 只在用户明确点名，并通过 runtime/provider/CLIProxyAPI 版本/工具序列门后使用。
- 每个新 `host/surface/model/thinking/speed/tool-signature` 的首个真实业务 Worker 独立通过对应生命周期健康门；一个组合的健康不外推到另一个组合。
- 所有提示词含唯一 task id、task intent、mutation authority、完整任务包与禁止下级委派。
- 两个及以上 Worker 派遣前必须有通过校验的 TeamPlan；每个 Worker 记录 `unit_id/team_plan_revision`，并恰好关联一份 Task Packet 和 RoutePlan。
- 自动触发以净并行收益为准；`lead_only` 不构造完整 TeamPlan，微型 TeamPlan 不创建 Planner、不调用重型计划、不落持久文件。
- `threadId`、`pendingWorktreeId`、超时和未知返回形状分别处理；排队 worktree 的身份/cwd 需要两次稳定官方观察。
- 最新官方 Thread/turn 观察是当前状态真相；旧 status/event 文本只能诊断。
- `UNKNOWN` 不 follow-up、不归档、不 fallback、不重复创建。
- 同时运行不超过 6，worker attempts 不超过 8，任何 Worker 都不使用 Ultra。
- 每个子任务最多两个 Worker attempt；完整输出最多在原 Worker follow-up 一次。
- fallback 在派遣前固定，不随机选模、不形成循环、不静默改变 thinking/speed 或扩大 Provider allowlist。
- 上游 Skill 模式保留上游 Scale、业务单元、阶段门和输出路径；路由层只编译 TeamPlan，不重复拆分或改写任务。
- 有工作区输出路径时使用 project local，不因“通用调研”切换到 projectless。
- Deep Research 默认最多 4 个 researcher，为 verifier、reviewer 和两次重试预留累计额度。
- verifier 完成并产生 cited 文件后才能创建 reviewer。
- 写入范围互斥；同一文件保持单写者。
- 主 Agent 读取结果、按错误分类恢复、整合并验证。
- 原生采纳结果必须关闭 agent；只对 completed/idle 的正式 Thread 逐个归档；pending/歧义记录只按 task id 走官方恢复。
- 最终报告包含 Surface，以及 requested/platform/observed model 与 speed、Provider 门、预检、尝试、fallback、采纳与关闭/归档。

## 失败回退

- Grok High unsupported：精确组合立即熔断，进入预声明 Sol High；不再试 Grok Medium。
- Native Luna：静态排除，改走 Luna XHigh/Max App Thread；不得把 CLIProxyAPI catalog 能力外推为官方原生 V2 支持。
- Sol Medium/Low：静态排除，不因用户显式点名降级；改用 Sol High 或 Luna XHigh/Max。
- Terra 未明确点名：静态门排除；Terra 出现在 fallback 位置时 RoutePlan 拒绝。
- Terra 原生返回 unknown model：只熔断该 Surface 的精确组合；按预声明链进入 Sol 或 App Thread，禁止静默继承。
- Gemini 未明确点名：静态门排除，不运行 canary，不创建 Thread。
- 合规 Gemini API 路径首次语义 nonce 不匹配：原组合复测一次；第二次通过则保留 transient 记录并继续，连续两次失败才熔断。当前 blocked Antigravity 路径不运行 canary。
- 429 带 `Retry-After`：写入负向 TTL，当前子任务进入下一候选，同批任务跳过该组合。
- 认证失败：熔断 provider/account，不在同 provider 换模型碰撞。
- MCP 初始化失败：按 workspace/tool signature 处理，不连续更换模型。
- 创建超时且没有正式 ID：按唯一 task id 有界查询；唯一稳定匹配可恢复，零/多匹配进入 `UNKNOWN`；不切换 project/projectless 重撞，不修改数据库。
- 输出质量不足：原 Thread 追问一次；仍失败才创建第二 Worker，之后由主 Agent 接管。
- 原生工具缺失、App 工具缺失、精确模型未确认、项目无法匹配、权限不足、Provider 数据边界不允许或所有权冲突：只走预声明 Surface fallback；没有可用候选时由主 Agent 本地执行或明确报告限制。
