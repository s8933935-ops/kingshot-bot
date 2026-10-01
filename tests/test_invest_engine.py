"""
投資予測エンジンの基本動作検証テスト (unittest版)
"""

import unittest
import pandas as pd
import numpy as np
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.model_trainer import GoldPredictorModel
from src.invest_engine.backtester import run_backtest


def create_dummy_ohlcv(n_bars: int = 150) -> pd.DataFrame:
    """テスト用のダミーOHLCVデータを生成"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="B")
    close = 2000.0 + np.cumsum(np.random.randn(n_bars) * 10)
    high = close + np.random.rand(n_bars) * 5
    low = close - np.random.rand(n_bars) * 5
    open_p = close + np.random.randn(n_bars) * 2
    volume = np.random.randint(1000, 10000, size=n_bars)

    df = pd.DataFrame({
        "Open": open_p,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume
    }, index=dates)
    return df


class TestInvestEngine(unittest.TestCase):

    def test_feature_generation(self):
        df = create_dummy_ohlcv(150)
        clean_df, feature_cols = generate_features(df)
        self.assertFalse(clean_df.empty)
        self.assertGreaterEqual(len(feature_cols), 15)
        self.assertIn("rsi_14", feature_cols)
        self.assertIn("macd", feature_cols)
        self.assertIn("target_binary", clean_df.columns)

    def test_model_training_and_prediction(self):
        df = create_dummy_ohlcv(200)
        clean_df, feature_cols = generate_features(df)
        
        predictor = GoldPredictorModel(n_splits=3)
        results = predictor.train_walk_forward(clean_df, feature_cols)
        
        self.assertIn("overall_accuracy", results)
        self.assertTrue(0.0 <= results["overall_accuracy"] <= 1.0)
        
        # 予測のテスト
        latest = clean_df.iloc[-1]
        pred = predictor.predict_next_day(latest)
        self.assertIn("prob_up", pred)
        self.assertIn("signal", pred)
        self.assertTrue(0.0 <= pred["prob_up"] <= 1.0)

    def test_backtest_execution(self):
        df = create_dummy_ohlcv(100)
        df["pred_prob"] = np.random.uniform(0.4, 0.6, size=len(df))
        df["target_future_return"] = np.random.randn(len(df)) * 0.01

        res = run_backtest(df, threshold_long=0.52, threshold_short=0.48)
        m = res["metrics"]
        self.assertIn("win_rate_pct", m)
        self.assertIn("profit_factor", m)
        self.assertIn("risk_reward_ratio", m)
        self.assertIn("total_return_pct", m)
        self.assertIn("cagr_pct", m)
        self.assertIn("max_drawdown_pct", m)
        self.assertIn("sharpe_ratio", m)
        self.assertIn("calmar_ratio", m)


if __name__ == "__main__":
    unittest.main()
