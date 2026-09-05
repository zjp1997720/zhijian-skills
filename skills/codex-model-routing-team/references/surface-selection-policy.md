# 执行 Surface 选择策略

本 Skill 先选执行 Surface，再选模型。`native_subagent` 负责低协调开销的原生叶子执行；`app_thread` 负责有状态工作区与耐久生命周期。

## 确定性选择顺序

1. 简单问答、状态查询、单文件小改、强顺序任务和不可逆操作留在主 Agent。
2. 自动路由按 registry 的风险与工作负载画像选择；当前常规为 `native_subagent/gpt-5.6-sol/medium/standard`，复杂/高风险升 Sol High，关键审查升 Sol XHigh，机械批量使用 Luna XHigh。只有 live schema 对精确 tuple 开放 `service_tier=priority` 时才保留 Fast。
3. 任务需要独立 worktree、侧栏可见、跨任务恢复、长期监督，或原生路径缺少工具/身份/上下文能力时，选择 `app_thread`。使用 Luna 本身、短时任务或只读检查不是 App Thread 理由。
4. 当前候选缺少精确 live 能力、Provider 门不通过或所有权无法隔离时，只能进入预声明下一候选；没有下一项时由主 Agent 接管。

官方依据与策略解释见 [Codex Multi-Agent V2 官方依据](official-multi-agent-v2-evidence.md)。

## RoutePlan v3

`schema_version: "3.0"` 的原生候选必须显式声明上下文范围：

```json
{
  "surface": "native_subagent",
  "model": "gpt-5.6-luna",
  "thinking": "xhigh",
  "speed": "standard",
  "fork_turns": "none"
}
```

`fork_turns="none"` 表示 fresh context；正整数字符串表示只继承最近 N 轮。显式模型覆盖时禁止 `fork_turns="all"`，避免整段父上下文强制继承父模型。App Thread 候选不得写 `fork_turns`。

`thinking` 在原生工具映射为 `reasoning_effort`，在 App Thread 映射为 `thinking`。Luna 最低 XHigh，Sol 最低 Medium，风险与工作负载可提升门槛。`speed=fast` 映射为 `service_tier=priority`，并需要当前 Surface 的 tuple-bound live 证据。`surface + model + thinking + speed` 是候选去重键；上下文范围不能绕过单组合重试上限。

旧 `schema_version: "2.1"` 计划仍可校验；它没有 `fork_turns` 绑定，只用于完成既有 run。省略版本的 legacy 候选继续按 `app_thread/standard` 解释。所有新计划必须生成 v3。

## 额度与容量

- 一个子任务最多两个候选，`max_worker_threads` 等于候选数。
- 任何已开始的 `spawn_agent` 或 `create_thread` 都消耗一次 root Worker attempt；静态门排除不消耗。
- `standard` 档最多 6 个计划单元、root attempts 8、每波 3；`expanded` 档为 12/16/6，至少保留 2 个 reserved slots。
- 派遣前读取 live collaboration 容量。原生实际波次为 `min(计划波次上限, 当前可用 child slots)`；可用 child slots 必须扣除协调者与仍活动的 Worker。没有 live 容量证据时最多按“协调者 + 3 个 child”执行。
- Worker 永不使用 Ultra，永不继续派生 Agent、Thread 或后台任务。

## 模型身份

registry 与官方 catalog 只提供候选资格。原生候选的 `runtime_evidence` 必须来自当前会话 live spawn schema，与 host、Surface、model、thinking、fork_turns 绑定并在 10 分钟后失效；只有 Fast 才额外绑定 speed 与 `service_tier=priority`。App Fast 使用同样期限的 `speed_evidence`。成功调用分别写 `platform_accepted_model/platform_accepted_speed`，没有可信回显时 observed 字段保持 `unknown`。
