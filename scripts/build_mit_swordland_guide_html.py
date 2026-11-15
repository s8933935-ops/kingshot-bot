#!/usr/bin/env python3
"""Build #898 [MIT] vs #878 [BIZ] Swordland Showdown HTML guide from verified scores & UI assets."""

from __future__ import annotations

import json
import pathlib
import shutil

from swordland_i18n import load_and_validate_bundles
from swordland_portal_common import render_swordland_portal

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "swordland" / "898_mit_vs_878_biz"
MIT_SCORES_PATH = DATA_DIR / "mit_vs_biz_scores.json"
SRC_ASSETS_DIR = ROOT / "web_apps" / "sgr_swordland_guide" / "assets"
OUT_DIR = ROOT / "web_apps" / "mit_swordland_guide"

I18N_PATHS = {
    "ja": DATA_DIR / "i18n_ja_source.json",
    "en": DATA_DIR / "i18n_en.json",
    "ar": DATA_DIR / "i18n_ar.json",
    "tr": DATA_DIR / "i18n_tr.json",
}

# Explicit band assignment for #898 [MIT] core cannons & special-case players.
# Translated role/mission prose lives in DATA_DIR / i18n_*.json under roster.custom.
MIT_CUSTOM_BANDS: dict[str, str] = {
    "YetimDöven": "band1",
    "ツ\xa0GENGAR\xa0ツ": "band1",
    "Asi\xa0007": "band1",
    "Battle\xa0Cat": "band1",
    "Oflu": "band1",
    "Mithrandir": "band4",
    "Stark": "band3",
    "Yusuf13": "band3",
    "HoLeNaa": "band3",
}


def classify_mit_band(member: dict) -> str:
    """Assign each MIT Top-30 member to one of 5 conflict-free tactical band IDs."""
    name = member["nick_name"]
    if name in MIT_CUSTOM_BANDS:
        return MIT_CUSTOM_BANDS[name]

    tg = member.get("tg", 0)
    quad = member.get("quadrant")
    fat = member.get("fat_warn", False)

    if fat or tg <= 6:
        return "band5"
    if tg == 8 and quad == "A":
        return "band2"
    if tg == 8:
        return "band3"
    return "band4"


def sync_assets() -> set[str]:
    """Ensure self-contained assets exist inside web_apps/mit_swordland_guide/assets."""
    dst_assets = OUT_DIR / "assets"
    if SRC_ASSETS_DIR.exists():
        shutil.copytree(SRC_ASSETS_DIR, dst_assets, dirs_exist_ok=True)
    elif not dst_assets.exists():
        raise RuntimeError(f"Source assets directory missing: {SRC_ASSETS_DIR}")
    return {p.relative_to(OUT_DIR).as_posix() for p in dst_assets.rglob("*") if p.is_file()}


def build_mit_portal() -> str:
    """Construct configuration dict and render MIT vs BIZ HTML portal."""
    scores = json.loads(MIT_SCORES_PATH.read_text(encoding="utf-8"))
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
        missing_custom = set(MIT_CUSTOM_BANDS.keys()) - custom_keys
        if missing_custom:
            raise ValueError(f"[{lang}] missing roster.custom entries (check NBSP \\xa0): {sorted(missing_custom)}")

    mit_rows = []
    for idx, m in enumerate(self_data["top_roster"], 1):
        band_id = classify_mit_band(m)
        mit_rows.append(
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

    # Identify outside-Top30 TG8 substitutes for Legion 1 absences
    top30_names = {m["nick_name"] for m in self_data["top_roster"]}
    mit_all_pcs = sorted(
        [m for m in scores["self_all"] if m.get("pcs") is not None],
        key=lambda x: (-x["pcs"], -x["egc_M"]),
    )
    reserve_tg8 = [
        f'{m["nick_name"]} (PCS {m["pcs"]} / {m["troop_M"]:.1f}M)'
        for m in mit_all_pcs
        if m["nick_name"] not in top30_names and m["tg"] == 8
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
        "banner_alt": "聖剣リーグ MIT vs BIZ イメージバナー",
        "opp_code": "#878 [BIZ]",
        "kpis_num": [
            {
                "self_val": f'{self_data["avg_pcs_top_n"]}',
                "opp_val": f'vs {opp_data["avg_pcs_top_n"]}',
                "val_color": "#6ee7b7",
            },
            {
                "self_val": f'{self_data["avg_pcs_5_10"]} / {self_data["avg_pcs_11_plus"]}',
                "opp_val": f'vs {opp_data["avg_pcs_5_10"]} / {opp_data["avg_pcs_11_plus"]}',
                "val_color": "#7dd3fc",
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
        "roster_rows": mit_rows,
        "reserve_tg8_list": reserve_tg8,
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
            "self_label": "#898 [MIT]",
            "opp_label": "#878 [BIZ]",
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
    html_text = build_mit_portal()
    (OUT_DIR / "index.html").write_text(html_text, encoding="utf-8")
    (OUT_DIR / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    print(f"Built {OUT_DIR / 'index.html'} ({len(html_text)} chars)")


if __name__ == "__main__":
    main()
