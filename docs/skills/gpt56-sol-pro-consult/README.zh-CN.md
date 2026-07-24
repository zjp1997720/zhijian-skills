# GPT 5.6 Sol Pro Consult

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="GPT 5.6 Sol Pro Consult 把真实证据送入完成模型核验的二次判断闭环">
</p>

<p align="center"><strong>通过 Codex Chrome 获得有文件依据、完成模型核验的 GPT 5.6 Sol Pro 二次判断。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/gpt56-sol-pro-consult">统一源码</a></p>

适合需要外部挑战、并且必须基于真实文件做判断的复杂问题。OpenCLI 是可选后备路径，不是安装前提。

## 安装

```bash
npx skills add zjp1997720/zhijian-skills \
  --global --agent codex --skill gpt56-sol-pro-consult --yes
```

## 使用条件

- Codex 已连接 Chrome 插件
- 选中的 Chrome Profile 已登录 ChatGPT
- ChatGPT 模型选择器中可用 `Pro`
- Python 3.10 或更高版本，用于运行内置扫描器和测试
- 只有明确需要后备路径时才安装 OpenCLI

## 它会完成什么

- 把决策目标、证据、约束、本地判断、风险和未知项整理成结构化上下文包。
- 默认通过 Codex Chrome 完成文本输入、模型选择、附件上传、等待和结果提取。
- 发送前确认模型选择器显示 GPT-5.6 Sol，并且精确的 `Pro` 选项处于选中状态。
- 在一次 Chrome 调用内完成文件选择器生命周期；上传后重新定位输入框，并核验正文前缀与 Sentinel。
- 输入框空白时只使用一次精确的“在文本字段中显示”恢复；发送结果不确定时恢复原会话，禁止重复提交。
- 外发前扫描 token、Cookie、密码、API Key、私钥等凭据特征。
- 等待完整回答，并用唯一 Sentinel 验证咨询确实结束。
- 把 Pro 的意见带回本地工作流，明确哪些采用、拒绝或修改。

## 工作方式

```text
本地先形成判断
  -> 组织上下文包和真实证据
  -> 扫描凭据
  -> Codex Chrome
  -> 核验 GPT-5.6 Sol + Pro 已选中
  -> 核验输入框正文与附件
  -> 只提交一次并等待完成
  -> 提取完整回答
  -> 本地验证并形成最终判断
```

Pro 的回答属于外部会诊意见。本地 Agent 负责核对证据并交付最终结果。

## 示例

```text
让 GPT 5.6 Sol Pro 挑战这个架构决策。把相关源码作为真实附件提交，并带回最强反方意见。
```

```text
我在四种企业 AI 培训产品之间做选择。你先形成判断，再让 Pro 找最大漏洞，只合并有依据的建议。
```

```text
把这个本地 Skill 当成完整产物审查。上传实际相关文件，不要假设 ChatGPT 能读取本地路径。
```

## 安全边界与限制

- 咨询会把选中的材料提交给 ChatGPT Web，发送前需要确认证据范围。
- 禁止发送 token、Cookie、密码、API Key、私钥、OAuth Header、浏览器 Profile 和会话转储。
- ChatGPT 无法直接读取本地路径。需要上传文件、粘贴内容或生成 Markdown Bundle。
- 模型、附件、完整回答或 Sentinel 任一项无法核验时，本次咨询视为未完成。
- OpenCLI 只承担可选的纯文本后备路径；真实文件上传使用 Codex Chrome。

## 安装包结构

```text
gpt56-sol-pro-consult/
├── SKILL.md
├── agents/openai.yaml
├── evals/evals.json
├── references/
├── scripts/
└── tests/
```

## 协议

MIT，详见仓库根目录的 `LICENSE` 文件。
