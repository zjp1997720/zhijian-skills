# Codex 模型路由团队

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Codex 主 Agent 通过原生 V2 把执行任务路由给 Sol Medium，并把耐久任务留给 App Thread">
</p>

<p align="center"><strong>主 Agent 负责 TeamPlan、所有权、集成和验收；普通 Worker 默认走原生 Sol Medium，Luna 负责可机械验收的批量任务。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/codex-model-routing-team">统一源码</a></p>

适合存在明确净并行收益的任务。它把并行工作编译成轻量 TeamPlan，为每个单元固定 Surface、模型、推理强度、速度和上下文范围，再由主 Agent 统一验收。

## 安装

```bash
npx skills add zjp1997720/zhijian-skills
```

全局安装到 Codex，并复制真实文件：

```bash
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill codex-model-routing-team --copy -y
```

安装后检查：

```bash
npx skills ls -g -a codex
find ~/.agents/skills/codex-model-routing-team -maxdepth 2 -type f | sort
```

## 环境要求

- Codex 原生 Multi-Agent V2，或 Codex App Thread 工具，或两者。
- 当前 live schema 能确认 RoutePlan 里的精确模型、reasoning、context 和可选速度字段。
- 跨 Provider 路由前，项目数据边界、凭证路径和服务条款允许该候选。

## 启用

直接点名：

```text
使用 $codex-model-routing-team 并行调研这 6 个独立主题，最后统一核验。
```

需要自动触发时，把下面的授权放进用户级或项目级 `AGENTS.md`：

```markdown
## Codex 后台模型路由授权

- 可安全拆成至少两个独立交付物且并行净收益为正时，自动使用 `$codex-model-routing-team`；派遣前简报 Worker 数、Surface、模型、强度、速度和职责。
- 两个以上 Worker 先编译轻量 TeamPlan；已有上游计划时只编译。主 Agent 保持当前模型，负责所有权、集成和验收。
- 默认用 Native Sol Medium；复杂或高风险任务用 Sol High/XHigh，Luna XHigh 用于可机械验收的批量任务。App Task 需符合宿主授权及项目目录约束。
- Worker 禁止 Ultra、下级派遣和不可逆外部动作；实际波次必须为协调者预留 live slot。
```

## 为什么升级到 v3

OpenAI Codex 在 [leaf-model support PR](https://github.com/openai/codex/pull/36892) 与 [rust-v0.147.0](https://github.com/openai/codex/releases/tag/rust-v0.147.0) 中让 V2 父 Agent 可以创建 picker 可见且未禁用的 leaf model。Luna 虽然本身是 leaf、不能继续协作，但现在可以作为原生 V2 Worker。

最初 v3 把默认路径从“Luna App Thread”改为“Native Luna leaf Worker”；当前按工作负载采用常规 Sol Medium、机械批量 Luna XHigh。App Thread 仍保留给 worktree、侧栏可见、跨任务恢复和耐久监督。Skill 本身不添加 `model: luna` frontmatter，因为编排入口必须留在具备协作工具的父 Agent。

## 主要能力

- 净收益门：没有两个独立可验收交付物时，由主 Agent 直接完成。
- TeamPlan：校验依赖、同波写冲突、attempt、reserved slots 和集成顺序。
- RoutePlan v3：区分 `parent_integrated` 与 `durable_app`，Native 候选显式写 `fork_turns`。
- 精确路由：默认 Native Sol Medium Standard，复杂或高风险单元用 Sol High/XHigh；Fast 只在 live schema 接受 `service_tier=priority` 时启用。
- 生命周期：Native 结果按 live 能力 close 或 completed-idle 释放；App Thread 保留 pending、UNKNOWN、恢复和归档门。
- Provider 安全：Terra 仅显式首项，Grok 需过预检，Gemini Antigravity 当前 blocked。
- 主 Agent 保留发布、发送、付款、删除、账户和生产变更。

## 工作方式

1. 主 Agent 判断净并行收益，编译并校验 TeamPlan。
2. 每个 unit 生成 Task Packet 和 `schema_version: "3.0"` RoutePlan。
3. 普通任务写 `surface_intent=parent_integrated`，默认 Native Sol Medium；获宿主授权的耐久工作区写 `durable_app`。
4. Native fresh context 使用 `fork_turns="none"`；正整数字符串表示最近 N 轮；模型覆盖禁止 `all`。
5. 失败只沿预声明候选链，主 Agent按集成顺序验证真实产物。

轻量路径不需要落协调文件：

```bash
printf '%s' "$TEAM_PLAN_JSON" | python3 scripts/validate_team_plan.py -
printf '%s' "$ROUTE_PLAN_JSON" | python3 scripts/validate_route_plan.py -
printf '%s' "$TEAM_LEDGER_JSON" | python3 scripts/validate_team_ledger.py -
```

## 示例

```text
使用 $codex-model-routing-team 分别实现、测试和审查 3 个独立模块，避免文件所有权重叠。
```

```text
用 Native Sol XHigh 并行审计三个高风险模块；只有宿主授权且项目允许时，才把耐久工作区放到 App Task。
```

```text
让 $codex-model-routing-team 作为 $deep-research 的路由 Orchestrator，保留 verifier 和 reviewer 阶段。
```

## 安全与限制

- Sol Medium 为常规起点，复杂或高风险用 High/XHigh；Luna 保留 XHigh 下限，仅承担低风险批量工作；Ultra 永久禁止。
- picker/catalog 资格不是 live runtime 证据；没有精确 schema 证明时，不派遣该 tuple。
- Standard Native evidence 不伪造 speed/service tier；Fast 才绑定 priority evidence。
- v2.1 RoutePlan 仅用于完成既有 run；所有新计划使用 v3。
- App durable fallback 必须留在 App Surface，避免丢失 worktree 或恢复语义。

## 验证

确定性测试覆盖 Sol Medium、风险升级、stdin 编译器、App 授权、Native Luna、leaf 边界、fork scope、Fast live gate、durable App、RELEASED 生命周期、TeamPlan 档位、Provider 门、pending/UNKNOWN 恢复和隔离安装。

## 许可证

[MIT](../../../skills/codex-model-routing-team/LICENSE)

## Route compiler / 路由编译器

```bash
python3 scripts/compile_route_plan.py - < request.json
```

传入工作负载、风险、Provider 边界与当前宿主能力证据。编译器返回已校验的 RoutePlan 和派遣参数，本身不创建 Worker。详见[输入合同](../../../skills/codex-model-routing-team/references/route-compiler.md)。尚无同任务对照，不承诺比 Luna 更快或更便宜。
