#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3: context inheritance and model-routing checks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bot.ai_client import classify_complexity, run_autonomous_solver
from src.rag.search_engine import SatisfactoryRAG


def test_three_turn_rate_context_is_preserved():
    rag = SatisfactoryRAG()
    first = "原油480から希釈燃料を作る場合、発電機は何台？"
    first_context = rag.query(first)
    first_solver, rates = run_autonomous_solver(first, first_context)
    assert first_solver is not None
    assert rates["crude_oil"] == 480.0

    topic = {"resource_rates": rates, "item_name": "希釈燃料"}
    second = "これをターボ燃料に変えるには？"
    second_context = rag.query(second, fallback_topic=topic["item_name"])
    second_solver, second_rates = run_autonomous_solver(second, second_context, current_topic=topic)
    assert second_solver is not None
    assert second_rates["crude_oil"] == 480.0

    third = "代替レシピと比較してどっちがいい？"
    third_context = rag.query(third, fallback_topic="ロケット燃料")
    assert third_context.get("comparison_table") is not None
    assert classify_complexity(third, third_context, sticky_high=True) == "HIGH"


def test_routing_boundaries():
    rag = SatisfactoryRAG()
    standard_context = rag.query("イオン化燃料の材料を教えて")
    assert classify_complexity("イオン化燃料の材料を教えて", standard_context) == "STANDARD"

    comparison_context = rag.query("ロケット燃料の代替レシピを比較して")
    assert comparison_context.get("comparison_table") is not None
    assert classify_complexity("ロケット燃料の代替レシピを比較して", comparison_context) == "HIGH"

    assert classify_complexity("大規模な原子力発電所をどう組む？") == "HIGH"
    assert classify_complexity("このBotの記憶仕様は？") == "STANDARD"


def test_short_followup_requires_sticky_high_context():
    assert classify_complexity("どっち？", sticky_high=True) == "HIGH"
    assert classify_complexity("どっち？", sticky_high=False) == "HIGH"
    assert classify_complexity("教えて", sticky_high=True) == "HIGH"


if __name__ == "__main__":
    tests = [
        test_three_turn_rate_context_is_preserved,
        test_routing_boundaries,
        test_short_followup_requires_sticky_high_context,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print("Phase 3 context/routing tests: 100% PASS")
