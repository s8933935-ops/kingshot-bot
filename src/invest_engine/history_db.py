"""
予測履歴＆的中実績データベース (SQLite)
出走表の履歴、AI予想印、翌日の実際の結果（的中/不的中・リターン）、
およびユーザー取引ログを永続化し、過去の的中実績統計を算出します。
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = Path("data/invest_history.db")


def init_db(db_path: Path = DB_PATH):
    """データベース初期化"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 出走表＆AI予想履歴テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS race_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        race_name TEXT NOT NULL,
        target_date TEXT NOT NULL,
        close_price REAL NOT NULL,
        ai_mark TEXT NOT NULL,
        ai_stance TEXT NOT NULL,
        confidence TEXT NOT NULL,
        prob_up_pct REAL NOT NULL,
        prob_down_pct REAL NOT NULL,
        paddock_comment TEXT,
        actual_next_price REAL,
        actual_return_pct REAL,
        is_hit INTEGER,  -- 1: 的中, 0: 不的中, NULL: 未確定
        created_at TEXT NOT NULL,
        UNIQUE(symbol, target_date)
    )
    """)

    # ユーザー口座永続化テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        user_name TEXT NOT NULL,
        cash REAL NOT NULL,
        equity REAL NOT NULL,
        initial_cash REAL NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def save_race_card(card: Dict[str, Any], race_name: str = "金先物カップ", db_path: Path = DB_PATH):
    """本日の出走表をDBに保存（既にあれば更新）"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO race_history (
        symbol, race_name, target_date, close_price,
        ai_mark, ai_stance, confidence, prob_up_pct, prob_down_pct,
        paddock_comment, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(symbol, target_date) DO UPDATE SET
        close_price=excluded.close_price,
        ai_mark=excluded.ai_mark,
        ai_stance=excluded.ai_stance,
        confidence=excluded.confidence,
        prob_up_pct=excluded.prob_up_pct,
        prob_down_pct=excluded.prob_down_pct,
        paddock_comment=excluded.paddock_comment
    """, (
        card["symbol"],
        race_name,
        card["target_date"],
        card["current_price"],
        card["ai_mark"],
        card["ai_stance"],
        card["confidence"],
        card["prob_up_pct"],
        card["prob_down_pct"],
        card["paddock_comment"],
        now_iso
    ))

    conn.commit()
    conn.close()


def update_yesterday_result(symbol: str, target_date: str, next_price: float, db_path: Path = DB_PATH):
    """過去の予想に対して、翌日の確定値で的中判定を行う"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT close_price, ai_mark FROM race_history WHERE symbol = ? AND target_date = ?", (symbol, target_date))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    close_p, mark = row
    actual_return = ((next_price - close_p) / close_p) * 100.0

    # 的中判定:
    # ◎(本命) または ◯(対抗) で 上昇なら 的中(1)
    # ✕(危険) で 下落なら 的中(1)
    # それ以外は 不的中(0)
    is_hit = 0
    if ("◎" in mark or "◯" in mark) and actual_return > 0:
        is_hit = 1
    elif "✕" in mark and actual_return < 0:
        is_hit = 1
    elif "△" in mark and abs(actual_return) <= 0.3:  # レンジ予想的中
        is_hit = 1

    cursor.execute("""
    UPDATE race_history SET
        actual_next_price = ?,
        actual_return_pct = ?,
        is_hit = ?
    WHERE symbol = ? AND target_date = ?
    """, (round(next_price, 2), round(actual_return, 2), is_hit, symbol, target_date))

    conn.commit()
    conn.close()
    return {"is_hit": is_hit, "actual_return": actual_return}


def get_ai_prediction_stats(symbol: str = "GC=F", limit: int = 30, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """AI予想の過去の的中率・成績統計を取得"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*), SUM(is_hit)
    FROM race_history
    WHERE symbol = ? AND is_hit IS NOT NULL
    ORDER BY target_date DESC
    LIMIT ?
    """, (symbol, limit))

    total, hits = cursor.fetchone()
    total = total or 0
    hits = hits or 0
    hit_rate = (hits / total * 100.0) if total > 0 else 0.0

    # 直近の履歴一覧
    cursor.execute("""
    SELECT target_date, ai_mark, ai_stance, prob_up_pct, actual_return_pct, is_hit
    FROM race_history
    WHERE symbol = ?
    ORDER BY target_date DESC
    LIMIT 10
    """, (symbol,))

    history = [
        {
            "target_date": r[0],
            "ai_mark": r[1],
            "ai_stance": r[2],
            "prob_up_pct": r[3],
            "actual_return_pct": r[4],
            "is_hit": bool(r[5]) if r[5] is not None else None
        }
        for r in cursor.fetchall()
    ]

    conn.close()
    return {
        "symbol": symbol,
        "total_evaluated_races": total,
        "total_hits": hits,
        "hit_rate_pct": round(hit_rate, 1),
        "recent_history": history
    }
