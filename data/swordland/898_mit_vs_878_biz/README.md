# #898 [MIT] vs #878 [BIZ] 聖剣リーグ ポータル正本データ

- **目的**: `#898 [MIT] 軍団1`（`[MI2]` 合流の `CEO`・`GuyTheGreat`・`༺Fayezᵏˢᵃ༻` 3名マージ反映済み）vs `#878 [BIZ] 軍団1` 聖剣リーグ作戦ポータル（`web_apps/mit_swordland_guide/index.html`）を再ビルドするための正本スコア・4言語（`ja` / `en` / `ar` / `tr`）翻訳バンドルの格納先。
- **更新日**: 2026-11-15（`MI2` 3名マージ反映・最新API再算出済み）
- **含まれるファイル**:
  - `mit_vs_biz_scores.json`: `scripts/pvp_two_axis_scorer.py` 出力の戦力・PCS・DTV集計データ（MIT 94名 + MI2合流 3名 = 97名 / BIZ 99名）
  - `i18n_ja_source.json`: 日本語マスター翻訳バンドル
  - `i18n_en.json`: 英語翻訳バンドル
  - `i18n_ar.json`: アラビア語（RTL）翻訳バンドル
  - `i18n_tr.json`: トルコ語翻訳バンドル
- **再ビルド方法**:
  ```bash
  python scripts/build_mit_swordland_guide_html.py
  ```
