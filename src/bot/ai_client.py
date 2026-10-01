#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Client & Dynamic Router for Satisfactory Discord Bot
- File-based prompt passing (100% bypasses Windows 8,191 char CLI limits)
- Fast AI (Local Qwen 14B) & Claude 3.7 Sonnet (Vision support)
- Anti-Repetition Loop Guard (prevents repeating previous turns)
- Human-like FICSIT Pioneer Persona & Meta-Query Handling
"""

import os
import sys
import subprocess
import json
import re
import tempfile
import time
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

# Import Production Calculator Engine
from src.rag.calculator import ProductionCalculator

load_dotenv()

# OpenAI Client Setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_openai_client = None
if OPENAI_API_KEY:
    try:
        import openai
        _openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"[!] Failed to initialize OpenAI client: {e}")

# Paths to existing bridges
CLAUDE_BRIDGE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../config/skills/claude-specialist/scripts/claude_bridge.js"))
LOCAL_BRIDGE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../config/skills/claude-specialist/scripts/local_bridge.js"))


import unicodedata

def run_autonomous_solver(question: str, rag_context: Optional[Dict[str, Any]] = None, current_topic: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Dict[str, float]]:
    """
    Autonomous Engineering Solver for Agentic Reasoning:
    - Normalizes full-width Japanese characters (e.g. ４８０ -> 480).
    - Extracts resource input rates, inheriting from previous topic context if pronoun is used.
    - Executes deterministic calculation tools to feed verified mathematical constants to the LLM.
    Returns: (calculation_summary_string, calculated_rates_dict)
    """
    # 1. NFKC normalization: converts全角「４８０」to半角「480」
    norm_q = unicodedata.normalize('NFKC', question)
    q_lower = norm_q.lower()
    results = []
    saved_rates = {}

    # Extract stored rates from topic memory if available
    memory_rates = (current_topic.get("resource_rates") or {}) if current_topic else {}

    # Deterministic recipe scaling for production-rate questions.
    target_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:個|/分|分)?', norm_q)
    target_rate = float(target_match.group(1)) if target_match else None
    if target_rate and "ニトロ" in q_lower and "ロケット燃料" in q_lower:
        scaled = ProductionCalculator.calculate_recipe_target("Recipe_Alternate_RocketFuel_Nitro_C", target_rate)
        inputs = "、".join(f"{k} {v}/分" for k, v in scaled["inputs_per_min"].items())
        outputs = "、".join(f"{k} {v}/分" for k, v in scaled["outputs_per_min"].items())
        return (f"🧮 **確定生産計算: ニトロ・ロケット燃料 {target_rate}/分**\n"
                f"投入: {inputs}\n搬出: {outputs}\n必要ブレンダー: {scaled['machines']}台", saved_rates)
    if target_rate and "イオン化燃料" in q_lower and any(x in q_lower for x in ["作る", "生産", "必要"]):
        scaled = ProductionCalculator.calculate_recipe_target("Recipe_IonizedFuel_C", target_rate)
        inputs = "、".join(f"{k} {v}/分" for k, v in scaled["inputs_per_min"].items())
        outputs = "、".join(f"{k} {v}/分" for k, v in scaled["outputs_per_min"].items())
        return (f"🧮 **確定生産計算: イオン化燃料 {target_rate}/分**\n"
                f"投入: {inputs}\n搬出: {outputs}\n必要製油所: {scaled['machines']}台", saved_rates)

    # 1. Fuel / Crude Oil / Power Plant Solver
    if any(kw in q_lower for kw in ["燃料", "原油", "希釈", "ターボ", "発電", "fuel", "oil"]):
        # Regex for numbers: e.g. "原油480", "480個", "480/分", "480から", "480"
        m = re.search(r'(?:原油|毎分|入力)?\s*(\d+(?:\.\d+)?)\s*(?:個|/分|分|から)?', norm_q)
        input_rate = None
        if m and m.group(1):
            try:
                val = float(m.group(1))
                if val >= 10: # Avoid capturing small numbers like tier 8 or phase 4
                    input_rate = val
            except ValueError:
                pass

        # Inherit from memory if user uses pronouns like "これを", "それを", "さっきの"
        if input_rate is None and any(p in q_lower for p in ["これ", "それ", "さっき", "前"]):
            input_rate = memory_rates.get("crude_oil")

        if input_rate is None:
            # Fallback to standard pure node 300.0
            input_rate = memory_rates.get("crude_oil", 300.0)

        saved_rates["crude_oil"] = input_rate

        # Calculate Standard Fuel vs Diluted Fuel vs Turbofuel
        std_calc = ProductionCalculator.calculate_fuel_power(input_rate, "standard")
        diluted_calc = ProductionCalculator.calculate_fuel_power(input_rate, "diluted_fuel")
        
        calc_str = (
            f"⚡ **【自律検算ツール: 原油 {input_rate}/分 からの発電シミュレーション結果】**\n"
            f"1. **通常燃料（直接精製）**: 燃料 `{std_calc['fuel_output']}/分` ➔ 燃料発電機 `{std_calc['generators']}台` ➔ 発電量 `{std_calc['total_power_mw']} MW` (純余剰: `{std_calc['net_power_mw']} MW`)\n"
            f"   - 必要施設: {std_calc['facilities'][0]['name']} `{std_calc['facilities'][0]['rate']}`\n"
            f"2. **希釈燃料コンボ（重油残渣 ➔ 希釈燃料）**: 燃料 `{diluted_calc['fuel_output']}/分` ➔ 燃料発電機 `{diluted_calc['generators']}台` ➔ 発電量 `{diluted_calc['total_power_mw']} MW` (純余剰: `{diluted_calc['net_power_mw']} MW`)\n"
            f"   - 必要施設: 精製機（重油残渣）`{diluted_calc['facilities'][0]['desc']}`、ブレンダー（希釈燃料）`{diluted_calc['facilities'][1]['desc']}`、水抽出機 `{diluted_calc['facilities'][2]['desc']}` (水消費: `{diluted_calc['water_input']}/分`)\n"
            f"   - **効率差**: 希釈燃料は通常精製の **ぴったり{diluted_calc['efficiency_multiplier']}** の電力を生成！"
        )
        if "ターボ" in q_lower:
            turbo_calc = ProductionCalculator.calculate_fuel_power(input_rate, "turbofuel")
            calc_str += (
                f"\n3. **希釈ターボ燃料**: ターボ燃料 `{turbo_calc['turbofuel_output']}/分` ➔ 燃料発電機 `{turbo_calc['generators']}台` ➔ 発電量 `{turbo_calc['total_power_mw']} MW` (要圧縮石炭 `{turbo_calc['compacted_coal_required']}/分`)"
            )
        results.append(calc_str)

    # 2. Aluminum Refining & Water-Loop Solver
    if any(kw in q_lower for kw in ["アルミ", "ボーキサイト", "スクラップ", "シリカ", "aluminum", "bauxite"]):
        m = re.search(r'(?:ボーキサイト|毎分|入力)?\s*(\d+(?:\.\d+)?)\s*(?:個|/分|分|から)?', norm_q)
        input_rate = None
        if m and m.group(1):
            try:
                val = float(m.group(1))
                if val >= 10:
                    input_rate = val
            except ValueError:
                pass

        if input_rate is None and any(p in q_lower for p in ["これ", "それ", "さっき", "前"]):
            input_rate = memory_rates.get("bauxite")

        if input_rate is None:
            input_rate = memory_rates.get("bauxite", 300.0)

        saved_rates["bauxite"] = input_rate

        std_alum = ProductionCalculator.calculate_aluminum_chain(input_rate, "standard")
        alt_alum = ProductionCalculator.calculate_aluminum_chain(input_rate, "alt_scrap")

        calc_str = (
            f"🏭 **【自律検算ツール: ボーキサイト {input_rate}/分 からのアルミ精製シミュレーション結果】**\n"
            f"1. **通常アルミ生産（水循環 + シリカ再利用）**:\n"
            f"   - スクラップ生産: `{std_alum['scrap_output']}/分`, インゴット生産: `{std_alum['ingot_output']}/分`\n"
            f"   - 水収支: 総必要水 `{std_alum['water_balance']['total_required']}/分`, 副産物回収水 `{std_alum['water_balance']['recycled_byproduct']}/分`, 新規補充水 `{std_alum['water_balance']['net_fresh_water_input']}/分` (回収率: `{std_alum['water_balance']['recycling_ratio']}`)\n"
            f"   - シリカ収支: 副産物シリカ `{std_alum['silica_balance']['produced_as_byproduct']}/分`, 鋳造炉必要量 `{std_alum['silica_balance']['needed_for_ingot']}/分` ➔ 外部追加必要シリカ: `{std_alum['silica_balance']['net_additional_silica_needed']}/分`\n"
            f"2. **代替電極スクラップ + 純アルミインゴット（シリカ完全不要コンボ）**:\n"
            f"   - スクラップ生産: `{alt_alum['scrap_output']}/分`, インゴット生産: `{alt_alum['ingot_output']}/分` (必要石油コークス: `{alt_alum['petroleum_coke_input']}/分`)\n"
            f"   - 特徴: シリカライン完全撤廃。原油の石油コークスで直結可能！"
        )
        results.append(calc_str)

    res_str = "\n\n".join(results) if results else None
    return res_str, saved_rates

COMPLEX_KEYWORDS = [
    "最適", "効率", "比較", "レイアウト", "自動化ライン", "工場設計",
    "トレードオフ", "ボトルネック", "フェーズ", "代替レシピの優先", "計算",
    "最大化", "循環", "副産物", "ウラン", "プルトニウム", "アルミ",
    "スパコン", "スーパーコンピューター", "コンピューター", "ティア", "tier", "進捗", "納品", "軌道エレベータ",
    "optimal", "layout", "maximize", "ratio", "design"
]

META_KEYWORDS = [
    "思考回路", "アプデ", "アップデート", "バージョン", "記憶", "メモリ",
    "覚えている", "覚えてる", "忘れた", "自己紹介", "だれ", "誰", "機能",
    "仕様", "仕組み", "二重記憶", "ログ", "チャット履歴", "感想", "定型文",
    "オウム返し", "bot", "ボット", "人工知能", "ai"
]


def classify_complexity(question: str, rag_context: Optional[Dict[str, Any]] = None, sticky_high: bool = False) -> str:
    """Classify query into 'HIGH' (Claude recommended) or 'STANDARD' (Fast AI)."""
    q_lower = question.lower()
    
    # Meta questions don't require Claude quota unless specifically requested
    if is_meta_query(question):
        return "STANDARD"

    # Sticky high: Maintain HIGH state for short follow-up questions in an ongoing consultation
    if sticky_high and len(question.strip()) <= 45:
        return "HIGH"

    # Comparison / Alternative recipes are structurally high complexity
    if rag_context and rag_context.get("comparison_table"):
        return "HIGH"

    compare_keywords = ["代替え", "代替", "比較", "どっち", "違い", "優先", "おすすめ", "オススメ", "どれが", "効率"]
    if any(kw in q_lower for kw in compare_keywords):
        return "HIGH"

    match_count = sum(1 for kw in COMPLEX_KEYWORDS if kw in q_lower)
    if match_count >= 1 or len(question) > 50 or "どう組む" in question or "進捗" in q_lower:
        return "HIGH"
    return "STANDARD"


def is_meta_query(question: str) -> bool:
    """Detect if the user is asking about the bot itself, updates, or memory."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in META_KEYWORDS)


def _run_bridge_with_file(bridge_script: str, prompt: str, extra_args: Optional[list] = None, timeout: int = 60) -> Tuple[int, str, str]:
    """Execute bridge script using a temporary UTF-8 file to bypass OS argument limits."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as tmp:
            tmp.write(prompt)
            tmp_path = tmp.name

        cmd = ["node", bridge_script, "--file", tmp_path]
        if extra_args:
            cmd.extend(extra_args)

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )
        return res.returncode, res.stdout, res.stderr
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def call_claude_sonnet(prompt: str, image_path: Optional[str] = None) -> Tuple[str, str]:
    """Invoke Claude via the bridge, returning (answer, actual model) including fallback."""
    extra = ["--model", "sonnet"]
    if image_path and os.path.exists(image_path):
        extra.extend(["--image", os.path.abspath(image_path)])

    try:
        ret, stdout, stderr = _run_bridge_with_file(CLAUDE_BRIDGE, prompt, extra_args=extra, timeout=75)
        if ret == 0 and stdout.strip():
            out = stdout.strip()
            out = re.sub(r"^\[claude_bridge\].*?\n", "", out)
            model_name = "Claude 3.7 Sonnet (Vision)" if image_path else "Claude 3.7 Sonnet"
            return out, model_name
        # Fallback to local AI if Claude bridge failed
        print(f"[!] Claude Bridge returned error ({stderr[:150]}). Falling back to Fast AI...")
        return call_fast_ai(prompt)
    except Exception as e:
        print(f"[!] Claude Bridge failed ({e}). Falling back to Fast AI...")
        return call_fast_ai(prompt)


def call_openai_mini(prompt: str, max_retries: int = 2, timeout_sec: float = 25.0) -> Optional[str]:
    """
    Invoke OpenAI GPT-4o-mini with high fidelity, strict timeouts, and retry fallback.
    Audit Recommendation #3: タイムアウト設定と障害時リトライ制御を完備
    """
    global _openai_client
    if not _openai_client:
        return None

    for attempt in range(1, max_retries + 1):
        try:
            start_time = time.time()
            response = _openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1000,
                timeout=timeout_sec
            )
            elapsed = time.time() - start_time
            if response.choices and response.choices[0].message.content:
                out = response.choices[0].message.content.strip()
                # 監査・実測用テレメトリログ
                # print(f"[OpenAI Telemetry] GPT-4o-mini succeeded in {elapsed:.2f}s (Tokens: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens})")
                return out
        except Exception as e:
            err_msg = str(e)
            print(f"[!] OpenAI GPT-4o-mini attempt {attempt}/{max_retries} failed ({err_msg[:120]})")
            if attempt < max_retries:
                time.sleep(1.0 * attempt)

    print("[!] OpenAI GPT-4o-mini exhausted retries. Safely falling back to secondary engine...")
    return None


def call_fast_ai(prompt: str) -> Tuple[str, str]:
    """Invoke GPT-4o-mini as primary fast engine, falling back to Local Qwen."""
    # 1. Primary: OpenAI GPT-4o-mini
    gpt_out = call_openai_mini(prompt)
    if gpt_out:
        return gpt_out, "GPT-4o-mini (OpenAI)"

    # 2. Fallback: Local Qwen 14B
    try:
        if os.path.exists(LOCAL_BRIDGE):
            ret, stdout, _ = _run_bridge_with_file(LOCAL_BRIDGE, prompt, timeout=50)
            if ret == 0 and stdout.strip():
                out = stdout.strip()
                out = re.sub(r"^\[local_bridge.*?\].*?\n", "", out)
                # Post-filter to block hallucinated words
                if not any(bad in out for bad in ["インク", "ロジスティックマークツァイ", "紙", "砂と水"]):
                    return out, "Local Qwen 14B"
    except Exception as e:
        print(f"[!] Local Fast AI error: {e}")

    return (
        "開拓お疲れ様！通信ログを確認したよ。工場のアドバイスや仕様について何でも聞いてね！",
        "Fallback"
    )


def generate_rag_answer(
    question: str, 
    rag_context: Dict[str, Any], 
    use_claude: bool, 
    image_path: Optional[str] = None, 
    history_context: Optional[str] = None,
    last_bot_response: Optional[str] = None,
    current_topic: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Build prompt with RAG context, Space Elevator Phases, conversation history, and invoke selected AI model.
    Includes Anti-Repetition Guard to prevent echoing previous answers.
    Returns: (answer_text, model_name)
    """
    is_meta = is_meta_query(question)
    unknown_item_markers = ["存在しない", "架空", "実在しない", "ないアイテム", "存在しないアイテム"]
    has_unknown_item_intent = any(marker in question for marker in unknown_item_markers)
    known_fuel_names = ["希釈燃料", "ターボ燃料", "ロケット燃料", "イオン化燃料"]
    unknown_fuel_compound = "燃料" in question and not any(
        name in question for name in known_fuel_names
    ) and len(question.split("燃料", 1)[0].strip()) > 0
    unknown_entity_terms = ["チタン", "未知合金", "架空素材", "素材X", "超合金", "チタン製"]
    has_unknown_entity = any(term in question for term in unknown_entity_terms)
    has_grounded_entity = bool(rag_context.get("recipe_matches") or rag_context.get("production_meta"))
    if (has_unknown_item_intent or unknown_fuel_compound or has_unknown_entity) and not has_grounded_entity:
        return (
            "⚠️ 確定レシピDBに該当するアイテム・素材・レシピがありません。\n"
            "別の素材名へ置き換えず、ゲーム内名称を確認してから再検索してください。",
            "Grounding Guard"
        )
    context_parts = []

    if is_meta:
        context_parts.append(
            "### 【あなた（Bot）自身の現在の仕様・思考回路・状態】\n"
            "- **二重記憶システム**: 直近30ターン分の会話を生ログ（短期記憶）として完全に記憶しています。30ターンを超えた古い会話は、自動的に要約されて長期記憶（Markdown/JSON）へ移行し、一定容量を超えないよう人間と同じ脳の記憶回路のように整理・保管されています。\n"
            "- **検索エンジン**: ゲーム内公式確定データベース（871レシピ、155アイテム、539設備、軌道エレベーター確定納品）と、YouTubeトップビルダーによる実証済み攻略Tips（秒数リンク付き）を組み合わせたハイブリッドRAGです。\n"
            "- **最高峰AI召喚システム**: 複雑な工場設計や最適化の相談時は、1日30回限定のClaude 3.7 Sonnetを召喚するか確認ボタンを出し、枠を温存しながら回答できます。\n"
            "- **受け答えの心得**: ユーザーが「感想は？」「記憶容量は？」「定型文なの？」と尋ねてきたら、工場の定型挨拶を繰り返さず、人間らしいウィットとユーモアを交えて自分の言葉で正直に答えてください。\n"
            "※注意: 「思考回路」を架空のゲーム内アイテムやレシピとして説明してはなりません。あなた自身の機能として人間らしく温かみを持って答えてください。"
        )
    else:
        # 1. Space Elevator / Phase Deliveries
        if rag_context.get("matched_phases"):
            context_parts.append("### 【軌道エレベーター各フェーズ確定納品情報 (公式データ)】")
            for p in rag_context["matched_phases"]:
                req_str = ", ".join([f"{r['item']} ({r['amount']}個)" for r in p["requirements"]])
                context_parts.append(f"- {p['name']} [解放目標: {p['target_tiers']}]: 納品物=[{req_str}]")

        # 2. Recipes
        if rag_context.get("recipe_matches"):
            context_parts.append("### 【公式確定レシピデータ (100%正確)】")
            for term, data in rag_context["recipe_matches"].items():
                for r in data["producing"][:3]:
                    ing_str = ", ".join([f"{i['name_ja']} {i['rate_per_min']}/分 ({i['amount']}個)" for i in r["ingredients"]])
                    prod_str = ", ".join([f"{p['name_ja']} {p['rate_per_min']}/分 ({p['amount']}個)" for p in r["products"]])
                    machines = "/".join(r.get("produced_in_names", []))
                    context_parts.append(f"- レシピ「{r['name_ja']}」: 製造機={machines}, 投入=[{ing_str}] -> 搬出=[{prod_str}]")

    # 3. Conversation History
    if history_context:
        context_parts.append(f"### 【これまでの会話ログ（直近の文脈・流れ）】\n{history_context}\n")

    # 4. Image Note
    if image_path:
        context_parts.append(f"### 【添付画像（プレイヤーの工場現場スクリーンショット）】\n画像ファイル: `{image_path}`\n※この画像を精査し、機械のランプ状態、配管の高低差・逆流、コンベアの向き、列車信号の配置などを視覚的に読み取って診断してください。")

    # 5. Production Meta Knowledge (Verified Game Metas)
    if not is_meta and rag_context.get("production_meta"):
        m = rag_context["production_meta"]
        context_parts.append(
            f"\n### 【FICSIT公式 効率メタ情報 (確定検証済み)】\n"
            f"- 対象品目: **{m['target_item']}**\n"
            f"- 最高効率構成: **{m['best_recipe']}** ({m['efficiency_multiplier']})\n"
            f"- 原料比較レート: {m['raw_ratio']}\n"
            f"- 詳細解説: {m['summary']}\n"
        )

    # 6. YouTube Tips (ゲーム内質問のみ)
    if not is_meta and rag_context.get("tips"):
        context_parts.append("\n### 【YouTube検証済み攻略Tips (該当秒数リンク付き)】")

    # 7. Autonomous Engineering Solver (Agentic Calculation Tools)
    autonomous_calc_res = None
    calculation_intent_keywords = [
        "原油", "発電", "発電機", "何台", "電力", "変える", "変換",
        "ライン", "必要", "oil", "power", "generator", "per minute"
    ]
    has_calculation_intent = any(kw in question.lower() for kw in calculation_intent_keywords)
    has_grounded_target = bool(rag_context.get("recipe_matches") or rag_context.get("production_meta"))
    # Recipe lookups alone must not inherit an old rate and emit an unrelated
    # power simulation. Pronoun follow-ups remain eligible through current_topic.
    if not is_meta and has_calculation_intent and (has_grounded_target or current_topic):
        autonomous_calc_res, calculated_rates = run_autonomous_solver(question, rag_context, current_topic)
        rag_context["calculated_rates"] = calculated_rates
        if autonomous_calc_res:
            context_parts.append(
                f"\n### 【自律検算ツール（Deterministic Engineering Solver）の確定計算結果】\n"
                f"{autonomous_calc_res}\n"
                f"※この数値はゲーム内公式定数に基づく厳密な線形計算結果です。AIの推測や概算ではなく、100%確定した物理的事実として思考・アドバイスの根拠にしてください。"
            )

    full_context_str = "\n".join(context_parts)

    # Format Deterministic Cards & Trees (Guaranteed 100% Accuracy)
    card_sections = []

    # 0. Autonomous Calculation Result Card (if solved)
    if autonomous_calc_res:
        card_sections.append(autonomous_calc_res)

    # 1. Supply Chain Tree (if requested)
    if rag_context.get("supply_chain_tree"):
        card_sections.append(rag_context["supply_chain_tree"])

    # 2. Alternate Recipe Comparison Table (Deterministic 100% Guaranteed)
    has_comparison_table = bool(rag_context.get("comparison_table"))
    if has_comparison_table:
        card_sections.append(rag_context["comparison_table"])

    # 3. Recipe Cards (if asking for recipe/crafting and NOT already showing comparison table)
    elif rag_context.get("recipe_matches") and any(kw in question.lower() for kw in ["レシピ", "作り方", "材料", "素材", "生産", "毎分"]):
        seen_recipe_ids = set()
        # Find exact or longest matching term in query
        all_matched_terms = list(rag_context["recipe_matches"].keys())
        # Sort terms by length descending so "スーパーコンピューター" is processed before "コンピューター"
        all_matched_terms.sort(key=lambda t: len(t), reverse=True)
        primary_terms = [t for t in all_matched_terms if t in question.lower()][:1] or all_matched_terms[:1]

        for term in primary_terms:
            data = rag_context["recipe_matches"][term]
            prods = data.get("producing", [])
            default_recs = [r for r in prods if not r.get("is_alternate")]
            alt_recs = [r for r in prods if r.get("is_alternate")]
            
            # Show primary default recipe card (deduplicated)
            for r in default_recs[:1]:
                if r["id"] in seen_recipe_ids:
                    continue
                seen_recipe_ids.add(r["id"])

                machines = " / ".join(r.get("produced_in_names", [])) or "製作機等"
                in_lines = [f"  • {i['name_ja']}: `{i['rate_per_min']}/分` (1回あたり {i['amount']}個)" for i in r["ingredients"]]
                out_lines = [f"  • **{p['name_ja']}**: `{p['rate_per_min']}/分` (1回あたり {p['amount']}個)" for p in r["products"]]
                
                card_text = (
                    f"⚙️ **【{r['name_ja']}】通常レシピ**\n"
                    f"🏭 **製造機**: `{machines}` (製造サイクル: {r.get('duration_seconds', 0)}秒)\n"
                    f"📥 **投入 (材料/分)**:\n" + "\n".join(in_lines) + "\n"
                    f"📤 **搬出 (完成/分)**:\n" + "\n".join(out_lines)
                )
                if alt_recs:
                    alt_names = "、".join([f"「{a['name_ja']}」" for a in alt_recs[:3]])
                    card_text += f"\n💡 *代替レシピ: {alt_names} も存在します。*"
                card_sections.append(card_text)

    # 4. Space Elevator Phases (STRICT: only if phase/delivery is explicitly requested)
    if not is_meta and rag_context.get("matched_phases"):
        phase_blocks = []
        for p in rag_context["matched_phases"]:
            req_list = [f"• **{r['item']}**: `{r['amount']}個` ({r.get('rate_info', '製造機で生産')})" for r in p["requirements"]]
            phase_blocks.append(f"📦 **【{p['name']}】** (解放: {p['target_tiers']})\n" + "\n".join(req_list))
        card_sections.append("\n\n".join(phase_blocks))

    official_cards_header = "\n\n".join(card_sections) + ("\n\n---\n" if card_sections else "")

    # Conversational instruction: No repetitive greetings if dialogue is ongoing
    greeting_instruction = (
        "- 【最重要】会話が継続中のため、「開拓お疲れ様！」などの冒頭の挨拶は絶対に言わないこと。直ちに相手の発言へのリアクションや本題に入ること。\n"
        if history_context and len(history_context) > 50 else
        "- 最初の一言は親しみやすく挨拶してもよいが、同じセリフを毎回答えないこと。\n"
    )

    meta_instruction = ""
    if not is_meta and rag_context.get("production_meta"):
        m = rag_context["production_meta"]
        meta_instruction = (
            f"- 【効率・推奨レシピの絶対遵守ルール】対象品目（{m['target_item']}）のゲーム内最高効率構成は「{m['best_recipe']}」（{m['efficiency_multiplier']}）です。\n"
            f"  原料換算レート: {m['raw_ratio']}\n"
            f"  プレイヤーから「一番効率いいのは？」「どっちがいい？」と聞かれた場合、必ずこの確定メタ知識に基づいて回答してください。単一工程の単純さだけで「原油直結が最高」等と嘘をつくことは厳禁です。\n"
        )

    system_instruction = (
        "あなたはSatisfactoryの現場を熟知したベテラン開拓者仲間（FICSIT技術顧問）です。\n"
        "マニュアル棒読みのロボットではなく、隣でモニターを見ながら気さくに話す頼れる同僚として回答してください。\n\n"
        "【思考プロセス（Reasoning Instructions）】\n"
        "- まず裏で思考（Chain-of-Thought）を行い、自律検算ツールの確定数値（発電機台数、必要精製機、水収支、副産物）と工場の敷地・配管ボトルネックを綿密に分析してください。\n"
        "- その上で、プレイヤーに対しては数値の単なる再読み上げではなく、ベテラン開拓者としての実践的な洞察・アドバイス・注意点（パイプの揚程・逆流対策、水循環の詰まり防止、オーバークロック等）を力強く語ってください。\n\n"
        "【会話テンポとスタイルの絶対遵守ルール】\n"
        f"{greeting_instruction}"
        f"{meta_instruction}"
        "- 末尾に「何か特別な問題があれば〜一緒に確認してみよう」などの判子を押したような決まり文句を書くことは厳禁。自然な相棒として簡潔に会話を締めること。\n"
        "- レシピや比較表に関する質問の場合、100%正確な確定カード/比較表が画面上部に既に表示されているため、数値の文章読み上げ（「〜個を〜個出す」「通常レシピは〜」など）は絶対に行わないこと。工場の立地・ボトルネック・プレイヤーの状況に応じた実践的な選び方やアドバイスのみを2〜3行で簡潔に添えること。\n"
        "- ユーザーからのツッコミやメタ質問には、ユーモアと人間味を持って自然に返すこと。\n"
        "- ゲーム内に実在しない架空のアイテム（電子チップ、チタン、インク、紙など）は絶対に言及しないこと。"
    )

    prompt = f"{system_instruction}\n\n【提供された資料・過去の会話ログ】\n{full_context_str}\n\n【最新のプレイヤー発言】\n{question}"

    # Execution & Anti-Repetition Loop Guard
    for attempt in range(2):
        if use_claude:
            raw_answer, model_name = call_claude_sonnet(prompt, image_path=image_path)
        else:
            raw_answer, model_name = call_fast_ai(prompt)

        # Post-filter 0: Clean Output Guard (Strip any leaky <think> or 'Thinking:' blocks)
        raw_answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()
        raw_answer = re.sub(r"^(?:思考|Thinking):\s*.*?\n\n", "", raw_answer, flags=re.DOTALL).strip()

        # Post-filter 1: Strip robotic trailing phrases
        raw_answer = re.sub(r"何か特別な問題があれば.*?一緒に確認してみよう[。！]?", "", raw_answer).strip()
        raw_answer = re.sub(r"一緒に確認してみよう[。！]?", "", raw_answer).strip()

        # Post-filter 2: Grounding Validator (Sanitize hallucinated fictional items)
        fictional_items_pattern = r"(?:電子チップ|チタン|インク|紙|砂と水|ロジスティックマークツァイ|関連部材製)"
        if re.search(fictional_items_pattern, raw_answer):
            raw_answer = (
                "⚠️ 回答に確定レシピDBで確認できない素材名が含まれていたため、回答を止めました。\n"
                "ゲーム内の正式名称を確認して再質問してください。"
            )

        # Post-filter 3: Mechanical Deduplication (Strip echoing recipe card lines)
        if official_cards_header:
            # Strip lines that mimic recipe cards like "• item: rate/min" or "投入:" or "搬出:"
            raw_lines = raw_answer.split("\n")
            cleaned_lines = []
            for line in raw_lines:
                # Remove card bullet lines if they contain numbers and colons
                if re.match(r"^\s*[•\-\*]\s*.*?:.*?\d+", line) and any(u in line for u in ["/分", "個", "秒"]):
                    continue
                if any(line.strip().startswith(prefix) for prefix in ["⚙️", "🏭 製造機:", "📥 投入", "📤 搬出", "【通常レシピ】"]):
                    continue
                cleaned_lines.append(line)
            raw_answer = "\n".join(cleaned_lines).strip()

        # Check if response repeated the exact last bot response
        if last_bot_response and raw_answer.strip() == last_bot_response.strip() and attempt == 0:
            print("[!] Detected repetitive answer loop. Adding strict diversity constraint and retrying...")
            prompt += "\n\n※直前の回答と全く同じ定型文を出力することは厳禁です。相手の最新の発言に直接答えてください。"
            continue
        break

    final_answer = official_cards_header + raw_answer if official_cards_header else raw_answer
    return final_answer, model_name

