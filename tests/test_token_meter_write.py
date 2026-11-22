#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load():
    p = ROOT / "scripts" / "session" / "token-meter-write.py"
    spec = importlib.util.spec_from_file_location("token_meter_write", p)
    return spec.loader.load_module()


class TestTokenMeterWrite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tm = _load()

    def test_parses_claude_type_assistant_sessionId(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        trans = Path(td.name) / "t.jsonl"
        trans.write_text(
            json.dumps({
                "type": "assistant",
                "sessionId": "s1",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 200,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                    },
                },
            })
            + "\n"
        )
        m = self.tm.parse_transcript(str(trans))
        self.assertEqual(m["session_id"], "s1")
        self.assertIn("claude-sonnet-5", m["by_model"])
        self.assertEqual(m["by_model"]["claude-sonnet-5"]["tokens_in"], 1000)

    def test_write_cost_log_appends(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        log = Path(td.name) / "cost-log.jsonl"
        metrics = {
            "timestamp": "2026-08-22T00:00:00Z",
            "session_id": "s1",
            "project": "raven",
            "by_model": {
                "claude-sonnet-5": {
                    "tokens_in": 10,
                    "tokens_out": 5,
                    "cache_read": 0,
                    "cache_creation": 0,
                    "cost_usd": 0.01,
                    "calls": 1,
                }
            },
        }
        with mock.patch.object(self.tm, "COST_LOG", log), mock.patch.object(
            self.tm, "RAVEN_DIR", Path(td.name)
        ):
            self.assertTrue(self.tm.write_cost_log(metrics))
        rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["computed_cost_usd"], 0.01)

    def test_settings_stop_paths_exist(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        cmds = []
        for block in settings["hooks"]["Stop"]:
            for h in block["hooks"]:
                cmds.append(h.get("command") or "")
        meter = next(c for c in cmds if "token-meter-write" in c)
        self.assertNotIn("2>/dev/null", meter)
        # Every python hook runs through hook-run.py (a missing script audits and exits 0).
        self.assertIn("scripts/ops/hook-run.py", meter)
        self.assertIn("scripts/session/token-meter-write.py", meter)
        self.assertTrue((ROOT / ".claude" / "scripts" / "token-meter-write.py").exists())
        self.assertTrue((ROOT / "scripts" / "session" / "token-meter-write.py").is_file())
        self.assertIn('"async": false', json.dumps(settings["hooks"]["Stop"]))

    def test_full_turn_cycle_writes_computed_cost(self):
        """router-classify analogue -> Stop parse -> cost-log row with computed_cost_usd."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        raven = root / ".raven"
        raven.mkdir()
        trans = root / "session.jsonl"
        trans.write_text(
            json.dumps({
                "type": "assistant",
                "sessionId": "cycle1",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": 2000,
                        "output_tokens": 400,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                    },
                },
            })
            + "\n"
        )
        log = raven / "cost-log.jsonl"
        with mock.patch.object(self.tm, "RAVEN_DIR", raven), mock.patch.object(
            self.tm, "COST_LOG", log
        ), mock.patch.object(self.tm, "CHECKPOINT_FILE", raven / ".token-meter-checkpoint.json"):
            metrics = self.tm.parse_transcript(str(trans))
            self.assertTrue(metrics.get("by_model"))
            ok = self.tm.write_cost_log(metrics)
            self.assertTrue(ok)
        rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0].get("computed_cost_usd"))
        self.assertGreater(float(rows[0]["computed_cost_usd"]), 0)


if __name__ == "__main__":
    unittest.main()
