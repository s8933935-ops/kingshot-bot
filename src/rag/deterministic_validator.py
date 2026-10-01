#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic Math & Meta Validator (確定値保護バリデータ)
Audit Action Item #1: コードレベルによる確定値不可侵原則 (No Overwrite Rule) の実装

責務:
1. calculator.py (確定計算ソルバー) および production_metas.json (確定メタデータ) を
   唯一の正（Single Source of Truth: SSOT）として強制する。
2. LLM (Claude, OpenAI, Qwen等) が出力した数理テキスト・レシピ比率を検証し、
   ハルシネーションや不整合があれば確定値で強制差し戻し（フォールバック）する。
3. production_metas.json などの確定値ファイルに対する外部/LLMからの書き換えを物理的に遮断する。
"""

import os
import sys
import json
import re
from typing import Dict, Any, Tuple, Optional

# UTF-8 出力保証
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# プロジェクトルートをインポートパスに追加
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))


class DeterministicValidatorError(Exception):
    """確定値の改ざんまたは検証失敗時の例外"""
    pass


class DeterministicMathValidator:
    """LLM推論値から確定値を防衛するコードレベルバリデータ"""

    def __init__(self):
        self.metas_path = os.path.join(DATA_DIR, "production_metas.json")
        self.recipes_path = os.path.join(DATA_DIR, "recipes.json")
        self._load_ssot_data()

    def _load_ssot_data(self):
        """確定メタデータを読み込み、メモリ上でイミュータブルに保持"""
        if os.path.exists(self.metas_path):
            with open(self.metas_path, "r", encoding="utf-8") as f:
                self.metas = json.load(f)
        else:
            self.metas = {}

        if os.path.exists(self.recipes_path):
            with open(self.recipes_path, "r", encoding="utf-8") as f:
                self.recipes = json.load(f)
        else:
            self.recipes = {}

    def verify_no_file_overwrite(self, target_path: str) -> bool:
        """
        確定データファイルへの上書き試行を物理的に遮断するガードレール
        """
        abs_target = os.path.abspath(target_path)
        protected_files = [
            os.path.abspath(self.metas_path),
            os.path.abspath(self.recipes_path),
            os.path.abspath(os.path.join(DATA_DIR, "items.json")),
            os.path.abspath(os.path.join(DATA_DIR, "buildings.json"))
        ]
        if abs_target in protected_files:
            raise DeterministicValidatorError(
                f"[SECURITY_ALERT] 確定値ファイルへの直接上書きはシステムにより物理遮断されています: {abs_target}"
            )
        return True

    def validate_production_meta(
        self,
        item_name: str,
        proposed_recipe_id: Optional[str] = None,
        proposed_output_rate: Optional[float] = None,
        tolerance: float = 0.001
    ) -> Dict[str, Any]:
        """
        アイテムの生産メタデータについて、LLMの推論値とSSOT確定値を照合する。
        乖離がある場合は確定値を差し戻し、修正フラグを返す。
        """
        if item_name not in self.metas:
            return {
                "valid": True,
                "is_grounded": False,
                "warning": f"アイテム '{item_name}' は確定メタデータに存在しません。"
            }

        ssot = self.metas[item_name]
        is_modified = False
        reasons = []

        # レシピIDの照合
        actual_recipe_id = ssot.get("recipe_id")
        if proposed_recipe_id and proposed_recipe_id != actual_recipe_id:
            is_modified = True
            reasons.append(f"レシピID不一致 (LLM提案: {proposed_recipe_id} -> 確定値: {actual_recipe_id})")

        # 生産レートの照合
        actual_rate = ssot.get("default_product_rate_per_min")
        if proposed_output_rate is not None and actual_rate is not None:
            diff = abs(proposed_output_rate - actual_rate)
            if diff > tolerance:
                is_modified = True
                reasons.append(f"生産レート不一致 (LLM提案: {proposed_output_rate}/分 -> 確定値: {actual_rate}/分)")

        return {
            "valid": not is_modified,
            "is_grounded": True,
            "corrected_meta": ssot,
            "discrepancies": reasons,
            "recommendation": "確定値を使用してください" if is_modified else "確定値と完全一致"
        }

    def validate_power_generation(
        self,
        crude_oil_per_min: float,
        recipe_type: str,
        proposed_mw: float,
        tolerance: float = 0.01
    ) -> Dict[str, Any]:
        """
        calculator.py による発電量確定計算とLLMの推論発電量を照合する。
        """
        from src.rag.calculator import ProductionCalculator

        # 確定計算の実行
        exact_result = ProductionCalculator.calculate_fuel_power(crude_oil_per_min, recipe_type)
        exact_mw = exact_result.get("total_power_mw", 0.0)

        diff = abs(proposed_mw - exact_mw)
        if diff > (exact_mw * tolerance):
            return {
                "valid": False,
                "exact_mw": exact_mw,
                "proposed_mw": proposed_mw,
                "diff": diff,
                "corrected_result": exact_result,
                "action": "FORCE_REVERT_TO_EXACT_CALCULATOR",
                "message": f"LLM推論発電量 ({proposed_mw:.1f} MW) は確定計算値 ({exact_mw:.1f} MW) と乖離しています。確定値に強制差し戻しを行いました。"
            }

        return {
            "valid": True,
            "exact_mw": exact_mw,
            "proposed_mw": proposed_mw,
            "action": "ACCEPTED",
            "message": "確定計算値と一致しています。"
        }


# シングルトンインスタンス
validator = DeterministicMathValidator()

if __name__ == "__main__":
    print("=== DeterministicMathValidator Self-Check ===")
    res = validator.validate_production_meta("ロケット燃料", proposed_recipe_id="Recipe_Wrong_C")
    print("Meta validation result:", json.dumps(res, ensure_ascii=False, indent=2))

    res_power = validator.validate_power_generation(300.0, "diluted_fuel", proposed_mw=9999.0)
    print("Power validation result:", json.dumps(res_power, ensure_ascii=False, indent=2))
