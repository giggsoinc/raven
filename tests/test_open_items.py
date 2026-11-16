"""Regression tests for the open-item fixes made after the 6.1.2 release.

- push-approve prints the go-ahead banner only in guided mode.
- the MCP server reports the real raven-core version, not a stale constant.
- .mcp.json never uses the VS Code-only ${workspaceFolder} variable.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUSH_APPROVE = ROOT / "scripts" / "guards" / "push-approve.py"


def _run_push_approve(mode: str, prompt: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        raven = Path(td) / ".raven"
        raven.mkdir()
        (raven / "educate.json").write_text(json.dumps({"mode": mode}), encoding="utf-8")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=td)
        result = subprocess.run(
            [sys.executable, str(PUSH_APPROVE)],
            input=json.dumps({"prompt": prompt}),
            capture_output=True, text=True, env=env, timeout=10,
        )
        return result.stdout


class TestPushApproveBanner(unittest.TestCase):
    def test_guided_yes_prints_go_ahead(self):
        self.assertIn("go-ahead", _run_push_approve("guided", "yes"))

    def test_off_yes_prints_nothing(self):
        self.assertEqual(_run_push_approve("off", "yes").strip(), "")

    def test_off_still_writes_approval_file(self):
        with tempfile.TemporaryDirectory() as td:
            raven = Path(td) / ".raven"
            raven.mkdir()
            (raven / "educate.json").write_text('{"mode": "off"}', encoding="utf-8")
            subprocess.run(
                [sys.executable, str(PUSH_APPROVE)],
                input=json.dumps({"prompt": "go ahead"}),
                capture_output=True, text=True, timeout=10,
                env=dict(os.environ, CLAUDE_PROJECT_DIR=td),
            )
            self.assertTrue((raven / ".push-approved").is_file())


class TestMcpConfig(unittest.TestCase):
    def test_server_version_matches_version_file(self):
        sys.path.insert(0, str(ROOT / "mcp"))
        try:
            import dispatch
            expected = (ROOT / "raven-core" / "VERSION").read_text(encoding="utf-8").strip()
            self.assertEqual(dispatch.server_version(), expected)
            self.assertEqual(dispatch.handle("initialize", {})["serverInfo"]["version"], expected)
        finally:
            sys.path.remove(str(ROOT / "mcp"))

    def test_mcp_json_has_no_workspace_folder_variable(self):
        text = (ROOT / ".mcp.json").read_text(encoding="utf-8")
        self.assertNotIn("${workspaceFolder}", text)
        self.assertIn("${CLAUDE_PROJECT_DIR}", text)


if __name__ == "__main__":
    unittest.main()
