#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Satisfactory v1.0 Discord Assistant Bot (Interactive Summoning Edition)
Features:
- FICSIT Specialist Advisory Team personality
- Interactive Summoning Confirmation for Claude 3.7 Sonnet ("残り○回ですが使いますか？")
- Fallback to Standard Team when "いいえ" is selected (conserves Claude quota)
- Hybrid RAG (Official Game DB + YouTube timestamped Tips)
- Slash Commands: /ask, /recipe, /troubleshoot, /limit
- Natural Chat Support (Mentions, Replies, Dedicated Channels)
"""

import os
import sys
import asyncio
import subprocess
from typing import Optional, Dict, Any

# Force UTF-8 console output with safe replace fallback
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import discord
from discord import app_commands
from discord.ext import commands
import logging

# Configure Logging to both stdout and bot.log
log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../bot.log"))
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8")
    ]
)

# Import custom modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.rag.search_engine import SatisfactoryRAG
from src.bot.usage_tracker import UsageTracker, CLAUDE_DAILY_LIMIT
from src.bot.ai_client import classify_complexity, generate_rag_answer
from src.bot.dual_memory import DualMemoryManager

# Initialize RAG, Tracker & Human-like Dual Memory (Short-term 30 + Long-term Rolling)
rag_engine = SatisfactoryRAG()
tracker = UsageTracker(limit=CLAUDE_DAILY_LIMIT)
dual_memory = DualMemoryManager()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ==========================================
# 最高峰AI 召喚確認ビュー (インタラクティブボタン・画像対応)
# ==========================================
class ClaudeConfirmationView(discord.ui.View):
    def __init__(self, author: discord.User, channel_id: str, question: str, rag_result: Dict[str, Any], image_path: Optional[str] = None, timeout: float = 90.0):
        super().__init__(timeout=timeout)
        self.author = author
        self.channel_id = str(channel_id)
        self.question = question
        self.rag_result = rag_result
        self.image_path = image_path
        self.remaining = tracker.daily_limit - tracker.data.get("claude_used", 0)

        # ボタンのラベルに残枠数を動的に反映
        action_name = "画像診断で召喚" if image_path else "最高峰AIを召喚"
        self.btn_summon.label = f"はい、{action_name} (残り{self.remaining}回)"
        self._processing = False

    @discord.ui.button(label="はい、最高峰AIを召喚", style=discord.ButtonStyle.success, emoji="🧠")
    async def btn_summon(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ 質問者本人のみ選択できます。", ephemeral=True)
            return

        if self._processing:
            await interaction.response.send_message("⚠️ 既に処理を受け付けています。少々お待ちください。", ephemeral=True)
            return
        self._processing = True

        for child in self.children:
            child.disabled = True
        
        status_msg = "🧠 **最高峰AI (Claude 3.7 Sonnet Vision) が工場スクリーンショットと過去の文脈を深層解析中...**" if self.image_path else "🧠 **最高峰AI (Claude 3.7 Sonnet) を召喚中... これまでの会話ログを踏まえて深層解析しています**"
        await interaction.response.edit_message(content=status_msg, embed=None, view=self)

        try:
            # 過去の二重記憶（長期確定事実＋ナラティブ＋短期ログ）を取得
            history_context = dual_memory.format_prompt_memory(self.channel_id, short_term_limit=20)
            last_bot_response = dual_memory.get_last_bot_response(self.channel_id)
            current_topic = dual_memory.get_current_topic(self.channel_id)

            # Claude推論実行（asyncio.to_thread で非同期化）
            answer_text, model_name = await asyncio.to_thread(
                generate_rag_answer,
                self.question, 
                self.rag_result, 
                use_claude=True, 
                image_path=self.image_path, 
                history_context=history_context,
                last_bot_response=last_bot_response,
                current_topic=current_topic
            )
            _, remaining = tracker.record_usage("claude", str(self.author.id), self.author.display_name)
            pbar = tracker.get_progress_bar(8)

            # 二重記憶にターンを記録 & 資源レート保存
            dual_memory.add_turn(self.channel_id, str(self.author.id), self.author.display_name, self.question, answer_text)
            calculated_rates = self.rag_result.get("calculated_rates")
            if calculated_rates and current_topic:
                dual_memory.set_current_topic(
                    self.channel_id,
                    current_topic.get("item_id", "Unknown"),
                    current_topic.get("item_name", "Unknown"),
                    resource_rates=calculated_rates
                )

            embed = discord.Embed(
                title="🏭 FICSIT 工場技術顧問団 (最高峰推論モード)",
                description=answer_text[:4000],
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"🧠 {model_name} | 本日Claude残り: {remaining}/{tracker.daily_limit}回 [{pbar}]")

            try:
                await interaction.message.edit(content=None, embed=embed, view=None)
            except Exception:
                await interaction.channel.send(embed=embed)
        finally:
            if self.image_path and os.path.exists(self.image_path):
                try: os.remove(self.image_path)
                except Exception: pass

    @discord.ui.button(label="いいえ、通常チームで回答 (枠温存)", style=discord.ButtonStyle.secondary, emoji="🛠️")
    async def btn_standard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ 質問者本人のみ選択できます。", ephemeral=True)
            return

        if self._processing:
            await interaction.response.send_message("⚠️ 既に処理を受け付けています。少々お待ちください。", ephemeral=True)
            return
        self._processing = True

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🛠️ **通常返答チームがこれまでの工場の歩みを踏まえて回答を生成しています...**",
            embed=None,
            view=self
        )

        try:
            history_context = dual_memory.format_prompt_memory(self.channel_id, short_term_limit=20)
            last_bot_response = dual_memory.get_last_bot_response(self.channel_id)
            current_topic = dual_memory.get_current_topic(self.channel_id)

            answer_text, model_name = await asyncio.to_thread(
                generate_rag_answer,
                self.question, 
                self.rag_result, 
                use_claude=False, 
                image_path=self.image_path, 
                history_context=history_context,
                last_bot_response=last_bot_response,
                current_topic=current_topic
            )
            _, remaining = tracker.record_usage("gemini", str(self.author.id), self.author.display_name)
            pbar = tracker.get_progress_bar(8)

            # 二重記憶にターンを記録 & 資源レート保存
            dual_memory.add_turn(self.channel_id, str(self.author.id), self.author.display_name, self.question, answer_text)
            calculated_rates = self.rag_result.get("calculated_rates")
            if calculated_rates and current_topic:
                dual_memory.set_current_topic(
                    self.channel_id,
                    current_topic.get("item_id", "Unknown"),
                    current_topic.get("item_name", "Unknown"),
                    resource_rates=calculated_rates
                )

            embed = discord.Embed(
                title="🏭 FICSIT 工場技術顧問団 (通常解析チーム)",
                description=answer_text[:4000],
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"🛠️ 通常チーム [{model_name}] | 🧠 Claude残り: {remaining}/{tracker.daily_limit}回 [{pbar}]")

            try:
                await interaction.message.edit(content=None, embed=embed, view=None)
            except Exception:
                await interaction.channel.send(embed=embed)
        finally:
            if self.image_path and os.path.exists(self.image_path):
                try: os.remove(self.image_path)
                except Exception: pass

    async def on_timeout(self):
        # タイムアウトした場合は自動的にボタンを無効化
        for child in self.children:
            child.disabled = True
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


@bot.event
async def on_ready():
    print("==================================================")
    print(f"🤖 Satisfactory Bot logged in as: {bot.user} (ID: {bot.user.id})")
    print(f"🎯 Daily Claude Quota: {tracker.daily_limit} shared queries")
    print("==================================================")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"[!] Failed to sync slash commands: {e}")


# ==========================================
# /ask コマンド (画像添付・召喚確認付き)
# ==========================================
@bot.tree.command(name="ask", description="Satisfactoryの攻略や工場設計について質問します（画像添付対応）")
@app_commands.describe(
    question="質問内容（例: 重モジュラーフレームの最適代替レシピ、アルミ水ループの止め方）",
    image="工場のスクリーンショット画像（任意）"
)
async def ask_command(interaction: discord.Interaction, question: str, image: Optional[discord.Attachment] = None):
    image_path = None
    if image and image.content_type and any(image.content_type.startswith(t) for t in ["image/png", "image/jpeg", "image/webp"]):
        os.makedirs("temp_images", exist_ok=True)
        image_path = f"temp_images/{interaction.id}_{image.filename}"
        await image.save(image_path)

    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)
    username = interaction.user.display_name

    current_topic = dual_memory.get_current_topic(channel_id)
    fallback_item = current_topic.get("item_name") if current_topic else None

    rag_result = rag_engine.query(question, fallback_topic=fallback_item)
    if rag_result.get("recipe_matches"):
        top_term = list(rag_result["recipe_matches"].keys())[0]
        matched_items = rag_result["recipe_matches"][top_term].get("matched_items", [])
        if matched_items:
            dual_memory.set_current_topic(channel_id, matched_items[0]["id"], matched_items[0]["name_ja"])
        else:
            dual_memory.set_current_topic(channel_id, top_term, top_term)

    complexity = "HIGH" if image_path else classify_complexity(question, rag_context=rag_result)
    can_use_claude = tracker.can_use_claude()

    # 高度な設計相談または画像診断で、かつClaude枠がある場合 -> 選択肢を表示！
    if complexity == "HIGH" and can_use_claude:
        remaining = tracker.daily_limit - tracker.data.get("claude_used", 0)
        pbar = tracker.get_progress_bar(8)

        reason_text = "📸 工場現場のスクリーンショット画像が添付されています。\n機械のランプや配管・信号の配置を視覚的に解析するため、" if image_path else "⚠️ この相談はこれまでの工場の歩みや複数のレシピ比較・最適化など、高度な推論を要します。\n"

        embed_confirm = discord.Embed(
            title="🏭 FICSIT 工場技術顧問団からの確認",
            description=(
                f"**質問**: 「{question[:120]}」\n\n"
                f"{reason_text}"
                f"**最高峰AI（Claude 3.7 Sonnet Vision）** を召喚して画像診断・深層設計を行いますか？\n\n"
                f"📊 **本日残り利用回数**: **`{remaining} / {tracker.daily_limit} 回`** `[{pbar}]`"
            ),
            color=discord.Color.orange()
        )
        view = ClaudeConfirmationView(author=interaction.user, channel_id=channel_id, question=question, rag_result=rag_result, image_path=image_path)
        await interaction.response.send_message(embed=embed_confirm, view=view)
        view.message = await interaction.original_response()
        return

    # 通常の質問 または Claude上限到達時は通常チームが直接回答
    await interaction.response.defer(thinking=True)
    try:
        history_context = dual_memory.format_prompt_memory(channel_id, short_term_limit=20)
        last_bot_response = dual_memory.get_last_bot_response(channel_id)
        answer_text, model_name = await asyncio.to_thread(
            generate_rag_answer,
            question, 
            rag_result, 
            use_claude=False, 
            image_path=image_path, 
            history_context=history_context,
            last_bot_response=last_bot_response,
            current_topic=current_topic
        )
        _, remaining = tracker.record_usage("gemini", user_id, username)
        pbar = tracker.get_progress_bar(8)

        # 二重記憶にターンを記録
        dual_memory.add_turn(channel_id, user_id, username, question, answer_text)

        embed = discord.Embed(
            title="🏭 FICSIT 工場技術顧問団 (通常解析チーム)",
            description=answer_text[:4000],
            color=discord.Color.blue()
        )
        if complexity == "HIGH":
            embed.set_footer(text=f"🛠️ 通常チーム (※本日Claude上限到達) | 🧠 Claude残り: 0/{tracker.daily_limit}回 [{pbar}]")
        else:
            embed.set_footer(text=f"🛠️ 通常チーム (無制限) | 🧠 Claude残り: {remaining}/{tracker.daily_limit}回 [{pbar}]")

        await interaction.followup.send(embed=embed)
    finally:
        if image_path and os.path.exists(image_path):
            try: os.remove(image_path)
            except Exception: pass


# ==========================================
# /recipe コマンド (公式DB直結 / 100%正確 / $0)
# ==========================================
@bot.tree.command(name="recipe", description="指定アイテムの公式レシピ（通常・代替・生産レート）を照会します")
@app_commands.describe(item="アイテム名（例: 鉄板, 強化鉄板, 高密度鋼管, 鉄インゴット）")
async def recipe_command(interaction: discord.Interaction, item: str):
    await interaction.response.defer()
    tracker.record_usage("db", str(interaction.user.id), interaction.user.display_name)

    res = rag_engine.find_recipes_for_item(item)
    matched = res.get("matched_items", [])
    producing = res.get("producing", [])

    if not producing:
        await interaction.followup.send(f"⚠️ アイテム `{item}` を生産するレシピが見つかりませんでした。別の名称でお試しください。")
        return

    primary_item = matched[0] if matched else {"name_ja": item, "name_en": ""}
    embed = discord.Embed(
        title=f"📜 レシピ照会: {primary_item.get('name_ja')} ({primary_item.get('name_en')})",
        description=f"ゲーム内公式データ (v1.0) より {len(producing)} 件のレシピが見つかりました。",
        color=discord.Color.green()
    )

    for r in producing[:6]:
        alt_str = "【代替】" if r.get("is_alternate") else "【通常】"
        machines = "/".join(r.get("produced_in_names", []))
        
        in_list = [f"• {i['name_ja']}: `{i['rate_per_min']}/分`" for i in r["ingredients"]]
        out_list = [f"• {p['name_ja']}: `{p['rate_per_min']}/分`" for p in r["products"]]

        field_val = (
            f"**製造機**: `{machines}` (所要 {r['duration_seconds']}s)\n"
            f"**投入**: {', '.join(in_list)}\n"
            f"**搬出**: {', '.join(out_list)}"
        )
        embed.add_field(name=f"{alt_str} {r['name_ja']}", value=field_val, inline=False)

    remaining = tracker.daily_limit - tracker.data.get("claude_used", 0)
    pbar = tracker.get_progress_bar(8)
    embed.set_footer(text=f"⚡ 公式ゲーム内DB直結 (無制限) | 🧠 Claude残り: {remaining}/{tracker.daily_limit}回 [{pbar}]")
    await interaction.followup.send(embed=embed)


# ==========================================
# /troubleshoot コマンド (YouTube秒数リンク直結)
# ==========================================
@bot.tree.command(name="troubleshoot", description="パイプ詰まり、水ループ、列車信号などの動画解説Tipsを検索します")
@app_commands.describe(problem="トラブル内容（例: 水ループ, パイプ 詰まり, 列車 信号）")
async def troubleshoot_command(interaction: discord.Interaction, problem: str):
    await interaction.response.defer()
    tracker.record_usage("db", str(interaction.user.id), interaction.user.display_name)

    tips = rag_engine.search_knowledge(problem, top_k=3)
    if not tips:
        await interaction.followup.send(f"⚠️ 「{problem}」に関連する検証済みTipsが見つかりませんでした。別のキーワードでお試しください。")
        return

    embed = discord.Embed(
        title=f"🔧 トラブルシューティング解説: {problem}",
        description="YouTubeのトップビルダーによる解説（該当秒数直結リンク付き）です。",
        color=discord.Color.orange()
    )

    for i, t in enumerate(tips):
        v1_badge = "✅ v1.0検証済" if t.get("is_v1_0") else "⚠️ 旧版"
        field_val = (
            f"**動画**: [{t['video_title']}]({t['url']})\n"
            f"**該当チャプター**: `{t['chapter_title']}` ({v1_badge})\n"
            f"**解説抜粋**:\n{t['content'][:220]}..."
        )
        embed.add_field(name=f"💡 解決Tips #{i+1}（▶ [該当箇所を再生]({t['url']})）", value=field_val, inline=False)

    remaining = tracker.daily_limit - tracker.data.get("claude_used", 0)
    pbar = tracker.get_progress_bar(8)
    embed.set_footer(text=f"🎥 YouTube検証済みTips (無制限) | 🧠 Claude残り: {remaining}/{tracker.daily_limit}回 [{pbar}]")
    await interaction.followup.send(embed=embed)


# ==========================================
# /limit コマンド (残枠・上限ステータス確認)
# ==========================================
@bot.tree.command(name="limit", description="最高峰AI（Claude 3.7 Sonnet）の本日残り利用回数と上限を確認します")
async def limit_command(interaction: discord.Interaction):
    status = tracker.get_status_embed_data()

    embed = discord.Embed(
        title="📊 Satisfactory Bot 利用リミット状況",
        description=f"**日付**: `{status['date']}` (毎朝0時に自動リセット)",
        color=discord.Color.teal()
    )

    quota_display = (
        f"**本日残り回数**: **`{status['claude_remaining']} / {status['claude_limit']} 回`**\n"
        f"進捗: `[{status['progress_bar']}]` ({status['claude_used']}回使用済み)"
    )
    embed.add_field(name="🧠 最高峰AI (Claude 3.7 Sonnet)", value=quota_display, inline=False)

    other_display = (
        f"• **公式レシピ検索 (DB)**: `無制限` (本日 {status['db_used']} 回利用)\n"
        f"• **標準AI / YouTube Tips**: `無制限` (本日 {status['gemini_used']} 回利用)"
    )
    embed.add_field(name="⚡ その他機能（完全使い放題）", value=other_display, inline=False)

    users_display = status["users_list"]
    if len(users_display) > 1000:
        users_display = users_display[:980] + "\n...他"
    embed.add_field(name="👥 本日のメンバー別利用内訳", value=users_display, inline=False)

    embed.set_footer(text="※Claude枠が0になっても、高速標準AIとDB検索は無制限で使い続けられます。")
    await interaction.response.send_message(embed=embed)


# ==========================================
# /memory コマンド (Botが記憶している工場の現状と歩みを確認)
# ==========================================
@bot.tree.command(name="memory", description="Botが記憶している現在の工場の歩み（長期記憶・採用レシピ・工場一覧）を確認します")
async def memory_command(interaction: discord.Interaction):
    channel_id = str(interaction.channel_id)
    facts = dual_memory.get_facts(channel_id)
    narrative = dual_memory.get_long_term_narrative(channel_id)
    short_items = dual_memory.get_short_term(channel_id)

    embed = discord.Embed(
        title="🧠 FICSIT 工場記憶データバンク",
        description=f"チャンネル固有の「二重記憶システム」に保存されている記録です。",
        color=discord.Color.purple()
    )

    facts_text = (
        f"• **推定進行状況**: `Tier {facts.get('tier', 1)}`\n"
        f"• **採用代替レシピ**: {', '.join(facts['alternate_recipes_adopted']) if facts.get('alternate_recipes_adopted') else '記録なし'}\n"
        f"• **建設済み工場**: {len(facts.get('factories', []))} 件\n"
        f"• **直近の短期ログ**: `{len(short_items)} / 30 ターン`"
    )
    embed.add_field(name="📊 長期確定事実 (Facts)", value=facts_text, inline=False)

    narrative_snippet = narrative[:800] if narrative else "まだ長期記憶はありません。"
    embed.add_field(name="📜 工場の歩み・歴史 (Long-Term Narrative)", value=narrative_snippet, inline=False)

    embed.set_footer(text="※30ターンを超えた会話は、自動的に要約されて長期記憶へ固定化されます。")
    await interaction.response.send_message(embed=embed)


# ==========================================
# /reset コマンド (会話記憶のリセット)
# ==========================================
@bot.tree.command(name="reset", description="このチャンネルの会話履歴（記憶）をリセットし、新しい相談を始めます")
async def reset_command(interaction: discord.Interaction):
    channel_id = str(interaction.channel_id)
    res = dual_memory.clear(channel_id)
    embed = discord.Embed(
        title="🧹 工場記憶バンクをリセットしました",
        description=f"このチャンネルの短期ログおよび長期記憶を初期化しました。\n新しい工場設計や別のトピックについてお気軽に話しかけてください！",
        color=discord.Color.light_grey()
    )
    await interaction.response.send_message(embed=embed)


# ==========================================
# 自然言語チャット対応 (メンション・リプライ・Botチャンネル)
# ==========================================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    is_mentioned = bot.user in message.mentions
    is_reply_to_bot = (
        message.reference and 
        message.reference.resolved and 
        isinstance(message.reference.resolved, discord.Message) and 
        message.reference.resolved.author.id == bot.user.id
    )
    ch_name = getattr(message.channel, "name", "").lower()
    is_bot_channel = any(kw in ch_name for kw in ["bot", "質問", "攻略", "satisfactory", "factory"])

    if not (is_mentioned or is_reply_to_bot or is_bot_channel):
        return

    clean_content = message.content
    if bot.user:
        clean_content = clean_content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

    if not clean_content and not message.attachments:
        return

    channel_id = str(message.channel.id)
    user_id = str(message.author.id)
    username = message.author.display_name

    # リセットのテキストコマンド対応
    if clean_content.lower() in ["リセット", "reset", "記憶リセット", "会話リセット"]:
        dual_memory.clear(channel_id)
        embed = discord.Embed(
            title="🧹 工場記憶バンクをリセットしました",
            description="このチャンネルの会話履歴と長期記憶を初期化しました。新しい話題をどうぞ！",
            color=discord.Color.light_grey()
        )
        await message.reply(embed=embed, mention_author=False)
        return

    # 添付画像のチェック (スクリーンショット添付対応)
    image_path = None
    if message.attachments:
        for att in message.attachments:
            if att.content_type and any(att.content_type.startswith(t) for t in ["image/png", "image/jpeg", "image/webp"]):
                os.makedirs("temp_images", exist_ok=True)
                image_path = f"temp_images/{message.id}_{att.filename}"
                await att.save(image_path)
                break

    # 1. RAG検索 (直前のトピック継承付き)
    current_topic = dual_memory.get_current_topic(channel_id)
    fallback_item = current_topic.get("item_name") if current_topic else None

    rag_result = rag_engine.query(clean_content, fallback_topic=fallback_item)
    if rag_result.get("recipe_matches"):
        top_term = list(rag_result["recipe_matches"].keys())[0]
        matched_items = rag_result["recipe_matches"][top_term].get("matched_items", [])
        if matched_items:
            dual_memory.set_current_topic(channel_id, matched_items[0]["id"], matched_items[0]["name_ja"])
        else:
            dual_memory.set_current_topic(channel_id, top_term, top_term)

    # 2. 難易度判定 (画像付きの場合は自動的に画像診断モード/HIGH)
    complexity = "HIGH" if image_path else classify_complexity(clean_content, rag_context=rag_result)
    can_use_claude = tracker.can_use_claude()

    # 高度な設計相談または画像診断で、かつClaude枠がある場合 -> 選択肢ボタンを表示！
    if complexity == "HIGH" and can_use_claude:
        remaining = tracker.daily_limit - tracker.data.get("claude_used", 0)
        pbar = tracker.get_progress_bar(8)

        reason_text = "📸 工場現場のスクリーンショット画像が添付されています。\n機械のランプや配管・信号の配置を視覚的に解析するため、" if image_path else "⚠️ この相談はこれまでの工場の歩みや複数のレシピ比較・最適化など、高度な推論を要します。\n"

        embed_confirm = discord.Embed(
            title="🏭 FICSIT 工場技術顧問団からの確認",
            description=(
                f"**質問**: 「{clean_content[:120] if clean_content else '(画像診断リクエスト)'}」\n\n"
                f"{reason_text}"
                f"**最高峰AI（Claude 3.7 Sonnet Vision）** を召喚して画像診断・深層設計を行いますか？\n\n"
                f"📊 **本日残り利用回数**: **`{remaining} / {tracker.daily_limit} 回`** `[{pbar}]`"
            ),
            color=discord.Color.orange()
        )
        view = ClaudeConfirmationView(
            author=message.author, 
            channel_id=channel_id, 
            question=clean_content or "この工場スクリーンショットの配管・ボトルネック・配置を診断してください", 
            rag_result=rag_result, 
            image_path=image_path
        )
        msg = await message.reply(embed=embed_confirm, view=view, mention_author=False)
        view.message = msg
        return

    # 通常質問 または Claude枠上限時は通常チームが直接回答
    async with message.channel.typing():
        try:
            history_context = dual_memory.format_prompt_memory(channel_id, short_term_limit=20)
            last_bot_response = dual_memory.get_last_bot_response(channel_id)

            answer_text, model_name = await asyncio.to_thread(
                generate_rag_answer,
                clean_content or "画像を確認してください", 
                rag_result, 
                use_claude=False, 
                image_path=image_path, 
                history_context=history_context,
                last_bot_response=last_bot_response,
                current_topic=current_topic
            )
            _, remaining = tracker.record_usage("gemini", user_id, username)
            pbar = tracker.get_progress_bar(8)

            # 二重記憶にターンを記録 & 資源レート保存
            dual_memory.add_turn(channel_id, user_id, username, clean_content or "(画像添付のみ)", answer_text)
            calculated_rates = rag_result.get("calculated_rates")
            if calculated_rates:
                cur_item = current_topic.get("item_name", "燃料") if current_topic else "燃料"
                cur_id = current_topic.get("item_id", "Desc_LiquidFuel_C") if current_topic else "Desc_LiquidFuel_C"
                dual_memory.set_current_topic(channel_id, cur_id, cur_item, resource_rates=calculated_rates)

            embed = discord.Embed(
                title="🏭 FICSIT 工場技術顧問団 (通常解析チーム)",
                description=answer_text[:4000],
                color=discord.Color.blue()
            )
            if complexity == "HIGH":
                embed.set_footer(text=f"🛠️ 通常チーム [{model_name}] (※本日Claude上限到達) | 🧠 Claude残り: 0/{tracker.daily_limit}回 [{pbar}]")
            else:
                embed.set_footer(text=f"🛠️ 通常チーム [{model_name}] | 🧠 Claude残り: {remaining}/{tracker.daily_limit}回 [{pbar}]")

            try:
                await message.reply(embed=embed, mention_author=False)
            except Exception:
                await message.channel.send(embed=embed)
        except Exception as e:
            import traceback
            print(f"[!] on_message error: {e}\n{traceback.format_exc()}")
            try:
                err_embed = discord.Embed(
                    title="⚠️ 一時的なエラーが発生しました",
                    description="申し訳ありません。回答の生成または送信中に一時的な問題が発生しました。もう一度お試しください。",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=err_embed)
            except Exception:
                pass
        finally:
            if image_path and os.path.exists(image_path):
                try: os.remove(image_path)
                except Exception: pass


def ensure_single_instance():
    """Ensure only one instance of the Discord bot runs at any time across the OS."""
    pid_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../bot.pid"))
    current_pid = os.getpid()

    # Aggressive process cleanup: kill any other python process running discord_bot.py
    try:
        kill_cmd = (
            f'Get-CimInstance Win32_Process -Filter "name = \'python.exe\'" | '
            f'Where-Object {{ $_.ProcessId -ne {current_pid} -and $_.CommandLine -like "*discord_bot.py*" }} | '
            f'ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", kill_cmd], capture_output=True)
    except Exception as e:
        print(f"[!] Warning during process deduplication: {e}")

    with open(pid_file, "w", encoding="utf-8") as f:
        f.write(str(current_pid))


def main():
    ensure_single_instance()

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("DISCORD_BOT_TOKEN="):
                        token = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not token:
        print("[!] DISCORD_BOT_TOKEN is not set in .env")
        sys.exit(1)

    while True:
        try:
            bot.run(token)
            print("[*] Bot connection closed normally. Reconnecting in 5s...")
            import time
            time.sleep(5)
        except Exception as e:
            print(f"[!] Fatal bot error: {e}. Auto-reconnecting in 5s...")
            import time
            time.sleep(5)


if __name__ == "__main__":
    main()

