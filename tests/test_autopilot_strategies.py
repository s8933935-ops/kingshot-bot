"""
AIオートパイロット戦術スタイル（スキャルピング、デイトレ、スイング、中期、長期）
およびメタラベリング・ロット配分連動のユニットテスト
"""

import unittest
from src.invest_engine.virtual_broker import VirtualAccount
from src.invest_engine.autopilot_engine import AutopilotEngine, STRATEGY_PROFILES


class TestAutopilotStrategies(unittest.TestCase):

    def setUp(self):
        self.account = VirtualAccount("test_trader", "テストトレーダー", initial_cash=10_000_000.0)
        self.autopilot = AutopilotEngine(self.account)

    def test_strategy_profiles_exist(self):
        """5大戦術プロファイルが正しく定義されていることを検証"""
        expected_styles = ["scalping", "day_trade", "swing", "medium_term", "long_term"]
        for style in expected_styles:
            self.assertIn(style, STRATEGY_PROFILES)
            prof = STRATEGY_PROFILES[style]
            self.assertIn("take_profit_pct", prof)
            self.assertIn("stop_loss_pct", prof)
            self.assertIn("buy_threshold", prof)
            self.assertIn("max_leverage", prof)

    def test_scalping_tight_take_profit(self):
        """スキャルピング戦術でわずかな上昇(+0.4%)で即座に利確されることを検証"""
        self.autopilot.toggle(is_active=True, allocated_capital=3_000_000.0, strategy_style="scalping")
        self.assertEqual(self.autopilot.config.strategy_style, "scalping")
        self.assertEqual(self.autopilot.config.max_leverage, 5.0)

        # 買いエントリー
        race_card = {
            "symbol": "GC=F",
            "current_price": 4000.0,
            "prob_up_pct": 70.0,
            "meta_bet_size_pct": 100.0,
            "meta_confidence": "FULL"
        }
        action = self.autopilot.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(action, "ORDER_BUY")
        self.assertEqual(len(self.account.positions), 1)

        # 価格が 4000.0 -> 4020.0 (+0.5%) に上昇 -> 利確トリガー
        pos_id = list(self.account.positions.keys())[0]
        self.account.positions[pos_id].current_price = 4020.0  # +0.5%
        race_card["current_price"] = 4020.0

        exit_action = self.autopilot.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(exit_action, "CLOSE_TAKE_PROFIT")
        self.assertEqual(len(self.account.positions), 0)
        self.assertEqual(len(self.account.trade_history), 1)
        self.assertGreater(self.account.trade_history[0].net_pnl, 0)

    def test_meta_bet_size_skip_on_macro_risk(self):
        """メタ推奨ロットが0%（マクロ危険水域）のときはBUYシグナルでも見送り(SKIP)になることを検証"""
        self.autopilot.toggle(is_active=True, allocated_capital=3_000_000.0, strategy_style="day_trade")

        # 一次モデルは強気(80%)だが、メタモデルが0%(SKIP)
        race_card = {
            "symbol": "GC=F",
            "current_price": 4000.0,
            "prob_up_pct": 80.0,
            "meta_bet_size_pct": 0.0,
            "meta_confidence": "SKIP (マクロ逆風・見送り)"
        }
        action = self.autopilot.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(action, "SKIP_MACRO_RISK")
        self.assertEqual(len(self.account.positions), 0)
        self.assertEqual(len(self.autopilot.logs), 2)  # ENABLE + SKIP
        self.assertEqual(self.autopilot.logs[0].action, "SKIP")

    def test_meta_bet_size_scales_position_amount(self):
        """メタ推奨比率(50%)に応じて建玉数量が半減スケールされることを検証"""
        self.autopilot.toggle(is_active=True, allocated_capital=1_000_000.0, strategy_style="day_trade")
        # デイトレ base_ratio=0.20, capital=1,000,000 => base trade_value = 200,000
        # meta_bet_size_pct = 50.0% => scaled trade_value = 100,000
        # price = 4000 => amount = 100,000 / 4000 = 25.0
        race_card = {
            "symbol": "GC=F",
            "current_price": 4000.0,
            "prob_up_pct": 75.0,
            "meta_bet_size_pct": 50.0,
            "meta_confidence": "NORMAL"
        }
        action = self.autopilot.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(action, "ORDER_BUY")
        pos = list(self.account.positions.values())[0]
        self.assertAlmostEqual(pos.amount, 25.0, places=1)


if __name__ == "__main__":
    unittest.main()
