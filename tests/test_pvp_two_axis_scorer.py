#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit and snapshot regression tests for scripts/pvp_two_axis_scorer.py."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pvp_two_axis_scorer as scorer  # noqa: E402


class TestPvpTwoAxisScorer(unittest.TestCase):
    def test_top_whale_not_misclassified_as_depleted(self) -> None:
        # リョ〜〜〜朕 empirical profile
        towers = {"CC": 376, "MF": 422, "KN": 307, "FoL": 322, "Col": 719, "RS": 805}
        res = scorer.score_member(power_m=752.9, mig=2714626, stove=70, towers=towers)
        self.assertEqual(res["flag"], "A")
        self.assertEqual(res["pcs"], 945)
        self.assertGreater(res["troop_M"], 550.0)
        self.assertGreaterEqual(res["dtv"], 95.0)
        self.assertEqual(res["quadrant"], "A")
        self.assertFalse(res["fat_warn"])

    def test_troop_depleted_high_quality_account(self) -> None:
        # Shmosby1: TG8, decent PCS, ~5M remaining troop
        towers = {"CC": 209, "MF": 228, "KN": 170, "FoL": 210, "Col": 416, "RS": 400}
        res = scorer.score_member(power_m=132.8, mig=1021000, stove=70, towers=towers)
        self.assertEqual(res["flag"], "A")
        self.assertEqual(res["tg"], 8)
        self.assertLess(res["dtv"], 10.0)
        self.assertLess(res["troop_M"], 20.0)
        self.assertEqual(res["quadrant"], "D")

    def test_fat_warn_and_egc_dilution(self) -> None:
        # TG6 (stove 64) with large troop count triggers FAT_WARN and 0.5625 EGC ratio
        towers = {"CC": 228, "MF": 281, "KN": 199, "FoL": 229, "Col": 482, "RS": 509}
        res = scorer.score_member(power_m=394.0, mig=986640, stove=64, towers=towers)
        self.assertEqual(res["flag"], "A")
        self.assertEqual(res["tg"], 6)
        self.assertTrue(res["fat_warn"])
        self.assertAlmostEqual(res["egc_M"], res["troop_M"] * (6 / 8) ** 2, delta=0.15)

    def test_flag_b_c_d_fallback_paths(self) -> None:
        towers = {"CC": 260, "MF": 330, "KN": 240, "FoL": 230, "Col": 550, "RS": 600}
        expected_q_core = sum(
            scorer.W[k] * (towers[k] / scorer.CAP[k]) for k in scorer.W
        )
        res_b = scorer.score_member(power_m=480.0, mig=None, stove=70, towers=towers)
        self.assertEqual(res_b["flag"], "B")
        self.assertEqual(res_b["pcs"], round(1000.0 * expected_q_core))
        self.assertIsNotNone(res_b["dtv"])

        res_c = scorer.score_member(power_m=480.0, mig=1400000, stove=70, towers=None)
        self.assertEqual(res_c["flag"], "C")
        self.assertIsNotNone(res_c["pcs"])
        self.assertIsNone(res_c["pcs_joiner"])
        self.assertIsNotNone(res_c["dtv"])

        res_c_no_stove = scorer.score_member(power_m=200.0, mig=600000, stove=None, towers=None)
        res_c_stove30 = scorer.score_member(power_m=200.0, mig=600000, stove=30, towers=None)
        self.assertEqual(res_c_no_stove["flag"], "C")
        self.assertEqual(res_c_no_stove["pcs"], res_c_stove30["pcs"])
        self.assertEqual(res_c_no_stove["base_M"], res_c_stove30["base_M"])

        res_d = scorer.score_member(power_m=380.0, mig=None, stove=None, towers=None)
        self.assertEqual(res_d["flag"], "D")
        self.assertIsNone(res_d["pcs"])
        self.assertIsNone(res_d["dtv"])
        self.assertEqual(res_d["quadrant"], "D_UNSCORED")

    def test_extract_towers_handles_empty_and_dict(self) -> None:
        self.assertIsNone(scorer.extract_towers({"trails_list": []}))
        sample = {
            "trails": {
                "3": {"name": "Crystal Cave", "stage": 300},
                "5": {"name": "Molten Fort", "stage": 350},
            }
        }
        tw = scorer.extract_towers(sample)
        self.assertEqual(tw["CC"], 300)
        self.assertEqual(tw["MF"], 350)


if __name__ == "__main__":
    unittest.main()
