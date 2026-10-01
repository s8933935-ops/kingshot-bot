"""
Unit tests for Data Quality Cleaner, Session Features, and HTF Merging
=======================================================================
"""

import unittest
import numpy as np
import pandas as pd
from src.invest_engine.data_cleaner import (
    clean_outliers_and_bad_ticks,
    add_session_features,
    merge_htf_trend_features
)
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.zero_leakage_engine import PointInTimeAuditor


class TestDataCleaner(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range("2026-09-01", periods=100, freq="15min")
        self.sample_df = pd.DataFrame(
            {
                "Open": 100.0 + np.cumsum(np.random.randn(100) * 0.1),
                "High": 100.5 + np.cumsum(np.random.randn(100) * 0.1),
                "Low": 99.5 + np.cumsum(np.random.randn(100) * 0.1),
                "Close": 100.0 + np.cumsum(np.random.randn(100) * 0.1),
                "Volume": np.random.randint(100, 1000, 100)
            },
            index=dates
        )
        # Ensure High >= Low
        self.sample_df["High"] = self.sample_df[["Open", "Close", "High"]].max(axis=1) + 0.1
        self.sample_df["Low"] = self.sample_df[["Open", "Close", "Low"]].min(axis=1) - 0.1

    def test_clean_outliers_and_bad_ticks(self):
        """1バー限りの異常スパイク（Bad Tick）が検知・平滑化されるか"""
        df = self.sample_df.copy()
        # 50番目のバーに極端な急騰・即急落パルスを挿入 (+50%)
        normal_close = df["Close"].iloc[49]
        df.iloc[50, df.columns.get_loc("Close")] = normal_close * 1.50
        df.iloc[50, df.columns.get_loc("High")] = normal_close * 1.55

        cleaned = clean_outliers_and_bad_ticks(df, threshold_sigma=4.0, window=30)
        # 異常パルスが補正され、直前終値近傍に抑えられていること
        self.assertLess(cleaned["Close"].iloc[50], normal_close * 1.10)

    def test_add_session_features(self):
        """取引セッション（NY/London vs Asia）が正確にフラグ付けされるか"""
        df = self.sample_df.copy()
        with_session = add_session_features(df)
        self.assertIn("session_ny_london", with_session.columns)
        self.assertIn("session_asia", with_session.columns)
        self.assertIn("session_offhours", with_session.columns)
        # 各行でセッションフラグの合計は 1.0
        row_sums = with_session["session_ny_london"] + with_session["session_asia"] + with_session["session_offhours"]
        self.assertTrue((row_sums == 1.0).all())

    def test_merge_htf_trend_features_zero_leakage(self):
        """上位足（日足）トレンドが 1バー遅行（shift(1)）で結合され、先読みリークがないか"""
        ltf_dates = pd.date_range("2026-09-01 09:00", periods=50, freq="15min")
        ltf_df = pd.DataFrame(
            {"Close": np.linspace(100, 110, 50)},
            index=ltf_dates
        )

        htf_dates = pd.date_range("2026-08-25", periods=10, freq="D")
        htf_df = pd.DataFrame(
            {"Close": np.linspace(90, 100, 10)},
            index=htf_dates
        )

        merged = merge_htf_trend_features(ltf_df, htf_df, htf_name="daily")
        self.assertIn("htf_daily_trend", merged.columns)
        self.assertIn("htf_daily_dist_sma20", merged.columns)
        # 行数が維持されていること
        self.assertEqual(len(merged), len(ltf_df))

    def test_generate_features_with_htf_passes_point_in_time_audit(self):
        """HTF結合特徴量を含む特徴量生成が Point-in-Time 監査に合格するか"""
        raw_df = self.sample_df.copy()
        htf_df = pd.DataFrame(
            {"Close": np.linspace(95, 105, 30)},
            index=pd.date_range("2026-08-15", periods=30, freq="D")
        )

        clean_df, feature_cols = generate_features(raw_df, max_holding_days=5, htf_df=htf_df)
        self.assertIn("htf_daily_trend", feature_cols)

        auditor = PointInTimeAuditor()
        audit_res = auditor.audit_features(clean_df, feature_cols)
        self.assertTrue(audit_res["audit_passed"])


if __name__ == "__main__":
    unittest.main()
