# html-express

`html-express` 是一个 Agent Skill，用来把信息密集的内容整理成一个干净、自包含、可双击打开的 HTML 文件。

适合调研报告、对比矩阵、清单、时间线、数据看板、决策页和视觉化总结。它解决的问题很简单：当 Markdown 变成一堵文字墙时，用 HTML 让信息重新变得可读。

## 它做什么

- 判断信息形态。
- 选择合适的 HTML/CSS 组件。
- 生成单个 `.html` 文件。
- 把 CSS 内联进最终文件，不需要构建、不需要服务端。

## 内置组件

组件片段在 `assets/components/`：

| 组件 | 适合什么 |
|---|---|
| `metric-card` | 关键指标、状态数字 |
| `comparison-table` | 多方案横向对比 |
| `data-table` | 结构化数据 |
| `timeline` | 时间线、路线图 |
| `checklist` | 步骤、SOP、检查项 |
| `quote-card` | 判断、引用、重点结论 |
| `code-block` | 命令、配置、代码 |
| `details` | 折叠长内容 |
| `badge` | 状态标签 |
| `columns` | 多视角并置 |

## 安装

```bash
npx skills add zjp1997720/html-express -g -a codex --skill html-express -y
```

## 示例请求

```text
使用 $html-express 把这份调研整理成一页 HTML 报告。
```

```text
把这三个方案做成一个对比看板，输出自包含 HTML。
```

```text
根据这些项目笔记生成一个时间线 + 检查清单页面。
```

## 工作流

完整的 Agent 指令在 `SKILL.md`。

简版流程：

1. 识别信息形态。
2. 选择 2-5 个组件。
3. 从 `assets/skeleton.html` 开始。
4. 内联 `assets/tokens.css`。
5. 填入真实内容。
6. 保存单个 `.html` 文件并本地验证。

## 视觉风格

默认风格是 Warm Paper：暖纸背景、克制陶色强调、墨蓝结构、易读字体、少装饰。

你可以替换 `assets/tokens.css` 成自己的品牌系统，只要保留组件 class 和自包含输出规则。

## 许可证

MIT
