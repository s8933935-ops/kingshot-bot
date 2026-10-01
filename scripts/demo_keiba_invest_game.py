"""
競馬型仮想投資プラットフォーム・デモ実行スクリプト
出走表（AI予想印・パドックコメント）、仮想トレード、および視聴者・AI合同ランキングを表示します。
"""

import sys
from pathlib import Path

# Windows UTF-8 出力対策
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.invest_engine.game_manager import InvestmentGameManager


def main():
    print("=" * 75)
    print("  🏇 【投資グランプリ】競馬型 仮想投資＆AI予想プラットフォーム 🏇")
    print("=" * 75)

    gm = InvestmentGameManager()

    # 1. 競馬新聞風の出走表（AIパドック診断）生成
    print("\n[Step 1/3] 本日のメインレース: 『金先物 (Gold Futures: GC=F)』出走表発表！")
    race = gm.generate_race_card(symbol="GC=F")

    print("-" * 75)
    print(f"  ■ 銘柄:          {race['symbol']} (金先物)")
    print(f"  ■ 現在レート:    ${race['current_price']:,} ドル")
    print(f"  ■ AI本日の印:    {race['ai_mark']}  【{race['ai_stance']}】")
    print(f"  ■ シグナル確信度: {race['confidence']}")
    print(f"  ■ 上昇期待確率:  {race['prob_up_pct']}%  (下落警戒: {race['prob_down_pct']}%)")
    print(f"  ■ パドック診断:  「{race['paddock_comment']}」")
    print(f"  ■ テクニカル気配: RSI(14)={race['rsi_14']} / MACD={race['macd']} / 前日比={race['return_1d_pct']:+}%")
    print("-" * 75)

    # 2. プレイヤーたちの仮想エントリー（初期資金 1,000万円）
    print("\n[Step 2/3] 各プレイヤーの仮想エントリー（初期軍資金: 1,000万円）...")

    # プレイヤー1: AIの印（◎本命）を信じてロングした「競馬ファン田中」
    u1 = gm.register_user("tanaka", "競馬ファン田中")
    p1 = u1.open_position("GC=F", "BUY", current_price=race["current_price"], amount=40.0)

    # プレイヤー2: 逆張りを狙ってショートした「穴党のスズキ」
    u2 = gm.register_user("suzuki", "穴党スズキ (逆張り)")
    p2 = u2.open_position("GC=F", "SELL", current_price=race["current_price"], amount=30.0)

    # プレイヤー3: 公式AIゴールド予想屋（自ら算出した確率で自動エントリー）
    gm.execute_ai_auto_trade("GC=F")

    # 翌日：金価格が +1.5% 上昇したとシミュレーション！
    next_day_price = race["current_price"] * 1.015
    print(f"  >> 翌日の市場結果: 金価格が ${race['current_price']:.1f} から ${next_day_price:.1f} (+1.5%) へ急伸！")

    # ポジション決済
    u1.close_position(p1.position_id, next_day_price)
    u2.close_position(p2.position_id, next_day_price)

    # AIの決済
    ai_acc = gm.get_user(gm.ai_user_id)
    for pos_id in list(ai_acc.positions.keys()):
        ai_acc.close_position(pos_id, next_day_price)

    # 3. ランキング発表
    print("\n[Step 3/3] 🏆 本日のグランプリ回収率・実力ランキング 発表！")
    leaderboard = gm.get_leaderboard(sort_by="payout_rate_pct")

    print("=" * 75)
    print(f"{'順位':^4} | {'プレイヤー名':<22} | {'総資産(有効証拠金)':>14} | {'回収率':>8} | {'勝率':>6} | {'称号・ランク':<15}")
    print("-" * 75)
    for item in leaderboard:
        print(f" {item['rank']:^2}位 | {item['user_name']:<20} | ¥{item['equity']:>14,.0f} | {item['payout_rate_pct']:>7.2f}% | {item['win_rate_pct']:>5.1f}% | {item['certified_rank']:<15}")
    print("=" * 75)


if __name__ == "__main__":
    main()
