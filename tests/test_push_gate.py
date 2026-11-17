#!/usr/bin/env python3
"""Educate gate hardening: parser false blocks and bypasses, fail-closed, go-ahead quoting, installer stamp, dashboard origin."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "guards" / "push-gate.py"
APPROVE = ROOT / "scripts" / "guards" / "push-approve.py"
HOOK_RUN = ROOT / "scripts" / "ops" / "hook-run.py"
INSTALL = ROOT / "plugin" / "install-host.sh"
DASH = ROOT / "scripts" / "ops" / "dashboard-server.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load("push_gate_hardening", GATE)
approve = _load("push_approve_hardening", APPROVE)

# Ordinary read-only checks, including the manifest probes a brownfield start needs.
SHOULD_PASS = [
    "ls .raven/manifest.json",
    "cat .raven/manifest.json",
    "test -f .raven/manifest.json && echo yes || echo no",
    "[ -f .raven/manifest.json ] && echo exists",
    "[[ -f .raven/manifest.json ]] && echo exists",
    "if [ -f .raven/manifest.json ]; then echo exists; fi",
    "[ -f .raven/manifest.json ] && echo ok || echo 'missing -> run init'",
    "ls .raven/manifest.json >/dev/null && echo ok",
    "ls x 2>/dev/null",
    "ls x 2>&1 | head",
    "cd /proj && ls .raven/manifest.json",
    "jq . .raven/manifest.json",
    "python3 -c \"import json;print(json.load(open('.raven/manifest.json'))['version'])\"",
    "python3 -m json.tool .raven/manifest.json",
    "readlink -f .raven/manifest.json",
    "grep -n '->' .raven/manifest.json",
    "git status",
    "git -C /x log --oneline",
    "git branch",
    "git branch --list 'a*'",
    "git tag -l",
    "git remote -v",
    "for f in a b; do cat $f; done",
    "find . -name '*.py'",
    "python3 scripts/memory/educate.py",
    "python3 scripts/routing/model-router.py --status",
    "python3 -m unittest tests.test_educate",
]

# Writes and bypass attempts. Every one must be treated as a write.
SHOULD_BLOCK = [
    "ls\nrm -rf /tmp/x",
    "ls & rm /tmp/x",
    "find . -delete",
    "find . -exec rm {} +",
    "env rm /tmp/x",
    "git branch -D foo",
    "git branch newbranch",
    "git tag -d v1",
    "git tag v1",
    "git remote add x y",
    "git push",
    "git diff --output=f",
    "sort -o out.txt in.txt",
    "uniq a b",
    "sed -i s/a/b/ f",
    "python3 -m pip install x",
    "python3 scripts/anything.py",
    "python3 ../x.py --status",
    "ls $(rm /tmp/x)",
    "ls `rm x`",
    "echo hi > f",
    "echo hi >> f",
    "cat a > b",
    "cat <<EOF\nx\nEOF",
    "echo x | tee f",
    "rm -rf x",
    "python3 scripts/dashboard.py --html",
    "python3 scripts/memory/educate.py --set off",
    "python3 -c \"open('f','w').write('x')\"",
    "python3 -c \"import os; os.system('rm x')\"",
    "python3 -c \"import subprocess\"",
    "python3 -c \"import json; json.dump({}, open('f','w'))\"",
    "python3 -c \"from pathlib import Path; Path('x').write_text('y')\"",
    "python3 -c \"import sys; print(sys.modules['os'])\"",
]


class TestReadOnlyParser(unittest.TestCase):
    def test_ordinary_reads_pass(self):
        for cmd in SHOULD_PASS:
            with self.subTest(cmd=cmd):
                self.assertTrue(gate.bash_is_read_only(cmd))

    def test_writes_and_bypasses_blocked(self):
        for cmd in SHOULD_BLOCK:
            with self.subTest(cmd=cmd):
                self.assertFalse(gate.bash_is_read_only(cmd))


class TestFailClosed(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / ".raven").mkdir()

    def tearDown(self):
        self.td.cleanup()

    def _run_gate(self, stdin_text: str):
        buf = io.StringIO()
        with patch.object(gate, "repo_root", return_value=str(self.root)):
            with patch.object(sys, "stdin", io.StringIO(stdin_text)):
                with patch("sys.stdout", buf):
                    try:
                        gate.main()
                    except SystemExit as exc:
                        return exc.code, buf.getvalue()
        return 0, buf.getvalue()

    def test_unparseable_payload_denies_and_audits(self):
        code, out = self._run_gate("not json")
        self.assertEqual(code, 0)
        self.assertIn("deny", out)
        rows = [json.loads(line) for p in (self.root / ".raven" / "audit").glob("*.log") for line in p.read_text().splitlines()]
        self.assertEqual(rows[0]["event"], "gate-error")

    def test_parser_crash_denies(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        with patch.object(gate, "bash_is_read_only", side_effect=RuntimeError("boom")):
            code, out = self._run_gate(payload)
        self.assertIn("deny", out)

    def test_error_with_educate_off_allows(self):
        (self.root / ".raven" / "educate.json").write_text('{"mode": "off"}')
        code, out = self._run_gate("not json")
        self.assertEqual(code, 0)
        self.assertNotIn("deny", out)


class TestHookRunGate(unittest.TestCase):
    def _run(self, td: str, script: str, payload: dict):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=td)
        return subprocess.run(
            ["python3", str(HOOK_RUN), script],
            cwd=td, env=env, input=json.dumps(payload),
            capture_output=True, text=True, timeout=20,
        )

    def test_missing_gate_denies_writes_and_audits(self):
        with tempfile.TemporaryDirectory() as td:
            ran = self._run(td, "scripts/guards/push-gate.py", {"tool_name": "Write"})
            self.assertEqual(ran.returncode, 0)
            self.assertIn('"deny"', ran.stdout)
            log = next((Path(td) / ".raven" / "audit").glob("*.log")).read_text()
            self.assertIn("gate-fail-closed", log)

    def test_missing_gate_still_allows_reads(self):
        with tempfile.TemporaryDirectory() as td:
            ran = self._run(td, "scripts/guards/push-gate.py", {"tool_name": "Read"})
            self.assertEqual(ran.returncode, 0)
            self.assertNotIn("deny", ran.stdout)

    def test_missing_gate_allows_when_educate_off(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".raven").mkdir()
            (Path(td) / ".raven" / "educate.json").write_text('{"mode": "off"}')
            ran = self._run(td, "scripts/guards/push-gate.py", {"tool_name": "Bash"})
            self.assertNotIn("deny", ran.stdout)

    def test_crashing_gate_denies_writes(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "push-gate.py"
            bad.write_text("raise SystemExit(1)\n")
            ran = self._run(td, str(bad), {"tool_name": "Bash"})
            self.assertIn('"deny"', ran.stdout)

    def test_real_gate_still_denies_guided_write(self):
        with tempfile.TemporaryDirectory() as td:
            ran = self._run(td, str(GATE), {"tool_name": "Write"})
            self.assertIn("deny", ran.stdout)
            self.assertNotIn("gate-fail-closed", "".join(
                p.read_text() for p in (Path(td) / ".raven" / "audit").glob("*.log")
            ) if (Path(td) / ".raven" / "audit").exists() else "")


class TestApproveQuoting(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / ".raven").mkdir()
        self._old = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._old
        self.td.cleanup()

    def _submit(self, prompt: str) -> None:
        with patch.object(sys, "stdin", io.StringIO(json.dumps({"prompt": prompt}))):
            with patch("sys.stdout", io.StringIO()):
                approve.main()

    def approved(self) -> bool:
        return (self.root / ".raven" / ".push-approved").is_file()

    def mode_file(self) -> bool:
        return (self.root / ".raven" / "educate.json").is_file()

    def test_plain_go_ahead_approves(self):
        self._submit("Go ahead")
        self.assertTrue(self.approved())

    def test_pasted_report_does_not_approve(self):
        report = (
            "Review this\n<pasted_content id=\"x\">The agent said go ahead and "
            "Lucky me, approved.</pasted_content>"
        )
        self._submit(report)
        self.assertFalse(self.approved())
        self.assertFalse(self.mode_file())

    def test_quoted_and_fenced_text_does_not_approve(self):
        for text in ('what does "go ahead" do?', "run `go ahead` for me", "```\ngo ahead\n```", "> go ahead"):
            with self.subTest(text=text):
                self._submit(text)
                self.assertFalse(self.approved())

    def test_long_message_keyword_in_middle_does_not_approve(self):
        filler = "analysis " * 100
        self._submit(filler + " go ahead " + filler)
        self.assertFalse(self.approved())

    def test_long_message_ending_with_go_ahead_approves(self):
        self._submit("analysis " * 100 + "\nGo ahead")
        self.assertTrue(self.approved())

    def test_lucky_in_pasted_text_does_not_turn_educate_off(self):
        self._submit("<pasted_content>I feel Lucky</pasted_content> please review")
        self.assertFalse(self.mode_file())


class TestInstallerVersionStamp(unittest.TestCase):
    def test_installer_copies_version(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            (Path(src) / "hosts").mkdir()
            (Path(src) / "VERSION").write_text("9.9.9\n")
            (Path(src) / "install-host.sh").write_text(INSTALL.read_text())
            ran = subprocess.run(
                ["bash", str(Path(src) / "install-host.sh"), dst],
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual((Path(dst) / "raven-core" / "VERSION").read_text().strip(), "9.9.9")


class TestDashboardOrigin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dash = _load("dashboard_server_hardening", DASH)

    def test_own_origin_allowed(self):
        self.assertTrue(self.dash.origin_allowed("http://127.0.0.1:9787", 9787))
        self.assertTrue(self.dash.origin_allowed("http://localhost:9787", 9787))

    def test_foreign_and_null_origin_rejected_for_sensitive_check(self):
        self.assertFalse(self.dash.origin_allowed("https://evil.example", 9787))
        self.assertFalse(self.dash.origin_allowed("null", 9787))
        self.assertFalse(self.dash.origin_allowed("http://127.0.0.1:1234", 9787))

    def test_host_rebinding_rejected(self):
        self.assertTrue(self.dash.host_allowed("127.0.0.1:9787", 9787))
        self.assertFalse(self.dash.host_allowed("evil.example:9787", 9787))

    def test_no_wildcard_cors_in_source(self):
        self.assertNotIn('"Access-Control-Allow-Origin", "*"', DASH.read_text())


if __name__ == "__main__":
    unittest.main()
