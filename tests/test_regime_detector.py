import unittest
import numpy as np
import pandas as pd
from src.invest_engine.regime_detector import (
    MarketRegime,
    detect_market_regime,
    ADXCalculator,
    EMATrendAnalyzer,
    BollingerBandwidthAnalyzer
)


class TestRegimeDetector(unittest.TestCase):
    """相場レジーム判別モジュールの単体テスト"""

    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=150, freq="B")
        returns = np.random.normal(0.0005, 0.01, size=len(dates))
        close = 100.0 * np.cumprod(1 + returns)
        high = close * 1.01
        low = close * 0.99
        open_p = close * 0.995
        
        self.df = pd.DataFrame({
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.random.randint(1000, 5000, size=len(dates))
        }, index=dates)

    def test_detect_market_regime_structure(self):
        res = detect_market_regime(self.df, adx_threshold=22.0)
        self.assertIsInstance(res, pd.DataFrame)
        
        expected_cols = [
            "adx", "plus_di", "minus_di",
            "ema_fast", "ema_slow", "ema_direction",
            "bb_bandwidth_pct", "bb_is_squeeze",
            "regime", "regime_label", "allow_entry"
        ]
        for col in expected_cols:
            self.assertIn(col, res.columns)

        # レジーム値が有効な範囲内か
        valid_regimes = {MarketRegime.TREND_BULL, MarketRegime.TREND_BEAR, MarketRegime.RANGE_CHOPPY}
        self.assertTrue(set(res["regime"].unique()).issubset(valid_regimes))
        self.assertTrue(res["allow_entry"].dtype == bool)

    def test_strong_bull_trend_detection(self):
        """明確な急上昇相場で TREND_BULL が検出されること"""
        dates = pd.date_range("2023-01-01", periods=100, freq="B")
        # 連続上昇トレンド
        close = [100.0 + i * 2.0 for i in range(100)]
        df_bull = pd.DataFrame({
            "High": [c + 1.0 for c in close],
            "Low": [c - 0.5 for c in close],
            "Close": close,
        }, index=dates)

        res = detect_market_regime(df_bull, adx_threshold=25.0)
        # 後半では明確に上昇トレンドが判定されていること
        later_regimes = res["regime"].iloc[60:]
        self.assertTrue((later_regimes == MarketRegime.TREND_BULL).any())


if __name__ == "__main__":
    unittest.main()
