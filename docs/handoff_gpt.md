# Satisfactory Discord RAG Bot 開発引き継ぎ指示書（GPT用）

---

## 📋 【ChatGPT貼り付け用】冒頭プロンプト

```text
あなたは熟練のフルスタック・シニアPythonエンジニアです。
現在開発中の「Satisfactory v1.0 攻略支援 Discord RAG Bot」の開発を引き継いでください。

このボットは、LLM特有の「ゲーム内クラフト計算ミスや架空素材の捏造（ハルシネーション）」を根本から排除するため、
「確定自律検算ソルバー（Python）」＋「確定レシピDB」＋「GPT-4o-mini / Claude 3.7 Sonnet の二刀流5層ルーティング」
という高度なマルチエージェント協調アーキテクチャを採用しています。

以下の引き継ぎドキュメントの内容を完全に把握した上で、次の開発タスクを進めてください。
```

---

## 1. プロジェクト概要

- **名称**: Satisfactory v1.0 攻略支援 Discord RAG Bot
- **稼働環境**: Windows 11 / Python 3.12 / Discord.py
- **作業ディレクトリ**: `c:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer`
- **現在の稼働状態**: バックグラウンド常駐デーモン（自動再接続・単一PIDロック）でDiscord Gatewayに正常接続中

---

## 2. システムアーキテクチャ（二刀流 ＆ 確定計算ハイブリッド）

```
[Discord ユーザー]
       │
       ▼
[discord_bot.py] ─── スラッシュコマンド / メンション / 画像受付
       │
       ├──► [dual_memory.py] ──── 短期ログ + 長期Fact + current_topic(話題永続化)
       │
       ├──► [search_engine.py] ── 871公式レシピ + 155アイテム + YouTube Tips(BM25)
       │           │
       │           └──► [calculator.py] ── 確定自律検算ソルバー (原油発電/水循環/シリカ収支)
       │           │
       │           └──► [production_metas.json] ── 公式効率メタ知識ベース
       │
       ▼
[ai_client.py] ───── 多次元難易度判定 & 5層ルーティング
       │
       ├── 通常質問 (月数十円・超高速) ──► OpenAI GPT-4o-mini (予備: Local Qwen 14B)
       │
       └── 高難度/画像 (1日30回共有枠) ──► Claude 3.7 Sonnet (Vision)
               │
               ▼
       [Grounding Validator & Clean Output Guard]
               │ (架空素材の置換 & <think>タグの完全除去)
               ▼
       [確定データ付きDiscordカード出力]
```

### チーム編成と役割
1. **通常解析チーム (`GPT-4o-mini`)**:
   - 日常的な質問、単発レシピ検索、基本相談を高速かつ月数十円レベルの超低コストで担当。
   - OpenAI障害時はローカルの `Qwen 2.5 Coder 14B`（RTX 5080 / Ollama）へ自動フォールバック。
2. **特別解析チーム (`Claude 3.7 Sonnet (Vision)`)**:
   - 高難度な代替レシピ比較、大規模プラント設計、添付スクリーンショット診断を担当。
   - `usage_tracker.py` により1日30回枠を管理（毎日JST深夜0時に自動リセット、残数プログレスバー付き）。
3. **確定自律検算ソルバー (`calculator.py`)**:
   - **「LLMにクラフト計算をさせない」** を徹底。
   - 原油発電シミュレーション（希釈燃料/通常燃料/ターボ燃料のMW・発電機台数）、アルミ精製の水循環回収・シリカ収支などを裏のPython数学ロジックで100%正確に連立計算し、AIへ確定値を渡す。

---

## 3. 主要ファイル構成マップ

| パス | 役割・最新実装内容 |
| :--- | :--- |
| `src/bot/discord_bot.py` | Bot本体。スラッシュコマンド（`/recipe`, `/limit` 等）、メンション/リプライ受付、単一PIDロック、フッターのモデル名表示。 |
| `src/bot/ai_client.py` | AIディスパッチャー。難易度自動判定、自律検算トリガー（`run_autonomous_solver`）、GPT-4o-mini / Claude 3.7 切替、`<think>`思考隠蔽フィルター。 |
| `src/rag/calculator.py` | 自律検算ソルバー。原油量やボーキサイト量から、消費精製機台数・水循環・発電量などを決定論的に算出。 |
| `src/rag/search_engine.py` | ハイブリッドRAG。871レシピ検索、確定代替レシピ比較表（Markdownテーブル）、サプライチェーンASCIIツリー、文脈解決（`current_topic` 継承）。 |
| `src/bot/dual_memory.py` | 二重記憶管理。短期会話履歴（直近5往復）＋ 長期工場設定（`facts.json`）＋ 直近の話題アイテム永続化（`topic.json`）。 |
| `src/bot/usage_tracker.py` | Claude 1日30回枠の管理。日付変更検知・自動リセット・利用履歴保存。 |
| `data/processed/recipes.json` | Satisfactory v1.0 公式レシピ（871種）。 |
| `data/processed/items.json` | ゲーム内全アイテムデータ（155種）。 |
| `data/processed/production_metas.json` | 燃料・アルミ・鋼鉄・純インゴット・ネジ等の確定最高効率コンボ知識。 |
| `tests/test_agent_reasoning.py` | 自律検算ソルバー、全角「４８０」正規化、文脈引き継ぎ、思考隠蔽の自動テスト。 |
| `tests/test_context_and_comparison.py` | 文脈継承、代替比較表、難易度判定、事実検証バリデータの自動テスト。 |
| `Satisfactory_Bot_起動.bat` | ワンクリック起動バッチ。 |
| `Satisfactory_Bot_停止.bat` | ワンクリック停止バッチ。 |
| `.env` | `DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`, `CLAUDE_DAILY_LIMIT=30` |

---

## 4. 直近の完了マイルストーン ＆ テスト状況

- **全テスト合格（100% Pass）**:
  - `python tests/test_agent_reasoning.py`
  - `python tests/test_context_and_comparison.py`
- **直近の改修**:
  - `src/rag/search_engine.py` の `find_recipes_for_item()` におけるレシピ格納ループを修復完了。
  - 全角数字（例: 「原油４８０」）の正規化処理を実装。
  - 代替レシピ比較表における「未包装（缶開封）」レシピのノイズ除去を実装。

---

## 5. Botの起動・停止・確認コマンド

- **テスト実行**:
  ```powershell
  python tests/test_agent_reasoning.py
  python tests/test_context_and_comparison.py
  ```
- **Bot停止**:
  ```powershell
  taskkill /F /PID (Get-Content bot.pid)
  # または Satisfactory_Bot_停止.bat を実行
  ```
- **Bot起動（バックグラウンド）**:
  ```powershell
  python -u src\bot\discord_bot.py
  # または Satisfactory_Bot_起動.bat を実行
  ```
- **ログ確認**:
  ```powershell
  Get-Content bot.log -Tail 20
  ```

---

## 6. 次の開発タスク（TODO）

1. **生産メタ（`data/processed/production_metas.json`）の拡充**:
   - **ロケット燃料（Rocket Fuel）/ イオン化燃料（Ionized Fuel）**:
     - v1.0で追加された窒素ガス＋ターボ燃料の超高出力ラインの確定メタと推奨構成を追加。
   - **ウラン原子力発電 ＆ プルトニウム廃棄物完全リサイクル**:
     - 放射性廃棄物を出さない「プルトニウム燃料棒沈没（FICSITシンク）コンボ」の確定メタ定義。
2. **Discord実機でのフィードバック確認**:
   - 新規ユーザーからの自然言語クエリに対する自律検算ソルバーの発動率・回答精度のチューニング。
3. **Webダッシュボード（工場進捗ビューア）の検討**:
   - `data/memory/` 配下の `facts.json` や `long_term.md` をブラウザから見られる軽量ビューア。

---

## 7. 開発時の厳守ルール（GPTへの注意事項）

1. **クラフト計算をLLMの自由作文に任せないこと**:
   - 比率計算や素材量、発電機台数は、必ず `calculator.py` または `production_metas.json` の確定値を使用・拡張してください。
2. **ルートディレクトリを汚染しないこと**:
   - スクリプトは `scripts/`、テストは `tests/`、ドキュメントは `docs/` に配置してください。
3. **既存の二刀流・二重記憶アーキテクチャを壊さないこと**:
   - `GPT-4o-mini`（通常）＋ `Claude 3.7 Sonnet`（高難度・画像）＋ `dual_memory.py` の協調フローを維持してください。
