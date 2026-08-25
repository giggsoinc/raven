#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load():
    p = ROOT / "scripts" / "session" / "cost_calc.py"
    spec = importlib.util.spec_from_file_location("cost_calc", p)
    return spec.loader.load_module()


class TestCostCalc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = _load()

    def test_known_haiku_math(self):
        # 1M in + 1M out at 1 / 5 = $6
        usd = self.cc.get_cost("anthropic/claude-haiku-4-5", 1_000_000, 1_000_000)
        self.assertEqual(usd, 6.0)

    def test_cache_read_bills_at_tenth_input(self):
        # 1M cache_read at $1/1M input → $0.10; no in/out
        usd = self.cc.get_cost("anthropic/claude-haiku-4-5", 0, 0, cache_read=1_000_000)
        self.assertEqual(usd, 0.1)

    def test_cache_creation_bills_at_1_25x_input(self):
        usd = self.cc.get_cost("anthropic/claude-haiku-4-5", 0, 0, cache_creation=1_000_000)
        self.assertEqual(usd, 1.25)

    def test_unknown_records_needs_rate(self):
        td = tempfile.TemporaryDirectory()
        local = Path(td.name) / "model-pricing.local.json"
        self.addCleanup(td.cleanup)
        with mock.patch.object(self.cc, "LOCAL_PRICING", local):
            usd = self.cc.get_cost("grok-4.6-never-priced-xyz", 100, 100)
        self.assertIsNone(usd)
        data = json.loads(local.read_text())
        self.assertTrue(any("grok-4.6-never-priced" in k for k in data["models"]))
        row = next(iter(data["models"].values()))
        self.assertTrue(row.get("needs_rate"))
        self.assertIsNone(row.get("input_per_1m"))

    def test_turn_end_adds_running_total(self):
        td = tempfile.TemporaryDirectory()
        last = Path(td.name) / ".last-turn-cost.json"
        self.addCleanup(td.cleanup)
        with mock.patch.object(self.cc, "LAST_TURN", last):
            rec = self.cc.write_turn_end(turn_usd=0.01, running_total=0.04, model="grok-4.6")
        self.assertEqual(rec["turn_usd"], 0.01)
        self.assertEqual(rec["total_cost_usd"], 0.04)
        self.assertIn("turn=$0.0100", self.cc.end_money_line(rec))
        self.assertIn("total-cost=$0.0400", self.cc.end_money_line(rec))

    def test_grok_has_published_rates(self):
        usd = self.cc.get_cost("grok-4.6", 1_000_000, 1_000_000)
        self.assertEqual(usd, 8.0)
        est = self.cc.estimate("grok-4.5", 400, reply_out_guess=500)
        self.assertFalse(est.get("needs_rate"))
        self.assertIsNotNone(est.get("est_cost_usd"))

    def test_spend_kind_estimated_when_no_cost_log(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        cost = Path(td.name) / "cost-log.jsonl"
        turn = Path(td.name) / "turn-log.jsonl"
        turn.write_text(json.dumps({"est_cost_usd": 0.33}) + "\n")
        with mock.patch.object(self.cc, "COST_LOG", cost), mock.patch.object(self.cc, "TURN_LOG", turn):
            kind, usd = self.cc.spend_kind()
        self.assertEqual(kind, "estimated")
        self.assertAlmostEqual(usd, 0.33)

    def test_running_total_falls_back_to_turn_est(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        cost = Path(td.name) / "cost-log.jsonl"
        turn = Path(td.name) / "turn-log.jsonl"
        turn.write_text(
            json.dumps({"est_cost_usd": 0.0077}) + "\n" + json.dumps({"est_cost_usd": 0.0026}) + "\n"
        )
        with mock.patch.object(self.cc, "COST_LOG", cost), mock.patch.object(self.cc, "TURN_LOG", turn):
            self.assertAlmostEqual(self.cc.running_total_usd(), 0.0103)

    def test_no_gpt4o_fallback_on_empty(self):
        td = tempfile.TemporaryDirectory()
        local = Path(td.name) / "model-pricing.local.json"
        self.addCleanup(td.cleanup)
        with mock.patch.object(self.cc, "LOCAL_PRICING", local):
            usd = self.cc.get_cost("totally-unknown-model-zzz", 10, 10)
        self.assertIsNone(usd)


if __name__ == "__main__":
    unittest.main()
