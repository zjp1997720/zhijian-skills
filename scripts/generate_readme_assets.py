#!/usr/bin/env python3
"""Generate project-native, GitHub-safe README heroes for Zhijian Skills."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif"
SERIF = "Georgia,'Songti SC',serif"
MONO = "ui-monospace,'SFMono-Regular',Menlo,monospace"


def attrs(**values: object) -> str:
    return " ".join(
        f'{key.replace("_", "-")}="{escape(str(value))}"'
        for key, value in values.items()
        if value is not None
    )


def text(x: int, y: int, value: str, size: int, fill: str, weight: int = 500, *, family: str = SANS, **extra: object) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" {attrs(**extra)}>{escape(value)}</text>'
    )


def rect(x: int, y: int, width: int, height: int, fill: str, radius: int = 0, stroke: str = "none", stroke_width: int = 1, **extra: object) -> str:
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {attrs(**extra)}/>'


def circle(x: int, y: int, radius: int, fill: str, stroke: str = "none", stroke_width: int = 1, **extra: object) -> str:
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {attrs(**extra)}/>'


def line(x1: int, y1: int, x2: int, y2: int, stroke: str, stroke_width: int = 2, **extra: object) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}" {attrs(**extra)}/>'


def path(d: str, *, fill: str = "none", stroke: str = "none", stroke_width: int = 1, **extra: object) -> str:
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {attrs(**extra)}/>'


def group(composition: str, body: list[str]) -> str:
    return f'<g data-composition="{composition}">{"".join(body)}</g>'


def svg(title_value: str, description: str, background: str, composition: str, body: list[str]) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc" data-composition="{composition}">
  <title id="title">{escape(title_value)}</title>
  <desc id="desc">{escape(description)}</desc>
  <rect width="1200" height="360" rx="28" fill="{background}"/>
  {group(composition, body)}
</svg>
'''


def portfolio() -> str:
    bg, paper, mint, orange, muted = "#102A43", "#F8F3E7", "#65D6AD", "#FF9F43", "#A9C2D6"
    body = [
        text(58, 62, "ZHIJIAN / OPEN AGENT SKILLS", 16, mint, 650, family=MONO, letter_spacing="2"),
        text(58, 140, "Zhijian", 58, paper, 700),
        text(58, 200, "Skills", 58, paper, 700),
        text(58, 244, "One source. Twelve focused capabilities.", 22, muted, 450),
        rect(58, 278, 356, 46, mint, 8),
        text(78, 308, "$ npx skills add zjp1997720/zhijian-skills", 16, bg, 700, family=MONO),
        line(478, 42, 478, 318, "#355B75", 2),
        text(530, 62, "CHOOSE BY OUTCOME", 15, muted, 650, family=MONO, letter_spacing="2"),
    ]
    groups = [
        (520, 90, "CONTROL", ["doctor", "routing", "admin", "theme"], mint),
        (735, 90, "CREATE", ["clone", "pro", "html", "styler"], orange),
        (950, 90, "SHIP", ["plan", "release", "search", "bridge"], "#A78BFA"),
    ]
    for x, y, label, skills, colour in groups:
        body += [text(x, y, label, 14, colour, 700, family=MONO, letter_spacing="1.5")]
        for index, skill in enumerate(skills):
            yy = y + 18 + index * 42
            body += [rect(x, yy, 184, 32, "#173B57", 6), rect(x, yy, 5, 32, colour, 2), text(x + 18, yy + 22, skill, 15, paper, 600, family=MONO)]
    return svg("Zhijian Skills", "One canonical portfolio of twelve focused and independently verified Agent Skills.", bg, "portfolio-outcome-map", body)


def codex_doctor() -> str:
    bg, ink, red, green, gray = "#F3F0E8", "#171717", "#E4572E", "#2A9D62", "#D8D3C8"
    body = [
        text(56, 55, "WORKSPACE HEALTH / READ-ONLY", 15, red, 700, family=MONO, letter_spacing="1.8"),
        text(56, 132, "Codex", 58, ink, 700), text(56, 190, "Doctor", 58, ink, 700),
        text(56, 235, "Find context drift before changing files.", 23, "#57534E", 450),
        rect(56, 270, 300, 42, ink, 6), text(75, 298, "SCAN  →  EXPLAIN  →  APPROVE", 15, bg, 700, family=MONO),
        rect(570, 42, 570, 276, "#FAF9F5", 10, ink, 2),
        text(602, 76, "DIAGNOSTIC REPORT", 15, ink, 700, family=MONO, letter_spacing="1.5"),
        line(602, 92, 1108, 92, gray, 2),
    ]
    checks = [("CONTEXT PRESSURE", "72%", green), ("CONFIG DRIFT", "2", red), ("WORKSPACE ROOT", "CLEAR", green), ("THREAD SCOPE", "CHECK", red)]
    for index, (label, value, colour) in enumerate(checks):
        y = 122 + index * 43
        body += [text(602, y + 21, label, 17, ink, 650, family=MONO), rect(900, y, 180, 28, gray, 4), rect(900, y, 132 if colour == green else 76, 28, colour, 4), text(1098, y + 21, value, 16, ink, 700, family=MONO, text_anchor="end")]
    body += [path("M602 294 L636 294 L651 264 L674 310 L697 280 L722 294 L760 294", stroke=red, stroke_width=4, stroke_linecap="round", stroke_linejoin="round"), circle(1092, 294, 10, green), text(1068, 299, "verified", 15, green, 700, family=MONO, text_anchor="end")]
    return svg("Codex Doctor", "A read-only diagnostic report for Codex context, configuration, and workspace drift.", bg, "diagnostic-report", body)


def routing_team() -> str:
    bg, white, cyan, orange, panel = "#101827", "#F7F5EF", "#66D9EF", "#FF8A4C", "#18263A"
    body = [
        text(52, 55, "CODEX ORCHESTRATION", 15, cyan, 700, family=MONO, letter_spacing="2"),
        text(52, 118, "Model Routing", 48, white, 720), text(52, 168, "Team", 48, white, 720),
        text(52, 212, "One lead. Bounded workers. Explicit routes.", 21, "#A8B5C7", 450),
        rect(52, 253, 358, 48, panel, 8, cyan, 2), text(72, 284, "PLAN  /  DELEGATE  /  VERIFY", 17, white, 700, family=MONO),
        circle(760, 178, 58, orange), text(760, 173, "LEAD", 19, bg, 800, family=MONO, text_anchor="middle"), text(760, 198, "integrates", 14, bg, 650, family=MONO, text_anchor="middle"),
    ]
    nodes = [(560, 86, "RESEARCH", "LUNA"), (980, 86, "REVIEW", "SOL"), (560, 270, "BUILD", "GROK"), (980, 270, "VERIFY", "LUNA")]
    for x, y, job, model in nodes:
        body += [line(760, 178, x, y, "#3B5975", 3), rect(x - 92, y - 36, 184, 72, panel, 10, cyan if model == "LUNA" else orange, 2), text(x, y - 5, job, 16, white, 700, family=MONO, text_anchor="middle"), text(x, y + 20, model, 14, cyan if model == "LUNA" else orange, 700, family=MONO, text_anchor="middle")]
    body += [text(760, 338, "provider gate  •  file ownership  •  final evidence", 15, "#8EA4B8", 500, family=MONO, text_anchor="middle")]
    return svg("Codex Model Routing Team", "A lead Codex task routes bounded background work to explicit models and verifies the result.", bg, "radial-routing-control", body)


def skill_admin() -> str:
    bg, ink, lime, gray, white = "#E9ECE5", "#161A16", "#B7F34A", "#C9CEC6", "#FAFBF8"
    body = [
        text(54, 55, "PROMPT SURFACE CONTROL", 15, ink, 750, family=MONO, letter_spacing="2"),
        text(54, 142, "42", 96, ink, 780, family=MONO), text(212, 112, "SKILLS", 18, ink, 700, family=MONO), text(212, 142, "VISIBLE", 18, ink, 700, family=MONO),
        text(54, 198, "Audit what loads. Disable safely.", 23, "#4C534C", 500),
        text(54, 232, "Restore from recorded state.", 23, "#4C534C", 500),
        rect(54, 272, 290, 42, ink, 5), text(75, 299, "AUDIT → DRY RUN → APPLY", 16, lime, 700, family=MONO),
        rect(470, 36, 670, 288, white, 8, ink, 2),
        text(500, 70, "PROMPT-VISIBLE SKILLS", 15, ink, 700, family=MONO),
    ]
    rows = [("RESEARCH", True, "USED TODAY"), ("LEGACY-PUBLISH", False, "RESTORABLE"), ("THEME-STUDIO", True, "USED 2D AGO"), ("OLD-EXPORT", False, "BACKUP 07/24")]
    for index, (label, enabled, note) in enumerate(rows):
        y = 92 + index * 55
        body += [line(500, y + 42, 1110, y + 42, gray, 1), text(500, y + 26, label, 17, ink, 700, family=MONO), text(860, y + 26, note, 14, "#6B746B", 600, family=MONO), rect(1040, y + 8, 64, 30, ink if enabled else gray, 15), circle(1087 if enabled else 1057, y + 23, 11, lime if enabled else white)]
    return svg("Codex Skill Admin", "A reversible switchboard for auditing, disabling, restoring, and verifying local Codex Skills.", bg, "prompt-switchboard", body)


def theme_studio() -> str:
    bg, ink, purple, coral, mint, paper = "#EEE9FF", "#24213A", "#6C4CF5", "#FF6B6B", "#59C9A5", "#FFFDF8"
    body = [
        text(54, 52, "CODEX EXPERIENCE / REVERSIBLE", 15, purple, 750, family=MONO, letter_spacing="1.8"),
        text(54, 116, "Theme", 54, ink, 760), text(54, 172, "Studio", 54, ink, 760),
        text(54, 216, "Brand the app. Verify every route.", 22, "#5F5874", 500),
        rect(54, 257, 46, 46, purple, 8), rect(112, 257, 46, 46, coral, 8), rect(170, 257, 46, 46, mint, 8), rect(228, 257, 46, 46, ink, 8),
        text(300, 286, "APPLY  •  PAUSE  •  RESTORE", 16, ink, 700, family=MONO),
        rect(520, 42, 620, 276, paper, 14, ink, 2),
        rect(520, 42, 620, 38, ink, 12), circle(545, 61, 5, coral), circle(562, 61, 5, "#FFD166"), circle(579, 61, 5, mint),
        rect(544, 100, 138, 194, "#E6E0F6", 10),
    ]
    for index, width in enumerate((82, 104, 65, 98, 76)):
        body += [rect(564, 126 + index * 31, width, 7, "#8B83A3", 3)]
    body += [rect(706, 100, 408, 82, bg, 10), text(730, 132, "WELCOME BACK", 15, purple, 750, family=MONO), text(730, 160, "Codex, in your visual language.", 22, ink, 700), rect(706, 202, 194, 92, ink, 10), rect(920, 202, 194, 92, "#F6EFE7", 10), circle(758, 247, 18, coral), circle(972, 247, 18, mint), text(808, 252, "task route", 16, paper, 650), text(1024, 252, "home route", 16, ink, 650), text(1094, 310, "VERIFY ✓", 14, mint, 800, family=MONO, text_anchor="end")]
    return svg("Codex Theme Studio", "A reversible Codex Desktop theme shown as a branded interface with verified routes.", bg, "theme-artboards", body)


def enterprise_clone() -> str:
    bg, paper, green, gold, ink = "#163B2D", "#F5F0E2", "#7ED6A6", "#E9C46A", "#122018"
    body = [
        text(50, 52, "KNOWLEDGE SYSTEM", 15, green, 750, family=MONO, letter_spacing="2"),
        text(50, 112, "Enterprise", 48, paper, 720), text(50, 162, "Clone Builder", 48, paper, 720),
        text(50, 205, "Evidence becomes a traceable company core.", 21, "#B8D5C6", 450),
        rect(50, 246, 354, 48, paper, 7), text(72, 277, "LOCAL MATERIALS + PUBLIC PROOF", 15, ink, 750, family=MONO),
        text(50, 329, "collect  →  verify  →  structure  →  reuse", 15, green, 650, family=MONO),
    ]
    sources = [(500, 70, "DOCS"), (500, 144, "WEB"), (500, 218, "VOICE"), (500, 292, "CASES")]
    for x, y, label in sources:
        body += [rect(x, y - 24, 120, 48, paper, 5), text(x + 60, y + 6, label, 16, ink, 750, family=MONO, text_anchor="middle"), line(x + 120, y, 700, 181, green, 2)]
    body += [circle(746, 181, 60, gold), text(746, 174, "CLAIM", 17, ink, 800, family=MONO, text_anchor="middle"), text(746, 198, "CORE", 17, ink, 800, family=MONO, text_anchor="middle")]
    outputs = [(900, 75, "PROFILE"), (980, 135, "ASSETS"), (980, 227, "VOICE"), (900, 287, "LEDGER")]
    for x, y, label in outputs:
        body += [line(806, 181, x - 18, y, green, 2), circle(x, y, 8, green), text(x + 24, y + 6, label, 17, paper, 700, family=MONO)]
    return svg("Enterprise Clone Builder", "Company documents, web evidence, voice, and cases flow into a traceable digital-twin repository.", bg, "evidence-to-knowledge-core", body)


def html_express() -> str:
    bg, white, blue, orange, ink = "#164E63", "#FCFAF4", "#38BDF8", "#FB923C", "#132C35"
    body = [
        text(50, 50, "INFORMATION DESIGN", 15, blue, 750, family=MONO, letter_spacing="2"),
        text(50, 112, "HTML", 58, white, 760), text(50, 170, "Express", 58, white, 760),
        text(50, 216, "Dense source in. Clear report out.", 22, "#B8DDE7", 500),
        rect(50, 258, 310, 44, blue, 7), text(72, 287, "ONE FILE  •  ZERO RUNTIME", 16, ink, 800, family=MONO),
        rect(452, 52, 220, 256, "#DCE6E5", 8), text(478, 84, "SOURCE", 14, ink, 750, family=MONO),
    ]
    for index, width in enumerate((150, 124, 168, 104, 148, 132, 164, 92)):
        body += [rect(478, 108 + index * 22, width, 6, "#6C7E7E", 3)]
    body += [line(700, 181, 756, 181, orange, 5), path("M742 168 L756 181 L742 194", stroke=orange, stroke_width=5, stroke_linecap="round", stroke_linejoin="round"), rect(790, 34, 360, 292, white, 12), rect(812, 56, 316, 32, blue, 5), text(830, 78, "DECISION REPORT", 14, ink, 800, family=MONO), rect(812, 108, 146, 72, "#E7F6FB", 8), rect(972, 108, 156, 72, "#FFF0E5", 8), text(830, 138, "72%", 28, blue, 800, family=MONO), text(990, 138, "04", 28, orange, 800, family=MONO), rect(812, 202, 316, 12, ink, 4), rect(812, 230, 230, 7, "#B7C5C5", 3), rect(812, 252, 280, 7, "#B7C5C5", 3), rect(812, 274, 196, 7, "#B7C5C5", 3), text(1128, 309, ".html", 16, orange, 800, family=MONO, text_anchor="end")]
    return svg("HTML Express", "Dense source material transforms into a clear, self-contained HTML decision report.", bg, "source-to-report", body)


def light_plan() -> str:
    bg, ink, cream, orange, gray = "#F8D7B8", "#241A15", "#FFF7EE", "#F0642E", "#C29C7C"
    body = [
        text(52, 52, "BOUNDED EXECUTION", 15, orange, 800, family=MONO, letter_spacing="2"),
        text(52, 114, "Light Plan", 52, ink, 760), text(52, 168, "and Work", 52, ink, 760),
        text(52, 214, "Plan briefly. Start now. Verify the result.", 22, "#6E4F3E", 500),
        rect(42, 261, 320, 50, ink, 7),
        text(62, 294, "$light-plan-and-work", 17, cream, 750, family=MONO),
    ]
    routes = [(470, 62, "DIRECT", "tiny / obvious", False), (470, 144, "LIGHT", "bounded / reversible", True), (470, 240, "HEAVY", "risky / multi-owner", False)]
    for x, y, label, note, active in routes:
        fill = orange if active else cream
        stroke = ink if active else gray
        body += [rect(x, y, 640, 66, fill, 8, stroke, 2), text(x + 24, y + 29, label, 20, ink, 850, family=MONO), text(x + 170, y + 29, note, 17, ink, 600, family=MONO)]
        if active:
            steps = ["GOAL", "PLAN", "WORK", "VERIFY"]
            for index, step in enumerate(steps):
                sx = x + 170 + index * 104
                body += [text(sx, y + 53, step, 13, cream, 800, family=MONO), line(sx + 54, y + 48, sx + 82, y + 48, cream, 2) if index < 3 else ""]
    body += [text(1110, 334, "ESCALATE ONLY WHEN THE RISK CHANGES", 14, ink, 750, family=MONO, text_anchor="end")]
    return svg("Light Plan and Work", "A three-route execution system that highlights the light path from goal to verified result.", bg, "three-route-decision", body)


def sol_pro_consult() -> str:
    bg, paper, gold, violet, green, panel = "#241A32", "#FFF8E8", "#F2C14E", "#A78BFA", "#66D9A6", "#342545"
    body = [
        text(48, 50, "VERIFIED SECOND OPINION", 15, gold, 800, family=MONO, letter_spacing="2"),
        text(48, 108, "GPT 5.6 Sol", 46, paper, 760), text(48, 158, "Pro Consult", 46, paper, 760),
        text(48, 202, "Evidence in. Verified Pro. Local decision.", 21, "#CFC2DA", 500),
        rect(48, 246, 340, 48, panel, 7, violet, 2), text(68, 277, "CHROME FIRST  •  SAFETY SCAN", 15, paper, 800, family=MONO),
    ]
    stages = [(466, "PACKET", "facts + files", gold), (650, "CHROME", "upload once", violet), (834, "PRO", "model checked", gold), (1018, "DECIDE", "adopt / reject", green)]
    for index, (x, label, note, colour) in enumerate(stages):
        if index:
            body += [line(stages[index - 1][0] + 62, 178, x - 62, 178, violet, 3), path(f"M{x-76} 168 L{x-62} 178 L{x-76} 188", stroke=violet, stroke_width=3)]
        body += [circle(x, 178, 58, panel, colour, 3), text(x, 173, label, 16, paper, 850, family=MONO, text_anchor="middle"), text(x, 198, note, 13, "#CFC2DA", 650, family=MONO, text_anchor="middle")]
    body += [rect(452, 270, 624, 44, panel, 6), text(474, 298, "LOCAL JUDGMENT", 14, gold, 800, family=MONO), line(638, 292, 862, 292, "#5D496F", 2), text(1054, 298, "SENTINEL VERIFIED ✓", 14, green, 800, family=MONO, text_anchor="end")]
    return svg("GPT 5.6 Sol Pro Consult", "A file-grounded second-opinion loop that verifies the Pro model and returns the decision to the local Agent.", bg, "verified-second-opinion-loop", body)


def open_sourcer() -> str:
    bg, paper, green, red, gray = "#171A18", "#F4F1E8", "#6FD08C", "#ED6A5A", "#525B55"
    body = [
        text(48, 50, "RELEASE GOVERNANCE", 15, green, 800, family=MONO, letter_spacing="2"),
        text(48, 108, "Skill Open", 48, paper, 730), text(48, 158, "Sourcer", 48, paper, 730),
        text(48, 203, "One Portfolio. Complete payloads.", 21, "#B8C0BA", 500),
        text(48, 232, "Verified releases.", 21, "#B8C0BA", 500),
        rect(48, 272, 338, 44, paper, 5), text(68, 301, "SCAN  •  PACKAGE  •  PUBLISH", 16, bg, 800, family=MONO),
    ]
    stages = [(470, "LOCAL", gray), (630, "AUDIT", green), (790, "PACKAGE", green), (950, "PORTFOLIO", red)]
    for index, (x, label, colour) in enumerate(stages):
        if index:
            body += [line(stages[index - 1][0] + 104, 181, x - 14, 181, green, 3), path(f"M{x-28} 173 L{x-14} 181 L{x-28} 189", stroke=green, stroke_width=3)]
        body += [rect(x, 126, 118, 110, "#222824", 8, colour, 2), text(x + 59, 165, label, 15, paper, 800, family=MONO, text_anchor="middle"), circle(x + 59, 202, 15, colour), text(x + 59, 208, "✓" if label != "LOCAL" else "1", 18, bg, 850, family=MONO, text_anchor="middle")]
    body += [rect(470, 72, 598, 32, "#222824", 5), text(492, 94, "SKILL.md + references + scripts + assets", 14, "#AAB5AD", 650, family=MONO), rect(470, 264, 598, 44, "#222824", 5), text(492, 292, "skills/<name>  ·  docs  ·  registry  ·  tag", 15, green, 700, family=MONO)]
    return svg("Skill Open Sourcer", "A verified pipeline from a local Agent Skill to one canonical Portfolio release.", bg, "canonical-release-pipeline", body)


def wechat_search() -> str:
    bg, white, green, ink, pale = "#EAF8EF", "#FFFFFF", "#07C160", "#17352A", "#CDEBD8"
    body = [
        text(50, 50, "CONTENT RESEARCH", 15, green, 800, family=MONO, letter_spacing="2"),
        text(50, 110, "WeChat Article", 46, ink, 760), text(50, 158, "Search", 46, ink, 760),
        text(50, 202, "Turn one keyword into structured evidence.", 21, "#537165", 500),
        rect(50, 246, 344, 50, white, 25, green, 2), circle(80, 271, 10, "none", green, 3), line(87, 279, 98, 290, green, 3), text(112, 278, "AI training", 18, ink, 600),
        text(50, 330, "JSON  •  SOURCE  •  TIME  •  DIRECT URL", 14, green, 800, family=MONO),
    ]
    results = [(520, 62, "AI training in real workflows", "ZHIJIAN AI", "2026-07-24"), (520, 150, "From tools to operating systems", "FIELD NOTES", "2026-07-22"), (520, 238, "How to organize Agent Skills", "BUILD LOG", "2026-07-20")]
    for x, y, title_value, source, date in results:
        body += [rect(x, y, 620, 70, white, 10), rect(x, y, 7, 70, green, 3), text(x + 28, y + 30, title_value, 20, ink, 700), text(x + 28, y + 55, source, 14, "#567065", 600), text(x + 588, y + 55, date, 14, "#567065", 600, family=MONO, text_anchor="end")]
    return svg("WeChat Article Search", "A WeChat-green search interface turns a keyword into dated, source-labelled article evidence.", bg, "search-evidence-stack", body)


def wechat_styler() -> str:
    bg, paper, wine, gold, ink = "#6F1D35", "#FFF8EC", "#B43E5D", "#E8B86D", "#24191D"
    body = [
        text(48, 50, "EDITORIAL PUBLISHING", 15, gold, 800, family=MONO, letter_spacing="2"),
        text(48, 112, "WeChat", 52, paper, 760, family=SERIF), text(48, 166, "Styler", 52, paper, 760, family=SERIF),
        text(48, 210, "Markdown becomes WeChat-ready HTML.", 21, "#E8C9D1", 500),
        rect(48, 252, 334, 48, paper, 5), text(70, 282, "8 THEMES  •  INLINE CSS  •  QA", 15, ink, 800, family=MONO),
        rect(456, 44, 248, 272, "#251F21", 10), text(482, 78, "MARKDOWN", 14, gold, 800, family=MONO),
        text(482, 122, "# A clear idea", 22, paper, 700, family=MONO), text(482, 158, "> one claim", 17, "#B8AFB2", 550, family=MONO), text(482, 192, "- proof", 17, "#B8AFB2", 550, family=MONO), text(482, 222, "- action", 17, "#B8AFB2", 550, family=MONO), rect(482, 250, 162, 32, wine, 4), text(498, 272, "validate.mjs ✓", 14, paper, 700, family=MONO),
        line(724, 181, 774, 181, gold, 4), path("M760 168 L774 181 L760 194", stroke=gold, stroke_width=4),
        rect(806, 26, 328, 308, paper, 12), text(834, 66, "ZHIJIAN AI", 14, wine, 800, letter_spacing="2"), text(834, 112, "A clear idea", 30, ink, 760, family=SERIF), line(834, 132, 1106, 132, gold, 3), text(834, 170, "Lead with the claim.", 18, ink, 550), rect(834, 194, 272, 62, "#F5E7DA", 6), text(852, 224, "KEY RESULT", 16, wine, 800), text(852, 247, "Compatibility passed", 17, ink, 600), rect(834, 278, 112, 30, wine, 4), text(890, 299, "SAVE DRAFT", 14, paper, 700, text_anchor="middle")]
    return svg("WeChat Styler", "A Markdown source panel transforms into a branded, validated WeChat article page.", bg, "editorial-before-after", body)


def model_bridge() -> str:
    bg, white, cyan, green, red, panel = "#071E2C", "#F4F8FA", "#38C6D9", "#5DD39E", "#FF6B5E", "#0D2D3E"
    body = [
        text(48, 50, "MODEL INFRASTRUCTURE / LOOPBACK", 15, cyan, 800, family=MONO, letter_spacing="1.7"),
        text(48, 108, "WorkBuddy", 46, white, 740), text(48, 158, "CLI Bridge", 46, white, 740),
        text(48, 202, "Authorize. Probe. Register exact routes.", 21, "#A9C5D1", 500),
        rect(48, 248, 318, 48, panel, 6, cyan, 2), text(68, 279, "LOCAL PROXY  •  NO KEY COPY", 15, white, 800, family=MONO),
    ]
    nodes = [(500, "CLI", cyan), (744, "PROXY", red), (988, "WORKBUDDY", green)]
    for index, (x, label, colour) in enumerate(nodes):
        if index:
            body += [line(nodes[index - 1][0] + 72, 164, x - 72, 164, cyan, 4), path(f"M{x-88} 151 L{x-72} 164 L{x-88} 177", stroke=cyan, stroke_width=4)]
        body += [circle(x, 164, 64, panel, colour, 4), text(x, 170, label, 17, white, 800, family=MONO, text_anchor="middle")]
    metrics = [(464, "AUTH", "READY", green), (660, "TOOLS", "PASS", green), (856, "VISION", "PASS", green), (1020, "LIMITS", "EXACT", cyan)]
    for x, label, value, colour in metrics:
        body += [rect(x, 254, 150, 58, panel, 6), text(x + 16, 277, label, 13, "#84A7B6", 700, family=MONO), text(x + 134, 298, value, 16, colour, 850, family=MONO, text_anchor="end")]
    body += [text(1134, 338, "VERIFIED ROUTE ✓", 14, green, 850, family=MONO, text_anchor="end")]
    return svg("WorkBuddy CLI Model Bridge", "A verified loopback route connects CLI subscription models through a proxy to WorkBuddy.", bg, "verified-loopback-route", body)


HEROES = {
    ROOT / "assets/readme/portfolio-hero.svg": portfolio,
    ROOT / "docs/skills/codex-doctor/assets/readme/hero.svg": codex_doctor,
    ROOT / "docs/skills/codex-model-routing-team/assets/readme/hero.svg": routing_team,
    ROOT / "docs/skills/codex-skill-admin/assets/readme/hero.svg": skill_admin,
    ROOT / "docs/skills/codex-theme-studio/assets/readme/hero.svg": theme_studio,
    ROOT / "docs/skills/enterprise-clone-builder/assets/readme/hero.svg": enterprise_clone,
    ROOT / "docs/skills/gpt56-sol-pro-consult/assets/readme/hero.svg": sol_pro_consult,
    ROOT / "docs/skills/html-express/assets/readme/hero.svg": html_express,
    ROOT / "docs/skills/light-plan-and-work/assets/readme/hero.svg": light_plan,
    ROOT / "docs/skills/skill-open-sourcer/assets/readme/hero.svg": open_sourcer,
    ROOT / "docs/skills/wechat-article-search/assets/readme/hero.svg": wechat_search,
    ROOT / "docs/skills/wechat-styler/assets/readme/hero.svg": wechat_styler,
    ROOT / "docs/skills/workbuddy-cli-model-bridge/assets/readme/hero.svg": model_bridge,
}


def main() -> int:
    for target, render in HEROES.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(), encoding="utf-8")
        print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
