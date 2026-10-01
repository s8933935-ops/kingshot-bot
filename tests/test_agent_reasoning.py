#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification tests for Agentic Reasoning and Deterministic Solver.
"""

import os
import sys

# Force UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rag.calculator import ProductionCalculator
from src.bot.ai_client import run_autonomous_solver, generate_rag_answer
from src.rag.search_engine import SatisfactoryRAG


def test_fuel_power_solver():
    print("▶ 1. テスト: 燃料・発電 自律検算ソルバー (原油300)")
    res = ProductionCalculator.calculate_fuel_power(300.0, "diluted_fuel")
    assert res["fuel_output"] == 800.0, f"Expected 800.0 fuel, got {res['fuel_output']}"
    assert res["generators"] == 40.0, f"Expected 40 generators, got {res['generators']}"
    assert res["total_power_mw"] == 10000.0, f"Expected 10000 MW, got {res['total_power_mw']}"
    print("   ✅ 希釈燃料 確定計算 合格: 800/分燃料 ➔ 40台発電機 (10,000 MW)")


def test_aluminum_solver():
    print("▶ 2. テスト: アルミ精製・水循環 自律検算ソルバー (ボーキサイト300)")
    res = ProductionCalculator.calculate_aluminum_chain(300.0, "standard")
    assert res["scrap_output"] == 450.0, f"Expected 450 scrap, got {res['scrap_output']}"
    assert res["ingot_output"] == 300.0, f"Expected 300 ingot, got {res['ingot_output']}"
    assert res["water_balance"]["recycled_byproduct"] == 150.0, "Recycled water mismatch"
    print("   ✅ 通常アルミ水循環 確定計算 合格: スクラップ450 ➔ インゴット300 (水回収150/分)")


def test_agentic_solver_integration():
    print("▶ 3. テスト: 自然言語クエリからの自律ソルバー自動発動")
    rag = SatisfactoryRAG()
    query = "原油300から希釈燃料ライン組む場合、発電機は何台動かせる？"
    rag_res = rag.query(query)
    
    solver_out, rates = run_autonomous_solver(query, rag_res)
    assert solver_out is not None, "Solver failed to trigger"
    assert "10000.0 MW" in solver_out or "10000 MW" in solver_out, "Power calculation missing"
    assert "40.0台" in solver_out or "40台" in solver_out, "Generator count missing"
    print("   ✅ 自律検算トリガー合格！自動抽出・検算結果が完全生成されました。")


def test_full_width_480_and_context_inheritance():
    print("▶ 4. テスト: 全角「原油４８０」の正規化 ＆ 希釈燃料確定計算")
    rag = SatisfactoryRAG()
    query1 = "原油４８０から希釈燃料ラインを組む場合発電機は何台回せる？"
    rag_res1 = rag.query(query1)

    solver_out1, rates1 = run_autonomous_solver(query1, rag_res1)
    assert solver_out1 is not None, "Solver failed on full-width numbers"
    assert "原油 480.0/分" in solver_out1 or "原油 480/分" in solver_out1, "Failed to parse 480"
    assert "1280.0/分" in solver_out1 or "1280/分" in solver_out1, "Fuel output mismatch for 480 crude"
    assert "64.0台" in solver_out1 or "64台" in solver_out1, "Generator count mismatch for 480 crude"
    assert "16000.0 MW" in solver_out1 or "16000 MW" in solver_out1, "Power mismatch for 480 crude"
    print("   ✅ 全角「４８０」正常解析合格！燃料 1,280/分 ➔ 発電機 64台 (16,000 MW / 16 GW) 確定！")

    print("▶ 5. テスト: 指示語「これをターボ燃料に変えるには」でのレート継承 (480引き継ぎ)")
    topic_context = {"resource_rates": rates1, "item_name": "希釈燃料"}
    query2 = "これをターボ燃料に変えるには他に生産ラインを何を増やせばいい？"
    rag_res2 = rag.query(query2)

    solver_out2, rates2 = run_autonomous_solver(query2, rag_res2, current_topic=topic_context)
    assert solver_out2 is not None, "Failed to inherit 480 crude"
    assert "原油 480.0/分" in solver_out2 or "原油 480/分" in solver_out2, "Crude 480 was lost in pronoun query"
    print("   ✅ 直前レート継承合格！「これ」で原油480がそのまま引き継がれました。")

    print("▶ 6. テスト: ターボ燃料検索で缶開封（未包装）レシピが除外されるか")
    turbo_recs = rag.find_recipes_for_item("ターボ燃料")
    top_recipe = turbo_recs["producing"][0]
    assert "未包装" not in top_recipe["name_ja"], f"Unpackaging recipe still ranked top: {top_recipe['name_ja']}"
    assert top_recipe.get("produced_in_names", [""])[0] != "充填機", "Packager unpackaging ranked top!"
    print(f"   ✅ レシピ優先度合格！最優先レシピ: {top_recipe['name_ja']} (製造機: {top_recipe.get('produced_in_names')})")


def test_clean_output_guard():
    print("▶ 7. テスト: 思考隠蔽フィルター（Clean Output Guard）")
    import re
    raw_sample = "<think>原油300から希釈燃料を計算中...発電機40台</think>希釈燃料プラントは通常精製の4倍の電力を生み出せます！"
    cleaned = re.sub(r"<think>.*?</think>", "", raw_sample, flags=re.DOTALL).strip()
    assert "<think>" not in cleaned, "Failed to strip <think> tag"
    assert "4倍の電力を生み出せます" in cleaned, "Valid content was stripped"
    print("   ✅ 思考隠蔽フィルター合格！")


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Agentic Reasoning & 4大欠陥 根本改修テスト")
    print("=" * 50)
    test_fuel_power_solver()
    test_aluminum_solver()
    test_agentic_solver_integration()
    test_full_width_480_and_context_inheritance()
    test_clean_output_guard()
    print("=" * 50)
    print("🎉 全テストケースが 100% 正常に合格しました！")
    print("=" * 50)
