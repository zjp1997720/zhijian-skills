# 微信公众号文章搜索

[English](README.md)

按关键词搜索微信公众号文章，返回结构化 JSON：标题、摘要、发布时间、来源公众号、链接。无需 API Key。

## 安装

```bash
npx skills add zjp1997720/wechat-article-search -g -a codex --skill wechat-article-search -y
```

## 环境要求

- Node.js 18+（在 Node 20 上验证过）
- 唯一依赖 `cheerio`。安装后在 skill 目录运行 `npm install` 即可。

## 解决什么问题

想找某个主题的公众号文章，但不知道是哪个账号写的——这个 skill 解决的就是「关键词发现」。输入关键词，跨全网公众号返回匹配的文章列表。

跟「按账号抓正文」的工具是两个环节，可串联使用。

## 它做什么

- **关键词搜索**：通过搜狗微信搜索，每次返回 1–50 篇文章。
- **结构化输出**：标题、链接、摘要、发布时间、来源公众号名。
- **真实链接解析**（`-r`）：把搜狗中间链接解析成 `mp.weixin.qq.com` 直链。
- **文件输出**（`-o`）：把结果写到 JSON 文件留档。

## 工作原理

skill 驱动一个自包含的 Node.js 脚本（`scripts/search_wechat.js`），通过搜狗微信搜索（`weixin.sogou.com`）发起请求，用 `cheerio` 解析 HTML，输出结构化 JSON 到 stdout。不依赖任何 API Key、MCP 工具或平台生态——任何能跑 `node` 的 agent 都能用。

## 使用示例

```
搜一下"Loop Engineering"的公众号文章，给我 10 条。
```

```
搜"AI培训"相关的公众号文章，要 5 条，保存到 result.json。
```

## 命令行用法

```bash
node scripts/search_wechat.js "<关键词>" [-n <数量>] [-o <输出文件>] [-r]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `query` | 必填 | 搜索关键词 |
| `-n, --num` | 10 | 返回数量（最大 50） |
| `-o, --output` | stdout | 输出到 JSON 文件 |
| `-r, --resolve-url` | 关 | 解析真实微信文章直链（较慢，反爬下易失败） |

首次使用：在 skill 目录跑一次 `npm install` 装 `cheerio`。

## 限制与免责

- 数据源是公开的搜狗微信搜索，受反爬策略影响，**偶发返回空结果或链接解析失败属正常现象**，换关键词或稍后重试即可。
- `-r` 解析真实链接在反爬收紧时成功率低，失败会保留搜狗中间链接并标记 `url_resolved: false`。
- 仅用于学习研究和个人资料整理，不要高频调用，不要做大规模商业爬取。过度使用可能导致 IP 被临时封禁。

## 目录结构

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── SKILL.md
├── agents/openai.yaml
├── package.json
└── scripts/
    └── search_wechat.js
```

## 许可证

MIT
