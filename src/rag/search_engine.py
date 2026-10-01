#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Satisfactory v1.0 Hybrid RAG Search Engine
Combines:
1. Exact Recipe & Item database lookup (100% accurate rates & machines)
2. BM25 Knowledge Retrieval over YouTube Tips & Guides with timestamp links
"""

import os
import sys
import json
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional

# Force UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))


def tokenize(text: str) -> List[str]:
    """Simple bilingual tokenizer for Japanese and English."""
    text = text.lower()
    # Extract alphanumeric words and Japanese kanji/hiragana/katakana sequences
    tokens = re.findall(r'[a-z0-9_]+|[\u3040-\u309F]+|[\u30A0-\u30FF]+|[\u4E00-\u9FFF]+', text)
    # Also generate bi-grams for single kanji/hiragana characters to boost Japanese search recall
    result = list(tokens)
    for t in tokens:
        if len(t) >= 2 and any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' for c in t):
            for i in range(len(t) - 1):
                result.append(t[i:i+2])
    return result


class BM25Index:
    """Lightweight self-contained BM25 index."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: List[Dict[str, Any]] = []
        self.doc_len: List[int] = []
        self.avg_doc_len = 0.0
        self.df: Counter = Counter()
        self.idf: Dict[str, float] = {}
        self.tf: List[Counter] = []

    def fit(self, docs: List[Dict[str, Any]], text_field: str = "content"):
        self.docs = docs
        total_len = 0
        for doc in docs:
            tokens = tokenize(doc.get(text_field, ""))
            self.tf.append(Counter(tokens))
            self.doc_len.append(len(tokens))
            total_len += len(tokens)
            for word in set(tokens):
                self.df[word] += 1

        n_docs = len(docs)
        self.avg_doc_len = total_len / n_docs if n_docs > 0 else 1.0

        for word, freq in self.df.items():
            self.idf[word] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        q_tokens = tokenize(query)
        scores = []

        for idx in range(len(self.docs)):
            score = 0.0
            doc_tf = self.tf[idx]
            d_len = self.doc_len[idx]
            for token in q_tokens:
                if token in doc_tf:
                    tf_val = doc_tf[token]
                    idf_val = self.idf.get(token, 0.0)
                    denom = tf_val + self.k1 * (1 - self.b + self.b * (d_len / self.avg_doc_len))
                    score += idf_val * (tf_val * (self.k1 + 1)) / denom

            if score > 0:
                # Prefer v1.0 verified guides
                if self.docs[idx].get("is_v1_0", False):
                    score *= 1.2
                scores.append((score, self.docs[idx]))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scores[:top_k]]


class SatisfactoryRAG:
    """Integrated Satisfactory v1.0 RAG Engine."""
    def __init__(self):
        self.items = self._load_json("items.json")
        self.buildings = self._load_json("buildings.json")
        self.recipes = self._load_json("recipes.json")
        self.dictionary = self._load_json("dictionary.json")
        self.youtube_tips = self._load_json("youtube_tips.json")
        self.phases_data = self._load_json("space_elevator_phases.json")
        self.production_metas = self._load_json("production_metas.json")

        # Initialize BM25 for YouTube Tips
        self.yt_index = BM25Index()
        if self.youtube_tips:
            self.yt_index.fit(self.youtube_tips, text_field="content")
            print(f"✅ RAG Engine Loaded: {len(self.recipes)} Recipes, {len(self.items)} Items, {len(self.production_metas)} Production Metas, {len(self.youtube_tips)} YouTube Tips.")

    def get_production_meta(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve verified production meta for common Satisfactory items."""
        if not self.production_metas:
            return None
        clean = item_name.strip()
        if clean in self.production_metas:
            return self.production_metas[clean]
        for k, v in self.production_metas.items():
            if k in clean or clean in k:
                return v
        return None

    def _load_json(self, filename: str) -> Any:
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def lookup_item(self, term: str) -> List[Dict[str, Any]]:
        """Find matching items by Japanese or English name."""
        clean = term.strip().lower()
        matched_entries = self.dictionary.get(clean, [])
        item_results = []
        for e in matched_entries:
            if e.get("type") == "item":
                item_info = self.items.get(e["id"])
                if item_info and item_info not in item_results:
                    item_results.append(item_info)
        return item_results

    def find_recipes_for_item(self, item_name_or_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Find all recipes that produce or consume this item."""
        matched_items = self.lookup_item(item_name_or_id)
        if not matched_items:
            # Fuzzy match in items
            clean = item_name_or_id.strip().lower()
            matched_items = [
                item for item in self.items.values()
                if clean in item["name_ja"].lower() or clean in item["name_en"].lower()
            ]

        target_ids = {item["id"] for item in matched_items}
        producing_recipes = []
        consuming_recipes = []

        for rec in self.recipes.values():
            if any(p.get("item_id") in target_ids for p in rec.get("products", [])):
                producing_recipes.append(rec)
            if any(i.get("item_id") in target_ids for i in rec.get("ingredients", [])):
                consuming_recipes.append(rec)

        def is_unpacking_recipe(r: Dict[str, Any]) -> bool:
            name = r.get("name_ja", "")
            if any(kw in name for kw in ["未包装", "開封", "空にする", "Unpackage", "Unpack"]):
                return True
            if "充填機" in r.get("produced_in_names", []):
                if any("容器入り" in i.get("name_ja", "") for i in r.get("ingredients", [])):
                    return True
            return False

        # Sort: Genuine standard recipes first, then alternates, unpackaging dead last
        producing_recipes.sort(key=lambda r: (is_unpacking_recipe(r), r.get("is_alternate", False)))

        return {
            "matched_items": matched_items,
            "producing": producing_recipes,
            "consuming": consuming_recipes
        }

    def search_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search YouTube guides and community tips."""
        return self.yt_index.search(query, top_k=top_k)

    def format_recipe_card(self, recipe: Dict[str, Any]) -> str:
        """Format a single recipe into a clean, beautiful Markdown card."""
        alt_badge = "🔄 **【代替レシピ】**" if recipe.get("is_alternate") else "⚙️ **【通常レシピ】**"
        machines = " / ".join(recipe.get("produced_in_names", [])) or "製作機等"
        duration = recipe.get("duration_seconds", 0)

        in_lines = [f"  • {i['name_ja']}: `{i['rate_per_min']}/分` (1回あたり {i['amount']}個)" for i in recipe["ingredients"]]
        out_lines = [f"  • **{p['name_ja']}**: `{p['rate_per_min']}/分` (1回あたり {p['amount']}個)" for p in recipe["products"]]

        return (
            f"{alt_badge} **{recipe['name_ja']}**\n"
            f"🏭 **製造機**: `{machines}` (製造サイクル: {duration}秒)\n"
            f"📥 **投入 (材料/分)**:\n" + "\n".join(in_lines) + "\n"
            f"📤 **搬出 (完成/分)**:\n" + "\n".join(out_lines)
        )

    def build_supply_chain_tree(self, item_name: str, max_depth: int = 3) -> Optional[str]:
        """Build a 100% deterministic ASCII supply chain tree for an item."""
        matched = self.lookup_item(item_name)
        if not matched:
            clean = item_name.strip().lower()
            matched = [it for it in self.items.values() if clean in it["name_ja"].lower() or clean in it["name_en"].lower()]
        if not matched:
            return None

        target_item = matched[0]
        raw_resources = {"鉱石", "原油", "水", "窒素", "石灰岩", "ウラン", "石炭", "ボーキサイト", "生体物質"}

        def _get_tree_lines(item_id: str, depth: int, visited: set) -> List[str]:
            if depth >= max_depth or item_id in visited:
                return []
            visited.add(item_id)

            item_info = self.items.get(item_id, {})
            name = item_info.get("name_ja", item_id)
            
            # Check if raw resource
            if any(r in name for r in raw_resources):
                return [f"⛏️ {name} (一次資源)"]

            # Find default recipe
            res = self.find_recipes_for_item(name)
            default_recipes = [r for r in res.get("producing", []) if not r.get("is_alternate")]
            if not default_recipes:
                default_recipes = res.get("producing", [])
            if not default_recipes:
                return [f"{name}"]

            rec = default_recipes[0]
            machine = rec.get("produced_in_names", ["製造機"])[0] if rec.get("produced_in_names") else "製造機"
            lines = [f"{name} ({machine})"]

            for idx, ing in enumerate(rec.get("ingredients", [])):
                is_last = (idx == len(rec["ingredients"]) - 1)
                prefix = " └─ " if is_last else " ├─ "
                sub_lines = _get_tree_lines(ing["item_id"], depth + 1, set(visited))
                if sub_lines:
                    lines.append(f"{prefix}{sub_lines[0]}")
                    indent = "    " if is_last else " │  "
                    for s in sub_lines[1:]:
                        lines.append(f"{indent}{s}")
                else:
                    lines.append(f"{prefix}{ing['name_ja']}")
            return lines

        tree_lines = _get_tree_lines(target_item["id"], 0, set())
        if not tree_lines:
            return None
        return f"```text\n🏭 【{target_item['name_ja']}】の製造サプライチェーン\n" + "\n".join(tree_lines) + "\n```"

    def build_alternate_comparison_table(self, item_name: str) -> Optional[str]:
        """Build a 100% deterministic Markdown comparison table for standard vs alternate recipes."""
        res = self.find_recipes_for_item(item_name)
        producing = res.get("producing", [])
        if not producing:
            return None

        matched_items = res.get("matched_items", [])
        item_display_name = matched_items[0]["name_ja"] if matched_items else item_name

        default_recs = [r for r in producing if not r.get("is_alternate")]
        alt_recs = [r for r in producing if r.get("is_alternate")]

        if not alt_recs:
            return None

        # Build Markdown Table
        lines = [
            f"📊 **【{item_display_name}】通常 vs 代替レシピ比較表**",
            "| レシピ名 | 施設 | 生産量/分 | 投入素材 (消費量/分) | 特徴・コスト傾向 |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        all_to_show = default_recs[:1] + alt_recs
        for r in all_to_show:
            is_alt = r.get("is_alternate", False)
            badge = f"**{r['name_ja']}**" if is_alt else "**通常レシピ**"
            facility = (r.get("produced_in_names") or ["製造施設"])[0]

            # Product rate
            prod_rate = "不明"
            for p in r.get("products", []):
                prod_rate = f"`{p.get('rate_per_min', 0)}/分`"
                break

            # Ingredient rates
            ing_parts = []
            for ing in r.get("ingredients", []):
                ing_parts.append(f"{ing.get('name_ja', '')} `{ing.get('rate_per_min', 0)}`")
            ing_str = ", ".join(ing_parts) if ing_parts else "なし"

            # Features / Trade-offs
            features = []
            if not is_alt:
                features.append("標準構成")
            else:
                features.append(f"素材{len(r.get('ingredients', []))}種")
                if "組立機" in facility:
                    features.append("組立機(省スペース)")
                elif "精製機" in facility:
                    features.append("液体利用")

            desc = " / ".join(features)
            lines.append(f"| {badge} | `{facility}` | {prod_rate} | {ing_str} | {desc} |")

        # Append Verified Production Meta if exists
        meta = self.get_production_meta(item_display_name)
        if meta:
            lines.append("")
            lines.append(f"💡 **【FICSIT公式 効率メタ解説（確定検証済み）】**")
            lines.append(f"• **最高効率構成**: `{meta['best_recipe']}` ({meta['efficiency_multiplier']})")
            lines.append(f"• **原料比較**: {meta['raw_ratio']}")
            lines.append(f"• **推奨方針**: {meta['summary']}")

        return "\n".join(lines)

    def query(self, question: str, fallback_topic: Optional[str] = None) -> Dict[str, Any]:
        """Integrated query handler: extracts recipe matches, phase data, supply chain, and tips."""
        q_lower = question.lower()
        unknown_item_markers = ["存在しない", "架空", "実在しない", "ないアイテム", "存在しないアイテム"]
        explicit_unknown_item = any(marker in question for marker in unknown_item_markers)
        # Do not inherit a previous fuel topic for an unknown compound such as
        # "超音速燃料". Only these grounded fuel names may use fuel fallback.
        known_fuel_names = ["燃料", "希釈燃料", "ターボ燃料", "ロケット燃料", "イオン化燃料"]
        has_fuel_compound = "燃料" in question and any(
            name in question for name in known_fuel_names if name != "燃料"
        )
        if "燃料" in question and not has_fuel_compound:
            explicit_unknown_item = True

        def is_cjk_or_kana(char: str) -> bool:
            return bool(char) and (
                '\u3040' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9fff'
            )

        def is_standalone_japanese_term(term: str) -> bool:
            """Reject a short dictionary term embedded in an unknown compound word."""
            start = q_lower.find(term)
            if start < 0:
                return False
            end = start + len(term)
            left = q_lower[start - 1] if start else ""
            # A Japanese postposition (e.g. "燃料の") is a valid suffix;
            # reject only when the term is attached to an unknown prefix.
            return not is_cjk_or_kana(left)

        # Check for meta questions (Bot's internal features, memory, updates)
        meta_keywords = ["思考回路", "アプデ", "アップデート", "二重記憶", "記憶", "メモリ", "覚えてる", "忘れた", "仕様", "だれ", "誰", "自己紹介"]
        if any(kw in q_lower for kw in meta_keywords):
            return {
                "query": question,
                "recipe_matches": {},
                "matched_phases": [],
                "supply_chain_tree": None,
                "comparison_table": None,
                "tips": []
            }

        # 1. Check for item / recipe queries
        recipe_matches = {}
        target_item_term = None
        # Longest terms win first. This prevents generic terms such as "燃料"
        # from stealing a query containing a more specific item name.
        for term in sorted(self.dictionary.keys(), key=len, reverse=True):
            if len(term) >= 2 and term in q_lower and is_standalone_japanese_term(term):
                res = self.find_recipes_for_item(term)
                if res["producing"] or res["consuming"]:
                    recipe_matches[term] = res
                    if not target_item_term:
                        target_item_term = term

        # Coreference Resolution: If no item found in query, inherit from fallback_topic
        if not target_item_term and fallback_topic and not explicit_unknown_item:
            # Check if user is asking a follow-up about recipes, comparison, or supply chain
            followup_indicators = ["代替え", "代替", "レシピ", "作り方", "材料", "素材", "ツリー", "比較", "どれ", "どっち", "ライン", "全部", "効率"]
            if any(ind in q_lower for ind in followup_indicators) or len(question.strip()) <= 20:
                fallback_res = self.find_recipes_for_item(fallback_topic)
                if fallback_res["producing"] or fallback_res["consuming"]:
                    recipe_matches[fallback_topic] = fallback_res
                    target_item_term = fallback_topic
                    print(f"🔗 [Context Resolution] Successfully inherited focus item: '{fallback_topic}'")

        # 2. Supply Chain Tree Check
        supply_chain_tree = None
        supply_chain_keywords = ["サプライチェーン", "ツリー", "原料", "素材ツリー", "作り方ツリー", "ライン"]
        if target_item_term and any(kw in q_lower for kw in supply_chain_keywords):
            supply_chain_tree = self.build_supply_chain_tree(target_item_term)

        # 3. Alternate Recipe Comparison Table Check
        comparison_table = None
        compare_keywords = ["代替え", "代替", "比較", "どっち", "違い", "優先", "おすすめ", "オススメ", "どれ"]
        if target_item_term and any(kw in q_lower for kw in compare_keywords):
            comparison_table = self.build_alternate_comparison_table(target_item_term)

        # 4. Check for Space Elevator / Phase Deliveries (STRICT: only if phase/delivery is explicitly requested)
        matched_phases = []
        phase_keywords = ["納品", "フェーズ", "エレベーター", "エレベータ", "phase", "軌道エレベータ"]
        if any(kw in q_lower for kw in phase_keywords) and self.phases_data:
            for p in self.phases_data.get("phases", []):
                req_names = [r["item"].lower() for r in p.get("requirements", [])]
                if any(kw in q_lower for kw in [f"フェーズ{p['phase']}", f"フェーズ {p['phase']}", f"phase{p['phase']}"]):
                    matched_phases.append(p)
                elif any("スーパーコンピューター" in r.get("rate_info", "") or "スーパーコンピューター" in r.get("item", "") for r in p.get("requirements", [])) and ("スパコン" in q_lower or "スーパーコンピューター" in q_lower):
                    matched_phases.append(p)
            if not matched_phases and any(kw in q_lower for kw in ["納品", "フェーズ", "軌道"]):
                matched_phases = self.phases_data.get("phases", [])

        # 5. Search YouTube & Community Knowledge
        tips = self.search_knowledge(question, top_k=2)

        # 6. Check for Production Meta
        production_meta = None
        if target_item_term:
            production_meta = self.get_production_meta(target_item_term)

        return {
            "query": question,
            "recipe_matches": recipe_matches,
            "matched_phases": matched_phases,
            "supply_chain_tree": supply_chain_tree,
            "comparison_table": comparison_table,
            "production_meta": production_meta,
            "tips": tips
        }


if __name__ == "__main__":
    engine = SatisfactoryRAG()
    
    test_queries = [
        "鉄板のレシピ教えて",
        "水ループが詰まってアルミニウム工場が止まる",
        "列車 信号の基本ルール"
    ]

    for q in test_queries:
        print(f"\n==========================================")
        print(f"❓ Query: {q}")
        print(f"==========================================")
        res = engine.query(q)
        
        if res["recipe_matches"]:
            print("📜 [確定レシピデータ]:")
            for term, data in res["recipe_matches"].items():
                for r in data["producing"][:2]:
                    print(engine.format_recipe_card(r))
                    print()
        
        if res["tips"]:
            print("🎥 [YouTube解説・攻略Tips]:")
            for tip in res["tips"]:
                print(f"  ▶ タイトル: {tip['video_title']}")
                print(f"    チャプター: {tip['chapter_title']}")
                print(f"    リンク: {tip['url']}")
                print(f"    要約/抜粋:\n    {tip['content'][:250]}...")
                print()
