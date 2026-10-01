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

    # 実約定・トレード履歴永続化テーブル（自己学習の教師データ）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        amount REAL NOT NULL,
        leverage REAL NOT NULL,
        gross_pnl REAL NOT NULL,
        fee REAL NOT NULL,
        net_pnl REAL NOT NULL,
        return_pct REAL NOT NULL,
        is_win INTEGER NOT NULL,  -- 1: 勝ち(利確), 0: 負け(損切/同値)
        source TEXT NOT NULL,     -- 'AUTOPILOT' または 'USER'
        opened_at TEXT NOT NULL,
        closed_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # AI意思決定・特徴量スナップショットテーブル（メタラベリング再学習用）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        reason TEXT NOT NULL,
        price REAL NOT NULL,
        prob_up REAL,
        regime TEXT,
        htf_trend REAL,
        meta_bet_size REAL,
        features_json TEXT,  -- 当時の特徴量ベクトル (JSON)
        timestamp TEXT NOT NULL,
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


def save_trade_record(user_id: str, trade: Dict[str, Any], source: str = "AUTOPILOT", db_path: Path = DB_PATH):
    """
    約定完了したトレード（利確・損切実績）をDBに永続化保存する。
    機械学習（メタラベリング再学習）の正解ラベル（is_win）として機能します。
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    now_iso = datetime.now().isoformat()
    net_pnl = float(trade.get("net_pnl", 0.0))
    is_win = 1 if net_pnl > 0 else 0

    cursor.execute("""
    INSERT OR REPLACE INTO trades (
        trade_id, user_id, symbol, side, entry_price, exit_price,
        amount, leverage, gross_pnl, fee, net_pnl, return_pct,
        is_win, source, opened_at, closed_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade.get("trade_id", str(datetime.now().timestamp())),
        user_id,
        trade.get("symbol", ""),
        trade.get("side", ""),
        float(trade.get("entry_price", 0.0)),
        float(trade.get("exit_price", 0.0)),
        float(trade.get("amount", 0.0)),
        float(trade.get("leverage", 1.0)),
        float(trade.get("gross_pnl", 0.0)),
        float(trade.get("fee", 0.0)),
        net_pnl,
        float(trade.get("return_pct", 0.0)),
        is_win,
        source,
        trade.get("opened_at", now_iso),
        trade.get("closed_at", now_iso),
        now_iso
    ))

    conn.commit()
    conn.close()


def save_ai_decision(
    user_id: str,
    symbol: str,
    action: str,
    reason: str,
    price: float,
    prob_up: Optional[float] = None,
    regime: Optional[str] = None,
    htf_trend: Optional[float] = None,
    meta_bet_size: Optional[float] = None,
    features: Optional[Dict[str, Any]] = None,
    db_path: Path = DB_PATH
):
    """
    AIの思考・意思決定と、その瞬間の市場特徴量をDBに永続化保存する。
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    now_iso = datetime.now().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    feat_json = json.dumps(features, ensure_ascii=False) if features else "{}"

    cursor.execute("""
    INSERT INTO ai_decisions (
        user_id, symbol, action, reason, price,
        prob_up, regime, htf_trend, meta_bet_size,
        features_json, timestamp, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, symbol, action, reason, price,
        prob_up, regime, htf_trend, meta_bet_size,
        feat_json, now_time, now_iso
    ))

    conn.commit()
    conn.close()


def get_completed_trades(
    user_id: Optional[str] = None,
    symbol: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 100,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """保存された約定履歴を取得"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = "SELECT trade_id, user_id, symbol, side, entry_price, exit_price, amount, leverage, fee, net_pnl, return_pct, is_win, source, opened_at, closed_at FROM trades WHERE 1=1"
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    if source:
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "trade_id": r[0],
            "user_id": r[1],
            "symbol": r[2],
            "side": r[3],
            "entry_price": r[4],
            "exit_price": r[5],
            "amount": r[6],
            "leverage": r[7],
            "fee": r[8],
            "net_pnl": r[9],
            "return_pct": r[10],
            "is_win": bool(r[11]),
            "source": r[12],
            "opened_at": r[13],
            "closed_at": r[14],
        }
        for r in rows
    ]


def export_learning_dataset(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    蓄積されたAI売買履歴と意思決定ログから、次世代メタモデルの再学習データセット（X, y）を抽出する。
    - X: エントリー時のシグナル確率、上位足トレンド、レジーム、市場特徴量
    - y: 実際のトレード結果（1: 利確成功, 0: 損切り/失敗）
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # AIがエントリーした約定トレード
    cursor.execute("""
    SELECT t.trade_id, t.symbol, t.side, t.net_pnl, t.return_pct, t.is_win, t.opened_at, t.closed_at
    FROM trades t
    WHERE t.source = 'AUTOPILOT'
    ORDER BY t.id ASC
    """)
    trades = cursor.fetchall()

    dataset_samples = []
    for tr in trades:
        tid, sym, side, pnl, ret_pct, is_win, opened_at, closed_at = tr

        # 当該トレードのエントリー付近で行われたAI意思決定ログを検索
        cursor.execute("""
        SELECT prob_up, regime, htf_trend, meta_bet_size, features_json
        FROM ai_decisions
        WHERE symbol = ? AND (action LIKE '%BUY%' OR action LIKE '%SELL%') AND created_at <= ?
        ORDER BY id DESC LIMIT 1
        """, (sym, closed_at))
        dec = cursor.fetchone()

        sample_features = {
            "symbol": sym,
            "side": side,
            "prob_up": dec[0] if dec else 0.5,
            "regime": dec[1] if dec else "TREND",
            "htf_trend": dec[2] if dec else 0.0,
            "meta_bet_size": dec[3] if dec else 10.0,
        }

        # 補助特徴量JSONを展開
        if dec and dec[4]:
            try:
                extra = json.loads(dec[4])
                if isinstance(extra, dict):
                    sample_features.update(extra)
            except Exception:
                pass

        dataset_samples.append({
            "trade_id": tid,
            "features": sample_features,
            "label_is_win": is_win,
            "net_pnl": pnl,
            "return_pct": ret_pct,
            "opened_at": opened_at,
            "closed_at": closed_at
        })

    conn.close()

    total_samples = len(dataset_samples)
    wins = sum(1 for s in dataset_samples if s["label_is_win"] == 1)
    win_rate = (wins / total_samples * 100.0) if total_samples > 0 else 0.0

    return {
        "total_samples": total_samples,
        "win_count": wins,
        "loss_count": total_samples - wins,
        "win_rate_pct": round(win_rate, 2),
        "samples": dataset_samples
    }

