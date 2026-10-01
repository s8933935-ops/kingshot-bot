"""
test_htf_pipeline_and_ui.py
HTF特徴量自己補完パイプライン、出走表整合性、および防御ゲートログの単体テスト
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import numpy as np
import pandas as pd

from src.invest_engine.feature_generator import generate_features
from src.invest_engine.game_manager import InvestmentGameManager
from src.invest_engine.autopilot_engine import AutopilotEngine, STRATEGY_PROFILES
from src.invest_engine.virtual_broker import VirtualAccount


class TestHTFPipelineAndUI(unittest.TestCase):
    def setUp(self):
        # 疑似OHLCV日足データ（150日分）
        dates = pd.date_range("2026-01-01", periods=150, freq="D")
        np.random.seed(42)
        base_price = 4000.0 + np.cumsum(np.random.normal(1.0, 10.0, 150))
        self.df = pd.DataFrame(
            {
                "Open": base_price + np.random.normal(0, 2, 150),
                "High": base_price + 15.0,
                "Low": base_price - 15.0,
                "Close": base_price,
                "Volume": np.random.randint(1000, 5000, 150),
            },
            index=dates
        )

    def test_htf_features_self_contained_daily(self):
        """日足単体でもHTF日足トレンド特徴量が安全に生成されることを検証"""
        clean_df, feature_cols = generate_features(self.df, use_triple_barrier=False)
        self.assertIn("htf_daily_trend", clean_df.columns)
        self.assertIn("htf_daily_dist_sma20", clean_df.columns)
        self.assertIn("htf_daily_dist_sma50", clean_df.columns)
        self.assertIn("htf_daily_slope", clean_df.columns)

        # feature_cols に含まれていることを確認
        self.assertIn("htf_daily_trend", feature_cols)
        self.assertIn("htf_daily_dist_sma20", feature_cols)

        # 先読みリークなし: トレンド値は +1.0, -1.0, 0.0 のいずれか
        unique_trends = set(clean_df["htf_daily_trend"].unique())
        self.assertTrue(unique_trends.issubset({-1.0, 0.0, 1.0}))

    def test_game_manager_card_has_regime_and_htf(self):
        """出走表に regime_state と htf_daily_trend が正しく含まれることを検証"""
        gm = InvestmentGameManager()
        with patch("src.invest_engine.game_manager.fetch_historical_data") as mock_fetch, \
             patch("src.invest_engine.game_manager.GoldPredictorModel") as mock_pred_cls:

            mock_fetch.return_value = self.df
            mock_pred = mock_pred_cls.return_value
            mock_pred.predict_next_day.return_value = {"prob_up": 0.65, "prob_down": 0.35, "confidence": "HIGH"}

            card = gm.generate_race_card("GC=F")

            self.assertIn("regime_state", card)
            self.assertIn("htf_daily_trend", card)
            self.assertIn("current_atr", card)
            self.assertIn("atr_pct", card)
            self.assertIsInstance(card["regime_state"], str)
            self.assertIsInstance(card["htf_daily_trend"], float)

    def test_autopilot_defensive_gate_logs_format(self):
        """防御ゲート遮断時のDecisionLogがUI互換フォーマットであることを検証"""
        account = VirtualAccount("test_user", "Test User", initial_cash=1_000_000.0)
        ap = AutopilotEngine(account)
        ap.toggle(is_active=True, strategy_style="day_trade")

        # 1. もみ合い相場遮断 (CHOPPY_RANGE)
        race_card_choppy = {
            "current_price": 4200.0,
            "prob_up_pct": 70.0,
            "current_atr": 30.0,
            "regime_state": "CHOPPY_RANGE",
            "htf_daily_trend": 1.0,
            "meta_bet_size_pct": 100.0,
            "meta_confidence": "FULL"
        }
        res1 = ap.evaluate_and_execute("GC=F", race_card_choppy)
        self.assertEqual(res1, "SKIP_CHOPPY_REGIME")
        self.assertEqual(ap.logs[0].action, "SKIP_CHOPPY_REGIME")
        self.assertIn("もみ合いレンジ相場", ap.logs[0].reason)

        # 2. 上位足逆行遮断 (HTF下降トレンド中の買い)
        race_card_htf = {
            "current_price": 4200.0,
            "prob_up_pct": 70.0,
            "current_atr": 30.0,
            "regime_state": "BULL_TREND",
            "htf_daily_trend": -1.0,  # 上位足下降
            "meta_bet_size_pct": 100.0,
            "meta_confidence": "FULL"
        }
        res2 = ap.evaluate_and_execute("GC=F", race_card_htf)
        self.assertEqual(res2, "SKIP_HTF_ALIGNMENT")
        self.assertEqual(ap.logs[0].action, "SKIP_HTF_ALIGNMENT")
        self.assertIn("上位足(日足)下降トレンド逆行", ap.logs[0].reason)

        # get_status() の recent_logs 整合性検証
        status = ap.get_status()
        self.assertIn("recent_logs", status)
        self.assertTrue(len(status["recent_logs"]) >= 2)
        actions = [log["action"] for log in status["recent_logs"]]
        self.assertIn("SKIP_CHOPPY_REGIME", actions)
        self.assertIn("SKIP_HTF_ALIGNMENT", actions)


if __name__ == "__main__":
    unittest.main()
