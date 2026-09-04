# 预设策略

## 内置预设

- `graphite-paper`：通用默认预设。只使用中性矢量工作流图、系统字体回退和无品牌配色。
- `zhijian-ai`：独立的智见 AI 暖纸预设。使用思源宋体栈、暖纸色板和用户确认的“控制杆启动”横幅。

先运行 `scripts/list-presets.mjs --json` 查看预设及图片哈希。导入会复制到用户状态目录，不直接修改 Skill 源文件：

```bash
./scripts/import-preset-macos.sh --id graphite-paper --no-apply
./scripts/import-preset-macos.sh --id zhijian-ai --no-apply
```

只有用户明确要求立即应用、且已授权必要的 Codex 重启时，才使用 `--apply`。

## 用户主题

用户图片、字体选择和主题配置保存在本机运行状态目录。不得把用户素材、账号信息、对话截图或绝对路径回写到发布包。升级引擎时，活动主题 ID 与内置默认 ID 不同则保留。

## 智见预设授权

允许随本 Skill 在官方 macOS Codex 中展示和使用智见预设。软件 MIT 许可不等于品牌素材的无限授权；不得拆包转售、改成其他品牌、声称原创或把角色素材用于无关商业项目。详见 `NOTICE.md` 与 `references/asset-provenance.md`。
