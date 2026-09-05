# 验证案例

## 触发边界

应触发：两个以上独立来源/模块/产物的并行研究、实现、验证或审查；用户明确要求模型路由、后台 Worker 或 Agents Team。

不应触发：解释、状态查询、单文件小改、强顺序流程，以及发布、发送、付款、删除、账户或生产操作。

## 核心回归

### 默认 Native Sol

Prompt：并行完成三个普通复杂子任务，没有点名 Surface 或模型。

应出现：3-unit TeamPlan；`surface_intent=parent_integrated`；首项按 registry 为 `native_subagent/gpt-5.6-sol/medium/standard`，复杂/高风险升 High，关键审查升 XHigh；候选显式写 `fork_turns="none"` 与匹配的 live runtime evidence。Worker 仍是 leaf，任务包禁止下级派遣。

### Native Luna Fast 缺少 schema

Prompt：创建 Luna XHigh Native Fast Worker，但 live spawn schema 没有 `service_tier`。

应出现：改写为 Standard；不得声称 Fast。若 RoutePlan 强制 Fast，则因缺少 tuple-bound priority evidence 被拒绝。

### Durable App

Prompt：实现任务需要独立 worktree、侧栏可见并可跨任务恢复。

应出现：`surface_intent=durable_app`；所有候选都使用 App Thread；当前 `live_create_schema` 证据之外，还要有独立 `host_authorization`（来源、host、时间戳和 `authorized=true`），再按项目与 worktree 绑定，保留 pending/UNKNOWN/归档门。不得 fallback 到 Native 丢失工作区语义。

### Context scope

Prompt：用 Luna Worker，只继承最近三轮；另一个 Worker 使用 fresh context。

应出现：两个 v3 Native 候选分别写 `fork_turns="3"` 与 `"none"`，runtime evidence 精确绑定；显式模型覆盖时拒绝 `all`。

### Release without close

Prompt：Native Worker 已完成并被采纳，当前 live tools 没有 close_agent，官方状态显示 completed/idle。

应出现：记录 `control_state=RELEASED`、`released=true`、`release_method=completed_idle`；不得用 interrupt 冒充 close。若仍 active 或状态未知，不得释放。

### Sol thinking 与 Fast

Prompt：创建 Sol Medium Fast Worker。

应出现：Sol Medium Standard 可作为常规首项；Low 静态拒绝。复杂/高风险使用 Sol High/XHigh；Fast 仍需要用户明确点名和 live priority evidence。

### RoutePlan 紧凑编译

Prompt：只提供 workload、risk、Provider 门和按候选顺序排列的 live evidence，运行 `scripts/compile_route_plan.py -`。

应出现：registry 选择 profile，生成 v3 RoutePlan 并调用现有 validator；`dispatch.auto_dispatch=false`。缺少 accepted、host、时间戳或 priority 证据时返回错误/Standard warning，不补写 accepted、observed、capacity 或 tier。

### TeamPlan write collision

Prompt：两个无依赖实现 Worker 都修改 `scripts/router.py`。

应出现：TeamPlan validator 拒绝同波写冲突；主 Agent 增加依赖、重分所有权或串行化。

### Expanded capacity

Prompt：12 个互不依赖审核对象，host 声称有 6 个 collaboration slots。

应出现：`expanded` 12/16/6 和至少 2 个 reserved slots；实际原生波次先扣除协调者与仍活动 Worker，再与计划波次上限取较小值。

### App pending 与歧义

Prompt：create_thread 返回 pending id，或按 task id 查询得到零/多个候选。

应出现：pending id 只进审计；唯一稳定正式匹配才进入 CONTROL_READY；零/多个进入 UNKNOWN，不追问、不归档、不 fallback、不重复创建。

### Provider 与 opt-in

- Grok 只在 runtime/provider/data 门通过后使用。
- Terra 只能作为用户点名的首项；unknown model 只熔断该精确 tuple。
- Gemini Antigravity 当前 terms blocked，即使点名也不创建。

### 上游 Skill

Prompt：Deep Research 已有 researcher/verifier/reviewer 与阶段门。

应出现：只把既有单元编译成 TeamPlan；保留 draft → verifier → cited → reviewer 顺序、产物和验收，不创建第二套业务计划。

## 运行断言

- 派遣前简报 Worker 数、Surface、模型、thinking、speed、职责、fallback 与 reserved slots。
- 两个以上 Worker 必须有通过 validator 的 TeamPlan；每个 unit 恰好一份 Task Packet 与 RoutePlan。
- RoutePlan v3 必须写 `surface_intent`；Native 必须写 `fork_turns`，App 不得写。
- registry 决定策略范围；live schema 只验证当前 host 的精确组合。
- requested、platform accepted 与 observed model/speed 分开记录；缺少回显时 observed 为 unknown。
- 一个子任务最多两个 Worker attempt；完整输出最多 follow-up 一次。
- fallback 只能沿预声明链，不静默改变 Surface、model、thinking、speed、context 或 Provider。
- Worker 禁止 Ultra、下级委派和外部不可逆动作；主 Agent保留集成与最终验收。
- Native adopted 输出必须 RELEASED；App 只有 completed/idle 正式 Thread 才能归档。
- v2.1 计划仅完成既有 run；legacy 缺省 Surface 继续解释为 App Thread Standard。

## 失败回退

- Native tuple unsupported：熔断精确组合，进入预声明下一候选；不得静默继承父模型或改写 registry。
- Expanded 容量：只写正整数不够；缺少 live 来源、时间戳过期、未扣协调者/活动 Worker 或算术不平衡都拒绝。
- completed-idle：只有 `agent_status=completed|idle` 才能进入 `RELEASED`；running/unknown 不得伪装成释放。
- Fast unsupported：同模型同 Surface 改用预声明 Standard；不把请求接受冒充 observed Fast。
- Provider 429/认证/MCP/协议故障按各自作用域隔离，不用无界换模型碰撞。
- 完整输出质量不足：原 Worker 追问一次；仍失败才进入第二候选，之后主 Agent 接管。
