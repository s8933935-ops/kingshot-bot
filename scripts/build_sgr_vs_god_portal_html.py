#!/usr/bin/env python3
"""Build #898 [SGR] vs #913 [GOD] 4-language Swordland Showdown HTML portal."""

from __future__ import annotations

import json
import pathlib
import shutil

from swordland_i18n import load_and_validate_bundles
from swordland_portal_common import render_swordland_portal

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "swordland" / "898_sgr_vs_913_god"
SCORES_PATH = DATA_DIR / "sgr_vs_god_scores.json"
SRC_ASSETS_DIR = ROOT / "web_apps" / "sgr_swordland_guide" / "assets"
OUT_DIR = ROOT / "web_apps" / "sgr_vs_god_guide"

I18N_PATHS = {
    "ja": DATA_DIR / "i18n_ja_source.json",
    "en": DATA_DIR / "i18n_en.json",
    "ar": DATA_DIR / "i18n_ar.json",
    "tr": DATA_DIR / "i18n_tr.json",
}

SGR_CUSTOM_BANDS: dict[str, str] = {
    "リョ〜〜〜朕": "band1",
    "レッサー": "band1",
    "だりゅDaryu": "band1",
    "Hinata": "band1",
    "ルーク": "band1",
}


def classify_sgr_band(member: dict) -> str:
    """Assign each verified active SGR member (25) to one of 5 tactical bands."""
    name = member["nick_name"]
    if name in SGR_CUSTOM_BANDS:
        return SGR_CUSTOM_BANDS[name]
    tg = member.get("tg", 0)
    quad = member.get("quadrant")
    fat = member.get("fat_warn", False)
    if tg == 8:
        return "band2"
    if tg == 7 and quad == "B":
        return "band3"
    if fat or (quad == "B" and tg <= 6):
        return "band4"
    return "band5"


def sync_assets() -> set[str]:
    """Ensure self-contained assets exist inside web_apps/sgr_vs_god_guide/assets."""
    dst_assets = OUT_DIR / "assets"
    if SRC_ASSETS_DIR.exists():
        shutil.copytree(SRC_ASSETS_DIR, dst_assets, dirs_exist_ok=True)
    elif not dst_assets.exists():
        raise RuntimeError(f"Source assets directory missing: {SRC_ASSETS_DIR}")
    return {p.relative_to(OUT_DIR).as_posix() for p in dst_assets.rglob("*") if p.is_file()}


def build_portal() -> str:
    scores = json.loads(SCORES_PATH.read_text(encoding="utf-8"))
    local_assets = sync_assets()

    required_imgs = [
        "assets/generated/banner_swordland_showdown.jpg",
        "assets/generated/swordland_tactical_map_base.jpg",
        "assets/generated/baggage_heist_scene.jpg",
        "assets/generated/infirmary_ready_scene.jpg",
        "assets/swordland/facility_swordshrine.png",
        "assets/swordland/facility_sanctum.png",
        "assets/swordland/facility_royal_stables.png",
        "assets/swordland/facility_abbey.png",
        "assets/swordland/facility_reformation.png",
        "assets/swordland/facility_mercenary.png",
        "assets/swordland/facility_undercellar.png",
        "assets/swordland/ui_rules_swordshrine.png",
        "assets/swordland/ui_rules_stables_buff.png",
        "assets/swordland/ui_battle_cluster_march.png",
        "assets/swordland/ui_entry_timezone_ja.png",
        "assets/swordland/ui_swordshrine_garrison_crop.jpg",
        "assets/swordland/ui_swordland_field_crop.jpg",
        "assets/ui/ui_chenko_skill1_crop.jpg",
        "assets/ui/ui_garrison_list.png",
        "assets/ui/ui_rally_panel.png",
        "assets/ui/ui_tg8_refinement_ja.png",
        "assets/ui/icon_infirmary.png",
        "assets/ui/icon_truegold_crucible.png",
        "assets/ui/icon_command_center.png",
        "assets/ui/icon_embassy.png",
        "assets/ui/icon_teleport.png",
    ]
    for rel in required_imgs:
        if rel not in local_assets:
            raise RuntimeError(f"Missing copied asset: {rel}")

    self_data = scores["self"]
    opp_data = scores["opp"]

    bundles = load_and_validate_bundles(I18N_PATHS)
    for lang, bundle in bundles.items():
        custom_keys = set(bundle["roster"]["custom"].keys())
        missing_custom = set(SGR_CUSTOM_BANDS.keys()) - custom_keys
        if missing_custom:
            raise ValueError(f"[{lang}] missing roster.custom entries: {sorted(missing_custom)}")

    sgr_rows = []
    band_counts = {"band1": 0, "band2": 0, "band3": 0, "band4": 0, "band5": 0}
    for idx, m in enumerate(self_data["top_roster"], 1):
        band_id = classify_sgr_band(m)
        band_counts[band_id] += 1
        sgr_rows.append(
            {
                "rank": idx,
                "name": m["nick_name"],
                "power_M": m["power_M"],
                "stove_lv": m["stove_lv"],
                "tg": m["tg"],
                "pcs": m["pcs"],
                "pcs_joiner": m["pcs_joiner"],
                "dtv": m["dtv"],
                "troop_M": m["troop_M"],
                "egc_M": m["egc_M"],
                "quadrant": m["quadrant"],
                "fat_warn": m["fat_warn"],
                "band_id": band_id,
            }
        )
    print("Band counts:", band_counts)

    reserve_list = [
        f'{m["nick_name"]} (TG{m["tg"]} / PCS {m["pcs"]} / {m["troop_M"]:.1f}M)'
        for m in self_data.get("reserve_roster", [])
    ]

    opp_top8 = [
        {
            "rank": i,
            "name": m["nick_name"],
            "power_M": m["power_M"],
            "stove_lv": m["stove_lv"],
            "tg": m["tg"],
            "pcs": m["pcs"],
            "dtv": m["dtv"],
            "troop_M": m["troop_M"],
            "fat_warn": m["fat_warn"],
        }
        for i, m in enumerate(opp_data["top_roster"][:8], 1)
    ]

    cfg = {
        "i18n_bundles": bundles,
        "banner_alt": "聖剣頂上リーグ SGR vs GOD イメージバナー",
        "opp_code": "#913 [GOD]",
        "kpis_num": [
            {
                "self_val": f'{self_data["avg_pcs_top4"]}',
                "opp_val": f'vs {opp_data["avg_pcs_top4"]}',
                "val_color": "#6ee7b7",
            },
            {
                "self_val": f'{self_data["avg_pcs_top_n"]} / {self_data["avg_pcs_5_10"]}',
                "opp_val": f'vs {opp_data["avg_pcs_top_n"]} / {opp_data["avg_pcs_5_10"]}',
                "val_color": "#f59e0b",
            },
            {
                "self_val": f'{self_data["total_troop_m_top_n"]:,.1f}M',
                "opp_val": f'vs {opp_data["total_troop_m_top_n"]:,.1f}M',
            },
            {
                "self_val": f'{self_data["total_egc_m_top_n"]:,.1f}M',
                "opp_val": f'vs {opp_data["total_egc_m_top_n"]:,.1f}M',
            },
        ],
        "roster_rows": sgr_rows,
        "reserve_tg8_list": reserve_list,
        "opp_top_rows": opp_top8,
        "phase_arrows": {
            "p1": [
                {"x1": 95, "y1": 255, "x2": 305, "y2": 82, "lx": 155, "ly": 128, "color": "#38bdf8"},
                {"x1": 105, "y1": 315, "x2": 615, "y2": 488, "lx": 155, "ly": 435, "color": "#f59e0b"},
                {"x1": 95, "y1": 275, "x2": 215, "y2": 232, "lx": 118, "ly": 220, "color": "#a855f7"},
                {"x1": 95, "y1": 305, "x2": 185, "y2": 335, "lx": 98, "ly": 388, "color": "#10b981"},
            ],
            "p2": [
                {"x1": 295, "y1": 240, "x2": 455, "y2": 275, "lx": 370, "ly": 295, "color": "#38bdf8"},
                {"x1": 375, "y1": 80, "x2": 468, "y2": 128, "lx": 500, "ly": 42, "color": "#38bdf8"},
                {"x1": 255, "y1": 355, "x2": 458, "y2": 425, "lx": 175, "ly": 465, "color": "#f59e0b"},
                {"x1": 675, "y1": 460, "x2": 735, "y2": 375, "lx": 875, "ly": 395, "color": "#10b981"},
            ],
            "p3": [
                {"x1": 540, "y1": 285, "x2": 695, "y2": 335, "lx": 595, "ly": 228, "color": "#ef4444"},
                {"x1": 680, "y1": 460, "x2": 765, "y2": 275, "lx": 885, "ly": 305, "color": "#f59e0b"},
                {"x1": 785, "y1": 440, "x2": 675, "y2": 405, "lx": 845, "ly": 468, "color": "#10b981"},
            ],
        },
        "chart_cfg": {
            "self_label": "#898 [SGR] (25)",
            "opp_label": "#913 [GOD] (30)",
            "self_pcs": [
                self_data["avg_pcs_top_n"],
                self_data["avg_pcs_top4"],
                self_data["avg_pcs_5_10"],
                self_data["avg_pcs_11_plus"],
            ],
            "opp_pcs": [
                opp_data["avg_pcs_top_n"],
                opp_data["avg_pcs_top4"],
                opp_data["avg_pcs_5_10"],
                opp_data["avg_pcs_11_plus"],
            ],
            "self_troop": [self_data["total_troop_m_top_n"], self_data["total_egc_m_top_n"]],
            "opp_troop": [opp_data["total_troop_m_top_n"], opp_data["total_egc_m_top_n"]],
        },
    }

    return render_swordland_portal(cfg)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_text = build_portal()
    (OUT_DIR / "index.html").write_text(html_text, encoding="utf-8")
    (OUT_DIR / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    print(f"Built {OUT_DIR / 'index.html'} ({len(html_text)} chars)")


if __name__ == "__main__":
    main()
