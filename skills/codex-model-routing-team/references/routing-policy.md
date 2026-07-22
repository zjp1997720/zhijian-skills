# 路由策略

## 是否创建后台任务

出现下列信号时评估并行；单个信号不强制触发：

- 至少 2 条互不依赖的工作流。
- 输入可按来源、章节、模块或主题拆分。
- 独立验证能降低主 Agent 的自证偏差。
- 任务跨调研、写作、编码、设计、测试或审查多个领域。
- 预计节省的时间或质量增益明显高于协调成本。

典型任务创建 2–3 个 Worker；广泛调研或多模块任务创建 4–6 个。简单问答、状态查询、单文件小改、强顺序流程直接由主 Agent 完成。

## 选择顺序

路由优先级固定为：

1. 数据边界、Provider 条款、工具需求、任务风险和最低 `thinking` 等硬门。
2. [模型注册表](model-registry.json) 的 automatic/manual-only 状态。
3. [恢复策略](recovery-policy.md) 中精确组合的熔断与近期健康证据。
4. 对应任务类型的能力匹配和独立验证需求。
5. 延迟、配额与稳定性信号。
6. 下表的稳定顺序作为最终 tie-break。

禁止只因模型更快或订阅额度看似充足而绕过前四项。

## 模型与推理强度

精确 ID、允许的 `thinking` 和自动状态以 [模型注册表](model-registry.json) 为唯一策略事实源。Codex App 工具元数据与本地 catalog 只验证当前 host 的运行接受性，不能自动把未知模型加入策略。

| 路由名 | `model` | `thinking` | 适用工作 |
| --- | --- | --- | --- |
| Luna High | `gpt-5.6-luna` | `high` | 机械提取、格式整理、分类、简单验证 |
| Luna X High | `gpt-5.6-luna` | `xhigh` | 默认 Worker；调研、初稿、方案扩展、常规编码与审查 |
| Luna Max | `gpt-5.6-luna` | `max` | 边界清晰、难度高、时效不敏感的深度执行 |
| Sol High | `gpt-5.6-sol` | `high` | 高歧义规划、架构、困难调试、高风险判断、关键审查 |
| Sol X High | `gpt-5.6-sol` | `xhigh` | 需要更深推理的关键审查与方案裁决 |
| Sol Max | `gpt-5.6-sol` | `max` | 有明确质量理由的最高强度单任务，必须说明升级原因 |
| Grok Medium | `xai/grok-4.5` | `medium` | 延迟敏感的技术分析、常规 Agent 执行、独立复核 |
| Grok High | `xai/grok-4.5` | `high` | 复杂编码、终端任务、长 Agent 循环、跨 provider 工程审查 |
| Gemini Low | `antigravity/gemini-3.6-flash` | `low` | blocked manual-review 模板：机械扫描与结构化提取 |
| Gemini Medium | `antigravity/gemini-3.6-flash` | `medium` | blocked manual-review 模板：高速广度、长上下文和多模态分析 |
| Gemini High | `antigravity/gemini-3.6-flash` | `high` | blocked manual-review 模板：复杂多模态或 Agent 执行 |

Grok 是条件自动候选，必须通过 runtime/provider 预检。Gemini Antigravity 是 manual-only 且当前 `terms_default: blocked`；它在模型表中出现用于解释显式请求和未来迁移，不代表当前路径可以创建。

Ultra 永久禁止。Terra 默认关闭。不得把成本比例、订阅额度或 TPS 写成未经当前环境验证的固定事实。

thinking 比较顺序固定为 `low < medium < high < xhigh < max`。跨模型 fallback 只比较该顺序与目标模型实际支持的值；任何候选都不得低于 RoutePlan 的 `minimum_thinking`。

## 任务画像与候选链

每个子任务在派遣前选择一个画像并固化候选链：

| 画像 | 最低 thinking | 主候选 → fallback | 说明 |
| --- | --- | --- | --- |
| `DEFAULT_GENERAL` | high | Luna X High → Sol High | 通用研究、写作、常规编码与验证 |
| `FAST_MECHANICAL` | high | Luna High → Luna X High | 低风险提取、分类和格式整理 |
| `DEEP_AGENTIC_CODE` | high | Grok High → Sol High | Grok/provider 通过硬门后用于复杂工程执行；否则直接从 Sol 开始 |
| `REVIEW_OPENAI_PRIMARY` | high | Grok High → Sol X High | OpenAI 主执行后的异构复核；xAI 不可用时回到 Sol |
| `REVIEW_XAI_PRIMARY` | xhigh | Sol X High → Luna X High | xAI 主执行后的 OpenAI 复核 |
| `REVIEW_COMPLIANT_GEMINI_PRIMARY` | high | Sol X High → Grok High | 未来合规 Gemini registry entry 主执行后的异构复核；两项都必须在 Provider allowlist |
| `CRITICAL_ARBITRATION` | xhigh | Sol X High → Sol Max | 关键裁决不把 Grok/Gemini 作为最终质量降级路径；它们可以作为挑战者 |
| `GEMINI_EXPLICIT_FAST_BREADTH` | medium | Gemini Medium → Luna X High | manual review 模板；当前 Antigravity 第三方登录条款为 blocked，不能执行 |
| `GEMINI_EXPLICIT_MULTIMODAL` | high | Gemini High → Sol High | manual review 模板；正式 API 路径需新建 registry entry 后才能执行 |

fallback 必须满足任务的最低 `thinking`。如果候选链中的首项被静态门排除，派遣通知应直接说明从下一项开始，不能伪称发生了运行时失败。

用户指定具体 fallback 时，先把它写入 concrete RoutePlan，再运行：

```bash
python3 scripts/validate_route_plan.py /path/to/route-plan.json
```

通过验证的用户链优先于画像默认链；不满足 Provider allowlist、最低 thinking、两 Worker 上限或无循环约束时拒绝采用，并回到上表的确定性链。

## 数量与失败升级

- 并发上限 6；root `creation_attempt` 上限 8，替换、超时歧义和未实体化尝试也计数。
- 创建前计算 `planned_workers + reserved_slots <= 8`。reserved slots 用于上游后续阶段和失败恢复，不能被前期并行任务占用。
- Deep Research 默认预算为 `2-4 researcher + 1 verifier + 1 reviewer + 2 retry reserve`。需要 5–6 个 researcher 时必须显式减少重试预留，禁止挤掉验证阶段。
- 完整输出质量不足时，同一 Thread 最多追问一次；仍失败才创建候选链中的第二 Worker。
- 同一子任务最多创建两个 Worker Thread，禁止无条件重复创建。
- 主 Agent 可组合不同 provider 做独立验证，不设置僵硬模型配额。

## 工作区与冲突

- 默认把可写任务按互斥文件或目录分配到同一项目的 local 环境。
- 只要任务包声明工作区输出路径，就必须使用匹配 project local；主题通用不构成 projectless 理由。
- projectless 只用于纯聊天交付且没有任何工作区产物的任务。
- 共享同一文件时实行单写者规则，其他 Worker 只提供建议或补丁说明。
- 跨模块且有合并风险的工程任务可使用 worktree；主 Agent 负责比较、移植和验证。
- 无法确认项目、起始状态、Provider 数据边界或合并路径时，留在主任务执行。
