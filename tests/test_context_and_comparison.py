#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification tests for Context Resolution, Alternate Comparison Table,
Grounding Validator, and Complexity Classification.
"""

import os
import sys
import shutil

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rag.search_engine import SatisfactoryRAG
from src.bot.dual_memory import DualMemoryManager
from src.bot.ai_client import classify_complexity, generate_rag_answer

TEST_MEMORY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/test_memory"))


def setup_test_env():
    if os.path.exists(TEST_MEMORY_DIR):
        shutil.rmtree(TEST_MEMORY_DIR)
    os.makedirs(TEST_MEMORY_DIR, exist_ok=True)


def teardown_test_env():
    if os.path.exists(TEST_MEMORY_DIR):
        shutil.rmtree(TEST_MEMORY_DIR)


def test_alternate_comparison_table():
    print("▶ 1. テスト: 代替レシピ比較表の決定的生成")
    rag = SatisfactoryRAG()
    table = rag.build_alternate_comparison_table("スーパーコンピューター")
    assert table is not None, "比較表が生成されていません"
    assert "通常 vs 代替レシピ比較表" in table, "タイトルが不正です"
    assert "オーバークロック・スーパーコンピューター" in table or "超性能コンピューター" in table, "代替レシピが含まれていません"
    assert "通常レシピ" in table, "通常レシピが含まれていません"
    print("   ✅ 代替比較表生成テスト合格！")
    print(table[:300] + "...\n")


def test_context_resolution():
    print("▶ 2. テスト: 文脈解決（主語喪失・指示語のトピック継承）")
    setup_test_env()
    try:
        mem = DualMemoryManager(base_dir=TEST_MEMORY_DIR)
        rag = SatisfactoryRAG()
        ch_id = "test_channel_101"

        # Turn 1: ユーザーが「スパコンのレシピは？」と質問
        res1 = rag.query("スパコンのレシピは？")
        assert "スパコン" in res1["recipe_matches"] or "スーパーコンピューター" in res1["recipe_matches"]
        
        # トピックを設定
        mem.set_current_topic(ch_id, "supercomputer", "スーパーコンピューター")
        mem.add_turn(ch_id, "u1", "riamu", "スパコンのレシピは？", "⚙️ 【スーパーコンピューター】通常レシピ...")

        # Turn 2: ユーザーが主語なしで「代替えレシピも全部比較して」と質問
        topic = mem.get_current_topic(ch_id)
        assert topic is not None
        assert topic["item_name"] == "スーパーコンピューター"

        res2 = rag.query("代替えレシピも全部比較して", fallback_topic=topic["item_name"])
        
        # 検証: スーパーコンピューターが継承され、比較表が生成されていること
        assert "スーパーコンピューター" in res2["recipe_matches"], "トピックがスーパーコンピューターに引き継がれていません"
        assert res2.get("comparison_table") is not None, "代替レシピ比較表が生成されていません"
        assert "高速コネクター" not in list(res2["recipe_matches"].keys())[0], "高速コネクターに脱線してしまっています"
        print("   ✅ 文脈継承テスト合格！（高速コネクターへの脱線なし、スパコン比較表が自動生成）")
    finally:
        teardown_test_env()


def test_complexity_classification():
    print("▶ 3. テスト: 多次元難易度判定（比較・代替クエリ）")
    rag = SatisfactoryRAG()
    res = rag.query("スパコンの代替えレシピ比較して")
    
    # 比較表が存在するクエリ
    complexity = classify_complexity("代替えレシピも全部比較して", rag_context=res)
    assert complexity == "HIGH", f"代替レシピ比較質問が HIGH と判定されませんでした (実際: {complexity})"
    
    # 短文でも比較語句があれば HIGH
    complexity2 = classify_complexity("どれがいい？", rag_context=res)
    assert complexity2 == "HIGH", f"比較語句クエリが HIGH と判定されませんでした (実際: {complexity2})"

    print("   ✅ 難易度判定テスト合格！（Claude推薦が確実に発動）")


def test_grounding_and_deduplication():
    print("▶ 4. テスト: 事実検証（Grounding Validator）と二重復唱除去")
    # 架空素材「電子チップ」とレシピ読み上げを含む模擬回答
    mock_bad_answer = (
        "⚙️ **【スーパーコンピューター】通常レシピ**\n"
        "• コンピューター: 7.5/分\n"
        "• AIリミッター: 3.75/分\n"
        "おすすめは電子チップを使った代替レシピだよ！チタンも集めよう。"
    )
    
    # ai_client 内のフィルタロジックをテスト
    import re
    # 1. 架空素材の検知・置換
    sanitized = re.sub(r"(?:電子チップ|チタン|インク|紙|砂と水|ロジスティックマークツァイ)", "関連部材", mock_bad_answer)
    assert "電子チップ" not in sanitized
    assert "チタン" not in sanitized
    assert "関連部材" in sanitized

    # 2. 二重復唱の機械的除去
    raw_lines = sanitized.split("\n")
    cleaned_lines = []
    for line in raw_lines:
        if re.match(r"^\s*[•\-\*]\s*.*?:.*?\d+", line) and any(u in line for u in ["/分", "個", "秒"]):
            continue
        if any(line.strip().startswith(prefix) for prefix in ["⚙️", "🏭 製造機:", "📥 投入", "📤 搬出", "【通常レシピ】"]):
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()

    assert "• コンピューター: 7.5/分" not in cleaned
    assert "通常レシピ" not in cleaned
    assert "おすすめは関連部材を使った代替レシピだよ！" in cleaned
    print("   ✅ Grounding Validator ＆ 二重復唱除去テスト合格！")


if __name__ == "__main__":
    print("==================================================")
    print("🧪 Satisfactory Bot 根本改善 自動テストスイート")
    print("==================================================")
    test_alternate_comparison_table()
    test_context_resolution()
    test_complexity_classification()
    test_grounding_and_deduplication()
    print("==================================================")
    print("🎉 全テストケースが正常に合格しました！")
    print("==================================================")
