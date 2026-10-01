"""
Tests for Zero-Leakage & Anti-Overfit System
============================================

5大鉄壁防壁の決定論的動作を検証する unittest スイート:
1. 特徴量先読みリーク検知 (FeatureLeakageViolation)
2. 非OOF / 生DataFrameの執行遮断 (InSampleLeakageViolation)
3. 同一バー内 SL 最優先ペシミスティック約定 (SL_PESSIMISTIC_PRIORITY)
4. 多重検定バイアス検定 (Deflated Sharpe Ratio による過学習却下)
5. 正当な Purged OOF コンテナの正常合格
"""

import unittest
import numpy as np
import pandas as pd

from src.invest_engine.zero_leakage_engine import (
    PointInTimeAuditor,
    OOFProvenanceToken,
    StrictOOFContainer,
    PessimisticExecutionEngine,
    calculate_deflated_sharpe_ratio,
    ZeroLeakageGuard,
    FeatureLeakageViolation,
    InSampleLeakageViolation,
)


class TestZeroLeakageEngine(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        self.sample_df = pd.DataFrame(
            {
                "Close": 100.0 + np.cumsum(np.random.randn(100)),
                "feat_safe": np.random.randn(100),
                "target_future_return": np.random.randn(100) * 0.01,
            },
            index=dates,
        )

    def test_feature_leakage_detector_catches_future_target_leak(self):
        """未来リターンそのものや異常相関する特徴量を注入したとき、例外を投げるか"""
        df = self.sample_df.copy()
        # 意図的に未来リターンを特徴量として混入（悪質なリーク）
        df["feat_leaked"] = df["target_future_return"] * 1.0

        auditor = PointInTimeAuditor()
        with self.assertRaises(FeatureLeakageViolation) as cm:
            auditor.audit_features(df, ["feat_safe", "feat_leaked"])

        msg = str(cm.exception)
        self.assertTrue("UnrealisticFutureCorrelation" in msg or "相関" in msg)

    def test_feature_leakage_detector_catches_non_monotonic_index(self):
        """時系列インデックスが昇順でない場合（因果律崩壊）に例外を投げるか"""
        df = self.sample_df.copy()
        df = df.sample(frac=1.0, random_state=123)  # シャッフル

        auditor = PointInTimeAuditor()
        with self.assertRaises(FeatureLeakageViolation) as cm:
            auditor.audit_features(df, ["feat_safe"])

        msg = str(cm.exception)
        self.assertTrue("時系列" in msg or "NonMonotonicIndex" in msg)

    def test_insample_execution_blocked_without_strict_oof_container(self):
        """生DataFrameや未署名オブジェクトを渡したとき、バックテスト執行を物理拒絶するか"""
        guard = ZeroLeakageGuard()

        # 生DataFrameを渡して実行しようとする
        with self.assertRaises(InSampleLeakageViolation) as cm:
            guard.verify_and_protect_backtest(
                container=self.sample_df,  # StrictOOFContainer ではない
                strategy_func=lambda x: {"trade_returns": [0.01]},
                features=["feat_safe"]
            )

        self.assertIn("StrictOOFContainer", str(cm.exception))

    def test_pessimistic_execution_enforces_sl_priority_over_tp(self):
        """同一バー内で High >= TP かつ Low <= SL の場合、100% SL優先（損切り）と判定されるか"""
        engine = PessimisticExecutionEngine()

        entry_price = 100.0
        tp_price = 105.0
        sl_price = 95.0

        # 荒れたバー (High 106.0, Low 94.0): 両方に到達
        is_closed, exit_price, reason = engine.evaluate_bar(
            entry_price=entry_price,
            position=1,  # Long
            bar_high=106.0,  # TP(105) 達成
            bar_low=94.0,    # SL(95) 達成
            bar_close=101.0,
            tp_price=tp_price,
            sl_price=sl_price,
            slippage_pct=0.001,
            fee_pct=0.0003
        )

        self.assertTrue(is_closed)
        self.assertEqual(reason, "SL_PESSIMISTIC_PRIORITY")
        # SL価格から摩擦分（スリッページ+手数料）が引かれた損失価格になっていること
        self.assertLess(exit_price, sl_price)

    def test_deflated_sharpe_penalizes_multiple_testing_overfitting(self):
        """多重試行（データスヌーピング）された戦略が、DSRで厳格に過学習判定されるか"""
        np.random.seed(42)
        # 平均日次リターンがわずかにプラス（年率換算SR=1.2程度の見かけ上好調な戦略）
        returns = np.random.normal(0.0008, 0.01, 252)

        # 1試行の場合 (単独バックテスト)
        report_single = calculate_deflated_sharpe_ratio(returns, num_trials=1)
        
        # 1,000回ハイパーパラメータ探索を繰り返して選別した場合 (多重試行ペナルティ)
        report_mined = calculate_deflated_sharpe_ratio(returns, num_trials=1000)

        # 試行回数が増えると期待最大SRが跳ね上がり、DSRスコアが激減する
        self.assertLess(report_mined["deflated_sharpe_ratio"], report_single["deflated_sharpe_ratio"])
        self.assertGreater(report_mined["expected_max_sr"], report_single["expected_max_sr"])
        self.assertGreater(report_mined["p_value"], report_single["p_value"])

    def test_legitimate_oof_pipeline_passes_guard(self):
        """正規の OOF トークン付きコンテナは正しくパスし、バックテストが完走するか"""
        df = self.sample_df.copy()
        df["pred_prob"] = np.random.uniform(0.4, 0.6, len(df))
        df["_oof_fold"] = [i % 5 for i in range(len(df))]

        # 正当なトークンを発行
        token = OOFProvenanceToken.create(
            cv_method="PurgedKFold",
            n_splits=5,
            embargo_pct=0.01,
            total_samples=len(df),
            fold_train_indices=[np.arange(80) for _ in range(5)]
        )

        container = StrictOOFContainer(df, token)
        guard = ZeroLeakageGuard(num_trials=1)

        dummy_strategy = lambda data: {
            "trade_returns": np.random.normal(0.001, 0.01, 50),
            "status": "COMPLETED"
        }

        results = guard.verify_and_protect_backtest(
            container=container,
            strategy_func=dummy_strategy,
            features=["feat_safe"]
        )

        self.assertEqual(results["status"], "COMPLETED")
        self.assertIn("deflated_sharpe_analysis", results)


if __name__ == "__main__":
    unittest.main()
