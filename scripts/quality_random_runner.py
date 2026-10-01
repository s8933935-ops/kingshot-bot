#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe local quality loop for the Satisfactory RAG bot.

Generates deterministic/randomized prompts, validates grounded calculations,
and writes a report plus improvement suggestions. It never edits production code.
"""

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.bot.ai_client import generate_rag_answer, run_autonomous_solver
from src.rag.calculator import ProductionCalculator
from src.rag.search_engine import SatisfactoryRAG


REPORT_DIR = ROOT / "data" / "quality_reports"


def build_cases(rng: random.Random, count=50):
    cases = []
    for index in range(count):
        case_type = index % 5
        crude = rng.choice([120, 180, 240, 300, 480, 600, 720])
        nitro = rng.choice([75, 150, 225, 300, 450, 600])
        ionized = rng.choice([10, 20, 40, 60, 80])
        if case_type == 0:
            cases.append({
            "name": f"diluted_fuel_power_{index + 1}",
            "question": f"原油{crude}から希釈燃料を作る場合、発電機は何台？",
            "kind": "solver",
            "expected": [str(round(crude * 4 / 3 * 2 / 20, 2))],
            })
        elif case_type == 1:
            cases.append({
            "name": f"nitro_recipe_scaling_{index + 1}",
            "question": f"ニトロ・ロケット燃料を毎分{nitro}作るには、材料はいくつ必要？",
            "kind": "solver",
            "expected": [str(round(nitro * 2 / 3, 4)), str(float(nitro) / 2)],
            })
        elif case_type == 2:
            cases.append({
            "name": f"ionized_recipe_scaling_{index + 1}",
            "question": f"イオン化燃料{ionized}/分を作るために必要な材料は？",
            "kind": "solver",
            "expected": [str(float(ionized)), str(round(ionized / 16, 4))],
            })
        elif case_type == 3:
            cases.append({
            "name": f"unknown_fuel_guard_{index + 1}",
            "question": f"超音速燃料{index + 1}のレシピを教えて",
            "kind": "guard",
            "expected": ["確定レシピDBに該当"],
            })
        else:
            cases.append({
            "name": f"unknown_material_guard_{index + 1}",
            "question": rng.choice(["チタン製コンベアはある？", "未知合金の製造レシピは？", "架空素材Xの材料は？"]),
            "kind": "guard",
            "expected": ["確定レシピDB", "ありません"],
            })
    return cases


def run_case(rag, case):
    question = case["question"]
    context = rag.query(question)
    solver_output = None
    if case["kind"] == "solver":
        solver_output, _ = run_autonomous_solver(question, context)
    answer, model = generate_rag_answer(question, context, use_claude=False)
    combined = "\n".join(x for x in [solver_output or "", answer or ""])
    missing = [token for token in case["expected"] if token not in combined]
    forbidden = []
    if case["kind"] == "guard":
        forbidden_tokens = [
            "ロケット燃料", "ニトロ・ロケット燃料", "原油 300", "関連部材",
            "鋼鉄製コンベア", "鉄や銅", "プラスチックなど"
        ]
        forbidden = [token for token in forbidden_tokens if token in combined]
        if case["name"].startswith("unknown_material") and model != "Grounding Guard":
            forbidden.append(f"expected Grounding Guard, got {model}")
    return {
        "name": case["name"],
        "question": question,
        "model": model,
        "pass": not missing and not forbidden,
        "missing_expected": missing,
        "forbidden_found": forbidden,
        "answer_excerpt": answer[:1200],
    }


def suggestions(results):
    output = []
    for result in results:
        if result["pass"]:
            continue
        if result["name"].startswith("unknown_fuel_guard"):
            output.append("未知燃料名のフォールバック継承とLLM生成を遮断する")
        elif result["name"].startswith("unknown_material_guard"):
            output.append("未知素材を別名へ置換せず、確定DB不在として固定応答する")
        elif "recipe_scaling" in result["name"]:
            output.append("対象レシピIDを固定し、recipes.jsonから毎分レートを再計算する")
        else:
            output.append("質問意図と自律ソルバーの発動条件を確認する")
    return sorted(set(output))


def main(seed=None):
    rng = random.Random(seed)
    rag = SatisfactoryRAG()
    results = [run_case(rag, case) for case in build_cases(rng, count=50)]
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "total": len(results),
        "passed": sum(item["pass"] for item in results),
        "failed": sum(not item["pass"] for item in results),
        "results": results,
        "improvement_suggestions": suggestions(results),
        "auto_mutation": False,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "passed": report["passed"], "failed": report["failed"]}, ensure_ascii=False))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 20260929
    raise SystemExit(main(seed))
