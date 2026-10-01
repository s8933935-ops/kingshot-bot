#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2: local anti-hallucination and grounding checks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.search_engine import SatisfactoryRAG
from src.bot.ai_client import generate_rag_answer


FORBIDDEN_FABRICATED_ITEMS = ("電子チップ", "チタン", "インク", "紙")


def test_unknown_item_is_not_grounded():
    rag = SatisfactoryRAG()
    result = rag.query("存在しない超音速燃料のレシピと材料を教えて", fallback_topic="ロケット燃料")
    assert not result["recipe_matches"]
    assert result.get("production_meta") is None

    result_without_marker = rag.query("超音速燃料のレシピを教えて", fallback_topic="ロケット燃料")
    assert not result_without_marker["recipe_matches"]
    assert result_without_marker.get("production_meta") is None


def test_rocket_fuel_does_not_claim_turbofuel_alt_recipe():
    rag = SatisfactoryRAG()
    result = rag.query("ロケット燃料の代替レシピと材料を教えて")
    assert result["recipe_matches"]
    meta = result["production_meta"]
    assert meta["recipe_id"] == "Recipe_Alternate_RocketFuel_Nitro_C"
    recipe_text = str(result["recipe_matches"])
    assert "Nitro Rocket Fuel" in recipe_text
    recipes = next(iter(result["recipe_matches"].values()))["producing"]
    nitro = next(r for r in recipes if r["id"] == "Recipe_Alternate_RocketFuel_Nitro_C")
    ingredients = {item["name_en"] for item in nitro["ingredients"]}
    assert "Turbofuel" not in ingredients


def test_ionized_fuel_is_grounded_to_rocket_fuel_and_shards():
    rag = SatisfactoryRAG()
    meta = rag.get_production_meta("イオン化燃料")
    assert meta is not None
    recipe = rag.recipes["Recipe_IonizedFuel_C"]
    ingredients = {item["name_en"]: item["rate_per_min"] for item in recipe["ingredients"]}
    assert ingredients["Rocket Fuel"] == 40
    assert ingredients["Desc_CrystalShard_C"] == 2.5


def test_waste_free_policy_does_not_recommend_burning_plutonium_rods():
    rag = SatisfactoryRAG()
    meta = rag.get_production_meta("ウラン廃棄物処理")
    assert meta is not None
    assert "FICSITシンク" in meta["best_recipe"]
    assert "原子炉" not in meta["best_recipe"]
    assert "FICSIT" in meta["summary"]


def test_grounded_recipe_text_contains_no_known_fabricated_items():
    rag = SatisfactoryRAG()
    result = rag.query("ロケット燃料のレシピと材料を教えて")
    text = repr(result)
    for fabricated_item in FORBIDDEN_FABRICATED_ITEMS:
        assert fabricated_item not in text


def test_unknown_item_is_blocked_before_llm_generation():
    rag = SatisfactoryRAG()
    question = "存在しない超音速燃料のレシピを教えて"
    context = rag.query(question)
    answer, model = generate_rag_answer(question, context, use_claude=False)
    assert model == "Grounding Guard"
    assert "確定レシピDBに該当する" in answer
    assert "ロケット燃料" not in answer
    assert "通常レシピ" not in answer

    plain_question = "超音速燃料のレシピを教えて"
    plain_answer, plain_model = generate_rag_answer(plain_question, rag.query(plain_question), use_claude=False)
    assert plain_model == "Grounding Guard"
    assert "ニトロ" not in plain_answer


if __name__ == "__main__":
    tests = [
        test_unknown_item_is_not_grounded,
        test_rocket_fuel_does_not_claim_turbofuel_alt_recipe,
        test_ionized_fuel_is_grounded_to_rocket_fuel_and_shards,
        test_waste_free_policy_does_not_recommend_burning_plutonium_rods,
        test_grounded_recipe_text_contains_no_known_fabricated_items,
        test_unknown_item_is_blocked_before_llm_generation,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print("Phase 2 anti-hallucination tests: 100% PASS")
