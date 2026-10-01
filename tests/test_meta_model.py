import unittest
import numpy as np
import pandas as pd
from src.invest_engine.meta_model import (
    FEATURE_COLUMNS,
    MetaLabelingEngine,
    compute_bet_size,
    generate_meta_labels
)


class TestMetaModel(unittest.TestCase):
    """メタラベリングモジュールの単体テスト"""

    def test_compute_bet_size(self):
        # 期待値ゼロ以下のときは見送り (0.0)
        self.assertEqual(compute_bet_size(0.5, 1.0), 0.0)
        # 高確率・高RR比では正のロット比率を返す
        bet_positive = compute_bet_size(0.7, 1.5)
        self.assertGreater(bet_positive, 0.0)
        self.assertLessEqual(bet_positive, 1.0)

    def test_generate_meta_labels(self):
        # 一次モデルがLong(0.55 >= 0.52)で実約定が1 (勝ち) -> メタラベル 1
        meta_win = generate_meta_labels(
            pred_prob=pd.Series([0.55]),
            true_label=pd.Series([1]),
            threshold=0.52
        )
        self.assertEqual(meta_win.iloc[0], 1)

        # 一次モデルがLong(0.55 >= 0.52)で実約定が0 (負け) -> メタラベル 0
        meta_loss = generate_meta_labels(
            pred_prob=pd.Series([0.55]),
            true_label=pd.Series([0]),
            threshold=0.52
        )
        self.assertEqual(meta_loss.iloc[0], 0)

    def test_meta_labeling_engine(self):
        engine = MetaLabelingEngine()
        
        # 100サンプル分のダミーデータ作成
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "pred_prob": np.random.uniform(0.4, 0.7, size=n),
            "dxy": np.random.normal(0, 0.01, size=n),
            "us10y": np.random.normal(0, 0.02, size=n),
            "tailwind_score": np.random.choice([-1.0, 0.0, 1.0], size=n)
        })
        y_meta = pd.Series(np.random.choice([0, 1], size=n))

        engine.fit(df, y_meta)
        proba = engine.predict_proba(df)

        self.assertEqual(len(proba), n)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in proba))


    def test_compute_bet_size_invalid_inputs(self):
        """Kelly計算の異常値入力バリデーションを検証"""
        with self.assertRaises(ValueError):
            compute_bet_size(-0.1, 1.5)
        with self.assertRaises(ValueError):
            compute_bet_size(1.1, 1.5)
        with self.assertRaises(ValueError):
            compute_bet_size(0.6, 0.0)
        with self.assertRaises(ValueError):
            compute_bet_size(0.6, -1.0)
        with self.assertRaises(ValueError):
            compute_bet_size(0.6, 1.5, kelly_fraction=0.0)
        with self.assertRaises(ValueError):
            compute_bet_size(0.6, 1.5, kelly_fraction=1.5)

    def test_meta_engine_save_and_load(self):
        """モデルの保存と load_from_file による推論再現性を検証"""
        import tempfile
        import os

        engine = MetaLabelingEngine()
        np.random.seed(42)
        n = 50
        df = pd.DataFrame({
            "pred_prob": np.random.uniform(0.4, 0.7, size=n),
            "dxy": np.random.normal(0, 0.01, size=n),
            "us10y": np.random.normal(0, 0.02, size=n),
            "tailwind_score": np.random.choice([-1.0, 0.0, 1.0], size=n)
        })
        y_meta = pd.Series(np.random.choice([0, 1], size=n))
        engine.fit(df, y_meta)
        orig_proba = engine.predict_proba(df)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            engine.save_model(tmp_path)
            loaded_engine = MetaLabelingEngine.load_from_file(tmp_path)
            loaded_proba = loaded_engine.predict_proba(df)
            np.testing.assert_allclose(orig_proba, loaded_proba, atol=1e-6)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


    def test_game_manager_failsafe_on_missing_model(self):
        """モデルファイル不在時に安全側(0%見送り)にフェイルセーフすることを検証"""
        from unittest.mock import patch
        from pathlib import Path
        from src.invest_engine.game_manager import InvestmentGameManager

        gm = InvestmentGameManager()
        # 存在しないパスをモック
        with patch.object(Path, "exists", return_value=False):
            # ダミーデータでの実行または安全側フォールバック確認
            # generate_race_card の安全保護挙動をテスト
            with patch("src.invest_engine.game_manager.fetch_historical_data") as mock_fetch, \
                 patch("src.invest_engine.game_manager.generate_features") as mock_feat, \
                 patch("src.invest_engine.game_manager.GoldPredictorModel") as mock_pred_cls:
                
                # モックデータ構築
                idx = pd.date_range("2026-01-01", periods=10, freq="D")
                mock_df = pd.DataFrame({"Close": [4000.0] * 10, "rsi_14": [50.0] * 10, "macd": [0.0] * 10, "return_1d": [0.01] * 10}, index=idx)
                mock_fetch.return_value = mock_df
                mock_feat.return_value = (mock_df, ["rsi_14"])
                mock_pred = mock_pred_cls.return_value
                mock_pred.predict_next_day.return_value = {"prob_up": 0.80, "confidence": "HIGH"}

                card = gm.generate_race_card("GC=F")
                self.assertEqual(card["meta_bet_size_pct"], 0.0)
                self.assertIn("UNVERIFIED", card["meta_confidence"])


if __name__ == "__main__":
    unittest.main()


