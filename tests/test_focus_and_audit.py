import unittest
from src.invest_engine.game_manager import InvestmentGameManager
from src.invest_engine.autopilot_engine import AutopilotEngine, STRATEGY_PROFILES
from src.invest_engine.virtual_broker import VirtualAccount


class TestFocusAndAudit(unittest.TestCase):
    def setUp(self):
        self.account = VirtualAccount(user_id="test_user", user_name="Test Trader", initial_cash=10_000_000.0)
        self.ap = AutopilotEngine(self.account)
        self.ap.config.is_active = True  # テスト用にオートパイロットを有効化

    def test_focused_symbol_filtering(self):
        """ゴールド専従モード時、他銘柄のエントリーが遮断されること"""
        self.ap.set_focused_symbol("GC=F")
        self.assertEqual(self.ap.config.focused_symbol, "GC=F")

        # ドル円 (USDJPY=X) の出走表シグナル (強い買い)
        card_usdjpy = {
            "current_price": 150.0,
            "prob_up_pct": 80.0,
            "meta_bet_size_pct": 100.0,
            "current_atr": 0.5
        }
        res_usdjpy = self.ap.evaluate_and_execute("USDJPY=X", card_usdjpy)
        # 専従外のため None（完全スキップ）
        self.assertIsNone(res_usdjpy)
        self.assertEqual(len(self.account.positions), 0)

        # ゴールド (GC=F) の出走表シグナル (強い買い)
        card_gold = {
            "current_price": 2700.0,
            "prob_up_pct": 80.0,
            "meta_bet_size_pct": 100.0,
            "current_atr": 15.0
        }
        res_gold = self.ap.evaluate_and_execute("GC=F", card_gold)
        self.assertIn("ORDER_", res_gold)
        self.assertEqual(len(self.account.positions), 1)

    def test_buy_only_side_direction(self):
        """BUY_ONLY（買い専用）モード時、下落シグナルでのSELL（空売り）が遮断されること"""
        self.ap.set_side_direction("BUY_ONLY")
        self.assertEqual(self.ap.config.allowed_side, "BUY_ONLY")

        # 強い下落シグナル (下落確率80% = prob_up 20%)
        card_bearish = {
            "current_price": 2700.0,
            "prob_up_pct": 20.0,
            "meta_bet_size_pct": 100.0,
            "current_atr": 15.0
        }
        res = self.ap.evaluate_and_execute("GC=F", card_bearish)
        # SELLはスキップされる
        self.assertEqual(res, "SKIP_SIDE_FILTER")
        self.assertEqual(len(self.account.positions), 0)

    def test_pyramiding_max_positions(self):
        """max_positions=2 の時、押し目で買い増しができること"""
        self.ap.update_symbol_config(
            symbol="GC=F",
            is_active=True,
            strategy_style="day_trade",
            allowed_side="BUY_ONLY",
            max_positions=2
        )

        # 1回目の買い (2700.0)
        card_1 = {
            "current_price": 2700.0,
            "prob_up_pct": 80.0,
            "meta_bet_size_pct": 100.0,
            "current_atr": 50.0  # SLを大きく取って誤決済防止
        }
        res_1 = self.ap.evaluate_and_execute("GC=F", card_1)
        self.assertIn("ORDER_", res_1)
        self.assertEqual(len(self.account.positions), 1)

        # 2回目: 押し目 (2690.0) での買い増し
        card_2 = {
            "current_price": 2690.0,
            "prob_up_pct": 80.0,
            "meta_bet_size_pct": 100.0,
            "current_atr": 50.0
        }
        res_2 = self.ap.evaluate_and_execute("GC=F", card_2)
        self.assertIn("ORDER_", res_2)
        self.assertEqual(len(self.account.positions), 2)

        # 3回目: 上限2のため新規エントリーは拒否されHOLDになる
        card_3 = {
            "current_price": 2685.0,
            "prob_up_pct": 80.0,
            "meta_bet_size_pct": 100.0,
            "current_atr": 50.0
        }
        res_3 = self.ap.evaluate_and_execute("GC=F", card_3)
        self.assertEqual(res_3, "HOLD")
        self.assertEqual(len(self.account.positions), 2)

    def test_trade_answer_audit_calculation(self):
        """決済トレードの答え合わせ監査判定が正しく行われること"""
        # ポジションを建てて決済する
        pos = self.account.open_position("GC=F", "BUY", 2700.0, amount=1.0, leverage=1.0)
        # 2680で損切り決済 (-20)
        self.account.close_position(pos.position_id, 2680.0)

        # 現在価格がさらに暴落して 2600.0 の場合
        cur_price = 2600.0
        trade = self.account.trade_history[0]
        hypothetical_pnl = (cur_price - trade.entry_price) * trade.amount * trade.leverage * trade.fx_rate
        avoided_loss = trade.net_pnl - hypothetical_pnl
        # 損切りしていなかったら -100だったが、-20で済んだため +80相当(円換算)の損失回避
        self.assertGreater(avoided_loss, 0)


if __name__ == "__main__":
    unittest.main()
