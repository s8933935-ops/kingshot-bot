import unittest
import numpy as np
import pandas as pd
from src.invest_engine.purged_cv import PurgedKFold


class TestPurgedKFold(unittest.TestCase):
    """Purged K-Fold Cross Validationの単体テスト"""

    def setUp(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        # 各サンプルは5日後にイベント終了（保有期間5日）
        t_exit = dates + pd.to_timedelta(5, unit="D")
        self.t1 = pd.Series(data=t_exit, index=dates, name="t1")
        self.X = pd.DataFrame(np.random.randn(100, 4), index=dates)
        self.y = pd.Series(np.random.randint(0, 2, size=100), index=dates)

    def test_purged_kfold_splits(self):
        pkf = PurgedKFold(n_splits=5, t1=self.t1, pct_embargo=0.02)
        folds = list(pkf.split(self.X, self.y))
        
        self.assertEqual(len(folds), 5)
        for train_idx, test_idx in folds:
            # 訓練とテストに共通インデックスがないこと
            common = set(train_idx).intersection(set(test_idx))
            self.assertEqual(len(common), 0)
            
            # パージ/エンバーゴにより、train + test < total であること
            self.assertLess(len(train_idx) + len(test_idx), len(self.X))


if __name__ == "__main__":
    unittest.main()
