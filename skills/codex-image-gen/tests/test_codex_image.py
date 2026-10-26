from __future__ import annotations

import base64
import datetime as dt
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "codex_image.py"
SPEC = importlib.util.spec_from_file_location("codex_image_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
codex_image = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = codex_image
SPEC.loader.exec_module(codex_image)


def make_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.signature"


class ArgumentContractTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = codex_image.parse_args(["--prompt", "a cover"])
        self.assertEqual(args.quality, "medium")
        self.assertEqual(args.aspect, "square")
        self.assertEqual(args.model, "gpt-image-2")
        self.assertEqual(args.out_dir, ".")
        self.assertEqual(args.image, [])
        self.assertEqual(args.reference_image, [])

    def test_prompt_is_required(self) -> None:
        with self.assertRaises(SystemExit):
            codex_image.parse_args([])

    def test_prompt_and_prompt_file_are_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit):
            codex_image.parse_args(["--prompt", "x", "--prompt-file", "y.txt"])

    def test_repeated_images_collect(self) -> None:
        args = codex_image.parse_args(
            ["--prompt", "x", "--image", "a.png", "--image", "b.png", "--reference-image", "c.png"]
        )
        self.assertEqual(args.image, ["a.png", "b.png"])
        self.assertEqual(args.reference_image, ["c.png"])


class PromptReadingTests(unittest.TestCase):
    def test_prompt_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.txt"
            path.write_text("  minimal cover, no text  \n", encoding="utf-8")
            args = codex_image.parse_args(["--prompt-file", str(path)])
            self.assertEqual(codex_image.read_prompt(args), "minimal cover, no text")

    def test_missing_prompt_file_is_actionable(self) -> None:
        args = codex_image.parse_args(["--prompt-file", "/nonexistent/prompt.txt"])
        with self.assertRaises(codex_image.CodexImageError):
            codex_image.read_prompt(args)

    def test_empty_prompt_is_rejected(self) -> None:
        args = codex_image.parse_args(["--prompt", "   "])
        with self.assertRaises(codex_image.CodexImageError):
            codex_image.read_prompt(args)


class RequestBodyTests(unittest.TestCase):
    def test_text_to_image_shape(self) -> None:
        args = codex_image.parse_args(["--prompt", "cover"])
        body = codex_image.build_request_body(args, "cover")
        self.assertEqual(body["model"], "gpt-6-astra")
        self.assertEqual(body["stream"], True)
        tool = body["tools"][0]
        self.assertEqual(tool["type"], "image_generation")
        self.assertEqual(tool["model"], "gpt-image-2")
        self.assertEqual(tool["size"], "1024x1024")
        self.assertEqual(tool["quality"], "medium")
        self.assertEqual(body["tool_choice"]["mode"], "required")
        self.assertEqual(body["input"][0]["content"][0], {"type": "input_text", "text": "cover"})

    def test_aspect_maps_to_size(self) -> None:
        cases = {"square": "1024x1024", "landscape": "1536x1024", "portrait": "1024x1536"}
        for aspect, size in cases.items():
            args = codex_image.parse_args(["--prompt", "x", "--aspect", aspect])
            self.assertEqual(codex_image.build_request_body(args, "x")["tools"][0]["size"], size)

    def test_local_input_image_becomes_data_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "draft.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n")
            args = codex_image.parse_args(["--prompt", "edit", "--image", str(image)])
            content = codex_image.build_request_body(args, "edit")["input"][0]["content"]
            self.assertEqual(content[0]["type"], "input_text")
            self.assertIn("Target/input image 1", content[1]["text"])
            self.assertTrue(content[2]["image_url"].startswith("data:image/"))

    def test_remote_and_data_sources_pass_through(self) -> None:
        args = codex_image.parse_args(
            ["--prompt", "x", "--reference-image", "https://example.com/ref.png"]
        )
        content = codex_image.build_request_body(args, "x")["input"][0]["content"]
        self.assertEqual(content[2]["image_url"], "https://example.com/ref.png")

    def test_targets_and_references_are_labeled_in_order(self) -> None:
        args = codex_image.parse_args(
            [
                "--prompt", "x",
                "--image", "https://example.com/canvas.png",
                "--reference-image", "https://example.com/face.png",
            ]
        )
        content = codex_image.build_request_body(args, "x")["input"][0]["content"]
        self.assertIn("Target/input image 1", content[1]["text"])
        self.assertEqual(content[2]["image_url"], "https://example.com/canvas.png")
        self.assertIn("Reference image 1", content[3]["text"])
        self.assertIn("Do not treat it as the target canvas", content[3]["text"])
        self.assertEqual(content[4]["image_url"], "https://example.com/face.png")


class SseParsingTests(unittest.TestCase):
    def test_final_image_wins_over_partial(self) -> None:
        payload = {
            "type": "response.completed",
            "nested": [{"partial_image_b64": "cGFydGlhbA=="}],
            "response": {"output": [{"type": "image_generation_call", "result": "ZmluYWw="}]},
        }
        finals, partials = codex_image.extract_image_candidates(payload)
        self.assertEqual(finals, ["ZmluYWw="])
        self.assertEqual(partials, ["cGFydGlhbA=="])

    def test_last_final_image_is_kept(self) -> None:
        payload = {
            "a": {"type": "image_generation_call", "result": "b28="},
            "b": {"type": "image_generation_call", "result": "bmV3ZXI="},
        }
        finals, _ = codex_image.extract_image_candidates(payload)
        self.assertEqual(finals, ["b28=", "bmV3ZXI="])
        self.assertEqual(finals[-1], "bmV3ZXI=")

    def test_blank_and_empty_results_are_ignored(self) -> None:
        payload = {"type": "image_generation_call", "result": "   "}
        finals, partials = codex_image.extract_image_candidates(payload)
        self.assertEqual((finals, partials), ([], []))


class TokenHandlingTests(unittest.TestCase):
    def test_expired_token_is_detected(self) -> None:
        expired = dt.datetime.now(dt.timezone.utc).timestamp() - 1000
        self.assertTrue(codex_image.token_expired(make_jwt({"exp": expired})))

    def test_valid_token_is_not_expired(self) -> None:
        valid = dt.datetime.now(dt.timezone.utc).timestamp() + 3600
        self.assertFalse(codex_image.token_expired(make_jwt({"exp": valid})))

    def test_missing_exp_is_treated_as_valid(self) -> None:
        self.assertFalse(codex_image.token_expired(make_jwt({"sub": "u"})))

    def test_non_jwt_token_raises(self) -> None:
        with self.assertRaises(codex_image.CodexImageError):
            codex_image.decode_jwt_payload("not-a-jwt")


class AuthFileTests(unittest.TestCase):
    def test_missing_auth_file_is_actionable(self) -> None:
        original = codex_image.AUTH_PATH
        try:
            codex_image.AUTH_PATH = Path("/nonexistent/auth.json")
            with self.assertRaises(codex_image.CodexImageError):
                codex_image.load_auth_data()
        finally:
            codex_image.AUTH_PATH = original

    def test_auth_roundtrip_preserves_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original = codex_image.AUTH_PATH
            try:
                target = Path(tmp) / "auth.json"
                codex_image.AUTH_PATH = target
                data = {"auth_mode": "chatgpt", "tokens": {"access_token": "a", "refresh_token": "r"}}
                codex_image.save_auth_data(dict(data))
                reloaded = codex_image.load_auth_data()
                self.assertEqual(reloaded, data)
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            finally:
                codex_image.AUTH_PATH = original

    def test_account_id_prefers_jwt_claim(self) -> None:
        token = make_jwt({"https://api.openai.com/auth": {"chatgpt_account_id": "acct-jwt"}})
        auth = {"tokens": {"access_token": token, "account_id": "acct-file"}}
        self.assertEqual(codex_image.extract_account_id(auth), "acct-jwt")

    def test_account_id_falls_back_to_file(self) -> None:
        token = make_jwt({"sub": "u"})
        auth = {"tokens": {"access_token": token, "account_id": "acct-file"}}
        self.assertEqual(codex_image.extract_account_id(auth), "acct-file")


class ImageSourceTests(unittest.TestCase):
    def test_missing_local_image_is_actionable(self) -> None:
        with self.assertRaises(codex_image.CodexImageError):
            codex_image.normalize_image_source("/nonexistent/image.png")

    def test_empty_source_is_rejected(self) -> None:
        with self.assertRaises(codex_image.CodexImageError):
            codex_image.normalize_image_source("   ")

    def test_data_url_passthrough(self) -> None:
        source = "data:image/png;base64,AAA"
        self.assertEqual(codex_image.normalize_image_source(source), source)


class OutputNamingTests(unittest.TestCase):
    def test_output_name_is_predictable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = codex_image.output_path_for("cover prompt", tmp)
            self.assertTrue(str(path).startswith(str(Path(tmp).resolve())))
            self.assertRegex(path.name, r"^codex-image-\d{8}-\d{6}-[0-9a-f]{12}-[0-9a-f]{6}\.png$")

    def test_parallel_same_prompt_gets_distinct_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = codex_image.save_new_image(b"a", "stable", tmp)
            second = codex_image.save_new_image(b"b", "stable", tmp)
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b"a")

    def test_name_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = codex_image.save_new_image(b"a", "x", tmp, "hero.png")
            (Path(tmp) / "hero-2.png.manifest.json").write_text("{}", encoding="utf-8")
            second = codex_image.save_new_image(b"b", "x", tmp, "hero")
            self.assertEqual(first.name, "hero.png")
            self.assertEqual(second.name, "hero-3.png")
            self.assertEqual(first.read_bytes(), b"a")

    def test_name_rejects_directories(self) -> None:
        for bad in ("../x", "a/b", "  ", ".png"):
            with self.assertRaises(codex_image.CodexImageError):
                codex_image.normalize_output_name(bad)


class ContinuationTests(unittest.TestCase):
    def _manifest(self, directory: Path, image: Path, refs: list) -> Path:
        manifest = {
            "schema_version": 1,
            "output": {"image": {"kind": "local_file", "source": str(image), "reusable": True}},
            "reference_images": refs,
        }
        path = directory / (image.name + ".manifest.json")
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_previous_image_and_reusable_references_carry_over(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            image = directory / "round1.png"
            image.write_bytes(b"png")
            refs = [
                {"source": "https://example.com/face.png", "reusable": True},
                {"source": "data:image/png;base64,AAA", "reusable": False},
            ]
            manifest = self._manifest(directory, image, refs)
            args = codex_image.parse_args(
                ["--prompt", "fix hair", "--continue-from", str(manifest),
                 "--reference-image", "https://example.com/style.png"]
            )
            continued = codex_image.apply_continuation(args)
            self.assertEqual(args.image, [str(image.resolve())])
            self.assertEqual(
                args.reference_image,
                ["https://example.com/face.png", "https://example.com/style.png"],
            )
            self.assertEqual(continued["path"], str(manifest.resolve()))

    def test_moved_folder_falls_back_to_manifest_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            image = directory / "round1.png"
            image.write_bytes(b"png")
            manifest = self._manifest(directory, Path("/old/place/round1.png"), [])
            args = codex_image.parse_args(["--prompt", "x", "--continue-from", str(manifest)])
            codex_image.apply_continuation(args)
            self.assertEqual(args.image, [str(image.resolve())])

    def test_missing_manifest_is_actionable(self) -> None:
        args = codex_image.parse_args(["--prompt", "x", "--continue-from", "/nonexistent/m.json"])
        with self.assertRaises(codex_image.CodexImageError):
            codex_image.apply_continuation(args)


class CliContractTests(unittest.TestCase):
    def test_help_runs_offline(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for token in (
            "--prompt", "--aspect", "--quality", "--image", "--reference-image",
            "--response-model", "--continue-from", "--manifest-out", "--name",
        ):
            self.assertIn(token, result.stdout)


if __name__ == "__main__":
    unittest.main()
