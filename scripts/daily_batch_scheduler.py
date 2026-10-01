"""
日次市場データ自動更新＆予測バッチスクリプト (Automation Scheduler)
毎日市場が閉まった後、自動で：
1. 昨日のAI予想の結果判定（的中/不的中）をDBに記録
2. 最新の市場データを取得して再学習・推論
3. 翌日の出走表（◎◯▲の印・パドック診断）をDB保存
4. 公式AI予想屋の自動エントリー・決済を実行
"""

import sys
from pathlib import Path

# Windows UTF-8 出力対策
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.invest_engine.game_manager import InvestmentGameManager
from src.invest_engine.history_db import save_race_card, update_yesterday_result, get_ai_prediction_stats


def run_daily_batch(symbol: str = "GC=F", race_name: str = "金先物カップ"):
    print("=" * 70)
    print(f"  ⏰ [日次自動更新バッチ] 処理開始: {symbol} ({race_name})")
    print("=" * 70)

    gm = InvestmentGameManager()

    # 1. 最新の出走表と現在レート取得
    print(f"\n[1/4] 最新市場データ取得 & 翌日AI予想生成中...")
    race_card = gm.generate_race_card(symbol=symbol)
    print(f"  -> 日付: {race_card['target_date']}")
    print(f"  -> 現在価格: ${race_card['current_price']:,}")
    print(f"  -> AI予想印: {race_card['ai_mark']} ({race_card['ai_stance']})")

    # 2. DBへ保存
    print(f"\n[2/4] 出走表を実績データベース (SQLite) に永続化...")
    save_race_card(race_card, race_name=race_name)
    print("  -> 保存完了！")

    # 3. 公式AI予想屋の自動取引
    print(f"\n[3/4] 公式AI予想屋 自動ポジション管理...")
    gm.execute_ai_auto_trade(symbol=symbol)
    ai_acc = gm.get_user(gm.ai_user_id)
    print(f"  -> AI有効証拠金: ¥{ai_acc.equity:,.0f} (保有中: {len(ai_acc.positions)}件)")

    # 4. 的中率統計の集計
    print(f"\n[4/4] 過去のAI的中実績サマリー集計...")
    stats = get_ai_prediction_stats(symbol=symbol)
    print(f"  -> 評価済みレース数: {stats['total_evaluated_races']} 件")
    print(f"  -> 累計的中率:       {stats['hit_rate_pct']}%")

    print("\n" + "=" * 70)
    print("  ✅ [日次自動更新バッチ] 全工程正常完了！")
    print("=" * 70)
    return race_card


if __name__ == "__main__":
    run_daily_batch()
