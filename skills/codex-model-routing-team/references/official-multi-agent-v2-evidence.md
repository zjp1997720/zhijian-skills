# Codex Multi-Agent V2 官方依据

本页只记录会改变路由合同的官方事实，不替代当前 host 的 live schema 预检。

## 依据

- OpenAI Codex PR [Support leaf models in multi-agent v2](https://github.com/openai/codex/pull/36892) 把 V2 父 Agent 的子模型范围扩展到 picker 可见且未显式禁用的 leaf model。
- Codex [rust-v0.147.0 release](https://github.com/openai/codex/releases/tag/rust-v0.147.0) 收录了 leaf-model support。
- OpenAI [Codex Subagents documentation](https://developers.openai.com/codex/subagents) 说明本地 Codex 的多模型、每 Agent reasoning 与原生子任务 Surface。
- 当前定位依据（2026-09-23）：OpenAI [模型指南](https://learn.chatgpt.com/docs/models) 与 [GPT-6 Sol/Luna 发布说明](https://openai.com/index/introducing-gpt-6-sol-and-luna/)。Luna 适合明确、可验收的执行，Sol 保留未决判断与关键审查；评测不能替代当前任务验收。具体决策合同见 [路由策略](routing-policy.md)。

- 2026-09-23 使用已登录账号的 Codex Desktop CLI `0.155.0-alpha.16` 执行 `codex debug models`，官方目录列出 `gpt-6-sol`、`gpt-6-luna`，两者 `multi_agent_version=v2`。Sol 支持 Low 至 Ultra；Luna 支持 Low 至 Max。本 Skill 继续限制 Sol 最低 Medium、Luna 最低 XHigh，并禁止 Ultra。
- 上述 catalog 是模型能力证据，不是当前运行中 host 的 live schema；旧会话可能仍只暴露 5.6 标识。重新加载前不得伪造 GPT-6 派遣成功。

## GPT-6.1 Sol 升级（2026-09-30）

- 用户要求直接替换 Sol 执行型号。当前路由中的 Sol 精确标识为 `gpt-6.1-sol`；GPT-6 Luna 的默认执行分工保持，主 Agent 不切换模型。
- Codex Desktop CLI `0.159.0` 使用已登录账号刷新官方目录，返回 `gpt-6.1-sol`、`multi_agent_version=v2` 和 Medium/High/XHigh/Max 等档位。本 Skill 继续禁止 Ultra；账号目录不代替当前宿主的 live schema。
- [官方模型页](https://developers.openai.com/api/docs/models/gpt-6.1-sol)支持 Medium/High/XHigh/Max。上方 2026-09-23 的 GPT-6 Sol/Luna 记录保留为历史依据，不能视为 6.1 的重测成绩。

## 策略解释

- `gpt-6-luna` 继续作为原生 leaf Worker 使用；这是本 Skill 的权限限制，不是模型缺少 V2 能力。`gpt-6.1-sol` 同样不得继续派生 Worker。
- picker/catalog 资格不是当前 host 接受精确 `model + reasoning_effort + fork_turns + service_tier` 的证明。实际派遣前仍使用 live tool schema。
- 本 Skill 不使用 `model: luna` frontmatter。该 frontmatter 会把编排入口本身固定到 Luna Worker，与“父 Agent 负责 TeamPlan 和协作工具、Luna 只执行叶子单元”的合同冲突。
- App Thread 继续承担 worktree、侧栏可见、跨任务恢复和耐久监督；它不再是使用 Luna 的必要条件。

## 维护与回滚

- Owner：canonical Portfolio 的 `codex-model-routing-team` maintainer。
- Review cadence：Codex multi-agent / subagent schema 或模型 catalog 发生变化时立即复核；没有变更时至少每 90 天复核一次。
- Rollback boundary：如果当前 live schema 不再接受某个 Native tuple，只熔断该精确组合，并沿预声明下一候选前进；不得静默继承父模型。App Thread 仍需独立 live 能力与宿主授权。
