#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1: deterministic validation of newly added production metas."""

import json
import sys
from pathlib import Path

# Allow direct execution from the repository root or from the tests directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.search_engine import SatisfactoryRAG
from src.rag.calculator import ProductionCalculator


ROOT = Path(__file__).resolve().parents[1]
META_PATH = ROOT / "data" / "processed" / "production_metas.json"
RECIPE_PATH = ROOT / "data" / "processed" / "recipes.json"


def load_data():
    return (
        json.loads(META_PATH.read_text(encoding="utf-8")),
        json.loads(RECIPE_PATH.read_text(encoding="utf-8")),
    )


def recipe(name):
    _, recipes = load_data()
    return next(value for value in recipes.values() if value.get("name_en") == name)


def rate(item, seconds):
    return item["amount"] * 60 / seconds


def test_metas_are_grounded_in_recipe_db():
    metas, recipes = load_data()
    expected = {
        "ロケット燃料": "Recipe_Alternate_RocketFuel_Nitro_C",
        "イオン化燃料": "Recipe_IonizedFuel_C",
        "プルトニウム燃料棒": "Recipe_PlutoniumFuelRod_C",
    }
    for meta_name, recipe_id in expected.items():
        assert meta_name in metas
        assert metas[meta_name]["recipe_id"] == recipe_id
        assert recipe_id in recipes
        assert metas[meta_name]["verified_against"] == "data/processed/recipes.json"


def test_nitro_rocket_fuel_rates():
    r = recipe("Alternate: Nitro Rocket Fuel")
    assert r["duration_seconds"] == 2.4
    assert rate(r["ingredients"][0], 2.4) == 100.0  # Fuel
    assert rate(r["ingredients"][1], 2.4) == 75.0   # Nitrogen Gas
    assert rate(r["ingredients"][2], 2.4) == 100.0  # Sulfur
    assert rate(r["ingredients"][3], 2.4) == 50.0   # Coal
    assert rate(r["products"][0], 2.4) == 150.0     # Rocket Fuel
    assert rate(r["products"][1], 2.4) == 25.0      # Compacted Coal byproduct


def test_ionized_fuel_rates():
    r = recipe("Ionized Fuel")
    assert r["duration_seconds"] == 24
    assert rate(r["ingredients"][0], 24) == 40.0
    assert rate(r["ingredients"][1], 24) == 2.5
    assert rate(r["products"][0], 24) == 40.0
    assert rate(r["products"][1], 24) == 5.0


def test_plutonium_fuel_rod_rates_and_sink_policy():
    metas, _ = load_data()
    r = recipe("Plutonium Fuel Rod")
    assert r["duration_seconds"] == 240
    assert rate(r["products"][0], 240) == 0.25
    assert metas["プルトニウム燃料棒"]["machine"] == "製造機"
    assert "FICSITシンク" in metas["プルトニウム燃料棒"]["summary"]
    assert "FICSIT" in metas["プルトニウム燃料棒"]["summary"]


def test_all_new_metas_are_retrievable_from_rag():
    rag = SatisfactoryRAG()
    for query in ("ロケット燃料", "イオン化燃料", "プルトニウム燃料棒", "ウラン廃棄物処理"):
        assert rag.get_production_meta(query) is not None, query


def test_recipe_target_scaling_is_deterministic():
    nitro = ProductionCalculator.calculate_recipe_target("Recipe_Alternate_RocketFuel_Nitro_C", 300)
    assert nitro["inputs_per_min"]["Fuel"] == 200.0
    assert nitro["inputs_per_min"]["Nitrogen Gas"] == 150.0
    assert nitro["inputs_per_min"]["Sulfur"] == 200.0
    assert nitro["inputs_per_min"]["Coal"] == 100.0
    ionized = ProductionCalculator.calculate_recipe_target("Recipe_IonizedFuel_C", 40)
    assert ionized["inputs_per_min"]["Rocket Fuel"] == 40.0
    assert ionized["inputs_per_min"]["Desc_CrystalShard_C"] == 2.5


if __name__ == "__main__":
    tests = [
        test_metas_are_grounded_in_recipe_db,
        test_nitro_rocket_fuel_rates,
        test_ionized_fuel_rates,
        test_plutonium_fuel_rod_rates_and_sink_policy,
        test_all_new_metas_are_retrievable_from_rag,
        test_recipe_target_scaling_is_deterministic,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print("Phase 1 production meta tests: 100% PASS")
