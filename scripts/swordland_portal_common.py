#!/usr/bin/env python3
"""Shared reusable HTML/CSS/JS renderer for 4-language (ja/en/ar/tr) Swordland Showdown portals."""

from __future__ import annotations

import html
import json
from typing import Any

PORTAL_CSS = """
    :root {
      --bg-0: #090d16;
      --bg-1: #111827;
      --bg-card: rgba(20, 29, 47, 0.9);
      --bg-glass: rgba(15, 23, 42, 0.78);
      --border: rgba(245, 158, 11, 0.25);
      --border-strong: rgba(245, 158, 11, 0.55);
      --gold: #f59e0b;
      --gold-lt: #fde68a;
      --blue: #38bdf8;
      --blue-bg: rgba(56, 189, 248, 0.14);
      --purple: #a855f7;
      --red: #ef4444;
      --red-bg: rgba(239, 68, 68, 0.14);
      --green: #10b981;
      --green-bg: rgba(16, 185, 129, 0.14);
      --amber-bg: rgba(245, 158, 11, 0.14);
      --text: #f3f4f6;
      --muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: 'Noto Sans JP', 'Noto Sans Arabic', sans-serif;
      background: var(--bg-0);
      color: var(--text);
      line-height: 1.7;
      background-image:
        radial-gradient(circle at 12% 15%, rgba(56, 189, 248, 0.10) 0%, transparent 42%),
        radial-gradient(circle at 88% 35%, rgba(168, 85, 247, 0.10) 0%, transparent 45%),
        radial-gradient(circle at 50% 85%, rgba(245, 158, 11, 0.07) 0%, transparent 45%);
      background-attachment: fixed;
    }
    html[dir="rtl"] body {
      font-family: 'Noto Sans Arabic', 'Noto Sans JP', sans-serif;
    }
    .t-formula, .map-board-wrap, canvas, code {
      direction: ltr;
      unicode-bidi: isolate;
    }
    .t-formula { text-align: left; }

    .top-nav {
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(12px);
      background: rgba(9, 13, 22, 0.90);
      border-bottom: 1px solid var(--border);
    }
    .top-nav-inner {
      max-width: 1180px;
      margin: 0 auto;
      padding: 9px 16px;
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }
    .brand-tag { font-weight: 900; font-size: 0.9rem; color: var(--gold-lt); letter-spacing: 0.03em; }
    .nav-right {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      max-width: 100%;
      min-width: 0;
    }
    .nav-links { display: flex; gap: 6px; flex-wrap: wrap; min-width: 0; }
    .nav-links a {
      color: var(--muted);
      text-decoration: none;
      font-size: 0.8rem;
      font-weight: 700;
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px solid transparent;
      transition: 0.18s ease;
    }
    .nav-links a:hover {
      color: var(--gold-lt);
      border-color: var(--border-strong);
      background: rgba(245, 158, 11, 0.1);
    }
    .lang-bar {
      display: inline-flex;
      gap: 4px;
      align-items: center;
      flex-wrap: wrap;
      max-width: 100%;
      background: rgba(15, 23, 42, 0.92);
      border: 1px solid var(--border-strong);
      border-radius: 999px;
      padding: 3px;
      direction: ltr;
      flex-shrink: 0;
    }
    .lang-btn {
      border: none;
      background: transparent;
      color: #cbd5e1;
      font-size: 0.74rem;
      font-weight: 800;
      padding: 4px 9px;
      border-radius: 999px;
      cursor: pointer;
      transition: 0.15s;
      white-space: nowrap;
      font-family: 'Noto Sans JP', 'Noto Sans Arabic', sans-serif;
    }
    .lang-btn:hover { color: #ffffff; background: rgba(255, 255, 255, 0.08); }
    .lang-btn.active {
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: #090d16;
      box-shadow: 0 2px 8px rgba(245, 158, 11, 0.35);
    }
    .hero-lang-strip {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }
    .hero-lang-bar {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      background: rgba(9, 13, 22, 0.85);
      border: 1px solid var(--border-strong);
      border-radius: 12px;
      padding: 5px 8px;
      direction: ltr;
    }
    .hero-lang-bar .lang-lbl {
      font-size: 0.74rem;
      font-weight: 800;
      color: var(--gold-lt);
      padding-inline: 4px;
    }
    .hero-lang-bar .lang-btn { font-size: 0.8rem; padding: 5px 11px; }

    @media (max-width: 640px) {
      .top-nav-inner { padding: 8px 12px; gap: 6px; }
      .nav-right { width: 100%; justify-content: space-between; }
      .nav-links {
        flex-wrap: nowrap;
        overflow-x: auto;
        max-width: 100%;
        padding-bottom: 4px;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: thin;
      }
      .nav-links a { white-space: nowrap; flex: 0 0 auto; font-size: 0.76rem; padding: 4px 8px; }
      .lang-btn { font-size: 0.72rem; padding: 3px 7px; }
      .grid-2, .grid-3, .glossary-grid { grid-template-columns: 1fr; }
    }

    .container { max-width: 1180px; margin: 0 auto; padding: 20px 16px 84px; }
    .hero {
      position: relative;
      border-radius: 20px;
      overflow: hidden;
      border: 1px solid var(--border-strong);
      margin-bottom: 28px;
      min-height: 360px;
      display: flex;
      align-items: flex-end;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.55);
    }
    .hero-bg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center 35%;
      filter: brightness(0.62) saturate(1.1);
    }
    .hero-overlay {
      position: relative;
      z-index: 2;
      width: 100%;
      padding: 28px 28px 28px;
      background: linear-gradient(180deg, rgba(9, 13, 22, 0.12) 0%, rgba(9, 13, 22, 0.84) 52%, rgba(9, 13, 22, 0.96) 100%);
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      font-weight: 800;
      padding: 4px 12px;
      border-radius: 999px;
      background: rgba(245, 158, 11, 0.18);
      border: 1px solid var(--border-strong);
      color: var(--gold-lt);
    }
    .hero h1 {
      font-size: clamp(1.45rem, 3.2vw, 2.3rem);
      font-weight: 900;
      line-height: 1.28;
      margin-bottom: 10px;
      text-shadow: 0 2px 12px rgba(0, 0, 0, 0.8);
    }
    .hero-sub { color: #d1d5db; font-size: 0.95rem; max-width: 880px; }
    .match-strip {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .match-box {
      background: rgba(15, 23, 42, 0.86);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 14px;
    }
    .match-box.self { border-color: rgba(56, 189, 248, 0.55); }
    .match-box.opp { border-color: rgba(168, 85, 247, 0.55); }
    .match-box .lbl { font-size: 0.75rem; color: var(--muted); font-weight: 700; }
    .match-box .val { font-size: 1.12rem; font-weight: 900; margin-top: 2px; }

    section { margin-bottom: 42px; scroll-margin-top: 72px; }
    .sec-head {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }
    .sec-num {
      font-family: 'Cinzel', serif;
      font-size: 1.05rem;
      font-weight: 900;
      background: linear-gradient(135deg, #f59e0b, #b45309);
      color: #090d16;
      padding: 3px 11px;
      border-radius: 8px;
      direction: ltr;
    }
    .sec-head h2 { font-size: clamp(1.18rem, 2.3vw, 1.52rem); font-weight: 900; }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    }
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 16px; }
    .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }
    .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
    .grid-2 > *, .grid-3 > *, .grid-4 > *, .kpi-grid > *, .glossary-grid > *, .dict-grid > *, .match-strip > * { min-width: 0; }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .kpi {
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 14px;
    }
    .kpi .k-lbl { font-size: 0.76rem; color: var(--muted); font-weight: 700; }
    .kpi .k-val { font-size: 1.25rem; font-weight: 900; color: var(--gold-lt); margin-top: 2px; direction: ltr; text-align: start; }
    .kpi .k-sub { font-size: 0.76rem; color: #cbd5e1; margin-top: 2px; }

    .callout { border-radius: 14px; padding: 14px 16px; margin-bottom: 16px; border: 1px solid; }
    .callout.ok { background: var(--green-bg); border-color: rgba(16, 185, 129, 0.45); }
    .callout.ng { background: var(--red-bg); border-color: rgba(239, 68, 68, 0.45); }
    .callout.warn { background: var(--amber-bg); border-color: rgba(245, 158, 11, 0.45); }
    .callout.info { background: var(--blue-bg); border-color: rgba(56, 189, 248, 0.45); }
    .callout h3 { font-size: 1rem; font-weight: 900; margin-bottom: 6px; }
    .callout ul { padding-inline-start: 18px; font-size: 0.9rem; }
    .callout li + li { margin-top: 4px; }

    .filter-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
    .search-input {
      flex: 1 1 220px;
      min-width: 200px;
      padding: 9px 14px;
      border-radius: 10px;
      border: 1px solid var(--border-strong);
      background: #0b1120;
      color: var(--text);
      font-size: 0.92rem;
    }
    .tab-btn {
      padding: 7px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(15, 23, 42, 0.85);
      color: #d1d5db;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      transition: 0.15s;
    }
    .tab-btn.active, .tab-btn:hover { background: var(--gold); color: #090d16; border-color: var(--gold); }
    .table-wrap { overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
    table { width: 100%; border-collapse: collapse; font-size: 0.86rem; min-width: 720px; }
    th, td { padding: 9px 10px; text-align: start; border-bottom: 1px solid rgba(255, 255, 255, 0.06); vertical-align: middle; }
    th {
      background: rgba(15, 23, 42, 0.95);
      color: var(--gold-lt);
      font-weight: 800;
      font-size: 0.78rem;
      white-space: nowrap;
    }
    tr:hover td { background: rgba(255, 255, 255, 0.03); }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.72rem; font-weight: 800; white-space: nowrap; }
    #oppNotesList .badge { white-space: normal; max-width: 100%; border-radius: 10px; line-height: 1.4; text-align: start; }
    .b-band1 { background: rgba(56, 189, 248, 0.22); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.5); }
    .b-band2 { background: rgba(16, 185, 129, 0.22); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.5); }
    .b-band3 { background: rgba(168, 85, 247, 0.22); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.5); }
    .b-band4 { background: rgba(245, 158, 11, 0.22); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.5); }
    .b-band5 { background: rgba(239, 68, 68, 0.22); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.5); }

    .ui-shot {
      background: rgba(11, 17, 32, 0.9);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .ui-shot > img { width: 100%; max-height: 310px; object-fit: contain; background: #060911; display: block; }
    .ui-shot .cap img { width: 18px; height: 18px; display: inline-block; vertical-align: text-bottom; }
    .ui-shot .cap { padding: 10px 12px; font-size: 0.82rem; color: #d1d5db; border-top: 1px solid rgba(255, 255, 255, 0.06); }
    .ui-tag { display: inline-block; font-size: 0.68rem; font-weight: 800; padding: 1px 7px; border-radius: 6px; margin-inline-end: 6px; vertical-align: middle; }
    .tag-real { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.45); }
    .tag-gen { background: rgba(168, 85, 247, 0.2); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.45); }

    .hero-strip { display: grid; grid-template-columns: repeat(auto-fill, minmax(112px, 1fr)); gap: 10px; margin-top: 10px; }
    .hero-chip {
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 8px;
      text-align: center;
    }
    .hero-chip.ban { border-color: rgba(239, 68, 68, 0.65); background: rgba(127, 29, 29, 0.25); }
    .hero-chip.limit { border-color: rgba(245, 158, 11, 0.65); background: rgba(120, 53, 15, 0.25); }
    .hero-chip img { width: 60px; height: 60px; border-radius: 10px; object-fit: cover; border: 2px solid rgba(255, 255, 255, 0.15); }
    .hero-chip .h-name { font-size: 0.8rem; font-weight: 800; margin-top: 4px; }
    .hero-chip .h-eff { font-size: 0.7rem; color: var(--muted); line-height: 1.3; margin-top: 2px; }

    .map-board-wrap { position: relative; border-radius: 16px; overflow: hidden; border: 1px solid var(--border-strong); background: #060911; direction: ltr; }
    .map-board-wrap img.base { width: 100%; display: block; filter: brightness(0.84); }
    .map-svg-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
    .map-pin { position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: transform 0.16s ease; }
    .map-pin:hover { transform: translate(-50%, -50%) scale(1.1); z-index: 10; }
    .map-pin img { width: clamp(28px, 4.4vw, 50px); height: clamp(28px, 4.4vw, 50px); object-fit: contain; filter: drop-shadow(0 3px 8px rgba(0,0,0,0.9)); }
    .map-pin .m-lbl {
      margin-top: 1px;
      padding: 1px 6px;
      border-radius: 6px;
      font-size: clamp(0.6rem, 1.05vw, 0.76rem);
      font-weight: 900;
      background: rgba(9, 13, 22, 0.9);
      border: 1px solid rgba(245, 158, 11, 0.55);
      color: #fef08a;
      white-space: nowrap;
      direction: auto;
    }
    .map-pin.priority .m-lbl { background: rgba(14, 116, 144, 0.95); border-color: #38bdf8; color: #ffffff; }
    .bell-emblem {
      width: clamp(28px, 4.4vw, 46px);
      height: clamp(28px, 4.4vw, 46px);
      border-radius: 50%;
      background: radial-gradient(circle at 32% 30%, #38bdf8, #0e7490 70%, #082f49);
      border: 2px solid #fde68a;
      display: grid;
      place-items: center;
      font-size: clamp(14px, 2.2vw, 22px);
      box-shadow: 0 3px 12px rgba(56, 189, 248, 0.55);
    }
    .phase-detail-box { margin-top: 12px; padding: 12px 14px; border-radius: 12px; background: rgba(15, 23, 42, 0.9); border: 1px solid var(--border); font-size: 0.88rem; }

    .th-help { color: var(--gold-lt); text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
    .th-help:hover { color: #38bdf8; text-decoration: underline; }
    .q-dot {
      display: inline-grid;
      place-items: center;
      width: 15px;
      height: 15px;
      border-radius: 50%;
      font-size: 0.65rem;
      font-weight: 900;
      background: rgba(56, 189, 248, 0.22);
      border: 1px solid rgba(56, 189, 248, 0.6);
      color: #bae6fd;
    }
    .glossary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
    .term-card {
      background: rgba(15, 23, 42, 0.92);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 15px 16px;
      scroll-margin-top: 72px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .term-card .t-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
    .term-card .t-title { font-size: 1.02rem; font-weight: 900; color: var(--gold-lt); }
    .term-card .t-range {
      font-size: 0.72rem;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(56, 189, 248, 0.14);
      border: 1px solid rgba(56, 189, 248, 0.4);
      color: #7dd3fc;
    }
    .term-card .t-easy {
      font-size: 0.85rem;
      color: #f3f4f6;
      background: rgba(30, 41, 59, 0.72);
      border-inline-start: 3px solid var(--gold);
      padding: 7px 10px;
      border-radius: 6px;
    }
    .term-card .t-formula {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.76rem;
      line-height: 1.55;
      color: #bae6fd;
      background: #060911;
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 8px;
      padding: 8px 10px;
      overflow-x: auto;
    }
    .term-card .t-use { font-size: 0.82rem; color: #d1d5db; }
    .dict-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(235px, 1fr)); gap: 10px; margin-top: 14px; }
    .dict-item { background: rgba(15, 23, 42, 0.78); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 11px 13px; font-size: 0.8rem; color: #d1d5db; }
    .dict-item > strong:first-child { display: block; color: var(--gold-lt); font-size: 0.86rem; margin-bottom: 3px; }
    .fac-card {
      display: flex;
      gap: 12px;
      align-items: center;
      background: rgba(15, 23, 42, 0.86);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px 12px;
    }
    .fac-card img { width: 58px; height: 58px; object-fit: contain; flex-shrink: 0; border-radius: 8px; background: #080c15; }
    .fac-card h4 { font-size: 0.9rem; font-weight: 900; color: var(--gold-lt); }
    .fac-card p { font-size: 0.78rem; color: #d1d5db; margin-top: 2px; }
    footer { border-top: 1px solid var(--border); padding-top: 20px; margin-top: 40px; font-size: 0.8rem; color: var(--muted); }
"""

LANG_BUTTONS_HTML = """
  <button class="lang-btn active" type="button" data-lang-btn="ja">🇯🇵 日本語</button>
  <button class="lang-btn" type="button" data-lang-btn="en">🇬🇧 EN</button>
  <button class="lang-btn" type="button" data-lang-btn="ar">🇸🇦 العربية</button>
  <button class="lang-btn" type="button" data-lang-btn="tr">🇹🇷 TR</button>
"""


def _render_kpi_cards(kpis_num: list[dict[str, str]], kpis_ja: list[dict[str, str]]) -> str:
    blocks = []
    for i, (num, txt) in enumerate(zip(kpis_num, kpis_ja)):
        style = f' style="color:{num["val_color"]}"' if num.get("val_color") else ""
        sub_val = f' <span style="font-size:0.85rem;color:#9ca3af">{num["opp_val"]}</span>' if num.get("opp_val") else ""
        blocks.append(
            f'<div class="kpi"><div class="k-lbl" data-t="kpis.{i}.label">{html.escape(txt["label"])}</div>'
            f'<div class="k-val"{style}>{num["self_val"]}{sub_val}</div>'
            f'<div class="k-sub" data-t="kpis.{i}.sub">{html.escape(txt["sub"])}</div></div>'
        )
    return "\n".join(blocks)


def _render_glossary(ja: dict[str, Any]) -> str:
    g = ja["glossary"]
    cards_html = []
    for key in ("tg", "pcs", "join", "troop", "dtv"):
        c = g["cards"][key]
        cards_html.append(
            f"""
        <article id="g-{key}" class="term-card">
          <div class="t-head">
            <span class="t-title" data-t="glossary.cards.{key}.title">{html.escape(c["title"])}</span>
            <span class="t-range" data-t="glossary.cards.{key}.range">{html.escape(c["range"])}</span>
          </div>
          <div class="t-easy" data-th="glossary.cards.{key}.easy_html">{c["easy_html"]}</div>
          <div class="t-formula" data-th="glossary.cards.{key}.formula_html">{c["formula_html"]}</div>
          <div class="t-use"><strong data-t="glossary.use_prefix">{html.escape(g["use_prefix"])}</strong><span data-th="glossary.cards.{key}.use_html">{c["use_html"]}</span></div>
        </article>"""
        )

    dict_html = "\n".join(
        f'<div class="dict-item"><strong data-t="glossary.dict.{i}.title">{html.escape(d["title"])}</strong>'
        f'<span data-th="glossary.dict.{i}.body_html">{d["body_html"]}</span></div>'
        for i, d in enumerate(g["dict"])
    )
    return f"""
    <section id="glossary">
      <div class="sec-head">
        <span class="sec-num">03</span>
        <h2 data-t="sec_titles.s03">{html.escape(ja["sec_titles"]["s03"])}</h2>
      </div>
      <div class="card" style="margin-bottom:16px">
        <p style="font-size:0.88rem;color:#e5e7eb" data-th="glossary.intro_html">{g["intro_html"]}</p>
      </div>
      <div class="glossary-grid">{"".join(cards_html)}</div>
      <div class="card" style="margin-top:14px">
        <h3 style="font-size:0.96rem;color:var(--gold-lt);margin-bottom:4px" data-t="glossary.dict_heading">{html.escape(g["dict_heading"])}</h3>
        <div class="dict-grid">{dict_html}</div>
      </div>
    </section>
"""


def _render_hero_chips(ja_heroes: dict[str, list[str]], slugs: list[tuple[str, str]]) -> str:
    chips = []
    for slug, cls in slugs:
        name, eff = ja_heroes[slug]
        extra = f' class="hero-chip {cls}"' if cls else ' class="hero-chip"'
        eff_style = ' style="color:#fcd34d"' if cls == "limit" else (' style="color:#fca5a5"' if cls == "ban" else "")
        chips.append(
            f'<div{extra}><img src="assets/heroes/{slug}.png" alt="{html.escape(name)}">'
            f'<div class="h-name" data-t="basic_ui.heroes.{slug}.0">{html.escape(name)}</div>'
            f'<div class="h-eff"{eff_style} data-t="basic_ui.heroes.{slug}.1">{html.escape(eff)}</div></div>'
        )
    return "\n".join(chips)


def _render_basic_ui(ja: dict[str, Any]) -> str:
    b = ja["basic_ui"]
    shot_meta = [
        ("assets/generated/infirmary_ready_scene.jpg", "医務室", True),
        ("assets/swordland/ui_entry_timezone_ja.png", "軍団1エントリー", False),
        ("assets/ui/ui_tg8_refinement_ja.png", "精製黄金TG8", False),
        ("assets/ui/ui_chenko_skill1_crop.jpg", "チェンコ", False),
        ("assets/ui/ui_rally_panel.png", "Rally", False),
        ("assets/ui/ui_garrison_list.png", "Garrison", False),
    ]
    cards_row = []
    for i, (src, alt, is_gen) in enumerate(shot_meta):
        tag_key = "basic_ui.tag_gen" if is_gen else "basic_ui.tag_real"
        tag_cls = "tag-gen" if is_gen else "tag-real"
        tag_txt = b["tag_gen"] if is_gen else b["tag_real"]
        cards_row.append(
            f'<div class="ui-shot"><img src="{src}" alt="{html.escape(alt)}">'
            f'<div class="cap"><span class="ui-tag {tag_cls}" data-t="{tag_key}">{html.escape(tag_txt)}</span>'
            f'<span data-th="basic_ui.cards.{i}">{b["cards"][i]}</span></div></div>'
        )

    atk_heroes = _render_hero_chips(b["heroes"], [("chenko", ""), ("yeonwoo", ""), ("amane", ""), ("margot", ""), ("vivian", ""), ("hilde", ""), ("petra", "limit")])
    def_heroes = _render_hero_chips(b["heroes"], [("gordon", ""), ("howard", ""), ("saul", ""), ("eric", ""), ("fahd", "")])
    ban_heroes = _render_hero_chips(b["heroes"], [("long-fei", "ban"), ("jabel", "ban"), ("helga", "ban"), ("zoe", "ban"), ("sophia", "ban")])

    return f"""
    <section id="basic-ui">
      <div class="sec-head">
        <span class="sec-num">04</span>
        <h2 data-t="sec_titles.s04">{html.escape(ja["sec_titles"]["s04"])}</h2>
      </div>
      <div class="grid-3" style="margin-bottom:18px">{"".join(cards_row[:3])}</div>
      <div class="grid-3" style="margin-bottom:18px">{"".join(cards_row[3:])}</div>
      <div class="card">
        <h3 style="font-size:1.05rem;font-weight:900;color:var(--gold-lt);margin-bottom:6px" data-t="basic_ui.hero_title">{html.escape(b["hero_title"])}</h3>
        <p style="font-size:0.86rem;color:#d1d5db" data-th="basic_ui.hero_desc_html">{b["hero_desc_html"]}</p>
        <h4 style="margin-top:14px;font-size:0.9rem;color:#7dd3fc" data-t="basic_ui.hero_atk_title">{html.escape(b["hero_atk_title"])}</h4>
        <div class="hero-strip">{atk_heroes}</div>
        <div class="grid-2" style="margin-top:16px">
          <div>
            <h4 style="font-size:0.9rem;color:#6ee7b7" data-t="basic_ui.hero_def_title">{html.escape(b["hero_def_title"])}</h4>
            <div class="hero-strip">{def_heroes}</div>
          </div>
          <div>
            <h4 style="font-size:0.9rem;color:#fca5a5" data-t="basic_ui.hero_ban_title">{html.escape(b["hero_ban_title"])}</h4>
            <div class="hero-strip">{ban_heroes}</div>
          </div>
        </div>
      </div>
    </section>
"""


def _render_tactical_map(ja: dict[str, Any]) -> str:
    m = ja["map"]
    pins = m["pins"]
    fac_imgs = [
        "assets/swordland/facility_royal_stables.png",
        "assets/swordland/facility_swordshrine.png",
        "assets/swordland/facility_sanctum.png",
        "assets/swordland/facility_reformation.png",
        "assets/swordland/facility_mercenary.png",
        "assets/swordland/facility_abbey.png",
    ]
    fac_cards = "\n".join(
        f'<div class="fac-card"><img src="{fac_imgs[i]}" alt=""><div>'
        f'<h4 data-t="map.facilities.{i}.title">{html.escape(f["title"])}</h4>'
        f'<p data-th="map.facilities.{i}.body_html">{f["body_html"]}</p></div></div>'
        for i, f in enumerate(m["facilities"])
    )
    ui_imgs = [
        "assets/swordland/ui_rules_swordshrine.png",
        "assets/swordland/ui_rules_stables_buff.png",
        "assets/swordland/ui_swordshrine_garrison_crop.jpg",
        "assets/swordland/ui_battle_cluster_march.png",
    ]
    ui_cards = "\n".join(
        f'<div class="ui-shot"><img src="{ui_imgs[i]}" alt=""><div class="cap"><span class="ui-tag tag-real" data-t="basic_ui.tag_real">{html.escape(ja["basic_ui"]["tag_real"])}</span><span data-th="map.ui_caps.{i}">{m["ui_caps"][i]}</span></div></div>'
        for i in range(4)
    )
    return f"""
    <section id="tactical-map">
      <div class="sec-head">
        <span class="sec-num">05</span>
        <h2 data-t="sec_titles.s05">{html.escape(ja["sec_titles"]["s05"])}</h2>
      </div>
      <div class="card" style="margin-bottom:18px">
        <div class="filter-bar" style="justify-content:space-between">
          <div>
            <strong style="color:var(--gold-lt)" data-t="map.board_title">{html.escape(m["board_title"])}</strong>
            <span style="font-size:0.78rem;color:var(--muted);margin-inline-start:8px" data-t="map.board_hint">{html.escape(m["board_hint"])}</span>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="tab-btn active" data-phase="p1" data-t="map.btn_p1">{html.escape(m["btn_p1"])}</button>
            <button class="tab-btn" data-phase="p2" data-t="map.btn_p2">{html.escape(m["btn_p2"])}</button>
            <button class="tab-btn" data-phase="p3" data-t="map.btn_p3">{html.escape(m["btn_p3"])}</button>
          </div>
        </div>

        <div class="map-board-wrap">
          <img class="base" src="assets/generated/swordland_tactical_map_base.jpg" alt="Swordland Tactical Map">
          <svg id="mapSvg" class="map-svg-overlay" viewBox="0 0 1000 562" preserveAspectRatio="none"></svg>

          <div class="map-pin priority" style="left:50%;top:50%"><img src="assets/swordland/facility_swordshrine.png" alt="Swordshrine"><span class="m-lbl" data-t="map.pins.swordshrine">{html.escape(pins["swordshrine"])}</span></div>
          <div class="map-pin" style="left:50%;top:24%"><img src="assets/swordland/facility_mercenary.png" alt="Mercenary Camp"><span class="m-lbl" data-t="map.pins.mercenary">{html.escape(pins["mercenary"])}</span></div>
          <div class="map-pin" style="left:50%;top:77%"><img src="assets/swordland/facility_reformation.png" alt="Hall of Reformation"><span class="m-lbl" data-t="map.pins.reformation">{html.escape(pins["reformation"])}</span></div>
          <div class="map-pin priority" style="left:34%;top:13%"><div class="bell-emblem" aria-label="Bell Tower">🔔</div><span class="m-lbl" data-t="map.pins.bell">{html.escape(pins["bell"])}</span></div>
          <div class="map-pin" style="left:66%;top:13%"><img src="assets/swordland/facility_abbey.png" alt="NE Abbey"><span class="m-lbl" data-t="map.pins.ne_abbey">{html.escape(pins["ne_abbey"])}</span></div>
          <div class="map-pin" style="left:25%;top:40%"><img src="assets/swordland/facility_sanctum.png" alt="W Sanctum"><span class="m-lbl" data-t="map.pins.w_sanctum">{html.escape(pins["w_sanctum"])}</span></div>
          <div class="map-pin" style="left:77%;top:43%"><img src="assets/swordland/facility_abbey.png" alt="CE Abbey"><span class="m-lbl" data-t="map.pins.ce_abbey">{html.escape(pins["ce_abbey"])}</span></div>
          <div class="map-pin" style="left:22%;top:60%"><img src="assets/swordland/facility_abbey.png" alt="CW Abbey"><span class="m-lbl" data-t="map.pins.cw_abbey">{html.escape(pins["cw_abbey"])}</span></div>
          <div class="map-pin" style="left:74%;top:61%"><img src="assets/swordland/facility_sanctum.png" alt="E Sanctum"><span class="m-lbl" data-t="map.pins.e_sanctum">{html.escape(pins["e_sanctum"])}</span></div>
          <div class="map-pin" style="left:34%;top:88%"><img src="assets/swordland/facility_abbey.png" alt="SW Abbey"><span class="m-lbl" data-t="map.pins.sw_abbey">{html.escape(pins["sw_abbey"])}</span></div>
          <div class="map-pin priority" style="left:66%;top:88%"><img src="assets/swordland/facility_royal_stables.png" alt="Royal Stables"><span class="m-lbl" data-t="map.pins.stables">{html.escape(pins["stables"])}</span></div>
          <div class="map-pin" style="left:36%;top:30%"><img src="assets/swordland/facility_undercellar.png" alt="Undercellar"><span class="m-lbl" style="font-size:0.62rem" data-t="map.pins.undercellar">{html.escape(pins["undercellar"])}</span></div>
          <div class="map-pin" style="left:64%;top:30%"><img src="assets/swordland/facility_undercellar.png" alt="Undercellar"><span class="m-lbl" style="font-size:0.62rem" data-t="map.pins.undercellar">{html.escape(pins["undercellar"])}</span></div>
          <div class="map-pin" style="left:36%;top:70%"><img src="assets/swordland/facility_undercellar.png" alt="Undercellar"><span class="m-lbl" style="font-size:0.62rem" data-t="map.pins.undercellar">{html.escape(pins["undercellar"])}</span></div>
          <div class="map-pin" style="left:64%;top:70%"><img src="assets/swordland/facility_undercellar.png" alt="Undercellar"><span class="m-lbl" style="font-size:0.62rem" data-t="map.pins.undercellar">{html.escape(pins["undercellar"])}</span></div>
        </div>
        <div id="phaseDetailBox" class="phase-detail-box"></div>
      </div>

      <div class="grid-3" style="margin-bottom:16px">{fac_cards}</div>
      <div class="grid-4">{ui_cards}</div>
    </section>
"""


def render_swordland_portal(cfg: dict[str, Any]) -> str:
    """Assemble full 4-language (ja/en/ar/tr) self-contained Swordland Showdown interactive HTML portal."""
    bundles = cfg["i18n_bundles"]
    ja = bundles["ja"]

    tabs_html = "\n".join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" data-band="{bid}" data-t="roster.tabs.{bid}">{html.escape(ja["roster"]["tabs"][bid])}</button>'
        for i, bid in enumerate(("all", "band1", "band2", "band3", "band4", "band5"))
    )
    ok_items = "\n".join(f'<li data-th="ok_bullets.{i}">{item}</li>' for i, item in enumerate(ja["ok_bullets"]))
    ng_items = "\n".join(f'<li data-th="ng_bullets.{i}">{item}</li>' for i, item in enumerate(ja["ng_bullets"]))
    reserve_codes = html.escape(" / ".join(cfg["reserve_tg8_list"]))
    reserve_html = (
        f'<div class="callout info" style="margin-top:14px;margin-bottom:0">'
        f'<h3 data-t="roster.reserve_title">{html.escape(ja["roster"]["reserve_title"])}</h3>'
        f'<p style="font-size:0.84rem;color:#e5e7eb"><span data-th="roster.reserve_desc_html">{ja["roster"]["reserve_desc_html"]}</span>'
        f'<br><code>{reserve_codes}</code></p></div>'
        if cfg.get("reserve_tg8_list")
        else ""
    )

    js_payload = f"""
    const I18N_BUNDLES = {json.dumps(bundles, ensure_ascii=False)};
    const ROSTER_DATA = {json.dumps(cfg["roster_rows"], ensure_ascii=False)};
    const OPP_TOP_DATA = {json.dumps(cfg["opp_top_rows"], ensure_ascii=False)};
    const PHASE_ARROWS = {json.dumps(cfg["phase_arrows"], ensure_ascii=False)};
    const CHART_CFG = {json.dumps(cfg["chart_cfg"], ensure_ascii=False)};
    """

    interactive_js = """
    let currentLang = 'ja';
    let currentBand = 'all';
    let currentPhase = 'p1';
    let pcsChart = null;
    let troopChart = null;

    function esc(s) {
      return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
    }

    function getPath(obj, path) {
      const parts = path.split('.');
      let cur = obj;
      for (const p of parts) {
        if (cur === null || cur === undefined) return undefined;
        cur = Array.isArray(cur) ? cur[Number(p)] : cur[p];
      }
      return cur;
    }

    function resolveMemberMission(m, D) {
      const custom = D.roster.custom[m.name];
      if (custom) return { bandLabel: custom[0], mission: custom[1] };
      return {
        bandLabel: D.roster.bands[m.band_id + '_label'],
        mission: D.roster.bands[m.band_id + '_mission']
      };
    }

    function renderRoster() {
      const D = I18N_BUNDLES[currentLang];
      const rosterBody = document.getElementById('rosterBody');
      const searchInput = document.getElementById('rosterSearch');
      const q = (searchInput.value || '').trim().toLowerCase();
      const rows = ROSTER_DATA.filter(m => {
        const matchBand = currentBand === 'all' || m.band_id === currentBand;
        if (!matchBand) return false;
        if (!q) return true;
        const localized = resolveMemberMission(m, D);
        return (
          m.name.toLowerCase().includes(q) ||
          localized.bandLabel.toLowerCase().includes(q) ||
          localized.mission.toLowerCase().includes(q)
        );
      });
      rosterBody.innerHTML = rows.map(m => {
        const localized = resolveMemberMission(m, D);
        const fatTag = m.fat_warn ? ` <span class="badge b-band5">${esc(D.roster.fat_warn_badge)}</span>` : '';
        return `<tr>
          <td><strong>${m.rank}</strong></td>
          <td><strong>${esc(m.name)}</strong>${fatTag}</td>
          <td><span class="badge b-${m.band_id}">${esc(localized.bandLabel)}</span></td>
          <td>Stv ${m.stove_lv} (TG${m.tg})</td>
          <td><strong>${m.pcs}</strong></td>
          <td>${m.pcs_joiner}</td>
          <td>${m.dtv.toFixed(1)}</td>
          <td>${m.troop_M.toFixed(1)}M</td>
          <td style="font-size:0.8rem;color:#e5e7eb">${esc(localized.mission)}</td>
        </tr>`;
      }).join('') || `<tr><td colspan="9" style="text-align:center;color:#9ca3af">${esc(D.roster.no_match)}</td></tr>`;
    }

    function renderOpp() {
      const D = I18N_BUNDLES[currentLang];
      document.getElementById('oppTopBody').innerHTML = OPP_TOP_DATA.map(m => {
        const warn = m.fat_warn ? ` <span class="badge b-band5">${esc(D.roster.fat_warn_badge)}</span>` : '';
        return `<tr>
          <td>${m.rank}</td>
          <td><strong>${esc(m.name)}</strong>${warn}</td>
          <td>Stv ${m.stove_lv} (TG${m.tg})</td>
          <td><strong>${m.pcs}</strong></td>
          <td>${m.dtv.toFixed(1)}</td>
          <td>${m.troop_M.toFixed(1)}M</td>
        </tr>`;
      }).join('');
      document.getElementById('oppNotesList').innerHTML = D.enemy.chips.map(u =>
        `<span class="badge b-band4">${esc(u)}</span>`
      ).join('');
    }

    const _measureCtx = document.createElement('canvas').getContext('2d');
    function measureSvgBoxWidth(text) {
      if (_measureCtx) {
        _measureCtx.font = "800 12px 'Noto Sans JP', 'Noto Sans Arabic', sans-serif";
        return Math.max(132, Math.ceil(_measureCtx.measureText(text).width) + 28);
      }
      return Math.max(136, text.length * 11 + 24);
    }

    function renderPhase(key) {
      currentPhase = key;
      const D = I18N_BUNDLES[currentLang];
      const specText = D.map.phases[key];
      const arrows = PHASE_ARROWS[key];
      const svg = document.getElementById('mapSvg');
      let inner = `<defs>
        <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/></marker>
        <marker id="arr-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#f59e0b"/></marker>
        <marker id="arr-purple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#a855f7"/></marker>
        <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981"/></marker>
        <marker id="arr-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444"/></marker>
      </defs>`;
      const markMap = {'#38bdf8':'arr-blue','#f59e0b':'arr-amber','#a855f7':'arr-purple','#10b981':'arr-green','#ef4444':'arr-red'};
      arrows.forEach((a, idx) => {
        const label = specText.labels[idx] || '';
        const boxW = measureSvgBoxWidth(label);
        let mx = a.lx !== undefined ? a.lx : (a.x1 + a.x2) / 2;
        mx = Math.max(boxW / 2 + 8, Math.min(1000 - boxW / 2 - 8, mx));
        const my = a.ly !== undefined ? a.ly : (a.y1 + a.y2) / 2 - 18;
        inner += `<line x1="${a.x1}" y1="${a.y1}" x2="${a.x2}" y2="${a.y2}" stroke="${a.color}" stroke-width="4" stroke-dasharray="10,6" marker-end="url(#${markMap[a.color]})" />`;
        inner += `<rect x="${mx - boxW / 2}" y="${my - 12}" width="${boxW}" height="24" rx="6" fill="rgba(9,13,22,0.92)" stroke="${a.color}" stroke-width="1.2"/>`;
        inner += `<text x="${mx}" y="${my + 4}" fill="#f8fafc" font-size="11.5" font-weight="800" text-anchor="middle">${esc(label)}</text>`;
      });
      svg.innerHTML = inner;
      document.getElementById('phaseDetailBox').innerHTML = specText.desc;
    }

    function initCharts() {
      const D = I18N_BUNDLES[currentLang];
      pcsChart = new Chart(document.getElementById('pcsChart'), {
        type: 'bar',
        data: {
          labels: D.charts.pcs_labels,
          datasets: [
            { label: CHART_CFG.self_label, data: CHART_CFG.self_pcs, backgroundColor: 'rgba(56, 189, 248, 0.78)', borderRadius: 6 },
            { label: CHART_CFG.opp_label, data: CHART_CFG.opp_pcs, backgroundColor: 'rgba(168, 85, 247, 0.78)', borderRadius: 6 }
          ]
        },
        options: {
          plugins: { legend: { labels: { color: '#e5e7eb' } } },
          scales: {
            x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.06)' } },
            y: { min: 0, max: 1000, ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.08)' } }
          }
        }
      });

      troopChart = new Chart(document.getElementById('troopChart'), {
        type: 'bar',
        data: {
          labels: D.charts.troop_labels,
          datasets: [
            { label: CHART_CFG.self_label, data: CHART_CFG.self_troop, backgroundColor: 'rgba(56, 189, 248, 0.78)', borderRadius: 6 },
            { label: CHART_CFG.opp_label, data: CHART_CFG.opp_troop, backgroundColor: 'rgba(168, 85, 247, 0.78)', borderRadius: 6 }
          ]
        },
        options: {
          plugins: { legend: { labels: { color: '#e5e7eb' } } },
          scales: {
            x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.06)' } },
            y: { min: 0, ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,0.08)' } }
          }
        }
      });
    }

    function setLang(lang, updateUrl) {
      if (!I18N_BUNDLES[lang]) lang = 'ja';
      currentLang = lang;
      const D = I18N_BUNDLES[lang];

      document.documentElement.lang = D.meta.lang;
      document.documentElement.dir = D.meta.dir;
      document.title = D.meta.page_title;

      document.querySelectorAll('[data-t]').forEach(el => {
        const val = getPath(D, el.dataset.t);
        if (val !== undefined) el.textContent = val;
      });
      document.querySelectorAll('[data-th]').forEach(el => {
        const val = getPath(D, el.dataset.th);
        if (val !== undefined) el.innerHTML = val;
      });
      document.querySelectorAll('[data-t-ph]').forEach(el => {
        const val = getPath(D, el.dataset.tPh);
        if (val !== undefined) el.setAttribute('placeholder', val);
      });

      document.querySelectorAll('[data-lang-btn]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.langBtn === lang);
      });

      try { localStorage.setItem('swordland_lang', lang); } catch (e) {}
      if (updateUrl) {
        try {
          const url = new URL(window.location.href);
          url.searchParams.set('lang', lang);
          window.history.replaceState(null, '', url.toString());
        } catch (e) {}
      }

      renderRoster();
      renderOpp();
      renderPhase(currentPhase);
      if (pcsChart) { pcsChart.data.labels = D.charts.pcs_labels; pcsChart.update(); }
      if (troopChart) { troopChart.data.labels = D.charts.troop_labels; troopChart.update(); }
    }

    document.querySelectorAll('[data-band]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-band]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentBand = btn.dataset.band;
        renderRoster();
      });
    });
    document.getElementById('rosterSearch').addEventListener('input', renderRoster);
    document.querySelectorAll('[data-phase]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-phase]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderPhase(btn.dataset.phase);
      });
    });
    document.querySelectorAll('[data-lang-btn]').forEach(btn => {
      btn.addEventListener('click', () => setLang(btn.dataset.langBtn, true));
    });

    initCharts();
    (function detectInitialLang() {
      let target = 'ja';
      try {
        const qp = new URLSearchParams(window.location.search).get('lang');
        if (qp && I18N_BUNDLES[qp]) {
          target = qp;
        } else {
          const saved = localStorage.getItem('swordland_lang');
          if (saved && I18N_BUNDLES[saved]) target = saved;
        }
      } catch (e) {}
      setLang(target, false);
    })();
    """

    return f"""<!DOCTYPE html>
<html lang="ja" dir="ltr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow, noarchive">
  <link rel="icon" href="data:,">
  <title>{html.escape(ja["meta"]["page_title"])}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Noto+Sans+Arabic:wght@400;600;700;900&family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>{PORTAL_CSS}</style>
</head>
<body>
  <nav class="top-nav">
    <div class="top-nav-inner">
      <div class="brand-tag" data-t="nav.brand">{html.escape(ja["nav"]["brand"])}</div>
      <div class="nav-right">
        <div class="nav-links">
          <a href="#summary" data-t="nav.summary">{html.escape(ja["nav"]["summary"])}</a>
          <a href="#roster" data-t="nav.roster">{html.escape(ja["nav"]["roster"])}</a>
          <a href="#glossary" data-t="nav.glossary">{html.escape(ja["nav"]["glossary"])}</a>
          <a href="#basic-ui" data-t="nav.basic_ui">{html.escape(ja["nav"]["basic_ui"])}</a>
          <a href="#tactical-map" data-t="nav.tactical_map">{html.escape(ja["nav"]["tactical_map"])}</a>
          <a href="#timeline" data-t="nav.timeline">{html.escape(ja["nav"]["timeline"])}</a>
          <a href="#enemy-risk" data-t="nav.enemy_risk">{html.escape(ja["nav"]["enemy_risk"])}</a>
        </div>
        <div class="lang-bar" role="group" aria-label="Language Switcher">
          {LANG_BUTTONS_HTML}
        </div>
      </div>
    </div>
  </nav>

  <main class="container">
    <header class="hero">
      <img class="hero-bg" src="assets/generated/banner_swordland_showdown.jpg" alt="{html.escape(cfg["banner_alt"])}">
      <div class="hero-overlay">
        <div class="hero-lang-strip">
          <span class="pill" data-t="hero.pill">{html.escape(ja["hero"]["pill"])}</span>
          <div class="hero-lang-bar" role="group" aria-label="Primary Language Switcher">
            <span class="lang-lbl">🌐 Lang:</span>
            {LANG_BUTTONS_HTML}
          </div>
        </div>
        <h1 data-th="hero.h1_html">{ja["hero"]["h1_html"]}</h1>
        <p class="hero-sub" data-th="hero.sub_html">{ja["hero"]["sub_html"]}</p>
        <div class="match-strip">
          <div class="match-box self">
            <div class="lbl" data-t="hero.self_lbl">{html.escape(ja["hero"]["self_lbl"])}</div>
            <div class="val" style="color:#7dd3fc" data-t="hero.self_val">{html.escape(ja["hero"]["self_val"])}</div>
            <div class="lbl" data-t="hero.self_sub">{html.escape(ja["hero"]["self_sub"])}</div>
          </div>
          <div class="match-box opp">
            <div class="lbl" data-t="hero.opp_lbl">{html.escape(ja["hero"]["opp_lbl"])}</div>
            <div class="val" style="color:#e9d5ff" data-t="hero.opp_val">{html.escape(ja["hero"]["opp_val"])}</div>
            <div class="lbl" data-t="hero.opp_sub">{html.escape(ja["hero"]["opp_sub"])}</div>
          </div>
          <div class="match-box">
            <div class="lbl" data-t="hero.core_lbl">{html.escape(ja["hero"]["core_lbl"])}</div>
            <div class="val" style="color:#fcd34d" data-t="hero.core_val">{html.escape(ja["hero"]["core_val"])}</div>
            <div class="lbl" data-t="hero.core_sub">{html.escape(ja["hero"]["core_sub"])}</div>
          </div>
        </div>
      </div>
    </header>

    <section id="summary">
      <div class="sec-head"><span class="sec-num">01</span><h2 data-t="sec_titles.s01">{html.escape(ja["sec_titles"]["s01"])}</h2></div>
      <div class="kpi-grid">{_render_kpi_cards(cfg["kpis_num"], ja["kpis"])}</div>
      <div class="grid-2" style="margin-bottom:16px">
        <div class="callout ok"><h3 data-t="ok_heading">{html.escape(ja["ok_heading"])}</h3><ul>{ok_items}</ul></div>
        <div class="callout ng"><h3 data-t="ng_heading">{html.escape(ja["ng_heading"])}</h3><ul>{ng_items}</ul></div>
      </div>
      <div class="grid-2">
        <div class="card"><h3 style="font-size:0.95rem;margin-bottom:10px;color:var(--gold-lt)" data-t="charts.pcs_title">{html.escape(ja["charts"]["pcs_title"])}</h3><canvas id="pcsChart" height="200"></canvas></div>
        <div class="card"><h3 style="font-size:0.95rem;margin-bottom:10px;color:var(--gold-lt)" data-t="charts.troop_title">{html.escape(ja["charts"]["troop_title"])}</h3><canvas id="troopChart" height="200"></canvas></div>
      </div>
    </section>

    <section id="roster">
      <div class="sec-head"><span class="sec-num">02</span><h2 data-t="sec_titles.s02">{html.escape(ja["sec_titles"]["s02"])}</h2></div>
      <div class="card">
        <div class="filter-bar">
          <input id="rosterSearch" class="search-input" type="text" placeholder="{html.escape(ja["roster"]["search_placeholder"])}" data-t-ph="roster.search_placeholder">
          {tabs_html}
        </div>
        <p style="font-size:0.78rem;color:var(--muted);margin-bottom:10px" data-th="roster.glossary_hint_html">{ja["roster"]["glossary_hint_html"]}</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th data-t="roster.th.rank">{html.escape(ja["roster"]["th"]["rank"])}</th>
                <th data-t="roster.th.player">{html.escape(ja["roster"]["th"]["player"])}</th>
                <th data-t="roster.th.band">{html.escape(ja["roster"]["th"]["band"])}</th>
                <th><a class="th-help" href="#g-tg"><span data-t="roster.th.tg">{html.escape(ja["roster"]["th"]["tg"])}</span><span class="q-dot">?</span></a></th>
                <th><a class="th-help" href="#g-pcs"><span data-t="roster.th.pcs">{html.escape(ja["roster"]["th"]["pcs"])}</span><span class="q-dot">?</span></a></th>
                <th><a class="th-help" href="#g-join"><span data-t="roster.th.join">{html.escape(ja["roster"]["th"]["join"])}</span><span class="q-dot">?</span></a></th>
                <th><a class="th-help" href="#g-dtv"><span data-t="roster.th.dtv">{html.escape(ja["roster"]["th"]["dtv"])}</span><span class="q-dot">?</span></a></th>
                <th><a class="th-help" href="#g-troop"><span data-t="roster.th.troop">{html.escape(ja["roster"]["th"]["troop"])}</span><span class="q-dot">?</span></a></th>
                <th data-t="roster.th.mission">{html.escape(ja["roster"]["th"]["mission"])}</th>
              </tr>
            </thead>
            <tbody id="rosterBody"></tbody>
          </table>
        </div>
        {reserve_html}
      </div>
    </section>

    {_render_glossary(ja)}
    {_render_basic_ui(ja)}
    {_render_tactical_map(ja)}

    <section id="timeline">
      <div class="sec-head"><span class="sec-num">06</span><h2 data-t="sec_titles.s06">{html.escape(ja["sec_titles"]["s06"])}</h2></div>
      <div class="grid-2" style="margin-bottom:16px">
        <div class="ui-shot"><img src="assets/generated/baggage_heist_scene.jpg" alt="Baggage Heist"><div class="cap"><span class="ui-tag tag-gen" data-t="basic_ui.tag_gen">{html.escape(ja["basic_ui"]["tag_gen"])}</span><span data-th="timeline.c1_html">{ja["timeline"]["c1_html"]}</span></div></div>
        <div class="ui-shot"><img src="assets/swordland/ui_swordland_field_crop.jpg" alt="Escrow Field UI"><div class="cap"><span class="ui-tag tag-real" data-t="basic_ui.tag_real">{html.escape(ja["basic_ui"]["tag_real"])}</span><span data-th="timeline.c2_html">{ja["timeline"]["c2_html"]}</span></div></div>
      </div>
      <div class="grid-3">
        <div class="card"><h3 style="color:#7dd3fc;font-size:1rem;margin-bottom:6px" data-t="timeline.p1_title">{html.escape(ja["timeline"]["p1_title"])}</h3><p style="font-size:0.86rem" data-th="timeline.p1_html">{ja["timeline"]["p1_html"]}</p></div>
        <div class="card"><h3 style="color:#fcd34d;font-size:1rem;margin-bottom:6px" data-t="timeline.p2_title">{html.escape(ja["timeline"]["p2_title"])}</h3><p style="font-size:0.86rem" data-th="timeline.p2_html">{ja["timeline"]["p2_html"]}</p></div>
        <div class="card"><h3 style="color:#fca5a5;font-size:1rem;margin-bottom:6px" data-t="timeline.p3_title">{html.escape(ja["timeline"]["p3_title"])}</h3><p style="font-size:0.86rem" data-th="timeline.p3_html">{ja["timeline"]["p3_html"]}</p></div>
      </div>
    </section>

    <section id="enemy-risk">
      <div class="sec-head">
        <span class="sec-num">07</span>
        <h2><span data-t="sec_titles.s07_prefix">{html.escape(ja["sec_titles"]["s07_prefix"])}</span> <code>{html.escape(cfg["opp_code"])}</code> <span data-t="sec_titles.s07_suffix">{html.escape(ja["sec_titles"]["s07_suffix"])}</span></h2>
      </div>
      <div class="grid-2">
        <div class="card">
          <h3 style="font-size:0.95rem;color:#e9d5ff;margin-bottom:10px" data-t="enemy.top_heading">{html.escape(ja["enemy"]["top_heading"])}</h3>
          <div class="table-wrap">
            <table style="min-width:460px">
              <thead>
                <tr>
                  <th data-t="enemy.th.rank">{html.escape(ja["enemy"]["th"]["rank"])}</th>
                  <th data-t="enemy.th.player">{html.escape(ja["enemy"]["th"]["player"])}</th>
                  <th data-t="enemy.th.tg">{html.escape(ja["enemy"]["th"]["tg"])}</th>
                  <th data-t="enemy.th.pcs">{html.escape(ja["enemy"]["th"]["pcs"])}</th>
                  <th data-t="enemy.th.dtv">{html.escape(ja["enemy"]["th"]["dtv"])}</th>
                  <th data-t="enemy.th.troop">{html.escape(ja["enemy"]["th"]["troop"])}</th>
                </tr>
              </thead>
              <tbody id="oppTopBody"></tbody>
            </table>
          </div>
          <p style="font-size:0.78rem;color:var(--muted);margin-top:8px" data-t="enemy.top_note">{html.escape(ja["enemy"]["top_note"])}</p>
        </div>
        <div class="card">
          <h3 style="font-size:0.95rem;color:#fcd34d;margin-bottom:10px" data-t="enemy.notes_heading">{html.escape(ja["enemy"]["notes_heading"])}</h3>
          <p style="font-size:0.82rem;color:#d1d5db;margin-bottom:8px" data-th="enemy.notes_desc_html">{ja["enemy"]["notes_desc_html"]}</p>
          <div id="oppNotesList" style="display:flex;flex-wrap:wrap;gap:6px"></div>
        </div>
      </div>
    </section>

    <footer><p data-th="footer.html">{ja["footer"]["html"]}</p></footer>
  </main>

  <script>
    {js_payload}
    {interactive_js}
  </script>
</body>
</html>
"""
