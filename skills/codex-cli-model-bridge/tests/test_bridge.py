import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bridge.py"


def run_bridge(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def native_template() -> dict:
    return {
        "slug": "gpt-5.6-sol",
        "display_name": "GPT-5.6-Sol",
        "description": "native",
        "default_reasoning_level": "high",
        "supported_reasoning_levels": [{"effort": "high", "description": "high"}],
        "visibility": "list",
        "supported_in_api": True,
        "priority": 1,
        "additional_speed_tiers": ["fast"],
        "service_tiers": [{"id": "priority", "name": "Fast"}],
        "context_window": 272000,
        "max_context_window": 272000,
        "effective_context_window_percent": 95,
        "input_modalities": ["text", "image"],
        "supports_search_tool": True,
        "supports_image_detail_original": False,
        "supports_parallel_tool_calls": True,
        "tool_mode": "code_mode_only",
        "model_messages": {"instructions_template": "test"},
    }


class BridgeTests(unittest.TestCase):
    def test_bundled_manifests_validate(self) -> None:
        for manifest in sorted((SCRIPT.parents[1] / "models").glob("*.json")):
            proc = run_bridge("validate-manifest", str(manifest))
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertEqual(json.loads(proc.stdout)["status"], "valid")

    def test_catalog_policy_blocks_superseding_thread_creation_models(self) -> None:
        module_spec = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        policy = {
            "protected_native_model_ids": ["gpt-5.6-sol"],
        }
        manifests = [
            {
                "slug": "gpt-5.6-sol-standard",
                "supersedes": ["gpt-5.6-sol"],
            }
        ]

        self.assertEqual(
            module.protected_supersede_conflicts(manifests, policy),
            ["gpt-5.6-sol"],
        )

    def test_required_live_routes_include_visible_and_default_models(self) -> None:
        module_spec = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        required = module.required_live_routes(
            [
                {"slug": "gpt-5.6-sol", "visibility": "list", "supported_in_api": True},
                {"slug": "gpt-5.5", "visibility": "hide", "supported_in_api": True},
                {"slug": "gpt-5.6-sol-wm", "visibility": "list", "supported_in_api": False},
                {"slug": "grok-4.6", "visibility": "list", "supported_in_api": True},
            ],
            ["grok-4.6"],
            "gpt-5.6-sol",
        )

        self.assertEqual(required, ["gpt-5.6-sol", "grok-4.6"])

    def test_parse_proxy_version(self) -> None:

        module_spec = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        self.assertEqual(
            module.parse_proxy_version("CLIProxyAPI Version: 7.2.130, Commit: Homebrew"),
            (7, 2, 130),
        )
        self.assertIsNone(module.parse_proxy_version("unknown"))

    def test_build_entry_can_disable_inherited_code_mode(self) -> None:
        manifest = {
            "template_slug": "gpt-5.6-sol",
            "slug": "grok-4.6",
            "display_name": "Grok 4.6",
            "description": "test",
            "default_reasoning_level": "high",
            "reasoning_efforts": ["high"],
            "priority": 40,
            "context_window": 500000,
            "effective_context_window_percent": 95,
            "input_modalities": ["text"],
            "tool_mode": None,
        }

        entry = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(entry)
        entry.loader.exec_module(module)
        result = module.build_entry(manifest, {"gpt-5.6-sol": native_template()})

        self.assertNotIn("tool_mode", result)

    def test_shell_probe_requires_command_execution_event(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog = root / "catalog.json"
            fake_codex = root / "codex"
            catalog.write_text(json.dumps({"models": [{"slug": "grok-4.6"}]}), encoding="utf-8")
            fake_codex.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "out = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
                "out.write_text('CODEX_BRIDGE_SHELL_OK', encoding='utf-8')\n"
                "print(json.dumps({'type':'item.completed','item':{'type':'command_execution',"
                "'command':'/bin/zsh -lc pwd','status':'completed','exit_code':0}}))\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o700)

            proc = run_bridge(
                "probe",
                "--desktop",
                "--shell",
                "--models",
                "grok-4.6",
                "--catalog",
                str(catalog),
                "--codex",
                str(fake_codex),
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            result = json.loads(proc.stdout)["results"]["grok-4.6"]
            self.assertTrue(result["shell_executed"])

    def test_desktop_probe_uses_active_config_catalog_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            catalog = root / "router-catalog.json"
            fake_codex = root / "codex"
            model = "zai-coding/glm-5.3-flash"
            config.write_text(
                f"model_catalog_json = {json.dumps(str(catalog))}\n",
                encoding="utf-8",
            )
            catalog.write_text(json.dumps({"models": [{"slug": model}]}), encoding="utf-8")
            fake_codex.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "out = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
                "out.write_text('CODEX_BRIDGE_OK', encoding='utf-8')\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o700)

            proc = run_bridge(
                "probe",
                "--desktop",
                "--models",
                model,
                "--config",
                str(config),
                "--codex",
                str(fake_codex),
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["catalog"], str(catalog))
            self.assertTrue(payload["results"][model]["ok"])

    def test_desktop_probe_explicit_catalog_overrides_active_config(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            catalog = root / "explicit-catalog.json"
            fake_codex = root / "codex"
            model = "grok-4.6"
            config.write_text(
                'model_catalog_json = "/missing/router-catalog.json"\n',
                encoding="utf-8",
            )
            catalog.write_text(json.dumps({"models": [{"slug": model}]}), encoding="utf-8")
            fake_codex.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "out = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
                "out.write_text('CODEX_BRIDGE_OK', encoding='utf-8')\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o700)

            proc = run_bridge(
                "probe",
                "--desktop",
                "--models",
                model,
                "--config",
                str(config),
                "--catalog",
                str(catalog),
                "--codex",
                str(fake_codex),
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertEqual(json.loads(proc.stdout)["catalog"], str(catalog))

    def test_desktop_probe_blocks_when_config_has_no_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            config = Path(raw) / "config.toml"
            config.write_text('model = "gpt-5.6-sol"\n', encoding="utf-8")

            proc = run_bridge(
                "probe",
                "--desktop",
                "--models",
                "gpt-5.6-sol",
                "--config",
                str(config),
            )

            self.assertEqual(proc.returncode, 2)
            self.assertIn("no model_catalog_json", json.loads(proc.stdout)["error"])

    def test_profile_probe_keeps_cli_proxy_catalog_default(self) -> None:
        module_spec = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        target = module.probe_catalog_path(
            argparse.Namespace(catalog=None, desktop=False)
        )

        self.assertEqual(
            target,
            module.DEFAULT_CODEX_HOME / "model-catalog-cli-proxy.json",
        )

    def test_tool_sequence_probe_requires_both_commands_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog = root / "catalog.json"
            fake_codex = root / "codex"
            catalog.write_text(json.dumps({"models": [{"slug": "grok-4.6"}]}), encoding="utf-8")
            fake_codex.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "out = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
                "out.write_text('CODEX_BRIDGE_TOOL_SEQUENCE_OK', encoding='utf-8')\n"
                "for command in ('/bin/zsh -lc pwd', \"/bin/zsh -lc 'git --version'\"):\n"
                " print(json.dumps({'type':'item.completed','item':{'type':'command_execution',"
                "'command':command,'status':'completed','exit_code':0}}))\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o700)

            proc = run_bridge(
                "probe",
                "--desktop",
                "--tool-sequence",
                "--models",
                "grok-4.6",
                "--catalog",
                str(catalog),
                "--codex",
                str(fake_codex),
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            result = json.loads(proc.stdout)["results"]["grok-4.6"]
            self.assertTrue(result["tool_sequence_executed"])

    def test_tool_sequence_prompt_wins_when_shell_flag_is_also_present(self) -> None:
        module_spec = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        prompt = module.probe_prompt(shell=True, tool_sequence=True)

        self.assertIn("first run pwd", prompt)
        self.assertIn("then run git --version", prompt)
        self.assertIn("CODEX_BRIDGE_TOOL_SEQUENCE_OK", prompt)

    def test_configure_writes_isolated_profile_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            profile = root / "cli-proxy.config.toml"
            catalog = root / "catalog.json"
            helper = root / "private" / "read-client-key.rb"
            proxy_config = root / "cliproxy.yml"
            config.write_text(
                'model = "keep-me"\npersonality = "pragmatic"\n\n'
                '[mcp_servers.keep]\ntype = "http"\nurl = "https://example.test"\n',
                encoding="utf-8",
            )
            proxy_config.write_text('api-keys: ["fixture"]\n', encoding="utf-8")
            args = (
                "configure",
                "--profile-config",
                str(profile),
                "--catalog",
                str(catalog),
                "--helper",
                str(helper),
                "--proxy-config",
                str(proxy_config),
                "--apply",
            )
            first = run_bridge(*args)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            self.assertIn('model = "keep-me"', config.read_text(encoding="utf-8"))
            text = profile.read_text(encoding="utf-8")
            self.assertIn("[model_providers.cli_proxy]", text)
            self.assertNotIn("cli_proxy", config.read_text(encoding="utf-8"))
            self.assertEqual(profile.stat().st_mode & 0o777, 0o600)
            self.assertEqual(helper.stat().st_mode & 0o777, 0o700)
            second = run_bridge(*args)
            self.assertEqual(json.loads(second.stdout)["status"], "unchanged")

    def test_restore_default_follows_dominant_history_without_mutating_threads(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            native = root / "models_cache.json"
            state_db = root / "state.sqlite"
            config.write_text(
                'model = "grok-4.6"\nmodel_provider = "cli_proxy"\nmodel_catalog_json = "/tmp/custom.json"\n',
                encoding="utf-8",
            )
            native.write_text(json.dumps({"models": [native_template()]}), encoding="utf-8")
            connection = sqlite3.connect(state_db)
            connection.execute("CREATE TABLE threads (id TEXT, model_provider TEXT, archived INTEGER)")
            connection.executemany(
                "INSERT INTO threads VALUES (?, ?, 0)",
                [("openai-1", "openai"), ("openai-2", "openai"), ("proxy-1", "cli_proxy")],
            )
            connection.commit()
            connection.close()
            sha = hashlib.sha256(config.read_bytes()).hexdigest()
            proc = run_bridge(
                "restore-default",
                "--config",
                str(config),
                "--state-db",
                str(state_db),
                "--native-catalog",
                str(native),
                "--expected-sha256",
                sha,
                "--apply",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["target_provider"], "openai")
            text = config.read_text(encoding="utf-8")
            self.assertIn('model_provider = "openai"', text)
            self.assertIn('model = "gpt-5.6-sol"', text)
            self.assertNotIn("model_catalog_json", text)
            self.assertNotIn("openai_base_url", text)
            connection = sqlite3.connect(state_db)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM threads").fetchone()[0], 3)
            connection.close()

    def test_configure_desktop_preview_preserves_openai_history_identity(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            catalog = root / "catalog.json"
            auth = root / "auth.json"
            helper = root / "read-client-key.rb"
            state_db = root / "state.sqlite"
            runtime = root / "runtime.mjs"
            launch_agent = root / "bridge.plist"
            node = root / "node"
            config.write_text('model = "gpt-5.6-sol"\nmodel_provider = "openai"\n', encoding="utf-8")
            catalog.write_text(
                json.dumps(
                    {
                        "models": [
                            native_template(),
                            {**native_template(), "slug": "grok-4.6"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            auth.write_text(
                json.dumps(
                    {
                        "auth_mode": "chatgpt",
                        "tokens": {
                            "id_token": "fixture",
                            "access_token": "fixture",
                            "refresh_token": "fixture",
                        },
                    }
                ),
                encoding="utf-8",
            )
            helper.write_text("fixture", encoding="utf-8")
            node.write_text("fixture", encoding="utf-8")
            connection = sqlite3.connect(state_db)
            connection.execute("CREATE TABLE threads (id TEXT, model_provider TEXT, archived INTEGER)")
            connection.executemany(
                "INSERT INTO threads VALUES (?, ?, 0)",
                [("openai-1", "openai"), ("openai-2", "openai"), ("proxy-1", "cli_proxy")],
            )
            connection.commit()
            connection.close()
            proc = run_bridge(
                "configure-desktop",
                "--config",
                str(config),
                "--state-db",
                str(state_db),
                "--catalog",
                str(catalog),
                "--auth-file",
                str(auth),
                "--helper",
                str(helper),
                "--runtime-script",
                str(runtime),
                "--launch-agent",
                str(launch_agent),
                "--node",
                str(node),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "planned")
            self.assertIn('model_provider = "openai"', payload["diff"])
            self.assertIn('openai_base_url = "http://127.0.0.1:8318/v1"', payload["diff"])
            self.assertFalse(runtime.exists())
            self.assertFalse(launch_agent.exists())

    def test_configure_multi_agent_is_guarded_redacted_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            proxy_config = root / "cliproxyapi.conf"
            proxy_config.write_text(
                'api-keys:\n  - "fixture-secret"\ncodex:\n  identity-confuse: false\n  optimize-multi-agent-v2: false\n',
                encoding="utf-8",
            )
            base = (
                "configure-multi-agent",
                "--proxy-config",
                str(proxy_config),
                "--skip-restart",
            )
            preview = run_bridge(*base)
            self.assertEqual(preview.returncode, 0, preview.stderr or preview.stdout)
            payload = json.loads(preview.stdout)
            self.assertEqual(payload["status"], "planned")
            self.assertNotIn("fixture-secret", payload["diff"])
            sha = payload["config_sha256"]
            wrong = run_bridge(*base, "--expected-sha256", "0" * 64, "--apply")
            self.assertEqual(wrong.returncode, 2)
            applied = run_bridge(*base, "--expected-sha256", sha, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            applied_payload = json.loads(applied.stdout)
            self.assertEqual(applied_payload["status"], "applied")
            self.assertTrue(applied_payload["backup"])
            text = proxy_config.read_text(encoding="utf-8")
            self.assertIn("  optimize-multi-agent-v2: true\n", text)
            self.assertIn("fixture-secret", text)
            again = run_bridge(*base, "--apply")
            self.assertEqual(again.returncode, 0, again.stderr or again.stdout)
            self.assertEqual(json.loads(again.stdout)["status"], "unchanged")

    def test_sync_requires_adoption_then_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            native = root / "models_cache.json"
            target = root / "catalog.json"
            state = root / "state"
            config.write_text(
                '[model_providers.cli_proxy]\nbase_url = "http://127.0.0.1:8317/v1"\nwire_api = "responses"\n',
                encoding="utf-8",
            )
            native.write_text(json.dumps({"models": [native_template()]}), encoding="utf-8")
            manual_grok = native_template()
            manual_grok.update({"slug": "grok-4.6", "display_name": "manual"})
            target.write_text(json.dumps({"models": [native_template(), manual_grok]}), encoding="utf-8")
            base = (
                "sync",
                "--config",
                str(config),
                "--catalog",
                str(target),
                "--native-catalog",
                str(native),
                "--state-dir",
                str(state),
                "--skip-live-check",
            )
            blocked = run_bridge(*base)
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(json.loads(blocked.stdout)["conflicts"], ["grok-4.6"])
            applied = run_bridge(*base, "--adopt", "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            payload = json.loads(applied.stdout)
            self.assertEqual(payload["status"], "applied")
            slugs = {item["slug"] for item in json.loads(target.read_text())["models"]}
            self.assertEqual(
                slugs,
                {"gpt-5.6-sol", "grok-4.6", "deepseek-v4-pro", "deepseek-v4-flash", "kimi-k3"},
            )
            again = run_bridge(*base, "--apply")
            self.assertEqual(again.returncode, 0, again.stderr or again.stdout)
            self.assertEqual(json.loads(again.stdout)["status"], "unchanged")

    def test_sync_hides_native_models_by_policy_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "config.toml"
            native = root / "models_cache.json"
            target = root / "catalog.json"
            policy = root / "catalog-policy.json"
            state = root / "state"
            config.write_text(
                '[model_providers.cli_proxy]\nbase_url = "http://127.0.0.1:8317/v1"\nwire_api = "responses"\n',
                encoding="utf-8",
            )
            old_model = {**native_template(), "slug": "gpt-5.4", "display_name": "GPT-5.4"}
            native.write_text(json.dumps({"models": [native_template(), old_model]}), encoding="utf-8")
            target.write_text(json.dumps({"models": [native_template(), old_model]}), encoding="utf-8")
            policy.write_text(
                json.dumps({"schema_version": 1, "hidden_native_model_ids": ["gpt-5.4"]}),
                encoding="utf-8",
            )
            base = (
                "sync",
                "--config",
                str(config),
                "--catalog",
                str(target),
                "--native-catalog",
                str(native),
                "--catalog-policy",
                str(policy),
                "--state-dir",
                str(state),
                "--skip-live-check",
            )
            applied = run_bridge(*base, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            payload = json.loads(applied.stdout)
            self.assertEqual(payload["hidden_native_models"], ["gpt-5.4"])
            entries = {item["slug"]: item for item in json.loads(target.read_text())["models"]}
            self.assertEqual(entries["gpt-5.4"]["visibility"], "hide")
            self.assertIn("gpt-5.4", entries)
            again = run_bridge(*base, "--apply")
            self.assertEqual(again.returncode, 0, again.stderr or again.stdout)
            self.assertEqual(json.loads(again.stdout)["status"], "unchanged")

    def test_configure_writes_python_helper_that_reads_api_keys(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile = root / "cli-proxy.config.toml"
            catalog = root / "catalog.json"
            helper = root / "private" / "read-client-key.py"
            proxy_config = root / "cliproxy.yml"
            proxy_config.write_text('api-keys:\n  - "fixture-key-value"\n', encoding="utf-8")
            proc = run_bridge(
                "configure",
                "--profile-config",
                str(profile),
                "--catalog",
                str(catalog),
                "--helper",
                str(helper),
                "--proxy-config",
                str(proxy_config),
                "--apply",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            text = profile.read_text(encoding="utf-8")
            self.assertIn(sys.executable, text)
            self.assertIn(str(helper), text)
            parsed = subprocess.run(
                [sys.executable, str(helper)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(parsed.returncode, 0, parsed.stderr)
            self.assertEqual(parsed.stdout, "fixture-key-value")

    def test_helper_invocation_matches_helper_extension(self) -> None:
        module_spec = __import__("importlib.util").util.spec_from_file_location("bridge", SCRIPT)
        module = __import__("importlib.util").util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        command, args = module.helper_invocation(Path("read-client-key.py"))
        self.assertEqual(command, sys.executable)
        self.assertEqual(args, ["read-client-key.py"])
        command, args = module.helper_invocation(Path("read-client-key.rb"))
        self.assertTrue(Path(command).name.startswith("ruby") or command.endswith("ruby"))
        self.assertEqual(args, ["read-client-key.rb"])


if __name__ == "__main__":
    unittest.main()
