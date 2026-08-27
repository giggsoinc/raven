#!/usr/bin/env python3
"""Observability spend tiles must reuse Costs log_spend / by_project."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load_core():
    p = ROOT / "scripts" / "dashboard" / "core.py"
    spec = importlib.util.spec_from_file_location("dash_core_obs_spend", p)
    return spec.loader.load_module()


class TestObsSpendAlign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = _load_core()

    def test_observability_spend_matches_costs_source(self):
        """Observability tile and Costs tile both bind headline $ to log_spend spend."""
        src = (ROOT / "scripts" / "dashboard" / "core.py").read_text(encoding="utf-8")
        self.assertIn('id="obsSpend">${spend:.4f}</div>', src)
        self.assertIn('id="costSpend">${spend:.4f}</div>', src)
        self.assertIn("same calculator as Costs", src)
        self.assertNotIn("Est spend (traces)", src)
        self.assertIn("bp.get(k) or {}).get('cost_usd')", src)
        self.assertIn("Money from log_spend by_project", src)
        self.assertIn('spend = float(metrics.get("total_cost_usd") or 0)', src)

    def test_obs_repo_cost_uses_by_project_not_trace_est(self):
        """Union of trace repos + cost repos; $ column is by_project cost_usd."""
        cost_log = [
            {
                "ts": "2026-08-25T01:00:00Z",
                "repo": "raven",
                "ide": "claude",
                "session_id": "sess-a",
                "model": "claude-haiku-4-5",
                "tokens_in": 1000,
                "tokens_out": 2000,
                "cache_read": 0,
                "cache_creation": 0,
                "computed_cost_usd": 0.25,
            },
        ]
        turn_log = [
            {
                "ts": "2026-08-25T02:00:00Z",
                "repo": "only-cost",
                "ide": "grok",
                "recommend": "grok-4.5",
                "tier": "SIMPLE",
                "prompt_chars": 400,
                "session_id": None,
            },
        ]

        def fake_gc(model, tin, tout, cache_read=0, cache_creation=0):
            return 0.05

        with mock.patch.object(self.core, "_get_cost_fn", return_value=fake_gc):
            spend = self.core._spend_from_logs(turn_log, cost_log)

        om = self.core._obs_metrics(
            [
                {
                    "ts": "2026-08-25T02:00:00Z",
                    "repo": "raven",
                    "ide": "grok",
                    "tier": "SIMPLE",
                    "prompt_chars": 100,
                    "est_cost_usd": 9.99,
                },
                {
                    "ts": "2026-08-25T03:00:00Z",
                    "repo": "trace-only",
                    "ide": "grok",
                    "tier": "SIMPLE",
                    "prompt_chars": 50,
                    "est_cost_usd": 1.23,
                },
            ]
        )
        bp = spend["by_project"]
        headline = float(spend["total_cost_usd"])
        self.assertNotAlmostEqual(om["est"], headline, places=2)
        self.assertAlmostEqual(om["est"], 9.99 + 1.23, places=4)
        self.assertEqual(bp["raven"]["cost_usd"], 0.25)
        self.assertIn("only-cost", bp)
        names = set(om["by_repo"].keys()) | set(bp.keys())
        self.assertIn("trace-only", names)
        self.assertIn("only-cost", names)
        self.assertEqual(om["by_repo"].get("raven"), 1)
        self.assertEqual(om["by_repo"].get("trace-only"), 1)
        self.assertEqual(float((bp.get("trace-only") or {}).get("cost_usd") or 0), 0.0)


if __name__ == "__main__":
    unittest.main()
