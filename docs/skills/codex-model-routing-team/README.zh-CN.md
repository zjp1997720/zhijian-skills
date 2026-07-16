# Codex 模型路由团队

[English](README.md)

让 Codex 主 Agent 继续负责规划、集成和验收，同时把复杂任务交给可以分别指定模型与推理强度的独立后台任务。

## 安装

这条常用简写是 `skills` CLI 的正确语法：

```bash
npx skills add zjp1997720/codex-model-routing-team
```

推荐用下面的命令全局安装到 Codex，并复制真实文件而不是创建软链接：

```bash
npx skills add zjp1997720/codex-model-routing-team \
  -g -a codex --skill codex-model-routing-team --copy -y
```

完整 GitHub 链接同样有效：

```bash
npx skills add https://github.com/zjp1997720/codex-model-routing-team
```

安装后检查入口文件和配套策略是否齐全：

```bash
npx skills ls -g -a codex
find ~/.agents/skills/codex-model-routing-team -maxdepth 2 -type f | sort
```

文件列表至少应包含 `SKILL.md`、`references/routing-policy.md`、`references/task-packet.md` 和 `references/thread-lifecycle.md`。如果只有 `SKILL.md`，说明装到的是旧版残缺包，删除后重新安装当前版本。

## 启用方式

安装完成后，可以直接点名使用：

```text
使用 $codex-model-routing-team 并行调研这 6 个互不依赖的主题，最后统一核验并整合结论。
```

如果希望 Codex 自动判断复杂度并主动使用这个 Skill，把下面的长期授权加入 `~/.codex/AGENTS.md`。只想在某个项目中启用时，把它放到该项目的 `AGENTS.md`。

```markdown
## Codex 后台模型路由授权

- 用户长期授权 Codex 在复杂、可并行任务中自动使用 `$codex-model-routing-team` 创建独立后台任务，并为其指定模型与推理强度；派遣前用一条简短通知说明数量、模型、强度和职责，无需再次确认。
- 主 Agent 保持当前模型，负责规划、文件所有权、集成、验证和最终交付。
- 同时运行最多 6 个后台任务；单个根任务累计最多创建 8 个。后台任务不得再创建任何后台任务或子 Agent。
- 后台任务禁止使用 Ultra；Terra 默认不参与路由。无法使用 Codex App 后台任务接口时，主 Agent 本地完成，禁止回退到 MultiAgentV2 `spawn_agent` 冒充模型路由。
- 简单问答、状态查询、单文件小改、强顺序任务以及发布、发送、付款、删除、账户或生产操作不自动派遣。
```

这段内容是用户自己配置的 Codex 指令，不是 OpenAI 隐藏的系统提示词。没有长期授权时，仍然可以通过点名 `$codex-model-routing-team` 手动启用。

## 为什么需要它

Codex 原生 MultiAgentV2 当前没有暴露按 Worker 选择模型和推理强度的能力。原生 Subagent 会继承当前会话模型，并行任务可能因此产生远高于预期的 Token 成本。

这个 Skill 改用 Codex App 的独立后台任务。主 Agent 负责判断复杂度、拆分任务、分配互斥的文件所有权、核验结果和最终整合；每个后台任务都显式获得一个当前可用的模型与推理强度。

## 主要能力

- 只路由真正复杂且可并行的任务，例如多来源调研、多章节内容、复杂 Skill 或 PPT、跨模块开发和独立验证。
- 默认围绕 Sol 与 Luna 路由，禁止 Ultra；Terra 默认不参加自动路由，除非用户明确要求或任务证据支持。
- 每波最多新增 3 个任务，同时运行最多 6 个，单个根任务累计最多 8 个。
- 首个任务充当健康探针；每个任务都要验证已经真实创建；后台任务禁止继续派生任务；只归档已完成且结果被采纳的任务。
- 可以作为 Deep Research 等上游 Skill 的 Thread Orchestrator，保留上游流程、阶段门、产物和质量标准。
- 发布、付款、删除、账户操作和生产变更始终由主 Agent 执行。

## 工作方式

1. 主 Agent 判断并行收益是否高于协调成本。
2. 创建第一个真实后台任务作为健康探针，确认可以读取后再继续。
3. 后续任务按受控批次创建，并明确模型、推理强度、范围、文件所有权和验收标准。
4. 主 Agent 亲自核验事实与产物、处理冲突并完成最终交付。
5. 已采纳且完成的任务逐个归档。

上游 Skill 已经完成任务拆分时，本 Skill 接受其阶段顺序和任务预算，只负责模型路由、任务生命周期与安全上限。声明工作区输出路径的任务始终绑定项目；只有纯聊天交付才能使用 projectless。

Deep Research 默认预算为 `2-4 个 researcher + 1 个 verifier + 1 个 reviewer + 2 个重试位`，总数不超过 8 个。

## 使用示例

```text
使用 $codex-model-routing-team 分别实现、测试和审查 3 个独立模块，避免文件所有权重叠。
```

```text
使用 $codex-model-routing-team 准备一套培训 PPT，分别安排调研、写作和审查任务。
```

```text
让 $codex-model-routing-team 作为 $deep-research 的 Thread Orchestrator，保留 verifier 和 reviewer 阶段。
```

## 环境要求与边界

- Codex App 能够提供项目定位、后台任务创建、任务读取、追问和归档工具。
- 当前账号可以使用主 Agent 选择的模型与推理强度。
- 后台任务必须能够验证已经真实创建；验证失败时停止委派。
- 这个 Skill 不会修改 MultiAgentV2，也不会让原生 Subagent 获得按 Agent 选择模型的能力。

## 仓库结构

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── skills/
│   └── codex-model-routing-team/
│       ├── SKILL.md
│       ├── agents/
│       ├── evals/
│       └── references/
└── tests/
```

Agent 的完整工作流见 [SKILL.md](skills/codex-model-routing-team/SKILL.md)，配套策略见 [references](skills/codex-model-routing-team/references/)。

## 验证情况

工作流已经在独立调研任务和绑定工作区的写入任务中完成实测，覆盖模型与推理强度核验、结果读取、失败处理和串行归档。发布包还会在隔离环境中执行一次真实的 `npx skills` 安装，确认配套文件被完整复制。

## 许可证

[MIT](LICENSE)
