# #898 [SGR] vs #913 [GOD] 聖剣頂上リーグ ポータル正本データ

- **目的**: `#898 [SGR] 軍団1`（ゲーム内実測：参戦25名・控え8名）vs `#913 [GOD] 軍団1`（Top 30）聖剣頂上リーグ 第14ブロック 昇格戦第3試合 作戦ポータル（`web_apps/sgr_vs_god_guide/index.html`）を再ビルドするための正本スコア・4言語（`ja` / `en` / `ar` / `tr`）翻訳バンドルの格納先。
- **更新日**: 2026-11-22（ゲーム内実画面15枚から GPT-6.1 Terra にて参戦25名・控え8名を抽出・検算済み＋MightPulse API 最新再算出）
- **含まれるファイル**:
  - `sgr_vs_god_scores.json`: `scripts/pvp_two_axis_scorer.py`＋実戦名簿照合による戦力・PCS・DTV集計データ
  - `i18n_ja_source.json`: 日本語マスター翻訳バンドル
  - `i18n_en.json`: 英語翻訳バンドル
  - `i18n_ar.json`: アラビア語（RTL）翻訳バンドル
  - `i18n_tr.json`: トルコ語翻訳バンドル
- **再ビルド方法**:
  ```bash
  python scripts/build_sgr_vs_god_portal_html.py
  ```
