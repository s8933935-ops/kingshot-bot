import unittest
import numpy as np
import pandas as pd
from src.invest_engine.labeling import get_dynamic_volatility, apply_triple_barrier


class TestTripleBarrierLabeling(unittest.TestCase):
    """トリプルバリア法（Triple Barrier Method）の単体テスト"""

    def setUp(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="B")
        np.random.seed(42)
        base_price = 100.0
        returns = np.random.normal(0.0005, 0.01, size=len(dates))
        close = base_price * np.cumprod(1 + returns)

        self.df = pd.DataFrame({
            "Open": close * (1 - 0.001),
            "High": close * (1 + 0.005),
            "Low": close * (1 - 0.005),
            "Close": close,
            "Volume": np.random.randint(1000, 5000, size=len(dates))
        }, index=dates)

    def test_get_dynamic_volatility(self):
        vol_atr = get_dynamic_volatility(self.df, vol_window=10, method="atr")
        self.assertIsInstance(vol_atr, pd.Series)
        self.assertTrue(vol_atr.dropna().gt(0).all(), "ATRボラティリティは正の実数であること")

        vol_ewma = get_dynamic_volatility(self.df, vol_window=10, method="ewma")
        self.assertIsInstance(vol_ewma, pd.Series)
        self.assertTrue(vol_ewma.dropna().gt(0).all(), "EWMAボラティリティは正の実数であること")

    def test_apply_triple_barrier_structure(self):
        events = apply_triple_barrier(
            self.df,
            pt_factor=2.0,
            sl_factor=1.0,
            max_holding_days=5,
            vol_window=10,
            vol_method="atr"
        )
        self.assertIsInstance(events, pd.DataFrame)
        required_cols = [
            "entry_price", "vol", "upper_barrier", "lower_barrier",
            "vertical_barrier_time", "touch_time", "holding_days", "ret", "label"
        ]
        for col in required_cols:
            self.assertIn(col, events.columns)

        unique_labels = set(events["label"].unique())
        self.assertTrue(unique_labels.issubset({0, 1}), "ラベルは0または1であること")
        self.assertTrue((events["holding_days"] >= 1).all(), "保有日数は1日以上であること")
        self.assertTrue((events["holding_days"] <= 5).all(), "保有日数は最大日数5日以内であること")

    def test_apply_triple_barrier_strong_uptrend(self):
        dates = pd.date_range("2024-01-01", periods=30, freq="B")
        close = [100.0] * 15 + [100.0 + i * 5.0 for i in range(15)]

        df = pd.DataFrame({
            "Open": close,
            "High": [c + 1.0 for c in close],
            "Low": [c - 1.0 for c in close],
            "Close": close,
            "Volume": [1000] * 30
        }, index=dates)

        events = apply_triple_barrier(
            df,
            pt_factor=1.5,
            sl_factor=1.5,
            max_holding_days=5,
            vol_window=5
        )
        uptrend_events = events.iloc[10:15]
        self.assertTrue((uptrend_events["label"] == 1).any(), "急上昇局面で利確バリアが発火すること")

    def test_apply_triple_barrier_strong_downtrend(self):
        dates = pd.date_range("2024-01-01", periods=30, freq="B")
        close = [100.0] * 15 + [100.0 - i * 5.0 for i in range(15)]

        df = pd.DataFrame({
            "Open": close,
            "High": [c + 1.0 for c in close],
            "Low": [c - 1.0 for c in close],
            "Close": close,
            "Volume": [1000] * 30
        }, index=dates)

        events = apply_triple_barrier(
            df,
            pt_factor=1.5,
            sl_factor=1.5,
            max_holding_days=5,
            vol_window=5
        )
        downtrend_events = events.iloc[10:15]
        self.assertTrue((downtrend_events["label"] == 0).any(), "急落局面で損切りバリアが発火すること")


if __name__ == "__main__":
    unittest.main()
