#!/usr/bin/env python3
"""Curate, crop, and verify UI assets for the SGR Swordland member guide."""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from datetime import datetime, timezone
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT / "scratch" / "ui_asset_library"
RAW_GUIDES = LIB / "raw_guides"
RAW_YT = LIB / "raw_youtube"
GENERATED = LIB / "generated"
HERO_ICONS = ROOT / "web_apps" / "web_tierlist" / "icons"

OUT_ASSETS = ROOT / "web_apps" / "sgr_swordland_guide" / "assets"
MANIFEST_OUT = LIB / "manifest.json"


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_guides_lookup() -> dict[str, dict]:
    raw_file = LIB / "guides_assets_raw.json"
    if not raw_file.exists():
        return {}
    data = json.loads(raw_file.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("assets", data.get("items", []))
    return {x["filename"]: x for x in items if isinstance(x, dict) and "filename" in x}


def copy_asset(
    src: pathlib.Path,
    dst: pathlib.Path,
    category: str,
    asset_type: str,
    source_label: str,
    caption: str,
) -> dict:
    if not src.exists():
        raise FileNotFoundError(f"Missing source asset: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Convert webp icons/photos cleanly or keep original extension for browser universal support
    if src.suffix.lower() == ".webp":
        # Convert to PNG for guaranteed offline & GitHub Pages compatibility across older Safari/iOS viewers
        dst = dst.with_suffix(".png")
        with Image.open(src) as im:
            im.convert("RGBA" if "A" in im.getbands() else "RGB").save(dst, format="PNG", optimize=True)
    else:
        shutil.copy2(src, dst)
    with Image.open(dst) as im:
        w, h = im.size
    return {
        "rel_path": dst.relative_to(OUT_ASSETS.parent).as_posix(),
        "category": category,
        "asset_type": asset_type,
        "source_label": source_label,
        "caption": caption,
        "width": w,
        "height": h,
        "size_bytes": dst.stat().st_size,
        "sha256": sha256_file(dst),
    }


def crop_asset(
    src: pathlib.Path,
    dst: pathlib.Path,
    box: tuple[int, int, int, int],
    category: str,
    source_label: str,
    caption: str,
) -> dict:
    if not src.exists():
        raise FileNotFoundError(f"Missing crop source: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        cropped = im.crop(box).convert("RGB")
        cropped.save(dst, format="JPEG", quality=92)
        w, h = cropped.size
    return {
        "rel_path": dst.relative_to(OUT_ASSETS.parent).as_posix(),
        "category": category,
        "asset_type": "ingame_ui_crop",
        "source_label": source_label,
        "caption": caption,
        "width": w,
        "height": h,
        "size_bytes": dst.stat().st_size,
        "sha256": sha256_file(dst),
    }


def main() -> None:
    guides_meta = load_guides_lookup()
    records: list[dict] = []

    # 1. AI Generated conceptual / banner visuals (clearly marked as illustrative/map base)
    gen_specs = [
        ("banner_swordland_showdown.jpg", "banner", "作戦ページトップ用ヒーローイメージ（AI生成イラスト）"),
        ("swordland_tactical_map_base.jpg", "map_base", "聖剣戦場戦略マップ土台（透かし無し生成図＋実アイコン配置用）"),
        ("baggage_heist_scene.jpg", "concept_heist", "Phase 3 輜重ハイスト（50%ドロップ箱回収）作戦イメージ（AI生成）"),
        ("infirmary_ready_scene.jpg", "concept_infirmary", "開戦前・医務室負傷兵ゼロ確認イメージ（AI生成）"),
    ]
    for fn, cat, cap in gen_specs:
        records.append(
            copy_asset(
                GENERATED / fn,
                OUT_ASSETS / "generated" / fn,
                cat,
                "ai_generated_illustration",
                "Antigravity image-generator (custom)",
                cap,
            )
        )

    # 2. Swordland facility icons & real UI panels from guides
    swordland_specs = [
        ("ks_swordland_swordshrine_icon_02.webp", "facility_swordshrine.png", "facility_icon", "聖剣祭壇（Swordshrine）"),
        ("ks_swordland_sanctum_icon_03.webp", "facility_sanctum.png", "facility_icon", "サンクタム／聖域（Sanctum）"),
        ("ks_swordland_royal_stables_icon_04.webp", "facility_royal_stables.png", "facility_icon", "王立厩舎（Royal Stables）"),
        ("ks_swordland_abbey_icon_05.webp", "facility_abbey.png", "facility_icon", "修道院（Abbey）"),
        ("ks_swordland_hall_reformation_icon_06.webp", "facility_reformation.png", "facility_icon", "宗教改革所（Hall of Reformation）"),
        ("ks_swordland_mercenary_camp_icon_07.webp", "facility_mercenary.png", "facility_icon", "傭兵キャンプ（Mercenary Camp）"),
        ("ks_swordland_undercellar_icon_08.webp", "facility_undercellar.png", "facility_icon", "地下室／地下貯蔵庫（Undercellar）"),
        ("ks_almanach_swordland_monument_art_15.webp", "swordland_monument_art.png", "swordland_art", "聖剣モニュメント公式アート"),
        ("ks_almanach_swordland_rules_swordshrine_12.webp", "ui_rules_swordshrine.png", "ingame_ui", "実機UI：聖剣祭壇ルール＆獲得ポイント"),
        ("ks_almanach_swordland_stables_buff_13.webp", "ui_rules_stables_buff.png", "ingame_ui", "実機UI：王立厩舎 無料移転クールダウン -50% バフ"),
        ("ks_almanach_swordland_alliance_cluster_march_14.webp", "ui_battle_cluster_march.png", "ingame_ui", "実機UI：聖剣戦場 同盟集結クラスタ＆行軍ライン"),
        ("ks_seiken_summit_league_shot_03.png", "ui_entry_timezone_ja.png", "ingame_ui", "日本語実機UI：軍団1 参戦時間帯エントリー画面"),
        ("ks_seiken_summit_league_shot_04.png", "ui_rules_ja.png", "ingame_ui", "日本語実機UI：聖剣ルール説明画面"),
    ]
    for src_fn, dst_fn, cat, cap in swordland_specs:
        src_url = guides_meta.get(src_fn, {}).get("source_page_url", "scraped guide")
        records.append(
            copy_asset(
                RAW_GUIDES / src_fn,
                OUT_ASSETS / "swordland" / dst_fn,
                cat,
                "official_or_ingame_ui",
                src_url,
                cap,
            )
        )

    # 3. Core Kingshot Battle & City UIs
    basic_ui_specs = [
        ("ks_almanach_vv_alliance_hq_garrison_17.webp", "ui_garrison_list.png", "rally_garrison", "実機UI：防衛駐屯リスト（10/15スロット＆英雄並び）"),
        ("ks_almanach_vv_kingdom_map_marches_16.webp", "ui_reinforce_marches.png", "rally_garrison", "実機UI：最大行軍枠＆増援派遣操作"),
        ("ks_almanach_bear_hunt_rally_panel_21.webp", "ui_rally_panel.png", "rally_garrison", "実機UI：集結（War Rally）参加メンバー＆残り時間パネル"),
        ("ks_almanach_mystic_squad_formation_lineup_25.webp", "ui_squad_formation.png", "squad_preset", "実機UI：出撃前 部隊編成確認画面"),
        ("ks_truegold_tg8_refinement_shot_02.png", "ui_tg8_refinement_ja.png", "tg_quality", "日本語実機UI：精製黄金（TG8）アイテム詳細"),
        ("ks_war_academy_tech_tree_shot_02.png", "ui_tg_troop_upgrade_ja.png", "tg_quality", "日本語実機UI：黄金兵士研究画面"),
        ("ks_building_infirmary_hospital_36.png", "icon_infirmary.png", "city_building", "公式施設アイコン：医務室（負傷兵0確認用）"),
        ("ks_building_truegold_crucible_35.webp", "icon_truegold_crucible.png", "city_building", "公式施設アイコン：真金のるつぼ（TG解放）"),
        ("ks_building_command_center_rally_42.webp", "icon_command_center.png", "city_building", "公式施設アイコン：指揮センター（集結上限）"),
        ("ks_building_embassy_reinforce_43.webp", "icon_embassy.png", "city_building", "公式施設アイコン：大使館（駐屯増援上限）"),
        ("ks_art_kingdom_transfer_relocation_48.png", "icon_teleport.png", "city_building", "公式アイコン：領地移転（Advanced Teleport）"),
    ]
    for src_fn, dst_fn, cat, cap in basic_ui_specs:
        src_url = guides_meta.get(src_fn, {}).get("source_page_url", "scraped guide")
        records.append(
            copy_asset(
                RAW_GUIDES / src_fn,
                OUT_ASSETS / "ui" / dst_fn,
                cat,
                "official_or_ingame_ui",
                src_url,
                cap,
            )
        )

    # 4. Crisp YouTube UI crops (verified dimensions 854x480 -> pure phone frame crops)
    records.append(
        crop_asset(
            RAW_YT / "8-HmCJO3F1o_f03_11m20s.jpg",
            OUT_ASSETS / "ui" / "ui_chenko_skill1_crop.jpg",
            (298, 2, 563, 478),
            "hero_skill_ui",
            "https://www.youtube.com/watch?v=8-HmCJO3F1o",
            "実機UI：チェンコ 第1遠征スキル（殺傷力+25%・一番左配置時の発動スキル枠）",
        )
    )
    records.append(
        crop_asset(
            RAW_YT / "Gfrz-ZS0dAA_f02_03m00s.jpg",
            OUT_ASSETS / "swordland" / "ui_swordshrine_garrison_crop.jpg",
            (305, 8, 553, 472),
            "swordland_garrison",
            "https://www.youtube.com/watch?v=Gfrz-ZS0dAA",
            "実機UI：聖剣祭壇 防衛駐屯メンバー一覧＆Dispatch Troops画面",
        )
    )
    records.append(
        crop_asset(
            RAW_YT / "Gfrz-ZS0dAA_f02_03m00s.jpg",
            OUT_ASSETS / "swordland" / "ui_swordland_field_crop.jpg",
            (589, 8, 804, 472),
            "swordland_field",
            "https://www.youtube.com/watch?v=Gfrz-ZS0dAA",
            "実機UI：聖剣戦場 輜重箱ドロップ（159/45/401）＆無料移転CD・Battle Map",
        )
    )

    # 5. Official Hero Icons (used in Preset Slot-1 Golden 4 vs Forbidden list)
    hero_list = [
        ("chenko.png", "チェンコ（攻撃確定殺傷+25%）"),
        ("yeonwoo.png", "インウー（攻撃確定殺傷+25%）"),
        ("amane.png", "アマネ（攻撃確定攻撃+25%）"),
        ("margot.png", "マーゴ（攻撃確定攻撃+25%）"),
        ("saul.png", "サウル（分割乗算バフ）"),
        ("hilde.png", "ヒルダ（分割乗算バフ）"),
        ("eric.png", "エリック（敵デバフ）"),
        ("fahd.png", "ファハド（敵デバフ）"),
        ("vivian.png", "ヴィヴィアン（与ダメ上昇）"),
        ("petra.png", "ペトラ（被ダメ増43.75%・同一集結内1名のみ）"),
        ("gordon.png", "ゴードン（防衛駐屯推奨）"),
        ("howard.png", "ハワード（防衛駐屯推奨）"),
        ("long-fei.png", "ロン・フェイ（攻撃集結時 禁止地雷）"),
        ("jabel.png", "ジェイブル（合流時 禁止地雷）"),
        ("helga.png", "ヘルガ（合流時 禁止地雷）"),
        ("zoe.png", "ゾーイ（合流時 禁止地雷）"),
        ("sophia.png", "ソフィア（合流時 禁止地雷）"),
    ]
    for h_fn, cap in hero_list:
        records.append(
            copy_asset(
                HERO_ICONS / h_fn,
                OUT_ASSETS / "heroes" / h_fn,
                "hero_icon",
                "official_hero_icon",
                f"web_apps/web_tierlist/icons/{h_fn}",
                cap,
            )
        )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_curated_assets": len(records),
        "raw_guides_pool_count": len(guides_meta),
        "assets": records,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(records)} verified assets into {OUT_ASSETS}")
    print(f"Manifest saved to {MANIFEST_OUT}")


if __name__ == "__main__":
    main()
