#!/usr/bin/env python3
"""Plugin session-start must not auto-tier Opus (Rule 8)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SS = ROOT / "plugin" / "scripts" / "session-start.py"
CANON = ROOT / "scripts" / "session" / "session-start.py"


class TestPluginMirrorRule8(unittest.TestCase):
    def test_plugin_session_start_is_symlink_to_canon(self):
        self.assertTrue(PLUGIN_SS.is_symlink() or PLUGIN_SS.is_file())
        text = PLUGIN_SS.read_text(encoding="utf-8")
        self.assertNotIn('"claude-opus-4-5": "high"', text)
        self.assertIn("NOT tiered", text)
        canon = CANON.read_text(encoding="utf-8")
        self.assertIn("NOT tiered", canon)


if __name__ == "__main__":
    unittest.main()
