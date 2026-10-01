#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Satisfactory v1.0 Production & Power Calculation Engine
Provides deterministic, mathematically exact calculations for:
1. Fuel & Power Plant scaling (Standard, Diluted, Turbo, Rocket)
2. Aluminum refining & water-loop balance
3. Target item production chain & machine count solver
4. Recipe efficiency comparative metrics
"""

import os
import sys
import json
import math
from typing import Dict, Any, List, Optional

# Force UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))


def load_json(filename: str) -> Any:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


RECIPES = load_json("recipes.json")
ITEMS = load_json("items.json")
BUILDINGS = load_json("buildings.json")
METAS = load_json("production_metas.json")


class ProductionCalculator:
    """Exact engineering calculator for Satisfactory v1.0 logistics."""

    @staticmethod
    def calculate_fuel_power(crude_oil_per_min: float, recipe_type: str = "diluted_fuel") -> Dict[str, Any]:
        """
        Calculate fuel power generation metrics from raw crude oil.
        recipe_type:
          - 'standard': Crude Oil -> Fuel (Refinery) + Polymer Resin
          - 'diluted_fuel': Crude Oil -> Heavy Oil Residue (Refinery) -> Diluted Fuel (Blender/Packer)
          - 'turbofuel': Crude Oil -> Heavy Oil Residue -> Turbofuel (Refinery/Blender)
        """
        crude = float(crude_oil_per_min)
        # Fuel Generator in v1.0: 250 MW, burns 20 Fuel / min (or 7.5 Turbofuel / min)
        # Note: v1.0 updated Fuel Generators to 250 MW!
        GEN_MW = 250.0

        if recipe_type == "standard":
            # Standard Fuel: 60 Crude -> 40 Fuel + 30 Polymer Resin
            # Ratio: 1 Crude -> 2/3 Fuel (0.6667)
            fuel_rate = crude * (40.0 / 60.0)
            resin_rate = crude * (30.0 / 60.0)
            refinery_count = crude / 60.0
            
            gen_count = fuel_rate / 20.0
            total_mw = gen_count * GEN_MW
            net_mw = total_mw - (refinery_count * 30.0) # Refinery: 30MW
            
            return {
                "method": "通常燃料（直接精製）",
                "crude_oil_input": crude,
                "fuel_output": round(fuel_rate, 2),
                "byproduct": {"ポリマー樹脂": round(resin_rate, 2)},
                "generators": round(gen_count, 2),
                "total_power_mw": round(total_mw, 1),
                "net_power_mw": round(net_mw, 1),
                "facilities": [
                    {"name": "精製機 (燃料)", "count": math.ceil(refinery_count * 100) / 100, "rate": f"{round(refinery_count, 2)}台"}
                ],
                "efficiency_multiplier": "1.0x (基準)"
            }

        elif recipe_type == "diluted_fuel":
            # Step 1: Heavy Oil Residue (Alt)
            # 30 Crude -> 40 Heavy Oil Residue + 20 Polymer Resin
            # Ratio: 1 Crude -> 4/3 HOR (1.3333)
            refinery_hor_count = crude / 30.0
            hor_rate = crude * (40.0 / 30.0)
            resin_rate = crude * (20.0 / 30.0)

            # Step 2: Diluted Fuel (Blender)
            # 50 HOR + 100 Water -> 100 Fuel
            # Ratio: 1 HOR -> 2 Fuel
            fuel_rate = hor_rate * 2.0
            water_required = hor_rate * 2.0
            blender_count = hor_rate / 50.0

            gen_count = fuel_rate / 20.0
            total_mw = gen_count * GEN_MW
            power_consumption = (refinery_hor_count * 30.0) + (blender_count * 75.0) + ((water_required / 120.0) * 20.0)
            net_mw = total_mw - power_consumption

            return {
                "method": "希釈燃料コンボ (重油残渣 ➔ 希釈燃料)",
                "crude_oil_input": crude,
                "fuel_output": round(fuel_rate, 2),
                "water_input": round(water_required, 2),
                "byproduct": {"ポリマー樹脂": round(resin_rate, 2)},
                "generators": round(gen_count, 2),
                "total_power_mw": round(total_mw, 1),
                "net_power_mw": round(net_mw, 1),
                "facilities": [
                    {"name": "精製機 (重油残渣)", "count": round(refinery_hor_count, 2), "desc": f"{round(refinery_hor_count, 2)}台"},
                    {"name": "ブレンダー (希釈燃料)", "count": round(blender_count, 2), "desc": f"{round(blender_count, 2)}台"},
                    {"name": "水抽出機", "count": round(water_required / 120.0, 2), "desc": f"{round(water_required / 120.0, 2)}台"}
                ],
                "efficiency_multiplier": "4.0x (標準精製の4倍の燃料/電力)"
            }

        elif recipe_type == "turbofuel":
            # Turbo Blend Fuel (Blender):
            # 15 Heavy Oil Residue + 15 Fuel + 22.5 Sulfur + 15 Petroleum Coke -> 45 Turbofuel
            # Standard Turbofuel (Refinery):
            # 22.5 Fuel + 15 Compacted Coal -> 18.75 Turbofuel
            # Here calculate standard diluted fuel -> turbofuel conversion
            diluted = ProductionCalculator.calculate_fuel_power(crude, recipe_type="diluted_fuel")
            fuel_rate = diluted["fuel_output"]
            # 22.5 Fuel + 15 Compacted Coal -> 18.75 Turbofuel
            # Ratio: 1 Fuel -> (18.75 / 22.5) = 0.8333 Turbofuel
            turbo_rate = fuel_rate * (18.75 / 22.5)
            compacted_coal_rate = fuel_rate * (15.0 / 22.5)
            refinery_turbo_count = fuel_rate / 22.5

            # Fuel Generator on Turbofuel: 250MW, burns 7.5 Turbofuel / min
            gen_count = turbo_rate / 7.5
            total_mw = gen_count * GEN_MW

            return {
                "method": "希釈ターボ燃料コンボ (重油残渣 ➔ 希釈燃料 ➔ ターボ燃料)",
                "crude_oil_input": crude,
                "turbofuel_output": round(turbo_rate, 2),
                "compacted_coal_required": round(compacted_coal_rate, 2),
                "generators": round(gen_count, 2),
                "total_power_mw": round(total_mw, 1),
                "facilities": [
                    {"name": "精製機 (重油残渣)", "count": round(crude / 30.0, 2)},
                    {"name": "ブレンダー (希釈燃料)", "count": round((crude * 4.0 / 3.0) / 50.0, 2)},
                    {"name": "精製機 (ターボ燃料)", "count": round(refinery_turbo_count, 2)}
                ],
                "efficiency_multiplier": "約8.0x (圧倒的な発電力、要硫黄・石炭)"
            }

        return {"error": f"Unknown recipe type: {recipe_type}"}

    @staticmethod
    def calculate_aluminum_chain(bauxite_per_min: float, recipe_type: str = "standard") -> Dict[str, Any]:
        """
        Calculate Aluminum production and water recycling metrics.
        """
        bauxite = float(bauxite_per_min)
        if recipe_type == "standard":
            # Standard:
            # 1. Alumina Solution: 120 Bauxite + 180 Water -> 120 Alumina Solution + 50 Silica
            # 2. Aluminum Scrap: 240 Alumina Solution + 120 Coal -> 360 Aluminum Scrap + 120 Water (Byproduct!)
            refinery_alumina = bauxite / 120.0
            alumina_rate = bauxite * (120.0 / 120.0) # 1:1
            water_need = bauxite * (180.0 / 120.0) # 1.5x
            silica_produced = bauxite * (50.0 / 120.0) # 0.4167x

            # Scrap
            refinery_scrap = alumina_rate / 240.0
            scrap_rate = alumina_rate * (360.0 / 240.0) # 1.5x
            coal_need = alumina_rate * (120.0 / 240.0) # 0.5x
            water_recycled = alumina_rate * (120.0 / 240.0) # 0.5x (120 water per 240 alumina)

            net_fresh_water = water_need - water_recycled

            # Ingot (Standard): 90 Scrap + 60 Silica -> 60 Ingot (Foundry)
            foundry_count = scrap_rate / 90.0
            ingot_rate = scrap_rate * (60.0 / 90.0)
            silica_needed_ingot = scrap_rate * (60.0 / 90.0)
            net_silica_shortage = max(0.0, silica_needed_ingot - silica_produced)

            return {
                "method": "通常アルミ生産 (水循環 + シリカ再利用)",
                "bauxite_input": bauxite,
                "coal_input": round(coal_need, 2),
                "scrap_output": round(scrap_rate, 2),
                "ingot_output": round(ingot_rate, 2),
                "water_balance": {
                    "total_required": round(water_need, 2),
                    "recycled_byproduct": round(water_recycled, 2),
                    "net_fresh_water_input": round(net_fresh_water, 2),
                    "recycling_ratio": f"{round((water_recycled / water_need) * 100, 1)}%"
                },
                "silica_balance": {
                    "produced_as_byproduct": round(silica_produced, 2),
                    "needed_for_ingot": round(silica_needed_ingot, 2),
                    "net_additional_silica_needed": round(net_silica_shortage, 2)
                },
                "facilities": [
                    {"name": "精製機 (アルミナ溶液)", "count": round(refinery_alumina, 2)},
                    {"name": "精製機 (アルミスクラップ)", "count": round(refinery_scrap, 2)},
                    {"name": "鋳造炉 (アルミインゴット)", "count": round(foundry_count, 2)}
                ]
            }
        elif recipe_type == "alt_scrap":
            # Electrode Aluminum Scrap:
            # 180 Alumina Solution + 60 Petroleum Coke -> 300 Scrap + 105 Water
            # Pure Aluminum Ingot (Smelter):
            # 60 Scrap -> 30 Ingot (No Silica required!)
            refinery_alumina = bauxite / 120.0
            alumina_rate = bauxite
            water_need = bauxite * 1.5
            silica_produced = bauxite * (50.0 / 120.0)

            refinery_scrap = alumina_rate / 180.0
            scrap_rate = alumina_rate * (300.0 / 180.0) # 1.6667x
            coke_need = alumina_rate * (60.0 / 180.0)
            water_recycled = alumina_rate * (105.0 / 180.0)

            net_fresh_water = water_need - water_recycled
            smelter_count = scrap_rate / 60.0
            ingot_rate = scrap_rate * (30.0 / 60.0)

            return {
                "method": "電極アルミスクラップ ＋ 純アルミインゴット (シリカ不要コンボ)",
                "bauxite_input": bauxite,
                "petroleum_coke_input": round(coke_need, 2),
                "scrap_output": round(scrap_rate, 2),
                "ingot_output": round(ingot_rate, 2),
                "water_balance": {
                    "total_required": round(water_need, 2),
                    "recycled_byproduct": round(water_recycled, 2),
                    "net_fresh_water_input": round(net_fresh_water, 2)
                },
                "key_advantage": "シリカラインが完全不要。原油の石油コークスで直結可能。",
                "facilities": [
                    {"name": "精製機 (アルミナ溶液)", "count": round(refinery_alumina, 2)},
                    {"name": "精製機 (電極スクラップ)", "count": round(refinery_scrap, 2)},
                    {"name": "製錬炉 (純アルミインゴット)", "count": round(smelter_count, 2)}
                ]
            }

        return {"error": f"Unknown aluminum recipe type: {recipe_type}"}

    @staticmethod
    def calculate_recipe_target(recipe_id: str, target_output_per_min: float) -> Dict[str, Any]:
        """Scale a verified recipe deterministically to a requested output rate."""
        recipe = RECIPES.get(recipe_id)
        if not recipe:
            return {"error": f"Unknown recipe: {recipe_id}"}
        products = recipe.get("products", [])
        if not products or recipe.get("duration_seconds", 0) <= 0:
            return {"error": f"Recipe has no scalable output: {recipe_id}"}
        target = float(target_output_per_min)
        base_output = products[0].get("rate_per_min")
        if not base_output:
            base_output = products[0].get("amount", 0) * 60 / recipe["duration_seconds"]
        scale = target / base_output
        return {
            "recipe_id": recipe_id,
            "recipe_name": recipe.get("name_en", recipe_id),
            "target_output_per_min": round(target, 4),
            "machines": round(scale, 4),
            "inputs_per_min": {
                item.get("name_en", item.get("item_id", "unknown")): round(
                    item.get("rate_per_min", item.get("amount", 0) * 60 / recipe["duration_seconds"]) * scale, 4
                ) for item in recipe.get("ingredients", [])
            },
            "outputs_per_min": {
                item.get("name_en", item.get("item_id", "unknown")): round(
                    item.get("rate_per_min", item.get("amount", 0) * 60 / recipe["duration_seconds"]) * scale, 4
                ) for item in products
            },
        }

    @staticmethod
    def get_recipe_comparison(item_name: str) -> Dict[str, Any]:
        """Get structural comparison data for recipes producing target item."""
        target_name = item_name.strip()
        recipes_for_item = []

        for r_id, r in RECIPES.items():
            for prod in r.get("products", []):
                if target_name.lower() in prod.get("name", "").lower():
                    recipes_for_item.append(r)
                    break

        if not recipes_for_item:
            return {"error": f"No recipes found for '{item_name}'"}

        results = []
        for r in recipes_for_item:
            is_alt = r.get("is_alternate", False)
            dur = r.get("duration", 1.0)
            prod_rate = 0.0
            for prod in r.get("products", []):
                if target_name.lower() in prod.get("name", "").lower():
                    prod_rate = (prod.get("amount", 1) / dur) * 60.0
                    break

            ingredients = []
            for ing in r.get("ingredients", []):
                ing_rate = (ing.get("amount", 1) / dur) * 60.0
                ingredients.append({
                    "name": ing.get("name", ""),
                    "rate_per_min": round(ing_rate, 2)
                })

            results.append({
                "recipe_name": r.get("name", ""),
                "is_alternate": is_alt,
                "building": r.get("produced_in", ["Unknown"])[0] if r.get("produced_in") else "Unknown",
                "production_rate_per_min": round(prod_rate, 3),
                "ingredients": ingredients
            })

        return {
            "target_item": target_name,
            "recipes_count": len(results),
            "recipes": results
        }


# Global tool dispatcher for Agent
def execute_calculation_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Executes a calculation tool and returns JSON string result."""
    try:
        if tool_name == "calculate_fuel_power":
            res = ProductionCalculator.calculate_fuel_power(
                crude_oil_per_min=arguments.get("crude_oil_per_min", 300.0),
                recipe_type=arguments.get("recipe_type", "diluted_fuel")
            )
            return json.dumps(res, ensure_ascii=False, indent=2)
        elif tool_name == "calculate_aluminum_chain":
            res = ProductionCalculator.calculate_aluminum_chain(
                bauxite_per_min=arguments.get("bauxite_per_min", 300.0),
                recipe_type=arguments.get("recipe_type", "standard")
            )
            return json.dumps(res, ensure_ascii=False, indent=2)
        elif tool_name == "get_recipe_comparison":
            res = ProductionCalculator.get_recipe_comparison(
                item_name=arguments.get("item_name", "")
            )
            return json.dumps(res, ensure_ascii=False, indent=2)
        elif tool_name == "calculate_recipe_target":
            res = ProductionCalculator.calculate_recipe_target(
                recipe_id=arguments.get("recipe_id", ""),
                target_output_per_min=arguments.get("target_output_per_min", 1.0)
            )
            return json.dumps(res, ensure_ascii=False, indent=2)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    # Test script directly
    print("=== Test: Fuel Power (Crude 300) ===")
    print(execute_calculation_tool("calculate_fuel_power", {"crude_oil_per_min": 300.0, "recipe_type": "diluted_fuel"}))
    print("\n=== Test: Aluminum Chain (Bauxite 300) ===")
    print(execute_calculation_tool("calculate_aluminum_chain", {"bauxite_per_min": 300.0, "recipe_type": "standard"}))
