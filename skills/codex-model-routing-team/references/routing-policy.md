# 路由策略

## 是否创建 Worker

至少两个独立交付物、各有可检查完成条件，且预计节省大于创建、监督和集成成本时才派遣。简单问答、状态查询、单文件小改、强顺序流程和不可逆外部操作留在主 Agent。

典型任务创建 2–3 个 Worker；广泛调研或多模块任务通常 4–6 个。只有 7–12 个写入隔离、独立可验收的产物带来明确净收益且 live host 容量允许时，才使用 TeamPlan `expanded`。

## 确定性选择顺序

1. 数据边界、Provider 条款、工具需求、任务风险和最低推理强度。
2. [Surface 选择策略](surface-selection-policy.md)：默认原生 V2 Worker；worktree、侧栏、跨任务恢复和耐久监督使用 App Thread。
3. [模型注册表](model-registry.json) 的 automatic、opt-in 和 manual-only 状态。
4. [恢复策略](recovery-policy.md) 中精确 tuple 的熔断与近期健康证据。
5. 任务能力匹配、独立验证、延迟和稳定性信号；下表只作最终 tie-break。

禁止只因模型更快或订阅额度看似充足而绕过前四项。

## Surface 与模型

| 路由 | Surface | 模型 / thinking | 速度 | 用途 |
| --- | --- | --- | --- | --- |
| Sol Native | `native_subagent` | `gpt-6.1-sol` Medium / High / XHigh / Max | Standard / 显式 Fast | 未决判断、疑难诊断、架构取舍与关键审查 |
| Luna Native | `native_subagent` | `gpt-6-luna` XHigh / Max | Standard / live-gated Fast | 默认明确执行、检索提取、草稿、实现与清单核验 |
| Sol App | `app_thread` | `gpt-6.1-sol` Medium / High / XHigh / Max | Standard / 显式 Fast | App 路径中的未决判断、架构、疑难调试与审查 |
| Luna App | `app_thread` | `gpt-6-luna` XHigh / Max | Standard / live-gated Fast | App 路径中的明确执行与耐久任务 |
| Grok | live 支持的 Surface | `xai/grok-4.5` Medium / High | Standard | 通过 runtime/provider 门后的执行或异构复核 |
| Terra | live 支持的 Surface | `gpt-5.6-terra` Low–Max | Standard / 显式 Fast | 仅用户点名的首项候选 |
| Gemini | live 支持的 Surface | `antigravity/gemini-3.6-flash` | Standard | 当前 terms blocked，不得创建 |

GPT-6.1 Sol / GPT-6 Luna 的官方 catalog 能力均为 V2；Luna 在本 Skill 中仍承担 leaf Worker 角色。所有 Worker 都受禁止下级派遣规则约束，能力元数据不扩大任务授权。官方依据见 [Multi-Agent V2 证据](official-multi-agent-v2-evidence.md)。

Ultra 永久禁止。Luna 自动路由只允许 XHigh/Max；Sol 自动路由最低 Medium，按工作负载与风险升 High/XHigh。`thinking` 在原生映射为 `reasoning_effort`，在 App Thread 映射为 `thinking`。

`speed` 取 `standard | fast`。Fast 映射为 `service_tier=priority`；Standard 不传 tier。Luna 只有在当前 Surface 提供 tuple-bound live priority 证据时才自动使用 Fast，否则保持 Standard。Sol/Terra 还要求用户明确点名 Fast。

## 任务画像与候选链

主 Agent 保持当前模型，负责拆分、确定关键方案、集成和验收；直接把明确的执行单元派给 Luna，不默认插入 Sol 协调层。提示词详细有利于交付，但不能弥补未定需求、隐藏耦合或未知验收标准。

| 实际子任务 | 主候选 → 唯一可选 fallback | 典型范围 |
| --- | --- | --- |
| 明确常规执行 `routine` / `mechanical` | Luna XHigh → Sol Medium | 给定来源检索/提取、按提纲写草稿、实现已定接口、明确根因的修复、清单核验 |
| 明确复杂执行 `complex` | Luna Max → Sol High | 已定设计的多文件实现、跨来源对照、约束较多的测试与迁移草案 |
| 有限未决判断 `judgment` | Sol Medium → Sol High | 局部方案取舍、有限证据冲突判断 |
| 开放探索 `exploratory` / `review` | Sol High → Sol XHigh | 根因未知的调试、架构边界设计、开放式审查、无规则可裁决的证据冲突 |
| 高风险 `high_risk` | Sol High → Sol XHigh | 错误后果严重、难以独立验收的单元 |
| 关键独立审查 `critical` | Sol XHigh；默认无 fallback | 核心设计/安全/正确性裁决；必要时显式声明 Sol Max |

`task_contract` 必须声明 `decision_state: specified|unresolved` 和具体 `acceptance`。`specified` 表示关键方案与边界已定；`unresolved` 表示仍需 Worker 做关键判断。routine/mechanical + unresolved → judgment，complex + unresolved → exploratory。任务量、文件数、提示词长度和“复杂”标签都不能单独作为 Sol 理由；普通测试核对也不因叫 reviewer 就升级。高风险与关键审查优先于成本优化。

自动路由的 `DEFAULT_GENERAL` 对应明确常规执行；`DURABLE_WORKSPACE` 使用同等能力的 App 路线（显式 durable intent）；`FAST_MECHANICAL` 对应 Luna XHigh，但仍需 live priority 门。Grok 等其他 Provider 继续按 Provider 门和显式 routes 处理；Terra 只能作为用户点名的首项，不能自动 fallback。

能力尺度跨模型不同：routine 全局最低 Medium、complex 最低 High，是为了容纳对应 Sol fallback；Luna 始终单独强制 XHigh/Max。派遣前如已知主要风险是执行深度不足，可将常规任务唯一 fallback 改为 Luna Max；不允许 XHigh → Max → Sol 三段链。已有完整输出只需局部纠错时，复用原 Worker 最多追问一次。暴露核心需求/方案缺口时交回主 Agent，不靠无限补提示词维持 Luna。

验收优先使用测试、权威来源对照和目标约束；主 Agent 检查关键证据，不默认让 Sol 全量重做通过验收的 Luna 产物。只为独立性确有价值的判断创建审查 Worker。控制输入范围、输出长度、返工和重复审查成本，不降低 Luna 推理档位。

本轮依据：官方 [模型定位](https://learn.chatgpt.com/docs/models) 将 Luna 用于明确、可重复且知道好结果是什么的任务；[发布说明](https://openai.com/index/introducing-gpt-6-sol-and-luna/) 的研究评估显示复杂能力差距较旧定位更小，但不保证任意任务等质。发布首日 X 用法与少量本地合成测试仅提供方向，不构成稳定胜率证据；高推理等级也不自动保证更快、更省或更准确。

## RoutePlan v3

每个新 RoutePlan 顶层写 `schema_version: "3.0"`。顶层保存上述 `task_contract`；Standard 原生候选示例：

```json
{
  "surface": "native_subagent",
  "model": "gpt-6-luna",
  "thinking": "xhigh",
  "speed": "standard",
  "fork_turns": "none",
  "runtime_evidence": {
    "kind": "live_spawn_schema",
    "surface": "native_subagent",
    "model": "gpt-6-luna",
    "thinking": "xhigh",
    "fork_turns": "none",
    "accepted": true,
    "host": "current-host",
    "checked_at": "<ISO-8601>"
  }
}
```

`fork_turns="none"` 表示 fresh context；正整数字符串表示最近 N 轮。显式模型覆盖禁止 `all`。App Thread 不写 `fork_turns`。v2.1 计划仍可完成既有 run；省略版本/Surface/speed 的 legacy 计划按 App Thread Standard 解释。所有证据 10 分钟过期，只证明控制面接受请求，不证明 observed 模型或速度。

具体 RoutePlan 必须通过：

```bash
python3 scripts/validate_route_plan.py /path/to/route-plan.json
```

## 数量与失败升级

- `standard` 最多 6 个计划单元、root attempts 8、每波 3；`expanded` 为 12/16/6，并至少保留 2 个 reserved slots。
- 原生实际波次取计划波次上限与 live 可用 child slots 的较小值；可用 slots 必须扣除协调者和仍活动的 Worker。没有 live 容量证据时最多按协调者 + 3 个 child。
- 每个子任务最多两个 Worker attempt；完整输出质量不足时先对原 Worker follow-up 一次。
- 单候选失败后由主 Agent 接管；Surface、模型、thinking、speed 或 Provider 的变化必须来自预声明下一候选。
- 主 Agent 可组合 Provider 或 Surface 做独立验证，不设置僵硬模型配额。

## 工作区与冲突

- 同一就绪层保持单写者；文件不重叠仍需检查共享 schema、API、migration、lockfile、生成物、数据库、浏览器会话和限流。
- 独立 cwd、分支、worktree、侧栏可见或跨任务恢复使用 `app_thread`。声明工作区输出路径时绑定匹配 project；projectless 只用于纯聊天交付。
- 原生 Worker 默认 fresh context；任务包必须独立提供工作目录、目标、约束和验证命令。
- 无法确认项目、起始状态、Provider 数据边界或合并路径时，留在主 Agent。
