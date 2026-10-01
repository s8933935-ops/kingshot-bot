"""
Unit tests for Defensive Gates (Regime Gating, HTF Trend Alignment, Expected Value Filter)
==========================================================================================
"""

import unittest
from src.invest_engine.autopilot_engine import (
    AutopilotEngine,
    AutopilotConfig,
    STRATEGY_PROFILES
)
from src.invest_engine.virtual_broker import VirtualAccount


class TestDefensiveGates(unittest.TestCase):

    def setUp(self):
        self.account = VirtualAccount(user_id="gate_user", user_name="GateTester", initial_cash=1_000_000.0)
        self.config = AutopilotConfig(is_active=True, strategy_style="scalping", base_equity_today=1_000_000.0)
        self.engine = AutopilotEngine(user_account=self.account)
        self.engine.config = self.config

    def test_choppy_regime_blocks_scalping(self):
        """レンジ相場 (CHOPPY_RANGE) ではスキャルピングの仕掛けを遮断(SKIP)するか"""
        race_card = {
            "symbol": "GC=F",
            "current_price": 2600.0,
            "prob_up_pct": 70.0,
            "current_atr": 10.0,
            "meta_bet_size_pct": 100.0,
            "regime_state": "CHOPPY_RANGE",
            "htf_daily_trend": 0.0
        }
        res = self.engine.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(res, "SKIP_CHOPPY_REGIME")
        self.assertEqual(len(self.account.positions), 0)

    def test_htf_counter_trend_blocks_buy(self):
        """日足下降トレンド(htf_trend=-1)逆行の買いエントリーを遮断(SKIP)するか"""
        race_card = {
            "symbol": "GC=F",
            "current_price": 2600.0,
            "prob_up_pct": 70.0,
            "current_atr": 10.0,
            "meta_bet_size_pct": 100.0,
            "regime_state": "BULL_TREND",
            "htf_daily_trend": -1.0  # 日足下降トレンド
        }
        res = self.engine.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(res, "SKIP_HTF_ALIGNMENT")
        self.assertEqual(len(self.account.positions), 0)

    def test_negative_expectancy_blocks_entry(self):
        """取引摩擦（スリッページ・手数料）控除後の期待値がマイナスのとき遮断(SKIP)するか"""
        # 微小な上昇期待(56%)だが、ATRが極小(0.1ドル)で利確幅が手数料に負けるケース
        race_card = {
            "symbol": "GC=F",
            "current_price": 2600.0,
            "prob_up_pct": 56.0,
            "current_atr": 0.5,  # 極小ATR -> TP幅が0.5ドル(0.019%)で摩擦0.16%に負ける
            "meta_bet_size_pct": 100.0,
            "regime_state": "BULL_TREND",
            "htf_daily_trend": 1.0
        }
        res = self.engine.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(res, "SKIP_NEGATIVE_EXPECTANCY")
        self.assertEqual(len(self.account.positions), 0)

    def test_positive_expectancy_and_aligned_gates_executes_order(self):
        """全ゲートクリアかつ期待値プラス(EV > 0)のときに正常約定(ORDER_BUY)するか"""
        race_card = {
            "symbol": "GC=F",
            "current_price": 2600.0,
            "prob_up_pct": 75.0,
            "current_atr": 15.0,  # TP=2630 (+1.15%), SL=2585 (-0.57%) -> EV >> 0
            "meta_bet_size_pct": 100.0,
            "regime_state": "BULL_TREND",
            "htf_daily_trend": 1.0
        }
        res = self.engine.evaluate_and_execute("GC=F", race_card)
        self.assertEqual(res, "ORDER_BUY")
        self.assertEqual(len(self.account.positions), 1)


if __name__ == "__main__":
    unittest.main()
