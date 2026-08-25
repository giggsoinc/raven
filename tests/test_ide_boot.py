#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    import importlib.util

    p = ROOT / "scripts" / "memory" / "ide-boot.py"
    spec = importlib.util.spec_from_file_location("ide_boot", p)
    mod = spec.loader.load_module()
    return mod


class TestIdeBoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _root(self, card_text: str | None):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / ".raven" / "memory").mkdir(parents=True)
        (root / ".raven" / "boot.json").write_text(
            (ROOT / ".raven" / "boot.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        if card_text is not None:
            (root / ".raven" / "memory" / "CARD.md").write_text(card_text, encoding="utf-8")
        self.addCleanup(td.cleanup)
        return root

    def test_claude_points_claudemd(self):
        root = self._root("schema: 1\nstatus: FRESH\n")
        r = self.mod.route({"CLAUDECODE": "1"}, root)
        self.assertEqual(r["host"], "claude")
        self.assertEqual(r["rules"], "CLAUDE.md")
        self.assertEqual(r["load"], 1)
        self.assertEqual(r.get("educate"), "guided")
        self.assertIn("SIMPLE→", r.get("expected_route", ""))
        self.assertIn("raven-first.py", r.get("route", ""))
        self.assertTrue(r.get("dashboard", "").startswith("http://127.0.0.1:9787"))
        self.assertIn("#", r.get("dashboard", ""))

    def test_codex_and_grok_use_agents(self):
        root = self._root("schema: 1\nstatus: FRESH\n")
        c = self.mod.route({"CODEX_HOME": "/tmp/c"}, root)
        g = self.mod.route({"GROK_SESSION_ID": "1"}, root)
        self.assertEqual(c["host"], "codex")
        self.assertEqual(g["host"], "grok")
        self.assertEqual(c["rules"], "AGENTS.md")
        self.assertEqual(g["rules"], "AGENTS.md")

    def test_antigravity_points_agents_dir(self):
        root = self._root("schema: 1\nstatus: FRESH\n")
        r = self.mod.route({"ANTIGRAVITY": "1"}, root)
        self.assertEqual(r["host"], "antigravity")
        self.assertEqual(r["rules"], ".agents/agents.md")
        self.assertEqual(r["load"], 1)

    def test_no_card_load_zero(self):
        root = self._root(None)
        r = self.mod.route({"CLAUDECODE": "1"}, root)
        self.assertEqual(r["load"], 0)
        self.assertEqual(r["memory"], "")

    def test_bad_schema_load_zero(self):
        root = self._root("schema: 99\nstatus: FRESH\n")
        r = self.mod.route({"CLAUDECODE": "1"}, root)
        self.assertEqual(r["load"], 0)

    def test_cursor_windsurf_replit(self):
        root = self._root("schema: 1\nstatus: FRESH\n")
        cur = self.mod.route({"CURSOR_AGENT": "1"}, root)
        win = self.mod.route({"WINDSURF": "1"}, root)
        rep = self.mod.route({"REPL_ID": "abc"}, root)
        self.assertEqual(cur["host"], "cursor")
        self.assertEqual(cur["rules"], "AGENTS.md")
        self.assertEqual(win["host"], "windsurf")
        self.assertEqual(win["rules"], ".windsurf/rules/ide-boot.md")
        self.assertEqual(rep["host"], "replit")
        self.assertEqual(rep["rules"], "replit.md")
        self.assertEqual(cur["load"], 1)
        self.assertIn("code-xray.py", cur.get("graph_cli") or "")
        self.assertIn("query_graph", cur.get("mcp") or "")

    def test_claim_browser_open_once(self):
        td = tempfile.TemporaryDirectory()
        lock = Path(td.name) / ".browser-opened"
        self.addCleanup(td.cleanup)
        self.assertTrue(self.mod.claim_browser_open(lock, force=False))
        self.assertFalse(self.mod.claim_browser_open(lock, force=False))
        self.assertTrue(self.mod.claim_browser_open(lock, force=True))

    def test_print_includes_first_load_line(self):
        src = (ROOT / "scripts" / "memory" / "ide-boot.py").read_text()
        self.assertIn(
            "first_load=run ide-boot then Read memory= if load=1 then model-router --session-start",
            src,
        )

    def test_ensure_dashboard_server_helpers(self):
        self.assertTrue(hasattr(self.mod, "ensure_dashboard_server"))
        self.assertTrue(hasattr(self.mod, "dashboard_server_up"))
        self.assertEqual(self.mod.DASH_PORT, 9787)
        # Down port must not raise
        self.assertIsInstance(self.mod.dashboard_server_up(1), bool)
