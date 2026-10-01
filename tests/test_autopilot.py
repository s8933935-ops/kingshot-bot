"""
AIオートパイロット＆フェイルセーフ安全機能の単体・結合テスト
"""

import unittest
from src.invest_engine.virtual_broker import VirtualAccount
from src.invest_engine.autopilot_engine import AutopilotEngine


class TestAutopilotEngine(unittest.TestCase):

    def setUp(self):
        self.acc = VirtualAccount(user_id="trader_test", user_name="テスト投資家", initial_cash=10_000_000.0)
        self.ap = AutopilotEngine(self.acc)

    def test_autopilot_toggle(self):
        # 起動テスト
        status = self.ap.toggle(is_active=True, allocated_capital=3_000_000.0, daily_max_loss_pct=3.0)
        self.assertTrue(status["is_active"])
        self.assertEqual(status["allocated_capital"], 3_000_000.0)
        self.assertGreater(len(status["recent_logs"]), 0)

        # 停止テスト
        status2 = self.ap.toggle(is_active=False)
        self.assertFalse(status2["is_active"])

    def test_autopilot_execution_and_panic_stop(self):
        self.ap.toggle(is_active=True)

        # STRONG BUYシグナル
        mock_card_buy = {
            "current_price": 4000.0,
            "prob_up_pct": 75.0  # >= 65% で買い
        }
        res = self.ap.evaluate_and_execute("GC=F", mock_card_buy)
        self.assertEqual(res, "ORDER_BUY")
        self.assertEqual(len(self.acc.positions), 1)

        # 【安全機能】ワンクリック緊急全停止（パニックストップ）
        panic_res = self.ap.emergency_panic_stop(current_prices={"GC=F": 4050.0})
        self.assertEqual(panic_res["status"], "PANIC_STOPPED")
        self.assertEqual(len(self.acc.positions), 0)
        self.assertFalse(self.ap.config.is_active)

    def test_kill_switch_on_excessive_loss(self):
        # 日次最大許容損失キルスイッチのテスト
        self.ap.toggle(is_active=True, allocated_capital=1_000_000.0, daily_max_loss_pct=2.0)
        # 強制的に有効証拠金を大幅減少させて損失状態を模倣
        self.acc.cash = 900_000.0  # -10%損失状態

        mock_card = {"current_price": 4000.0, "prob_up_pct": 80.0}
        res = self.ap.evaluate_and_execute("GC=F", mock_card)
        self.assertEqual(res, "KILL_SWITCH_TRIGGERED")
        self.assertTrue(self.ap.is_halted_by_killswitch)
        self.assertFalse(self.ap.config.is_active)


if __name__ == "__main__":
    unittest.main()
