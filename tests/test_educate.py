#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = spec.loader.load_module()
    return mod


class TestEducate(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / ".raven").mkdir()
        self.edu = _load("educate", ROOT / "scripts" / "memory" / "educate.py")
        # The wired hooks run scripts/guards/. Test the live files, not the stale .claude/scripts copies.
        self.gate = _load("push_gate", ROOT / "scripts" / "guards" / "push-gate.py")
        self.appr = _load("push_approve", ROOT / "scripts" / "guards" / "push-approve.py")

    def tearDown(self):
        self.td.cleanup()

    def test_missing_file_is_guided(self):
        self.assertEqual(self.edu.load_mode(self.root), "guided")

    def test_off_persists(self):
        self.edu.save_mode(self.root, "off")
        self.assertEqual(self.edu.load_mode(self.root), "off")
        self.assertTrue((self.root / ".raven" / "educate.json").is_file())

    def test_auto_alias_off(self):
        self.edu.save_mode(self.root, "auto")
        self.assertEqual(self.edu.load_mode(self.root), "off")

    def test_gate_denies_write_when_guided(self):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.py"}})
        buf = io.StringIO()
        with patch.object(self.gate, "repo_root", return_value=str(self.root)):
            with patch.object(sys, "stdin", io.StringIO(payload)):
                with patch("sys.stdout", buf):
                    try:
                        self.gate.main()
                    except SystemExit:
                        pass
        out = buf.getvalue()
        self.assertIn("deny", out)

    def test_gate_allows_when_off(self):
        self.edu.save_mode(self.root, "off")
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.py"}})
        with patch.object(self.gate, "repo_root", return_value=str(self.root)):
            with patch.object(sys, "stdin", io.StringIO(payload)):
                try:
                    self.gate.main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)
                    return
        self.fail("expected sys.exit(0)")

    def _bash(self, cmd: str):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
        buf = io.StringIO()
        with patch.object(self.gate, "repo_root", return_value=str(self.root)):
            with patch.object(sys, "stdin", io.StringIO(payload)):
                with patch("sys.stdout", buf):
                    try:
                        self.gate.main()
                    except SystemExit as e:
                        return e.code, buf.getvalue()
        return 0, buf.getvalue()

    def test_gate_allows_readonly_bash(self):
        code, out = self._bash("git status")
        self.assertEqual(code, 0)
        self.assertNotIn("deny", out)

    def test_gate_allows_python_status(self):
        code, out = self._bash("python3 scripts/routing/model-router.py --status")
        self.assertEqual(code, 0)
        self.assertNotIn("deny", out)

    def test_gate_allows_unittest(self):
        code, out = self._bash("python3 -m unittest tests.test_educate")
        self.assertEqual(code, 0)
        self.assertNotIn("deny", out)

    def test_gate_allows_educate_cli(self):
        code, out = self._bash("python3 scripts/memory/educate.py")
        self.assertEqual(code, 0)
        self.assertNotIn("deny", out)

    def test_gate_denies_python_html_write(self):
        code, out = self._bash("python3 scripts/dashboard.py --html")
        self.assertIn("deny", out)

    def test_approve_go_ahead(self):
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        payload = json.dumps({"prompt": "go ahead"})
        with patch.object(sys, "stdin", io.StringIO(payload)):
            self.appr.main()
        self.assertTrue((self.root / ".raven" / ".push-approved").is_file())

    def test_lucky_sets_off(self):
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        payload = json.dumps({"prompt": "Lucky"})
        with patch.object(sys, "stdin", io.StringIO(payload)):
            self.appr.main()
        data = json.loads((self.root / ".raven" / "educate.json").read_text())
        self.assertEqual(data["mode"], "off")


if __name__ == "__main__":
    unittest.main()
