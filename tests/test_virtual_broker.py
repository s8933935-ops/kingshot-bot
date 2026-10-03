"""
仮想投資口座およびゲーム統括マネージャーの単体テスト
"""

import unittest
from src.invest_engine.virtual_broker import VirtualAccount
from src.invest_engine.game_manager import InvestmentGameManager


class TestVirtualBrokerAndGame(unittest.TestCase):

    def test_virtual_account_trading_flow(self):
        acc = VirtualAccount(user_id="user_01", user_name="テスト投資家", initial_cash=10_000_000.0)
        self.assertEqual(acc.cash, 10_000_000.0)
        self.assertEqual(acc.equity, 10_000_000.0)

        # 1. 買いエントリー (金価格 4000ドルで 10オンス買い)
        pos = acc.open_position(symbol="GC=F", side="BUY", current_price=4000.0, amount=10.0, leverage=2.0)
        self.assertIn(pos.position_id, acc.positions)
        self.assertEqual(pos.side, "BUY")
        self.assertLess(acc.cash, 10_000_000.0)  # 手数料引き落とし

        # 2. 価格上昇 (4000 -> 4100ドル) の含み益テスト
        acc.update_market_price(symbol="GC=F", current_price=4100.0)
        self.assertGreater(pos.unrealized_pnl, 0.0)
        self.assertGreater(acc.equity, 10_000_000.0)

        # 3. 決済 (エグジット)
        trade = acc.close_position(position_id=pos.position_id, current_price=4100.0)
        self.assertEqual(len(acc.positions), 0)
        self.assertEqual(len(acc.trade_history), 1)
        self.assertGreater(trade.net_pnl, 0.0)

        # 4. パフォーマンス指標（回収率・勝率）
        stats = acc.get_performance_stats()
        self.assertEqual(stats["total_trades"], 1)
        self.assertEqual(stats["win_rate_pct"], 100.0)
        self.assertGreater(stats["payout_rate_pct"], 100.0)

    def test_game_manager_and_leaderboard(self):
        gm = InvestmentGameManager()
        # ユーザー登録
        u1 = gm.register_user("u1", "競馬ファンA")
        u2 = gm.register_user("u2", "クオンツ志望B")

        # 取引シミュレーション (レバレッジ2倍で10オンス)
        p1 = u1.open_position("GC=F", "BUY", current_price=2000.0, amount=10.0, leverage=2.0)
        u1.close_position(p1.position_id, current_price=2100.0)  # 勝ち

        p2 = u2.open_position("GC=F", "BUY", current_price=2000.0, amount=10.0, leverage=2.0)
        u2.close_position(p2.position_id, current_price=1900.0)  # 負け

        # ランキング確認
        lb = gm.get_leaderboard(sort_by="payout_rate_pct")
        self.assertGreaterEqual(len(lb), 3)  # AI + u1 + u2
        self.assertEqual(lb[0]["user_id"], "u1")  # u1がトップ


if __name__ == "__main__":
    unittest.main()
