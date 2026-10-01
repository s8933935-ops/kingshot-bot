"""
機械学習モデル学習・評価モジュール (LightGBM)
金融時系列データの特性に合わせ、Purged Walk-Forward (TimeSeriesSplit) で学習・評価を行います。
"""

import os
import warnings
from pathlib import Path
from typing import Dict, Any, Tuple
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from src.invest_engine.purged_cv import PurgedKFold

import warnings
warnings.filterwarnings("ignore")


MODEL_DIR = Path("data/invest_models")


class GoldPredictorModel:
    """
    金先物・コモディティ用のLightGBM分類予測モデル
    """

    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits
        self.model: lgb.LGBMClassifier = None
        self.feature_names = []
        self.feature_importances_ = None

    def train_walk_forward(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        target_col: str = "target_binary",
        use_purged_cv: bool = True,
        pct_embargo: float = 0.01
    ) -> Dict[str, Any]:
        """
        ウォークフォワード時系列検証（Purged K-Fold with Embargo）を行いながらモデルを学習・評価する。

        Parameters:
        - df: 特徴量とターゲットを含むDataFrame (時系列昇順)
        - feature_cols: 入力特徴量カラムのリスト
        - target_col: 予測ターゲット ('target_binary')
        - use_purged_cv: Purged K-Foldを使用するかどうか

        Returns:
        - Dict[str, Any]: 各フォールドのスコア、総合スコア、特徴量重要度
        """
        self.feature_names = feature_cols
        X = df[feature_cols].values
        y = df[target_col].values

        if use_purged_cv:
            # 各サンプルの終了日時 (target_holding_days または 1日後)
            if "target_holding_days" in df.columns:
                t1 = df.index + pd.to_timedelta(df["target_holding_days"].fillna(1).astype(int), unit="D")
            else:
                t1 = df.index + pd.to_timedelta(1, unit="D")
            cv = PurgedKFold(n_splits=self.n_splits, t1=pd.Series(t1, index=df.index), pct_embargo=pct_embargo)
            cv_splits = list(cv.split(df[feature_cols], df[target_col]))
        else:
            tscv = TimeSeriesSplit(n_splits=self.n_splits)
            cv_splits = list(tscv.split(X))

        fold_scores = []
        oof_preds = np.zeros(len(df))
        oof_probs = np.zeros(len(df))
        test_indices = []

        # クオンツ・金融時系列に適した過学習抑制パラメータ
        lgb_params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "n_estimators": 150,
            "learning_rate": 0.03,
            "max_depth": 4,
            "num_leaves": 15,
            "min_child_samples": 25,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "verbose": -1
        }

        importances = np.zeros(len(feature_cols))

        for fold, (train_idx, val_idx) in enumerate(cv_splits):
            X_train, y_train = X[train_idx], y[train_idx]
            X_val, y_val = X[val_idx], y[val_idx]

            clf = lgb.LGBMClassifier(**lgb_params)
            clf.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
            )

            preds_prob = clf.predict_proba(X_val)[:, 1]
            preds_class = (preds_prob >= 0.5).astype(int)

            oof_probs[val_idx] = preds_prob
            oof_preds[val_idx] = preds_class
            test_indices.extend(val_idx)

            acc = accuracy_score(y_val, preds_class)
            auc = roc_auc_score(y_val, preds_prob) if len(np.unique(y_val)) > 1 else 0.5

            fold_scores.append({
                "fold": fold + 1,
                "train_size": len(train_idx),
                "val_size": len(val_idx),
                "accuracy": float(acc),
                "auc": float(auc)
            })

            importances += clf.feature_importances_ / self.n_splits

        # 全データで最終モデルを学習（直近の推論用）
        self.model = lgb.LGBMClassifier(**lgb_params)
        self.model.fit(X, y)
        self.feature_importances_ = pd.DataFrame({
            "feature": feature_cols,
            "importance": self.model.feature_importances_
        }).sort_values(by="importance", ascending=False)

        # OOF（Out-of-fold: 未知データに対する検証）評価
        valid_oof_y = y[test_indices]
        valid_oof_preds = oof_preds[test_indices]
        valid_oof_probs = oof_probs[test_indices]

        overall_acc = accuracy_score(valid_oof_y, valid_oof_preds)
        overall_auc = roc_auc_score(valid_oof_y, valid_oof_probs)
        precision = precision_score(valid_oof_y, valid_oof_preds, zero_division=0)
        recall = recall_score(valid_oof_y, valid_oof_preds, zero_division=0)

        # OOF予測結果をDataFrameに付与してバックテストに渡せるようにする
        eval_df = df.iloc[test_indices].copy()
        eval_df["pred_prob"] = valid_oof_probs
        eval_df["pred_class"] = valid_oof_preds

        results = {
            "overall_accuracy": float(overall_acc),
            "overall_auc": float(overall_auc),
            "precision": float(precision),
            "recall": float(recall),
            "fold_scores": fold_scores,
            "feature_importance_top10": self.feature_importances_.head(10).to_dict(orient="records"),
            "eval_df": eval_df
        }

        return results

    def predict_next_day(self, latest_row: pd.Series) -> Dict[str, Any]:
        """
        最新データ1行（本日の確定値）から、翌日の上昇確率・推奨シグナルを判定する。
        """
        if self.model is None:
            raise ValueError("Model is not trained yet.")

        X_input = latest_row[self.feature_names].values.reshape(1, -1)
        prob_up = float(self.model.predict_proba(X_input)[0, 1])

        # 確率に応じたシグナル判定
        if prob_up >= 0.55:
            signal = "BUY (Long)"
            confidence = "HIGH" if prob_up >= 0.60 else "MEDIUM"
        elif prob_up <= 0.45:
            signal = "SELL (Short)"
            confidence = "HIGH" if prob_up <= 0.40 else "MEDIUM"
        else:
            signal = "HOLD / NEUTRAL"
            confidence = "LOW"

        return {
            "prob_up": prob_up,
            "prob_down": 1.0 - prob_up,
            "signal": signal,
            "confidence": confidence
        }

    def save(self, filepath: Path = MODEL_DIR / "gold_lgbm_model.txt"):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        self.model.booster_.save_model(str(filepath))

    def load(self, filepath: Path = MODEL_DIR / "gold_lgbm_model.txt"):
        self.model = lgb.Booster(model_file=str(filepath))
