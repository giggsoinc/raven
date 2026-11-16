#!/usr/bin/env python3
"""hook-run: a missing script exits 0 and leaves an audit row. A real script keeps its exit code."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "ops" / "hook-run.py"


class TestHookRun(unittest.TestCase):
    def test_missing_script_exits_0_and_audits(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, CLAUDE_PROJECT_DIR=td)
            ran = subprocess.run(
                ["python3", str(HOOK), "scripts/routing/does-not-exist.py"],
                cwd=td, env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(ran.returncode, 0)
            self.assertIn("hook script missing", ran.stderr)
            day_logs = list((Path(td) / ".raven" / "audit").glob("*.log"))
            self.assertEqual(len(day_logs), 1)
            row = json.loads(day_logs[0].read_text().strip())
            self.assertEqual(row["source"], "hook-run")
            self.assertEqual(row["event"], "missing-script")
            self.assertTrue(row["script"].endswith("scripts/routing/does-not-exist.py"))

    def test_existing_script_keeps_its_exit_code(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "exit3.py"
            script.write_text("import sys\nsys.exit(3)\n")
            env = dict(os.environ, CLAUDE_PROJECT_DIR=td)
            ran = subprocess.run(
                ["python3", str(HOOK), str(script)],
                cwd=td, env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(ran.returncode, 3)
            self.assertEqual(list((Path(td) / ".raven" / "audit").glob("*.log")), [])


if __name__ == "__main__":
    unittest.main()
