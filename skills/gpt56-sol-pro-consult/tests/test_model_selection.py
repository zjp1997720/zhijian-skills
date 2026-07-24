#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_gpt56_sol_pro_consult.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("gpt56_sol_pro_runner", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ModelSelectionTests(unittest.TestCase):
    def test_accepts_current_pro_testid(self) -> None:
        state = "[41] <div role=menuitemradio data-testid=model-switcher-gpt-5-pro aria-checked=true>Pro"
        self.assertTrue(MODULE.model_is_confirmed(state))

    def test_accepts_unified_picker_pro_entry(self) -> None:
        state = "[9] <div role=menuitemradio aria-checked=true>\n  Pro\n[10] <div role=menuitem>GPT-5.6 Sol"
        self.assertTrue(MODULE.model_is_confirmed(state))

    def test_rejects_bare_pro_without_gpt56_family(self) -> None:
        state = "[9] <div role=menuitemradio aria-checked=true>Pro"
        self.assertFalse(MODULE.model_is_confirmed(state))

    def test_rejects_legacy_gpt55_pro(self) -> None:
        state = "[12] <div role=menuitemradio data-testid=model-switcher-gpt-5-5-pro aria-checked=true>GPT 5.5 Pro"
        self.assertFalse(MODULE.model_is_confirmed(state))

    def test_rejects_base_sol_extra_high(self) -> None:
        state = "[18] <div role=menuitemradio aria-checked=true>Extra High GPT-5.6 Sol"
        self.assertFalse(MODULE.model_is_confirmed(state))

    def test_finds_current_pro_reference(self) -> None:
        state = "[27] <div role=menuitemradio aria-checked=false>Pro\n[28] <div role=menuitem>GPT-5.6 Sol"
        self.assertEqual(MODULE.find_pro_ref(state), "27")


if __name__ == "__main__":
    unittest.main()
