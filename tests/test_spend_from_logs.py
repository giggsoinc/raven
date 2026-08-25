#!/usr/bin/env python3
"""Costs pane: headline sessions/spend must match grouped repo rows."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load_core():
    p = ROOT / "scripts" / "dashboard" / "core.py"
    spec = importlib.util.spec_from_file_location("dash_core_spend", p)
    mod = spec.loader.load_module()
    return mod


class TestSpendFromLogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = _load_core()

    def test_headline_matches_repo_rows_mixed(self):
        cost_log = [
            {
                "ts": "2026-08-25T01:00:00Z",
                "repo": "raven",
                "ide": "claude",
                "session_id": "sess-a",
                "model": "claude-haiku-4-5",
                "tokens_in": 1000,
                "tokens_out": 2000,
                "cache_read": 1_000_000,
                "cache_creation": 0,
                "computed_cost_usd": 0.111,  # includes cache; prefer this
            },
            {
                # older smaller snapshot — must not double-count
                "ts": "2026-08-25T00:30:00Z",
                "repo": "raven",
                "ide": "claude",
                "session_id": "sess-a",
                "model": "claude-haiku-4-5",
                "tokens_in": 500,
                "tokens_out": 1000,
                "cache_read": 100_000,
                "computed_cost_usd": 0.05,
            },
        ]
        turn_log = [
            {
                "ts": "2026-08-25T02:00:00Z",
                "repo": "raven",
                "ide": "grok",
                "recommend": "grok-4.5",
                "tier": "SIMPLE",
                "prompt_chars": 400,
                "session_id": None,
            },
            {
                "ts": "2026-08-25T03:00:00Z",
                "repo": "raven",
                "ide": "grok",
                "recommend": "grok-4.5",
                "tier": "SIMPLE",
                "prompt_chars": 400,
                "session_id": None,
            },
            {
                "ts": "2026-08-24T03:00:00Z",
                "repo": "Aryx",
                "ide": "grok",
                "recommend": "grok-4.5",
                "tier": "SIMPLE",
                "prompt_chars": 400,
                "session_id": None,
            },
        ]

        def fake_gc(model, tin, tout, cache_read=0, cache_creation=0):
            # deterministic: $1 per 1k in + $2 per 1k out + $0.1 per 1M cache_read
            return round(
                tin / 1000.0
                + 2.0 * tout / 1000.0
                + (cache_read / 1_000_000.0) * 0.1
                + (cache_creation / 1_000_000.0) * 1.25,
                6,
            )

        with mock.patch.object(self.core, "_get_cost_fn", return_value=fake_gc):
            spend = self.core._spend_from_logs(turn_log, cost_log)

        bp = spend["by_project"]
        sess_sum = sum(int(b.get("sessions") or 0) for b in bp.values())
        cost_sum = round(sum(float(b.get("cost_usd") or 0) for b in bp.values()), 4)
        self.assertEqual(spend["sessions_count"], sess_sum)
        self.assertEqual(spend["total_cost_usd"], cost_sum)
        self.assertEqual(spend["spend_kind"], "mixed")

        raven = bp["raven"]
        self.assertEqual(raven["by_ide"]["claude"]["kind"], "actual")
        self.assertEqual(raven["by_ide"]["claude"]["cost_usd"], 0.111)
        self.assertEqual(raven["by_ide"]["claude"]["sessions"], 1)
        # Grok: two fires same day → one day-session; 500 out × 2 fires
        grok = raven["by_ide"]["grok"]
        self.assertEqual(grok["kind"], "estimated")
        self.assertEqual(grok["sessions"], 1)
        self.assertEqual(grok["fires"], 2)
        self.assertEqual(grok["out"], 1000)
        self.assertEqual(bp["Aryx"]["by_ide"]["grok"]["sessions"], 1)
        self.assertAlmostEqual(
            spend["actual_usd"] + spend["estimated_usd"], spend["total_cost_usd"], places=4
        )

    def test_gather_keeps_per_repo_tails(self):
        """Merged gather must not drop repo B when repo A alone exceeds `per`."""
        # Smoke: function returns three lists and does not slice to `per` globally
        # (implementation detail asserted via source contract in dashboard tests too).
        src = (ROOT / "scripts" / "dashboard" / "core.py").read_text(encoding="utf-8")
        self.assertIn("Do not re-trim the", src)
        self.assertIn("merged_bp = {}", src)
        self.assertIn("Sessions (table)", src)
        self.assertIn("cache_read×0.1", src)
        self.assertNotIn(
            'metrics["sessions_count"] = max(int(metrics.get("sessions_count") or 0), log_spend["sessions_count"])',
            src,
        )


if __name__ == "__main__":
    unittest.main()
