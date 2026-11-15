#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical two-axis PvP scoring tool for KingShot & Swordland Showdown.

Separates permanent account combat density (PCS: 0-1000) from deployable
troop volume readiness (DTV: 0-100) using orthogonalized MightPulse metrics:
{power, migrant_score, stove_lv, trails_list}.

Spec SSOT: docs/guides/KINGSHOT_PVP_SCORING_SPEC.md (designed by Claude Opus 5).
Do NOT modify calibration constants (CAP, W, WJ, WPS_CAP, LAMBDA, BASE_COEF)
without explicit benchmark re-calibration.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

# Fixed cap constants (observed max + ~5% headroom as of TG8/Stove 70 era)
CAP: dict[str, int] = {"CC": 400, "MF": 440, "KN": 320, "FoL": 340, "Col": 800, "RS": 840}
W: dict[str, float] = {"CC": 0.26, "MF": 0.18, "KN": 0.14, "FoL": 0.08, "Col": 0.20, "RS": 0.14}
WJ: dict[str, float] = {"Col": 0.45, "RS": 0.15, "CC": 0.10, "MF": 0.05}

WPS_CAP: float = 42000.0
LAMBDA: float = 0.12
A_DEN: float = math.log(31.0)
BASE_POWER_COEF: float = 5.79
BASE_POWER_EXP: float = 0.318

TOWER_NAME_MAP: dict[str, str] = {
    "Crystal Cave": "CC",
    "Molten Fort": "MF",
    "Knowledge Nexus": "KN",
    "Forest of Life": "FoL",
    "Coliseum": "Col",
    "Radiant Spire": "RS",
}


def clip(value: float, lo: float, hi: float) -> float:
    """Clamp numeric value into [lo, hi]."""
    return max(lo, min(hi, value))


def compute_tg_tier(stove_lv: int | float | None) -> int:
    """Map stove_lv to Truegold tier [1..8], defaulting conservatively if missing."""
    stv = int(stove_lv) if stove_lv is not None else 30
    return int(clip(math.floor((stv - 30) / 5.0), 1, 8))


def extract_towers(member: dict[str, Any]) -> dict[str, int] | None:
    """Extract normalized 6-tower stage dict from MightPulse trails_list/trails."""
    tlist = member.get("trails_list") or []
    if not tlist and isinstance(member.get("trails"), dict):
        tlist = list(member["trails"].values())
    if not tlist:
        return None
    out = {code: 0 for code in CAP}
    found = 0
    for item in tlist:
        code = TOWER_NAME_MAP.get(str(item.get("name", "")))
        stage = item.get("stage")
        if code and stage is not None:
            out[code] = int(stage)
            found += 1
    return out if found > 0 else None


def _compute_reliability_flag(has_mt: bool, has_mig: bool) -> str:
    if has_mt and has_mig:
        return "A"
    if has_mt:
        return "B"
    if has_mig:
        return "C"
    return "D"


def score_member(
    power_m: float,
    mig: float | None,
    stove: int | float | None,
    towers: dict[str, int] | None,
) -> dict[str, Any]:
    """Compute PCS (0-1000), DTV (0-100), role diagnostics, and Flag A-D."""
    tg = compute_tg_tier(stove)
    has_mt = towers is not None
    has_mig = mig is not None and mig > 0
    flag = _compute_reliability_flag(has_mt, has_mig)

    if flag == "D":
        return {
            "flag": "D",
            "pcs": None,
            "pcs_joiner": None,
            "base_M": None,
            "troop_M": None,
            "phi": None,
            "dtv": None,
            "tg": tg,
            "fat_warn": False,
            "egc_M": None,
            "join_value": None,
            "density": None,
            "quadrant": "D_UNSCORED",
        }

    q_core = (
        sum(W[k] * clip(towers[k] / CAP[k], 0.0, 1.0) for k in W)
        if has_mt and towers is not None
        else None
    )
    tc = min(int(stove), 70) if stove is not None and stove > 0 else 30
    wps = (float(mig) / tc + 2226.0) if has_mig and mig is not None else None

    if has_mig and wps is not None:
        nw = clip(wps / WPS_CAP, 0.0, 1.0)
    else:
        assert q_core is not None
        nw = clip(1.362 * q_core - 0.306, 0.0, 1.0)
        wps = max(WPS_CAP * nw, 1.0)

    if q_core is None:
        q_core_est = clip((nw + 0.306) / 1.362, 0.0, 1.0)
        pcs = 1000.0 * q_core_est
    elif not has_mig or mig is None:
        pcs = 1000.0 * clip(q_core, 0.0, 1.0)
    else:
        pcs = 1000.0 * clip((1.0 - LAMBDA) * q_core + LAMBDA * nw, 0.0, 1.0)

    base = BASE_POWER_COEF * (max(wps, 1.0) ** BASE_POWER_EXP)
    troop = max(power_m - base, 0.0)
    phi = troop / power_m if power_m > 0 else 0.0
    a = clip(math.log1p(troop / 20.0) / A_DEN, 0.0, 1.0)
    s = clip((phi - 0.15) / 0.65, 0.02, 1.0)
    qf = max(1.0 - 0.04 * (8 - tg), 0.60)
    dtv = 100.0 * qf * (a ** 0.6) * (s ** 0.4)

    pcs_j = (
        1000.0 * (sum(WJ[k] * clip(towers[k] / CAP[k], 0.0, 1.0) for k in WJ) + 0.25 * tg / 8.0)
        if has_mt and towers is not None
        else None
    )
    quadrant = (
        "A" if pcs >= 600 and dtv >= 60 else
        "B" if dtv >= 60 else
        "C" if pcs >= 600 else
        "D"
    )
    return {
        "flag": flag,
        "pcs": round(pcs),
        "pcs_joiner": round(pcs_j) if pcs_j is not None else None,
        "base_M": round(base, 1),
        "troop_M": round(troop, 1),
        "phi": round(phi, 3),
        "dtv": round(dtv, 1),
        "tg": tg,
        "fat_warn": bool(tg <= 6 and a >= 0.70),
        "egc_M": round(troop * ((tg / 8.0) ** 2), 1),
        "join_value": round((pcs_j / 1000.0) * dtv, 1) if pcs_j is not None else None,
        "density": round(pcs / math.sqrt(power_m), 1) if power_m > 0 else None,
        "quadrant": quadrant,
    }


def score_roster(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score every member record in a MightPulse alliance dump."""
    scored = []
    for m in members:
        power_m = round(float(m.get("power") or 0.0) / 1e6, 1)
        mig = m.get("migrant_score")
        stove = m.get("stove_lv")
        towers = extract_towers(m)
        res = score_member(power_m, mig, stove, towers)
        scored.append({
            "uid": m.get("uid"),
            "nick_name": m.get("nick_name"),
            "power_M": power_m,
            "migrant_score": mig,
            "stove_lv": stove,
            "mystic_trial": m.get("mystic_trial"),
            "kills": m.get("kills"),
            "towers": towers,
            **res,
        })
    return scored


def summarize_alliance(label: str, scored: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    """Compute top-N summary statistics separated by reliability flags."""
    valid = sorted(
        [r for r in scored if r["pcs"] is not None],
        key=lambda r: (r["pcs"], r["dtv"] or 0.0, r["power_M"]),
        reverse=True,
    )
    top_n = valid[:limit]
    flags_all = {f: sum(1 for r in scored if r["flag"] == f) for f in ("A", "B", "C", "D")}
    flags_top = {f: sum(1 for r in top_n if r["flag"] == f) for f in ("A", "B", "C", "D")}
    quads_top = {q: sum(1 for r in top_n if r["quadrant"] == q) for q in ("A", "B", "C", "D")}
    unscored_300m = [r for r in scored if r["flag"] == "D" and r["power_M"] >= 300.0]

    def _avg(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "label": label,
        "limit": limit,
        "total_members": len(scored),
        "scored_count": len(valid),
        "top_n_evaluated": len(top_n),
        "flags_all": flags_all,
        "flags_top": flags_top,
        "quads_top": quads_top,
        "fat_warn_top": sum(1 for r in top_n if r["fat_warn"]),
        "unscored_300m_count": len(unscored_300m),
        "avg_pcs_top_n": _avg([float(r["pcs"]) for r in top_n]),
        "avg_pcs_top4": _avg([float(r["pcs"]) for r in top_n[:4]]),
        "avg_pcs_5_10": _avg([float(r["pcs"]) for r in top_n[4:10]]),
        "avg_pcs_11_plus": _avg([float(r["pcs"]) for r in top_n[10:]]),
        "avg_dtv_top_n": _avg([float(r["dtv"]) for r in top_n if r["dtv"] is not None]),
        "total_troop_m_top_n": round(sum(float(r["troop_M"] or 0.0) for r in top_n), 1),
        "total_egc_m_top_n": round(sum(float(r["egc_M"] or 0.0) for r in top_n), 1),
        "top_roster": top_n,
        "unscored_300m": sorted(unscored_300m, key=lambda r: r["power_M"], reverse=True),
    }


def _load_members_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["members"] if isinstance(data, dict) else data


def fetch_mightpulse_members(aid: int) -> list[dict[str, Any]]:
    """Fetch live alliance member roster from MightPulse API."""
    from curl_cffi import requests  # Lazy import so offline mode needs no curl_cffi

    url = f"https://mightpulse.com/api/alliances/{aid}/members"
    res = requests.get(url, impersonate="chrome120", timeout=25)
    res.raise_for_status()
    data = res.json()
    return data["members"] if isinstance(data, dict) else data


def find_alliance_id(kid: int, abbr: str) -> int:
    """Resolve alliance aid on MightPulse map endpoint by kingdom ID and abbr."""
    from curl_cffi import requests

    url = f"https://mightpulse.com/api/map?kid={kid}&layers=cities&limit=50000"
    res = requests.get(url, impersonate="chrome120", timeout=25)
    res.raise_for_status()
    data = res.json()
    alliances = data.get("alliances") or []
    target = abbr.strip().lower()
    for a in alliances:
        if str(a.get("abbr", "")).strip().lower() == target:
            return int(a["aid"])
    raise ValueError(f"Alliance '{abbr}' not found in kingdom #{kid}")


def render_markdown_summary(self_sum: dict[str, Any], opp_sum: dict[str, Any] | None) -> str:
    """Render concise deterministic Markdown comparison & scorecard."""
    lines = ["# KingShot PvP 2軸スコア比較サマリー", ""]
    if opp_sum:
        lines += [
            "| 項目 | 自チーム (`self`) | 相手 (`opp`) |",
            "| :--- | :---: | :---: |",
            f"| 対象 / 評価人数 | {self_sum['label']} ({self_sum['top_n_evaluated']}/{self_sum['limit']}) | {opp_sum['label']} ({opp_sum['top_n_evaluated']}/{opp_sum['limit']}) |",
            f"| 平均 PCS (全体 / Top4 / #5-10 / #11+) | {self_sum['avg_pcs_top_n']} / {self_sum['avg_pcs_top4']} / {self_sum['avg_pcs_5_10']} / {self_sum['avg_pcs_11_plus']} | {opp_sum['avg_pcs_top_n']} / {opp_sum['avg_pcs_top4']} / {opp_sum['avg_pcs_5_10']} / {opp_sum['avg_pcs_11_plus']} |",
            f"| 平均 DTV | {self_sum['avg_dtv_top_n']} | {opp_sum['avg_dtv_top_n']} |",
            f"| 推定兵士戦力合計 (`Troop_M`) | {self_sum['total_troop_m_top_n']:,.1f}M | {opp_sum['total_troop_m_top_n']:,.1f}M |",
            f"| TG8換算実効戦力 (`EGC_M`) | {self_sum['total_egc_m_top_n']:,.1f}M | {opp_sum['total_egc_m_top_n']:,.1f}M |",
            f"| 象限内訳 (A / B / C / D) | A:{self_sum['quads_top']['A']} B:{self_sum['quads_top']['B']} C:{self_sum['quads_top']['C']} D:{self_sum['quads_top']['D']} | A:{opp_sum['quads_top']['A']} B:{opp_sum['quads_top']['B']} C:{opp_sum['quads_top']['C']} D:{opp_sum['quads_top']['D']} |",
            f"| `FAT_WARN` / 未クロール300M+ | {self_sum['fat_warn_top']}名 / {self_sum['unscored_300m_count']}名 | {opp_sum['fat_warn_top']}名 / {opp_sum['unscored_300m_count']}名 |",
            "",
        ]
    for s in ([self_sum, opp_sum] if opp_sum else [self_sum]):
        lines += [
            f"## {s['label']} 上位 {s['top_n_evaluated']} 名",
            "| # | 名前 | Flag | PCS | Join | Stv(TG) | 推定Troop(M) | φ | DTV | 実効EGC(M) | 象限 |",
            "| :---: | :--- | :---: | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: |",
        ]
        for idx, r in enumerate(s["top_roster"], 1):
            fat_mark = " ⚠FAT" if r["fat_warn"] else ""
            pj = r["pcs_joiner"] if r["pcs_joiner"] is not None else "-"
            lines.append(
                f"| {idx} | {r['nick_name']} | {r['flag']} | {r['pcs']} | {pj} | "
                f"{r['stove_lv'] or '-'}(TG{r['tg']}) | {r['troop_M']} | {r['phi']:.2f} | "
                f"{r['dtv']} | {r['egc_M']} | {r['quadrant']}{fat_mark} |"
            )
        lines.append("")
    return "\n".join(lines)


def _resolve_input(
    json_path: str | None,
    aid: int | None,
    kid: int | None,
    abbr: str | None,
) -> list[dict[str, Any]]:
    if json_path:
        return _load_members_json(Path(json_path))
    if aid is not None:
        return fetch_mightpulse_members(aid)
    if kid is not None and abbr:
        resolved = find_alliance_id(kid, abbr)
        return fetch_mightpulse_members(resolved)
    raise ValueError("Specify --*-json, --*-aid, or both --*-kid and --*-abbr")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="KingShot PvP Two-Axis Scorer (PCS & DTV)")
    parser.add_argument("--self-json", help="Saved JSON path for self alliance")
    parser.add_argument("--self-aid", type=int, help="MightPulse alliance ID for self")
    parser.add_argument("--self-kid", type=int, help="Kingdom ID for self")
    parser.add_argument("--self-abbr", help="Alliance tag for self")
    parser.add_argument("--self-label", default="SELF")
    parser.add_argument("--self-limit", type=int, default=30)

    parser.add_argument("--opp-json", help="Saved JSON path for opponent alliance")
    parser.add_argument("--opp-aid", type=int, help="MightPulse alliance ID for opponent")
    parser.add_argument("--opp-kid", type=int, help="Kingdom ID for opponent")
    parser.add_argument("--opp-abbr", help="Alliance tag for opponent")
    parser.add_argument("--opp-label", default="OPPONENT")
    parser.add_argument("--opp-limit", type=int, default=30)

    parser.add_argument("--out-json", help="Write full structured JSON result to path")
    parser.add_argument("--out-md", help="Write Markdown table report to path")
    args = parser.parse_args()

    self_raw = _resolve_input(args.self_json, args.self_aid, args.self_kid, args.self_abbr)
    self_scored = score_roster(self_raw)
    self_sum = summarize_alliance(args.self_label, self_scored, args.self_limit)

    opp_sum = None
    opp_scored = None
    if any(x is not None for x in (args.opp_json, args.opp_aid, args.opp_abbr)):
        opp_raw = _resolve_input(args.opp_json, args.opp_aid, args.opp_kid, args.opp_abbr)
        opp_scored = score_roster(opp_raw)
        opp_sum = summarize_alliance(args.opp_label, opp_scored, args.opp_limit)

    md_text = render_markdown_summary(self_sum, opp_sum)
    if args.out_md:
        Path(args.out_md).write_text(md_text, encoding="utf-8")
    if args.out_json:
        payload = {"self": self_sum, "opp": opp_sum, "self_all": self_scored, "opp_all": opp_scored}
        Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.out_md:
        print(md_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
