#!/usr/bin/env python3
"""Generate the GitHub-safe, light-theme Zhijian Skills README hero system."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]

# ZhiJian AI Warm Paper OS tokens. Keep decorative colour deliberately scarce.
PAPER = "#F5F4ED"
SURFACE = "#FAF9F5"
SURFACE_MUTED = "#E8E6DC"
INK = "#141413"
TERTIARY = "#504E49"
MUTED = "#6B6A64"
BORDER = "#E5E3D8"
CLAY = "#B85235"
CLAY_TEXT = "#A04A2E"
NAVY = "#1B365D"
INK_BLUE = "#2D5A8A"
SUCCESS = "#2F6F4E"
CODE = "#30302E"
CODE_TEXT = "#F5F4ED"

SERIF = (
    "'Source Han Serif SC VF','Source Han Serif SC','Noto Serif CJK SC',"
    "'Songti SC',STSong,SimSun,Georgia,serif"
)
MONO = "'SF Mono','JetBrains Mono',Menlo,Consolas,monospace"


SKILLS = {
    "codex-doctor": {
        "title": "Codex Doctor",
        "category": "WORKSPACE HEALTH",
        "tagline": "Diagnose context, configuration, and workspace drift.",
        "motif": "doctor",
    },
    "codex-model-routing-team": {
        "title": "Model Routing Team",
        "category": "CODEX ORCHESTRATION",
        "tagline": "Route bounded background work to the right model.",
        "motif": "routing",
    },
    "codex-skill-admin": {
        "title": "Codex Skill Admin",
        "category": "SKILL OPERATIONS",
        "tagline": "Audit, disable, restore, and verify local Skills.",
        "motif": "admin",
    },
    "codex-theme-studio": {
        "title": "Codex Theme Studio",
        "category": "CODEX EXPERIENCE",
        "tagline": "Design, apply, verify, and restore reversible themes.",
        "motif": "theme",
    },
    "enterprise-clone-builder": {
        "title": "Enterprise Clone Builder",
        "category": "KNOWLEDGE SYSTEM",
        "tagline": "Turn company evidence into a structured digital twin.",
        "motif": "enterprise",
    },
    "html-express": {
        "title": "HTML Express",
        "category": "INFORMATION DESIGN",
        "tagline": "Transform dense material into a clear standalone report.",
        "motif": "html",
    },
    "skill-open-sourcer": {
        "title": "Skill Open Sourcer",
        "category": "RELEASE GOVERNANCE",
        "tagline": "Audit, package, verify, and publish complete Agent Skills.",
        "motif": "release",
    },
    "wechat-article-search": {
        "title": "WeChat Article Search",
        "category": "CONTENT RESEARCH",
        "tagline": "Discover public-account articles as structured evidence.",
        "motif": "search",
    },
    "wechat-styler": {
        "title": "WeChat Styler",
        "category": "EDITORIAL PUBLISHING",
        "tagline": "Convert Markdown into polished WeChat-ready HTML.",
        "motif": "styler",
    },
    "workbuddy-cli-model-bridge": {
        "title": "WorkBuddy CLI Bridge",
        "category": "MODEL INFRASTRUCTURE",
        "tagline": "Connect verified CLI subscription models to WorkBuddy.",
        "motif": "bridge",
    },
}


def text(x: int, y: int, value: str, size: int, fill: str, weight: int = 400, *, family: str = SERIF, **attrs: str) -> str:
    extra = " ".join(f'{key.replace("_", "-")}="{escape(str(val))}"' for key, val in attrs.items())
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" {extra}>{escape(value)}</text>'
    )


def circle(x: int, y: int, radius: int, fill: str, stroke: str = "none", width: int = 1) -> str:
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def line(x1: int, y1: int, x2: int, y2: int, stroke: str, width: int = 2, dash: str | None = None) -> str:
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"{dashed}/>'


def rect(x: int, y: int, width: int, height: int, fill: str, radius: int = 8, stroke: str = "none", stroke_width: int = 1) -> str:
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def motif_doctor() -> str:
    parts = [circle(804, 181, 74, SURFACE, BORDER, 2), circle(804, 181, 55, "none", NAVY, 3)]
    parts += [line(770, 181, 790, 181, CLAY, 4), line(790, 181, 800, 161, CLAY, 4), line(800, 161, 816, 202, CLAY, 4), line(816, 202, 832, 178, CLAY, 4), line(832, 178, 844, 178, CLAY, 4)]
    for y, label in ((112, "CONTEXT"), (164, "CONFIG"), (216, "WORKSPACE")):
        parts += [rect(914, y - 23, 174, 42, SURFACE, 8, BORDER), circle(939, y - 2, 6, SUCCESS), text(956, y + 3, label, 12, TERTIARY, 500)]
    parts += [text(914, 276, "3 checks verified", 12, SUCCESS, 500)]
    return "".join(parts)


def motif_routing() -> str:
    workers = [(938, 96, "RESEARCH"), (1046, 138, "WRITE"), (1046, 224, "VERIFY"), (938, 266, "BUILD"), (832, 224, "PLAN")]
    parts = [line(916, 181, x, y, NAVY, 2) for x, y, _ in workers]
    parts += [circle(916, 181, 38, CLAY), text(916, 187, "LEAD", 12, SURFACE, 500, text_anchor="middle")]
    for x, y, label in workers:
        parts += [circle(x, y, 22, SURFACE, NAVY, 2), text(x, y + 38, label, 10, MUTED, 500, text_anchor="middle", letter_spacing=".5")]
    return "".join(parts)


def motif_admin() -> str:
    parts = [text(748, 90, "PROMPT-VISIBLE SKILLS", 11, NAVY, 500, letter_spacing="1.2")]
    for y, label, enabled in ((124, "RESEARCH", True), (178, "LEGACY TOOL", False), (232, "PUBLISHING", True)):
        parts += [rect(748, y - 23, 340, 44, SURFACE, 8, BORDER), text(770, y + 3, label, 13, TERTIARY, 500)]
        toggle_fill = NAVY if enabled else SURFACE_MUTED
        knob_x = 1058 if enabled else 1036
        parts += [rect(1026, y - 11, 44, 22, toggle_fill, 11), circle(knob_x, y, 8, SURFACE if enabled else MUTED)]
    parts += [text(748, 287, "2 active  ·  1 restorable", 12, SUCCESS, 500)]
    return "".join(parts)


def motif_theme() -> str:
    parts = [rect(726, 72, 390, 224, SURFACE, 14, BORDER)]
    parts += [circle(748, 91, 4, CLAY), circle(762, 91, 4, "#D6A82A"), circle(776, 91, 4, SUCCESS)]
    parts += [line(726, 106, 1116, 106, BORDER, 1), rect(742, 120, 82, 158, SURFACE_MUTED, 8)]
    for y, width in ((138, 54), (162, 62), (186, 46), (222, 60), (246, 50)):
        parts.append(rect(754, y, width, 5, MUTED, 2))
    parts += [rect(840, 120, 258, 82, PAPER, 10, BORDER), rect(969, 120, 129, 82, "#EEE7D8", 10)]
    parts += [rect(856, 139, 90, 7, CLAY, 3), rect(856, 160, 102, 5, TERTIARY, 2), rect(856, 176, 72, 4, SURFACE_MUTED, 2)]
    parts += [rect(994, 143, 50, 36, NAVY, 6), circle(1006, 155, 3, SURFACE), circle(1032, 155, 3, SURFACE), line(1006, 169, 1032, 169, SURFACE, 2)]
    for index, colour in enumerate((CLAY, NAVY, SUCCESS, SURFACE_MUTED)):
        x = 852 + index * 62
        parts += [rect(x, 218, 50, 48, SURFACE, 8, BORDER), circle(x + 25, 235, 7, colour), rect(x + 12, 251, 26, 4, SURFACE_MUTED, 2)]
    parts += [text(1088, 282, "VERIFY ✓", 10, SUCCESS, 500, text_anchor="end", letter_spacing=".7")]
    return "".join(parts)


def motif_enterprise() -> str:
    parts = []
    for y, label in ((108, "DOCS"), (181, "WEB"), (254, "VOICE")):
        parts += [rect(742, y - 21, 94, 42, SURFACE, 8, BORDER), text(789, y + 4, label, 11, TERTIARY, 500, text_anchor="middle"), line(836, y, 900, 181, NAVY, 2)]
    parts += [circle(920, 181, 32, CLAY), text(920, 186, "CORE", 11, SURFACE, 500, text_anchor="middle")]
    for x, y, label in ((1012, 96, "PROFILE"), (1048, 154, "ASSETS"), (1048, 214, "VOICE"), (1012, 272, "CLAIMS")):
        parts += [line(952, 181, x - 28, y, NAVY, 2), circle(x - 18, y, 6, NAVY), text(x, y + 4, label, 11, TERTIARY, 500)]
    return "".join(parts)


def motif_html() -> str:
    parts = [rect(738, 82, 146, 198, SURFACE_MUTED, 12, BORDER), text(756, 108, "SOURCE", 10, NAVY, 500, family=MONO, letter_spacing="1")]
    for index, width in enumerate((92, 105, 74, 110, 86, 100, 64)):
        parts.append(rect(756, 128 + index * 19, width, 5, MUTED, 2))
    parts += [line(904, 181, 936, 181, CLAY, 3), line(928, 173, 936, 181, CLAY, 3), line(928, 189, 936, 181, CLAY, 3)]
    parts += [rect(956, 82, 160, 198, SURFACE, 12, BORDER), rect(974, 101, 124, 22, NAVY, 4), rect(974, 140, 58, 52, PAPER, 8, BORDER), rect(1040, 140, 58, 52, PAPER, 8, BORDER), rect(974, 207, 124, 9, CLAY, 3), rect(974, 232, 98, 6, SURFACE_MUTED, 3), rect(974, 250, 116, 6, SURFACE_MUTED, 3)]
    return "".join(parts)


def motif_release() -> str:
    nodes = [(748, "LOCAL"), (844, "AUDIT"), (940, "SOURCE"), (1036, "MIRROR")]
    parts = [rect(748, 92, 288, 28, SURFACE, 6, BORDER), text(766, 111, "COMPLETE PAYLOAD  ·  VERIFIED RELEASE", 10, NAVY, 500, letter_spacing=".7")]
    for index, (x, label) in enumerate(nodes):
        if index:
            parts.append(line(nodes[index - 1][0] + 27, 181, x - 27, 181, NAVY, 2))
        fill = CLAY if label == "SOURCE" else SURFACE
        stroke = CLAY if label == "SOURCE" else NAVY
        parts += [circle(x, 181, 26, fill, stroke, 2), text(x, 226, label, 10, TERTIARY, 500, text_anchor="middle")]
    parts += [text(844, 187, "✓", 19, SUCCESS, 500, text_anchor="middle"), text(940, 186, "1", 15, SURFACE, 500, text_anchor="middle")]
    return "".join(parts)


def motif_search() -> str:
    parts = [rect(740, 72, 350, 44, SURFACE, 22, BORDER), circle(770, 94, 8, "none", NAVY, 2), line(776, 100, 783, 107, NAVY, 2), text(800, 100, "AI training", 13, TERTIARY, 400)]
    for index, (source, width) in enumerate((("智见 AI", 212), ("产业观察", 182), ("学习笔记", 230))):
        y = 138 + index * 58
        parts += [rect(740, y, 350, 46, SURFACE, 8, BORDER), rect(756, y + 12, width, 5, NAVY, 2), rect(756, y + 27, 134, 4, SURFACE_MUTED, 2), text(1068, y + 31, source, 10, MUTED, 400, text_anchor="end")]
    return "".join(parts)


def motif_styler() -> str:
    parts = [rect(732, 78, 145, 204, CODE, 12), text(750, 104, "MARKDOWN", 10, CODE_TEXT, 500, family=MONO, letter_spacing="1")]
    parts += [rect(750, 126, 94, 8, CLAY, 3), rect(750, 152, 108, 5, MUTED, 2), rect(750, 171, 83, 5, MUTED, 2), rect(750, 202, 108, 38, "#3B3B38", 7), rect(750, 255, 72, 5, MUTED, 2)]
    parts += [line(900, 181, 934, 181, CLAY, 3), line(926, 173, 934, 181, CLAY, 3), line(926, 189, 934, 181, CLAY, 3)]
    parts += [rect(956, 62, 158, 238, SURFACE, 12, BORDER), rect(976, 84, 118, 17, NAVY, 4), text(1035, 97, "WECHAT", 9, SURFACE, 500, text_anchor="middle", letter_spacing="1"), rect(976, 121, 92, 7, CLAY, 3), rect(976, 146, 118, 5, SURFACE_MUTED, 2), rect(976, 164, 103, 5, SURFACE_MUTED, 2), rect(976, 192, 118, 48, PAPER, 8, BORDER), rect(976, 256, 82, 5, SURFACE_MUTED, 2)]
    return "".join(parts)


def motif_bridge() -> str:
    nodes = ((776, "CLI"), (920, "PROXY"), (1064, "WORKBUDDY"))
    parts = [text(748, 91, "VERIFIED LOCAL ROUTE", 11, NAVY, 500, letter_spacing="1.1")]
    for index, (x, label) in enumerate(nodes):
        if index:
            previous = nodes[index - 1][0]
            parts += [line(previous + 38, 181, x - 38, 181, NAVY, 2), line(x - 46, 173, x - 38, 181, NAVY, 2), line(x - 46, 189, x - 38, 181, NAVY, 2)]
        fill = CLAY if label == "PROXY" else SURFACE
        stroke = CLAY if label == "PROXY" else NAVY
        parts += [circle(x, 181, 38, fill, stroke, 2), text(x, 186, label, 10, SURFACE if label == "PROXY" else TERTIARY, 500, text_anchor="middle")]
    for x, label in ((776, "OAUTH"), (920, "PROBE"), (1064, "SYNC")):
        parts += [rect(x - 42, 246, 84, 30, SURFACE, 6, BORDER), text(x, 266, label, 9, SUCCESS, 500, text_anchor="middle", letter_spacing=".7")]
    return "".join(parts)


MOTIFS = {
    "doctor": motif_doctor,
    "routing": motif_routing,
    "admin": motif_admin,
    "theme": motif_theme,
    "enterprise": motif_enterprise,
    "html": motif_html,
    "release": motif_release,
    "search": motif_search,
    "styler": motif_styler,
    "bridge": motif_bridge,
}


def svg_shell(title_value: str, description: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title_value)}</title>
  <desc id="desc">{escape(description)}</desc>
  <rect width="1200" height="360" rx="28" fill="{PAPER}"/>
  <path d="M46 314 H1154" stroke="{BORDER}" stroke-width="1"/>
  <path d="M620 40 V320" stroke="{BORDER}" stroke-width="1" stroke-dasharray="3 7"/>
  <circle cx="1150" cy="34" r="92" fill="{NAVY}" opacity="0.025"/>
  <circle cx="34" cy="350" r="74" fill="{CLAY}" opacity="0.035"/>
  {body}
</svg>
'''


def skill_hero(name: str, item: dict[str, str]) -> str:
    body = "".join(
        [
            text(64, 64, "智见 AI  /  ZHIJIAN SKILLS", 12, CLAY_TEXT, 500, letter_spacing="1.4"),
            text(64, 105, item["category"], 11, NAVY, 500, letter_spacing="1.3"),
            text(64, 164, item["title"], 43, INK, 500),
            text(64, 205, item["tagline"], 18, TERTIARY, 400),
            rect(64, 246, 190, 36, SURFACE, 8, BORDER),
            rect(64, 246, 5, 36, CLAY, 2),
            text(84, 269, "OPEN AGENT SKILL", 11, NAVY, 500, letter_spacing="1"),
            text(64, 335, name, 11, MUTED, 400, family=MONO),
            rect(660, 40, 484, 264, SURFACE, 12, BORDER),
            MOTIFS[item["motif"]](),
        ]
    )
    return svg_shell(item["title"], item["tagline"], body)


def portfolio_hero() -> str:
    cards = []
    labels = ["DOCTOR", "ROUTING", "ADMIN", "THEME", "CLONE", "PRO", "HTML", "PLAN", "RELEASE", "SEARCH", "STYLER", "BRIDGE"]
    for index, label in enumerate(labels):
        column = index % 3
        row = index // 3
        x = 684 + column * 148
        y = 72 + row * 55
        marker = CLAY if label in {"ROUTING", "THEME", "PRO", "RELEASE", "BRIDGE"} else NAVY
        cards += [rect(x, y, 132, 38, SURFACE, 8, BORDER), rect(x, y, 4, 38, marker, 2), text(x + 18, y + 24, label, 10, TERTIARY, 500, letter_spacing=".45")]
    body = "".join(
        [
            text(64, 64, "智见 AI  /  PUBLIC AGENT SKILLS", 12, CLAY_TEXT, 500, letter_spacing="1.4"),
            text(64, 139, "Zhijian Skills", 48, INK, 500),
            text(64, 183, "One source. Twelve focused skills.", 20, TERTIARY, 400),
            text(64, 215, "Complete packages · verifiable releases", 16, MUTED, 400),
            rect(64, 254, 224, 36, NAVY, 8),
            text(176, 277, "CANONICAL PORTFOLIO", 11, SURFACE, 500, text_anchor="middle", letter_spacing="1"),
            rect(660, 40, 484, 264, SURFACE, 12, BORDER),
            text(684, 58, "12 ACTIVE SKILLS", 10, NAVY, 500, letter_spacing="1.1"),
            *cards,
        ]
    )
    return svg_shell(
        "Zhijian Skills",
        "A canonical portfolio of twelve focused, installable, and independently released Agent Skills.",
        body,
    )


def main() -> int:
    targets = {ROOT / "assets/readme/portfolio-hero.svg": portfolio_hero()}
    for name, item in SKILLS.items():
        targets[ROOT / f"docs/skills/{name}/assets/readme/hero.svg"] = skill_hero(name, item)
    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
