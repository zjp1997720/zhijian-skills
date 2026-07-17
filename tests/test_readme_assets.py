from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_readme_assets.py"
SKILLS = (
    "codex-doctor",
    "codex-model-routing-team",
    "codex-skill-admin",
    "codex-theme-studio",
    "enterprise-clone-builder",
    "html-express",
    "skill-open-sourcer",
    "wechat-article-search",
    "wechat-styler",
)


class ReadmeAssetTests(unittest.TestCase):
    def expected_assets(self) -> tuple[Path, ...]:
        return (
            ROOT / "assets/readme/portfolio-hero.svg",
            *(ROOT / f"docs/skills/{skill}/assets/readme/hero.svg" for skill in SKILLS),
        )

    def expected_readmes(self) -> tuple[Path, ...]:
        return (
            ROOT / "README.md",
            ROOT / "README.zh-CN.md",
            *(
                ROOT / f"docs/skills/{skill}/{filename}"
                for skill in SKILLS
                for filename in ("README.md", "README.zh-CN.md")
            ),
        )

    def test_assets_are_safe_accessible_and_brand_aligned(self) -> None:
        assets = self.expected_assets()
        self.assertEqual(len(assets), 10)
        for asset in assets:
            content = asset.read_text(encoding="utf-8")
            self.assertLess(len(content.encode("utf-8")), 60_000, asset)
            self.assertIn('viewBox="0 0 1200 360"', content, asset)
            self.assertIn("<title", content, asset)
            self.assertIn("<desc", content, asset)
            self.assertIn("#F5F4ED", content, asset)
            for unsafe in ("<script", "<foreignObject", "<image", "href=", "@import", "url("):
                self.assertNotIn(unsafe, content, f"{asset}: unsafe token {unsafe}")

    def test_generator_is_deterministic(self) -> None:
        before = {path: path.read_bytes() for path in self.expected_assets()}
        result = subprocess.run(
            [sys.executable, str(GENERATOR)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {path: path.read_bytes() for path in self.expected_assets()}
        self.assertEqual(before, after)

    def test_readme_image_links_resolve(self) -> None:
        for readme in self.expected_readmes():
            content = readme.read_text(encoding="utf-8")
            sources = re.findall(r'<img[^>]+src="([^"]+\.svg)"', content)
            self.assertTrue(sources, f"{readme}: missing SVG hero")
            for source in sources:
                self.assertFalse(source.startswith(("http://", "https://")), source)
                self.assertTrue((readme.parent / source).resolve().is_file(), f"{readme}: {source}")

    def test_skill_readmes_keep_install_command(self) -> None:
        for skill in SKILLS:
            for filename in ("README.md", "README.zh-CN.md"):
                readme = ROOT / f"docs/skills/{skill}/{filename}"
                content = readme.read_text(encoding="utf-8")
                self.assertIn(f"npx skills add zjp1997720/{skill}", content, readme)


if __name__ == "__main__":
    unittest.main()
