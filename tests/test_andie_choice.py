#!/usr/bin/env python3
"""Andie reply tokens. A bare 1 or 2 is not a choice and must not log a skip."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "scripts" / "routing" / "triage-router.py"
ARCHITECT = ROOT / "scripts" / "routing" / "architect-router.py"


def _load_common():
    path = ROOT / "scripts" / "routing" / "router_common.py"
    spec = importlib.util.spec_from_file_location("router_common_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAndieChoice(unittest.TestCase):
    def setUp(self):
        # Isolated project dir so the live repo offer file is never touched.
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.common = _load_common()
        self._env = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)

    def tearDown(self):
        if self._env is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._env
        self._td.cleanup()

    def _offer(self, skill="andie", reason="architecture-class prompt detected", age=0):
        self.common.save_andie_offer(skill, reason)
        if age:
            path = self.root / ".raven" / "state" / "andie-offer.json"
            payload = json.loads(path.read_text())
            payload["ts"] = time.time() - age
            path.write_text(json.dumps(payload))

    def _skips(self):
        path = self.root / ".raven" / "state" / "andie-skip.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def _offer_exists(self):
        return (self.root / ".raven" / "state" / "andie-offer.json").exists()

    def test_bare_2_clears_offer_and_writes_no_skip(self):
        self._offer()
        self.assertIsNone(self.common.record_user_choice("2"))
        self.assertEqual(self._skips(), [])
        self.assertFalse(self._offer_exists())

    def test_other_menu_number_clears_offer(self):
        self._offer()
        self.assertIsNone(self.common.record_user_choice("3"))
        self.assertEqual(self._skips(), [])
        self.assertFalse(self._offer_exists())

    def test_plain_sentence_clears_offer(self):
        self._offer()
        self.assertIsNone(self.common.record_user_choice("fix the loop in triage"))
        self.assertFalse(self._offer_exists())
        self.assertEqual(self._skips(), [])

    def test_andie_1_clears_and_does_not_skip(self):
        self._offer(skill="andie-jr", reason="issue/existing-code prompt detected")
        self.assertEqual(self.common.pending_offer_skill(), "andie-jr")
        self.assertEqual(self.common.record_user_choice("andie 1"), 1)
        self.assertFalse(self._offer_exists())
        self.assertEqual(self._skips(), [])

    def test_andie_2_records_offer_reason(self):
        self._offer(reason="architecture-class prompt detected")
        self.assertEqual(self.common.record_user_choice("andie 2"), 2)
        rows = self._skips()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], "architecture-class prompt detected")
        self.assertEqual(rows[0]["choice"], 2)
        self.assertFalse(self._offer_exists())

    def test_andie_2_extra_text_is_the_reason(self):
        self._offer(reason="architecture-class prompt detected")
        self.assertEqual(self.common.record_user_choice("andie 2 this is a summary"), 2)
        self.assertEqual(self._skips()[0]["reason"], "this is a summary")

    def test_expired_offer_is_not_a_skip(self):
        self._offer(age=601)
        self.assertIsNone(self.common.record_user_choice("andie 2"))
        self.assertEqual(self._skips(), [])

    def test_second_andie_2_writes_nothing(self):
        self._offer()
        self.assertEqual(self.common.record_user_choice("andie 2"), 2)
        self.assertIsNone(self.common.record_user_choice("andie 2"))
        self.assertEqual(len(self._skips()), 1)

    def test_andie_2_after_bare_2_writes_nothing(self):
        self._offer()
        self.common.record_user_choice("2")
        self.assertIsNone(self.common.record_user_choice("andie 2"))
        self.assertEqual(self._skips(), [])


class TestAndieChoiceHooks(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _seed(self, skill="andie", reason="architecture-class prompt detected"):
        state = self.root / ".raven" / "state"
        state.mkdir(parents=True)
        (state / "andie-offer.json").write_text(json.dumps({
            "ts": time.time(), "skill": skill, "reason": reason,
        }))

    def _run(self, script, prompt):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root), PROMPT=prompt)
        return subprocess.run(
            ["python3", str(script)], cwd=self.root, env=env,
            capture_output=True, text=True, timeout=15,
        )

    def test_reply_1_says_load_now_and_does_not_reoffer(self):
        self._seed(skill="andie-jr", reason="issue/existing-code prompt detected")
        triage = self._run(TRIAGE, "andie 1")
        architect = self._run(ARCHITECT, "andie 1")
        self.assertEqual(triage.returncode, 0, triage.stderr)
        body = json.loads(triage.stdout)
        self.assertEqual(body["systemMessage"], "load andie now")
        ctx = body["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Load `andie-jr` now", ctx)
        self.assertNotIn("ANDIE RECOMMENDED", triage.stdout)
        self.assertNotIn("[ANDIE RECOMMENDED]", ctx)
        self.assertIn("Do not offer andie 1", ctx)
        self.assertEqual(architect.stdout.strip(), "")
        self.assertFalse((self.root / ".raven" / "state" / "andie-offer.json").exists())
        self.assertFalse((self.root / ".raven" / "state" / "andie-skip.jsonl").exists())

    def test_andie_2_does_not_open_a_new_offer(self):
        self._seed()
        triage = self._run(TRIAGE, "andie 2")
        architect = self._run(ARCHITECT, "andie 2")
        self.assertEqual(triage.stdout.strip(), "")
        self.assertEqual(architect.stdout.strip(), "")
        self.assertFalse((self.root / ".raven" / "state" / "andie-offer.json").exists())
        rows = (self.root / ".raven" / "state" / "andie-skip.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(rows[0])["reason"], "architecture-class prompt detected")

    def test_plain_prompt_opens_no_offer(self):
        ran = self._run(TRIAGE, "what time is the standup")
        self.assertEqual(ran.stdout.strip(), "")
        self.assertFalse((self.root / ".raven" / "state" / "andie-offer.json").exists())


if __name__ == "__main__":
    unittest.main()
