"""
指値注文 (Limit Order)、個別銘柄AIオート設定 (Multi-Asset Autopilot)、およびロット仕様の単体テスト
"""

import unittest
from src.invest_engine.virtual_broker import VirtualAccount, LimitOrder
from src.invest_engine.autopilot_engine import AutopilotEngine, STRATEGY_PROFILES
from src.invest_engine.data_loader import fetch_latest_price


class TestLimitOrdersAndMultiAutopilot(unittest.TestCase):

    def setUp(self):
        self.acc = VirtualAccount("test_user", "テストユーザー", initial_cash=10_000_000.0)
        self.ap = AutopilotEngine(self.acc)

    def test_place_and_match_buy_limit_order(self):
        """BUY指値の発注と現在価格到達による約定テスト"""
        # 現在値が 4200.0 のとき、4150.0 で買い指値を発注
        order = self.acc.place_limit_order(
            symbol="GC=F",
            side="BUY",
            target_price=4150.0,
            amount=5.0,
            leverage=5.0
        )
        self.assertEqual(order.status, "PENDING")
        self.assertEqual(order.target_price, 4150.0)
        self.assertIn(order.order_id, self.acc.limit_orders)

        # 価格が 4180.0（まだ指値より高い）の場合、約定しない
        filled = self.acc.check_and_match_limit_orders({"GC=F": 4180.0})
        self.assertEqual(len(filled), 0)
        self.assertEqual(order.status, "PENDING")

        # 価格が 4140.0（指値以下に下落・押し目到達）の場合、約定する！
        filled = self.acc.check_and_match_limit_orders({"GC=F": 4140.0})
        self.assertEqual(len(filled), 1)
        self.assertEqual(order.status, "FILLED")
        self.assertEqual(len(self.acc.positions), 1)

        pos = filled[0]
        self.assertEqual(pos.symbol, "GC=F")
        self.assertEqual(pos.side, "BUY")
        self.assertEqual(pos.amount, 5.0)
        # より有利な価格または指値で約定
        self.assertTrue(pos.entry_price <= 4150.0)

    def test_place_and_match_sell_limit_order(self):
        """SELL指値の発注と現在価格到達による約定テスト"""
        # 現在値が 155.0 のとき、158.0 で売り指値を発注
        order = self.acc.place_limit_order(
            symbol="USDJPY=X",
            side="SELL",
            target_price=158.0,
            amount=10.0,
            leverage=10.0
        )
        self.assertEqual(order.status, "PENDING")

        # 価格が 157.0 では約定しない
        filled = self.acc.check_and_match_limit_orders({"USDJPY=X": 157.0})
        self.assertEqual(len(filled), 0)

        # 価格が 158.5（指値以上に上昇・戻り目到達）で約定！
        filled = self.acc.check_and_match_limit_orders({"USDJPY=X": 158.5})
        self.assertEqual(len(filled), 1)
        self.assertEqual(order.status, "FILLED")
        self.assertEqual(len(self.acc.positions), 1)

    def test_cancel_limit_order(self):
        """指値の取消テスト"""
        order = self.acc.place_limit_order(
            symbol="BTC-USD",
            side="BUY",
            target_price=80000.0,
            amount=0.5,
            leverage=2.0
        )
        self.assertEqual(order.status, "PENDING")

        # 取消実行
        success = self.acc.cancel_limit_order(order.order_id)
        self.assertTrue(success)
        self.assertEqual(order.status, "CANCELLED")

        # 取消済みの指値は価格が到達しても約定しない
        filled = self.acc.check_and_match_limit_orders({"BTC-USD": 79000.0})
        self.assertEqual(len(filled), 0)

    def test_multi_asset_autopilot_configs(self):
        """個別銘柄AIオートパイロット設定の独立稼働テスト"""
        # 金先物のみON
        cfg_gold = self.ap.update_symbol_config(
            symbol="GC=F",
            is_active=True,
            strategy_style="scalping",
            allocated_capital=2_000_000.0,
            use_limit_orders=True
        )
        self.assertTrue(cfg_gold.is_active)
        self.assertEqual(cfg_gold.strategy_style, "scalping")

        # ドル円はOFF
        cfg_usdjpy = self.ap.update_symbol_config(
            symbol="USDJPY=X",
            is_active=False,
            strategy_style="day_trade"
        )
        self.assertFalse(cfg_usdjpy.is_active)

        # 全体ステータス取得の検証
        status = self.ap.get_status()
        self.assertIn("symbol_configs", status)
        self.assertTrue(status["symbol_configs"]["GC=F"]["is_active"])
        self.assertFalse(status["symbol_configs"]["USDJPY=X"]["is_active"])
        self.assertTrue(status["symbol_configs"]["GC=F"]["use_limit_orders"])

    def test_ai_smart_limit_order_execution(self):
        """AIオートパイロットによるスマート指値発注と約定連携テスト"""
        self.ap.update_symbol_config(
            symbol="GC=F",
            is_active=True,
            strategy_style="day_trade",
            allocated_capital=2_000_000.0,
            use_limit_orders=True
        )

        race_card_buy = {
            "current_price": 4200.0,
            "prob_up_pct": 75.0,  # 強い買いシグナル
            "meta_bet_size_pct": 100.0,
            "meta_confidence": "HIGH",
            "current_atr": 10.0,
            "regime_state": "TRENDING_UP",
            "htf_daily_trend": 1.0
        }

        # 評価実行 ➔ 成行ではなく指値（ORDER_LIMIT_BUY）が発注される！
        act = self.ap.evaluate_and_execute("GC=F", race_card_buy)
        self.assertEqual(act, "ORDER_LIMIT_BUY")

        # 待機中指値が1件存在することを確認
        pending = [o for o in self.acc.limit_orders.values() if o.status == "PENDING"]
        self.assertEqual(len(pending), 1)
        ai_order = pending[0]
        self.assertEqual(ai_order.source, "AI")
        # 押し目価格（現在値 4200 より安い）で指されていること
        self.assertTrue(ai_order.target_price < 4200.0)

        # 次のtickで価格が指値に到達したら約定すること
        fill_card = {
            "current_price": ai_order.target_price,
            "prob_up_pct": 75.0,
            "meta_bet_size_pct": 100.0,
            "meta_confidence": "HIGH",
            "current_atr": 10.0,
            "regime_state": "TRENDING_UP",
            "htf_daily_trend": 1.0
        }
        self.ap.evaluate_and_execute("GC=F", fill_card)
        self.assertEqual(ai_order.status, "FILLED")
        self.assertEqual(len(self.acc.positions), 1)

    def test_fetch_latest_price_fallback(self):
        """最新価格取得関数の動作およびフォールバック検証"""
        price = fetch_latest_price("GC=F")
        self.assertGreater(price, 0.0)
        price_jpy = fetch_latest_price("USDJPY=X")
        self.assertGreater(price_jpy, 50.0)


if __name__ == "__main__":
    unittest.main()
