---
name: wechat-article-search
description: "搜索微信公众号文章技能。通过微信搜索获取文章列表，覆盖科技/AI、社会热点、财经、教育、职场等各类中文资讯；可按关键词检索并返回标题、概要、发布时间、来源公众号与链接。当用户需要查找微信公众号文章、整理参考资料或快速获取文章信息时使用此技能。"
description_zh: "搜索微信公众号文章（标题、摘要、发布时间、来源账号、链接）"
description_en: "Search WeChat public account articles by keyword"
version: 0.1.0
allowed-tools: Bash,Read
metadata:
  clawdbot:
    emoji: "\U0001F50E"
    requires:
      bins:
        - node
display_name: "wechat-article-search"
display_name_en: "wechat-article-search"
visibility: "public"
---

# 微信公众号文章搜索说明

## 适用场景

- 用户说“帮我搜某个关键词的公众号文章/最近文章”
- 需要快速拿到：标题、摘要、发布时间、公众号名称、可访问链接

## 工作流程

### 步骤1: 确认已安装依赖包
该脚本依赖NodeJS依赖包 `cheerio`，建议先执行全局安装或在项目中安装：

```bash
npm install -g cheerio
```

### 步骤2: 确认搜索词语数量
1、 确认关键词与数量

### 步骤3: 执行搜索命令
1、执行常规搜索命令

```bash
node scripts/search_wechat.js "关键词" 
```

## 特殊流程（可选）
1) 执行包含数量限制的搜索命令

```bash
node scripts/search_wechat.js "关键词"  -n 15
```

2) 如果用户需要保存结果到文件，执行命令

```bash
node scripts/search_wechat.js "关键词" -n 20 -o result.json
```

3) 若想要获取微信文章域名的真实链接”，执行如下命令

```bash
node scripts/search_wechat.js "关键词" -n 5 -r
```

## 参数说明

- `query`：搜索关键词（必填）
- `-n, --num`：返回数量（默认 10，最大 50）
- `-o, --output`：输出 JSON 文件路径（可选）
- `-r, --resolve-url`：尝试把中间链接解析成微信文章真实链接（会额外请求每条结果）

## 输出字段（文章对象）
文章标题、文章地址、文章概要、发布时间、来源公众号名称

## 常见问题处理

- 结果为空：尝试更换关键词、更少的特殊字符、或稍后重试
- 解析真实 URL 失败：这是常态（反爬限制）；可提示用户用浏览器打开中间链接

## 注意事项

- 本工具仅用于学习和研究目的，请勿用于商业用途或大规模爬取。
- 使用本工具时请遵守相关网站的使用条款和规定。
- 过度使用可能导致 IP 被封禁，请谨慎使用。

---

## Vault 适配说明（deepsight_vault 专属，原版无此段）

> 以下内容由大鹏的 vault 自动追加，用于把本 skill 接入 Obsidian 仓库生态。原版说明见上方。

### 依赖安装（本仓库约定）

本 skill 在仓库内自包含依赖，**不要**全局安装。首次使用或克隆仓库后，在本 skill 目录执行一次：

```bash
cd .claude/skills/wechat-article-search
npm install
```

`cheerio` 会装到本目录的 `node_modules/`，已被 `.gitignore` 排除。脚本通过 Node 的向上查找机制能 `require('cheerio')`，无需配 `NODE_PATH`。

### 单一真源与同步

- 真源：`.claude/skills/wechat-article-search/`
- 同步：由 `scripts/sync-claude-skills.sh` 自动软链到 `.agents/skills/`、`.opencode/skills/`、`~/.codex/skills/`、`~/.config/opencode/skills/`、`.workbuddy/skills/`（LaunchAgent 监听 `.claude/skills` 目录变化 + git hook 兜底）。
- **改 skill 只改 `.claude/skills/wechat-article-search/`，不要直接改其它位置的软链。**

### 与 `wxmp-article-harvester` 的衔接

两个 skill 职责互补，可串联使用：

| 环节 | skill | 输入 | 输出 |
|------|-------|------|------|
| 关键词发现（本 skill） | `wechat-article-search` | 关键词，如「AI Agent」 | 文章列表 JSON（标题/链接/摘要/来源/时间） |
| 按账号/URL 抓正文 | `wxmp-article-harvester` | 公众号名或 `mp.weixin.qq.com/s/...` 链接 | 结构化索引 + Markdown 正文 |

典型链路：先用本 skill 按关键词发现一批文章 URL 和来源公众号 → 再用 harvester 对感兴趣的账号或具体 URL 抓取正文导出到 `~/.dapeng/wxmp-harvester/exports/`。

### 输出落点建议

- 临时检索：直接看 stdout JSON，不落盘。
- 需要留档：用 `-o` 写到 `00_收件箱/Clippings/` 或对应项目的来源目录，文件名带关键词和日期，如 `wechat-search-AI培训-2026-07-06.json`。
- 不要把搜索结果散落到仓库根目录。

### 反爬与免责（重要）

- 数据源是搜狗微信搜索（`weixin.sogou.com`），受反爬策略影响，**偶发返回空结果或被 antispider 拦截属正常现象**，换关键词或稍后重试即可。
- `-r` 解析真实链接在反爬收紧时成功率低，失败会保留搜狗中间链接并标记 `url_resolved: false`。
- 仅用于学习研究和个人资料整理，不要高频调用、不要做大规模商业爬取。
