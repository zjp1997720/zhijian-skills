# WorkBuddy CLI Model Bridge

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="WorkBuddy CLI Model Bridge 通过本地代理把已验证的 CLI 订阅模型接入 WorkBuddy">
</p>

<p align="center"><strong>自动安装、授权、探测并注册 CLI 订阅模型，避免手工处理凭证和 WorkBuddy 配置。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/workbuddy-cli-model-bridge">唯一源码</a></p>

当你希望在 WorkBuddy 中使用 Codex、Grok、AntiGravity/Gemini，现有本地模型链路失效，或者需要接入一个新的 CLI Provider 时，使用这个 Skill。

## 安装到 Agent

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill workbuddy-cli-model-bridge --agent codex --global --copy --yes
```

完整载荷同时支持 Claude Code 和通用 Agents-compatible Harness。

## 运行要求

- macOS
- Python 3.11 或更高版本；运行代码只使用标准库
- 已安装 WorkBuddy，并至少启动过一次
- 全新安装 CLIProxyAPI 时需要 Homebrew
- 每个 OAuth Provider 使用用户本人拥有的账户

## 它会做什么

- 只读审计 Homebrew、CLIProxyAPI、WorkBuddy、已安装 CLI、OAuth 文件数量和模型可用性，不读取 Token 内容。
- 在全新 macOS 环境中通过官方 Homebrew Formula 安装 CLIProxyAPI。
- 发现健康的手工版或 LaunchAgent 部署时继续复用，不强制迁移。
- 使用 CLIProxyAPI 原生的 Codex、xAI 和 AntiGravity OAuth 流程。
- 注册前实测文本、流式输出、工具、图片和推理控制。
- 图片探测使用 256×192 的红色方块与蓝色圆形组合；极小图片造成的歧义，或接口只接受图片参数但没有正确识别内容，都不算验证通过。
- 备份并原子合并 WorkBuddy 模型，保留用户手工条目。
- 通过机器本地 Provider 注册表扩展其他 CLI，不修改公共 Skill。

## 快速使用

直接告诉 Agent：

```text
使用 $workbuddy-cli-model-bridge 检测我已经登录的 CLI Agent，安装或修复 CLIProxyAPI，并把通过验证的推荐模型注册到 WorkBuddy。
```

也可以在安装后的 Skill 目录中直接运行确定性阶段：

```bash
python3 scripts/bridge.py audit
python3 scripts/bridge.py bootstrap --apply
python3 scripts/bridge.py authorize codex
python3 scripts/bridge.py sync --providers codex --apply
```

OAuth 阶段可能会打开浏览器。用户完成授权后，Agent 会继续执行。

## 内置 Provider

| Provider | CLI 信号 | CLIProxyAPI OAuth | 推荐路由 |
| --- | --- | --- | --- |
| OpenAI Codex | `codex` | `--codex-login` | GPT Sol 主力模型；已暴露且验证通过时注册 Fast 别名 |
| xAI Grok | `grok` | `--xai-login` | Grok 主力模型和可选 Fast 模型 |
| Google AntiGravity | `antigravity` / `agy` | `--antigravity-login` | Gemini Flash 主力模型 |

Provider 清单根据实时 `/v1/models` 选择模型。当前模型 ID 是带回退顺序的偏好，Skill 不会制造上游不存在的别名。

只有 CLIProxyAPI 已暴露且请求验证通过时，Skill 才注册 Fast 条目。CLIProxyAPI 对 OAuth 路由的正式做法是组合 `oauth-model-alias` 与对应的 `payload` 覆盖，例如 `service_tier: priority`；桥接器不会仅凭模型名把普通路由标记成 Fast。

## 推理内容可见性

桥接器会验证路由是否接受已配置的推理控制，但无法暴露 Provider 的私有思维链。WorkBuddy 可能显示 Provider 返回的推理概要或进度标题；录课需要完整拆解时，应要求模型把可教学的分步说明作为正常回答正文输出。

## 新 Provider 接入

机器本地 Provider 清单存放在：

```text
$HOME/.config/workbuddy-cli-model-bridge/providers.d/
```

接入顺序固定为：CLIProxyAPI 原生 OAuth、官方 OpenAI-compatible 接口、声明式别名，最后才考虑有明确风险说明的受限本地转接器。使用前先验证：

```bash
python3 scripts/bridge.py validate-provider path/to/provider.json
```

完整规则见安装包中的 `references/provider-schema.md` 和 `references/onboarding-new-cli.md`。

## 安全边界

- CLIProxyAPI 明确绑定到 loopback。
- 远程管理保持关闭。
- 不把原生 CLI Token 复制到代理。
- 本地代理 Key、OAuth 文件、WorkBuddy 配置和含凭证备份使用仅当前用户可读权限。
- 报告隐藏 Key、Token、账户标识、一次性授权码、Prompt 和图片。
- 保留 WorkBuddy 手工模型；ID 冲突时停止覆盖对应模型。
- Provider 服务条款和订阅限制继续有效；Skill 不提供配额或封禁规避。

## 开发与验证

```bash
python3 -m unittest discover -s skills/workbuddy-cli-model-bridge/tests -v
python3 skills/workbuddy-cli-model-bridge/scripts/bridge.py \
  validate-provider skills/workbuddy-cli-model-bridge/providers/codex.json
```

测试使用隔离临时 Home 和模拟 OpenAI-compatible 服务，覆盖 Provider 安全、密钥脱敏、模型选择、手工配置保护、能力降级、原子写入、备份和重复同步幂等性。

## 上游资料

- [CLIProxyAPI 仓库](https://github.com/router-for-me/CLIProxyAPI)
- [官方 macOS 快速开始](https://help.router-for.me/introduction/quick-start)
- [配置项、OAuth 别名与 Payload 规则](https://help.router-for.me/configuration/options)
- [Codex OAuth](https://help.router-for.me/configuration/provider/codex)、[xAI OAuth](https://help.router-for.me/configuration/provider/xai) 与 [AntiGravity OAuth](https://help.router-for.me/configuration/provider/antigravity)

## 许可证

[MIT](../../../skills/workbuddy-cli-model-bridge/LICENSE)
