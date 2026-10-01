"""
Tests for Dynamic ATR Triple Barrier & Multi-Timeframe High-Frequency Execution
================================================================================
"""

import unittest
import numpy as np
import pandas as pd
from src.invest_engine.autopilot_engine import (
    STRATEGY_PROFILES,
    compute_strategy_barriers,
    AutopilotEngine,
    AutopilotConfig
)
from src.invest_engine.virtual_broker import Position, VirtualAccount
from src.invest_engine.zero_leakage_engine import PessimisticExecutionEngine


class TestDynamicATRBarriers(unittest.TestCase):

    def test_compute_strategy_barriers_dynamic_long(self):
        """動的ATRバリア (LONG): TP = entry + pt_factor * atr, SL = entry - sl_factor * atr"""
        entry = 2000.0
        atr = 25.0
        profile = {
            "barrier_type": "dynamic",
            "pt_factor": 2.0,
            "sl_factor": 1.0,
            "take_profit_pct": 1.0,
            "stop_loss_pct": -0.5
        }
        barriers = compute_strategy_barriers(entry, atr, profile, position=1)
        self.assertAlmostEqual(barriers["take_profit"], 2000.0 + 2.0 * 25.0)  # 2050.0
        self.assertAlmostEqual(barriers["stop_loss"], 2000.0 - 1.0 * 25.0)    # 1975.0

    def test_compute_strategy_barriers_dynamic_short(self):
        """動的ATRバリア (SHORT): TP = entry - pt_factor * atr, SL = entry + sl_factor * atr"""
        entry = 2000.0
        atr = 25.0
        profile = {
            "barrier_type": "dynamic",
            "pt_factor": 2.0,
            "sl_factor": 1.0,
            "take_profit_pct": 1.0,
            "stop_loss_pct": -0.5
        }
        barriers = compute_strategy_barriers(entry, atr, profile, position=-1)
        self.assertAlmostEqual(barriers["take_profit"], 2000.0 - 2.0 * 25.0)  # 1950.0
        self.assertAlmostEqual(barriers["stop_loss"], 2000.0 + 1.0 * 25.0)    # 2025.0

    def test_compute_strategy_barriers_fixed_fallback(self):
        """固定%バリアへのフォールバック (ATR <= 0 または barrier_type == 'fixed')"""
        entry = 1000.0
        atr = 0.0
        profile = {
            "barrier_type": "fixed",
            "take_profit_pct": 2.0,  # +2.0%
            "stop_loss_pct": -1.0    # -1.0%
        }
        barriers = compute_strategy_barriers(entry, atr, profile, position=1)
        self.assertAlmostEqual(barriers["take_profit"], 1020.0)
        self.assertAlmostEqual(barriers["stop_loss"], 990.0)

    def test_position_stores_dynamic_barriers(self):
        """Position dataclass が tp_price と sl_price を保持できるか"""
        pos = Position(
            position_id="test_01",
            symbol="GC=F",
            side="BUY",
            entry_price=2600.0,
            current_price=2600.0,
            amount=1.0,
            tp_price=2650.0,
            sl_price=2575.0
        )
        self.assertEqual(pos.tp_price, 2650.0)
        self.assertEqual(pos.sl_price, 2575.0)

    def test_virtual_account_opens_position_with_barriers(self):
        """VirtualAccount.open_position が tp_price, sl_price を正確に設定するか"""
        account = VirtualAccount(user_id="test_user", user_name="Tester", initial_cash=1_000_000.0)
        pos = account.open_position(
            symbol="GC=F",
            side="BUY",
            current_price=2600.0,
            amount=1.0,
            leverage=2.0,
            tp_price=2650.0,
            sl_price=2575.0
        )
        self.assertEqual(pos.tp_price, 2650.0)
        self.assertEqual(pos.sl_price, 2575.0)
        self.assertIn(pos.position_id, account.positions)

    def test_pessimistic_execution_engine_with_dynamic_barriers(self):
        """PessimisticExecutionEngine が動的ATRバリアでもSL最優先で約定するか"""
        engine = PessimisticExecutionEngine()
        entry = 2000.0
        atr = 20.0
        tp_price = entry + 2.0 * atr  # 2040.0
        sl_price = entry - 1.0 * atr  # 1980.0

        # ケース1: 同一バーで High >= 2040 かつ Low <= 1980 (両方到達)
        is_closed, exit_px, reason = engine.evaluate_bar(
            entry_price=entry,
            position=1,
            bar_high=2045.0,
            bar_low=1975.0,
            bar_close=2030.0,
            tp_price=tp_price,
            sl_price=sl_price,
            slippage_pct=0.0005,
            fee_pct=0.0003
        )
        self.assertTrue(is_closed)
        self.assertEqual(reason, "SL_PESSIMISTIC_PRIORITY")
        self.assertLess(exit_px, sl_price)  # スリッページ・手数料控除

        # ケース2: High >= 2040 のみ到達 (Low = 1990)
        is_closed, exit_px, reason = engine.evaluate_bar(
            entry_price=entry,
            position=1,
            bar_high=2042.0,
            bar_low=1990.0,
            bar_close=2035.0,
            tp_price=tp_price,
            sl_price=sl_price,
            slippage_pct=0.0005,
            fee_pct=0.0003
        )
        self.assertTrue(is_closed)
        self.assertEqual(reason, "TP_HIT")

    def test_autopilot_engine_dynamic_barrier_exit(self):
        """AutopilotEngine が動的バリア価格で利確・損切りを正しく実行するか"""
        account = VirtualAccount(user_id="test_user", user_name="Tester", initial_cash=1_000_000.0)
        cfg = AutopilotConfig(is_active=True, strategy_style="scalping", base_equity_today=1_000_000.0)
        engine = AutopilotEngine(user_account=account)
        engine.config = cfg

        # ポジションを開く (動的バリア付与)
        account.open_position(
            symbol="GC=F",
            side="BUY",
            current_price=2600.0,
            amount=1.0,
            tp_price=2630.0,
            sl_price=2585.0
        )

        # 価格が 2635.0 に上昇 -> TP決済
        card_tp = {
            "current_price": 2635.0,
            "prob_up_pct": 60.0,
            "current_atr": 15.0,
            "meta_bet_size_pct": 100.0
        }
        res_tp = engine.evaluate_and_execute("GC=F", card_tp)
        self.assertEqual(res_tp, "CLOSE_TAKE_PROFIT")
        self.assertEqual(len(account.positions), 0)


if __name__ == "__main__":
    unittest.main()
