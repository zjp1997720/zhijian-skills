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
| Sol Native | `native_subagent` | `gpt-5.6-sol` Medium / High / XHigh / Max | Standard / 显式 Fast | 常规 Worker、实现、审查与裁决 |
| Luna Native | `native_subagent` | `gpt-5.6-luna` XHigh / Max | Standard / live-gated Fast | 规则明确、可机械验收的批量 Worker |
| Sol App | `app_thread` | `gpt-5.6-sol` Medium / High / XHigh / Max | Standard / 显式 Fast | App 路径中的常规工作、架构、调试与审查 |
| Luna App | `app_thread` | `gpt-5.6-luna` XHigh / Max | Standard / live-gated Fast | App 路径中的机械批量与耐久任务 |
| Grok | live 支持的 Surface | `xai/grok-4.5` Medium / High | Standard | 通过 runtime/provider 门后的执行或异构复核 |
| Terra | live 支持的 Surface | `gpt-5.6-terra` Low–Max | Standard / 显式 Fast | 仅用户点名的首项候选 |
| Gemini | live 支持的 Surface | `antigravity/gemini-3.6-flash` | Standard | 当前 terms blocked，不得创建 |

Luna 的官方 catalog 能力为 V1/leaf，但 V2 父 Agent可以创建 picker 可见且未禁用的 leaf model；leaf Worker 自身不获得协作工具。Sol/Terra 即使具备 V2 协作能力，也受本 Skill 的禁止下级派遣规则约束。官方依据见 [Multi-Agent V2 证据](official-multi-agent-v2-evidence.md)。

Ultra 永久禁止。Luna 自动路由只允许 XHigh/Max；Sol 自动路由最低 Medium，按工作负载与风险升 High/XHigh。`thinking` 在原生映射为 `reasoning_effort`，在 App Thread 映射为 `thinking`。

`speed` 取 `standard | fast`。Fast 映射为 `service_tier=priority`；Standard 不传 tier。Luna 只有在当前 Surface 提供 tuple-bound live priority 证据时才自动使用 Fast，否则保持 Standard。Sol/Terra 还要求用户明确点名 Fast。

## 任务画像与候选链

| 画像 | 最低 thinking | 主候选 → fallback |
| --- | --- | --- |
| `DEFAULT_GENERAL` | medium | Sol Native Medium → Sol Native High |
| `HIGH_RISK_GENERAL` | high | Sol Native High → Sol Native XHigh |
| `DURABLE_WORKSPACE` | medium | Sol App Medium → Sol App High |
| `FAST_MECHANICAL` | xhigh primary / medium fallback | Luna Native Fast/Standard → Sol Native Medium Standard |
| `CRITICAL_REVIEW` | xhigh | Sol Native XHigh → Sol Native Max |
| `DEEP_AGENTIC_CODE` | high | Grok High → Sol Native High |
| `REVIEW_OPENAI_PRIMARY` | high | Grok High → Sol Native XHigh |
| `REVIEW_XAI_PRIMARY` | xhigh | Sol Native XHigh → Luna Native XHigh |
| `CRITICAL_ARBITRATION` | xhigh | Sol Native XHigh → Sol Native Max |
| `TERRA_EXPLICIT` | low | Terra opt-in → Sol Native High |
| `GEMINI_EXPLICIT_FAST_BREADTH` | medium | Gemini Medium → Luna Native XHigh；当前首项 blocked |

首项被静态门排除时从下一项开始，不得伪称运行时失败。fallback 必须满足最低 thinking、Provider 与数据边界；Sol Medium 质量不足时只能沿预声明 Sol High，机械 Luna 失败时可沿预声明 Sol Medium。Terra 只能作为显式请求的首项，不能静默 fallback。

机械画像的 RoutePlan 全局最低值为 Medium，以允许预声明 Sol Medium fallback；registry 的逐模型下限仍强制 Luna 至少 XHigh。

## RoutePlan v3

每个新 RoutePlan 顶层写 `schema_version: "3.0"`。Standard 原生候选示例：

```json
{
  "surface": "native_subagent",
  "model": "gpt-5.6-luna",
  "thinking": "xhigh",
  "speed": "standard",
  "fork_turns": "none",
  "runtime_evidence": {
    "kind": "live_spawn_schema",
    "surface": "native_subagent",
    "model": "gpt-5.6-luna",
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
