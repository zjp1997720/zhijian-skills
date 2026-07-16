# Codex Doctor

[English](README.md)

一套面向 Codex 的只读健康检查 Skill，用来发现安装、配置和工作区上下文中的真实问题。

## 安装

```bash
npx skills add zjp1997720/codex-doctor -g -a codex --skill codex-doctor -y
```

安装后显式调用 `$codex-doctor`，或直接告诉 Codex“运行一次工作区健康检查”。

> Codex 当前不会把这个 Skill 注册成命令面板里的斜杠命令。请使用 `$codex-doctor` 或自然语言触发，不要直接输入 `/doctor`。

## 为什么做它

一个长期使用的 Agent 工作区会不断积累 `AGENTS.md`、Skills、MCP、hooks、配置和生成文件。时间久了，规则可能超过有效上下文上限，出现重复、失效引用和作用域错位，真正重要的约束反而更难被模型稳定执行。

Claude Code 在 [v2.1.205](https://github.com/anthropics/claude-code/releases/tag/v2.1.205) 把 `/doctor` 升级为完整的 setup checkup，又在 [v2.1.206](https://github.com/anthropics/claude-code/releases/tag/v2.1.206) 增加了“识别仓库本身可以推导出的 `CLAUDE.md` 内容”。Codex Doctor 复刻了这套核心思路，并换成 Codex 原生语义：`AGENTS.md`、Skills、MCP、hooks 和 `codex doctor --json`。

## 环境要求

- 支持 `codex doctor --json` 的 Codex CLI
- Python 3.11+
- Git
- macOS 或 Linux

扫描器只使用 Python 标准库。

## 它能做什么

- 合并 Codex 原生运行时诊断与确定性的工作区只读扫描。
- 检查有效 `AGENTS.md` 链、上下文体积、精确重复、Skills、MCP、hooks、配置、Git 状态和仓库根目录卫生。
- 把“机器可以证明的问题”和“需要模型理解语义的裁剪候选”分开，再对每一项修复单独授权。

它不会执行 hooks、暴露密钥值、自动删规则、停用扩展、更新 Codex、修改权限或直接修复文件。

## 工作原理

Codex Doctor 采用四层结构：

1. **原生诊断层**：直接消费 `codex doctor --json`，避免重复实现和版本漂移。
2. **确定性扫描层**：只读采集工作区配置和上下文治理证据，并对敏感值脱敏。
3. **模型判断层**：区分可删除的静态清单与必须保留的业务事实、安全边界、品牌表达、Git 规则和目录契约。
4. **受控修复层**：用户明确要求修复后，每次只展示一个 finding 和一个文件 diff；应用前核对 SHA-256，应用后重跑对应检查。

这层分工解决了一个关键问题：脚本可以证明两段文字完全相同，却无法安全判断这种重复是否承担跨宿主同步或安全强化作用。

## 使用示例

```text
使用 $codex-doctor 做一次完整健康检查。只诊断，不修改文件。

使用 $codex-doctor 检查 Codex 为什么总是忽略当前项目的 AGENTS.md。

使用 $codex-doctor 审计失效或低价值的 Skills、MCP 和 hooks，先给证据，再提修改方案。
```

也可以直接运行内置扫描器：

```bash
python3 scripts/scan_workspace.py --cwd /path/to/project --compact-json
```

## 安全机制

默认行为是只读诊断。严重等级只表示影响，不代表自动获得修复权限。

删除或改写规则、修改配置、启停组件、移动文件，都需要逐 finding 明确授权。扫描器只报告疑似密钥所在位置和键名，不输出真实值。

完整的证据门、授权门、并发校验和复测规则见[检查与修复政策](references/checks-and-repair-policy.md)。

## 仓库结构

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/checks-and-repair-policy.md
├── scripts/scan_workspace.py
├── tests/test_scan_workspace.py
└── evals/evals.json
```

## 开发与验证

```bash
python3 -m unittest discover -s tests -v
python3 scripts/scan_workspace.py --cwd /path/to/project --compact-json
```

当前测试覆盖指令作用域与截断、敏感值脱敏、MCP 与 hook 校验、Git 卫生、紧凑报告完整性和修复安全假设。

## 许可证

[MIT](LICENSE)
