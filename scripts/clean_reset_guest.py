"""
クリーンリセットスクリプト:
異常ドリフト（夜間複利乗算）による架空の巨額利益トレード履歴をDBおよびメモリから初期化します。
"""
from pathlib import Path
import sqlite3

db_path = Path("data/invest_history.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM trades WHERE user_id = 'guest'")
    cur.execute("DELETE FROM ai_decisions WHERE user_id = 'guest'")
    cur.execute("DELETE FROM users WHERE user_id = 'guest'")
    conn.commit()
    conn.close()
    print("Database cleaned for user 'guest'.")
else:
    print("Database file does not exist yet.")
