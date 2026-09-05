# Codex Multi-Agent V2 官方依据

本页只记录会改变路由合同的官方事实，不替代当前 host 的 live schema 预检。

## 依据

- OpenAI Codex PR [Support leaf models in multi-agent v2](https://github.com/openai/codex/pull/36892) 把 V2 父 Agent 的子模型范围扩展到 picker 可见且未显式禁用的 leaf model。
- Codex [rust-v0.147.0 release](https://github.com/openai/codex/releases/tag/rust-v0.147.0) 收录了 leaf-model support。
- OpenAI [Codex Subagents documentation](https://developers.openai.com/codex/subagents) 说明本地 Codex 的多模型、每 Agent reasoning 与原生子任务 Surface。
- OpenAI [GPT-5.6 Sol 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-sol) 与 [GPT-5.6 Luna 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-luna)（2026-09-05 复核）用于能力定位：Sol 面向复杂专业工作，Luna 面向高量、成本敏感且边界清楚的工作。它们不提供本任务的速度或成本实测。

## 策略解释

- `gpt-5.6-luna` 可以被 V2 父 Agent 作为原生 leaf Worker 创建；它自身仍不获得协作工具，不能继续派生 Worker。`gpt-5.6-sol` 作为常规原生 Worker 仍受本 Skill 的禁止下级派遣规则约束。
- picker/catalog 资格不是当前 host 接受精确 `model + reasoning_effort + fork_turns + service_tier` 的证明。实际派遣前仍使用 live tool schema。
- 本 Skill 不使用 `model: luna` frontmatter。该 frontmatter 会把编排入口本身固定到 leaf model，与“父 Agent 负责 TeamPlan 和协作工具、Luna 只执行叶子单元”的合同冲突。
- App Thread 继续承担 worktree、侧栏可见、跨任务恢复和耐久监督；它不再是使用 Luna 的必要条件。

## 维护与回滚

- Owner：canonical Portfolio 的 `codex-model-routing-team` maintainer。
- Review cadence：Codex multi-agent / subagent schema 或模型 catalog 发生变化时立即复核；没有变更时至少每 90 天复核一次。
- Rollback boundary：如果当前 live schema 不再接受某个 Native tuple，只熔断该精确组合，并沿预声明下一候选前进；不得静默继承父模型。App Thread 仍需独立 live 能力与宿主授权。
