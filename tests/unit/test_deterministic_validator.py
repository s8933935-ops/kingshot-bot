#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for DeterministicMathValidator
Audit Action Item #1: 確定値不可侵と改ざん防止の自動回帰テスト (標準 unittest 版)
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.rag.deterministic_validator import DeterministicMathValidator, DeterministicValidatorError


class TestDeterministicMathValidator(unittest.TestCase):

    def setUp(self):
        self.validator = DeterministicMathValidator()

    def test_protect_ssot_files_from_overwrite(self):
        """確定メタデータファイルへの直接書き込み遮断テスト"""
        protected_file = os.path.join(PROJECT_ROOT, "data/processed/production_metas.json")
        with self.assertRaises(DeterministicValidatorError) as ctx:
            self.validator.verify_no_file_overwrite(protected_file)
        self.assertIn("確定値ファイルへの直接上書きはシステムにより物理遮断されています", str(ctx.exception))

    def test_allow_safe_scratch_files(self):
        """安全な作業ファイルへの書き込み許可テスト"""
        scratch_file = os.path.join(PROJECT_ROOT, "scratch/temp_output.txt")
        self.assertTrue(self.validator.verify_no_file_overwrite(scratch_file))

    def test_validate_exact_recipe_match(self):
        """正当な確定レシピとの一致判定テスト"""
        res = self.validator.validate_production_meta(
            "ロケット燃料",
            proposed_recipe_id="Recipe_Alternate_RocketFuel_Nitro_C"
        )
        self.assertTrue(res["valid"])
        self.assertTrue(res["is_grounded"])
        self.assertEqual(len(res["discrepancies"]), 0)

    def test_detect_hallucinated_recipe_and_force_revert(self):
        """LLMが虚偽のレシピIDを提示した場合の検知と強制差し戻しテスト"""
        res = self.validator.validate_production_meta(
            "ロケット燃料",
            proposed_recipe_id="Recipe_Fake_TurboRocket_C"
        )
        self.assertFalse(res["valid"])
        self.assertIn("レシピID不一致", res["discrepancies"][0])
        self.assertEqual(res["corrected_meta"]["recipe_id"], "Recipe_Alternate_RocketFuel_Nitro_C")

    def test_validate_exact_power_generation(self):
        """希釈燃料による確定発電量 (原油300 -> 10,000 MW) の検証テスト"""
        res = self.validator.validate_power_generation(
            crude_oil_per_min=300.0,
            recipe_type="diluted_fuel",
            proposed_mw=10000.0
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["exact_mw"], 10000.0)
        self.assertEqual(res["action"], "ACCEPTED")

    def test_detect_power_hallucination_and_revert(self):
        """LLMが誤った発電量（例: 50,000 MW）を推論した場合の強制差し戻しテスト"""
        res = self.validator.validate_power_generation(
            crude_oil_per_min=300.0,
            recipe_type="diluted_fuel",
            proposed_mw=50000.0
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["exact_mw"], 10000.0)
        self.assertEqual(res["action"], "FORCE_REVERT_TO_EXACT_CALCULATOR")


if __name__ == "__main__":
    unittest.main()
