# Scholar Stickers

Generate interactive 16:9 scholar and concept sticker slides for classroom instruction with zero-scroll layouts, portrait sketches, and expandable biography beats.

## Install

```bash
npx skills add zjp1997720/zhijian-skills --skill scholar-stickers
```

## Requirements

- Node.js 18+ (for `npx skills`)
- An AI Agent runtime supporting `SKILL.md` (e.g. WorkBuddy, Claude Code, Codex)
- Image generation capability (e.g. built-in multimodal generation, DALL-E, or local tools)

## What It Does

- Generates single-file 16:9 interactive slide presentations from figure lists or conceptual domains.
- Produces a structured overview sticker wall with hover-level perspective and click-to-navigate interactions.
- Builds dedicated figure detail slides with expandable biography blocks, three core contributions, two authoritative quotes, and two seminal texts.
- Enforces strict projection-first layout constraints: fixed 16:9 viewport scale, zero scrollbars, high-contrast serif typography, and legible font sizes from classroom back rows.

## How It Works

1. **Information Verification**: Searches and extracts strict 5-part dossiers (biography, contributions, quotes, texts, modern inspirations) with character-count limits.
2. **Portrait Sketch Generation**: Uses a unified graphite engraving prompt template to generate white-bordered sticker portraits (768×960 PNG).
3. **Template Assembly**: Populates `template.html` with theme tokens, metadata, and structured figure data into an isolated single HTML file.
4. **Interactive Delivery**: Provides keyboard navigation (`←`/`→`, `Esc`, `Home`, `End`), responsive scale fitting (`fitStage`), and instant local browser preview.

## Example Requests

- "Use scholar-stickers to create an interactive slide for 5 education philosophers: Socrates, Confucius, Rousseau, Dewey, and Piaget. Domain: Educational Philosophy. Title: Philosophy Starts with Wonder."
- "帮我做一份唐宋八大家的课堂人物讲解 HTML 页面，使用 scholar-stickers 技能。"
- "Create an interactive presentation introducing classical physicists: Newton, Maxwell, Einstein, and Bohr."

## Safety or Limitations

- **Fact Checking**: Historical facts, quotes, birth/death years, and publications must be verified against authoritative records before instructional use.
- **Image Generation Limits**: Text and image generation inherit model stochasticity; visual consistency is maintained via rigid prompt constraints and CSS framing.
- **Browser Compatibility**: Output is pure standards-compliant HTML/CSS/JavaScript with Google Fonts CDN support.

## License

MIT License. See repository root for full details.
