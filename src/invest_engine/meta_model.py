"""
src/invest_engine/meta_model.py

Marcos Lopez de Prado 流「メタラベリング（Meta-Labeling）」と
ハーフケリー基準によるベッティングサイズ算出を行うモジュール。

構成:
    1. generate_meta_labels
        一次モデルの予測確率(pred_prob)と実約定ラベル(true_label)から
        メタラベル(y_meta: 一次シグナルが正解なら1、不正解なら0)を生成する。
    2. MetaLabelingEngine
        一次確率 + マクロ指標(DXY, US10Y, テールウィンドスコア)を特徴量として
        LightGBM分類器でメタ確率(的中確信度)を学習・推論するクラス。
        PurgedKFold等、sklearn の BaseCrossValidator 互換オブジェクトを
        そのまま cv 引数に渡せる。
    3. compute_bet_size
        メタ確率とリスクリワード比から、ハーフケリー基準による
        最適賭け金比率 (0.0〜1.0) を算出する関数。

参考: Marcos Lopez de Prado, "Advances in Financial Machine Learning" (2018),
      Chapter 3 (Meta-Labeling) and related bet-sizing literature.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb
except ImportError as exc:  # pragma: no cover - 環境依存の防御的処理
    raise ImportError(
        "MetaLabelingEngine を使用するには lightgbm が必要です。"
        " `pip install lightgbm` を実行してください。"
    ) from exc

from sklearn.metrics import roc_auc_score
from sklearn.model_selection import BaseCrossValidator

logger = logging.getLogger(__name__)

__all__ = [
    "FEATURE_COLUMNS",
    "generate_meta_labels",
    "MetaLabelingConfig",
    "MetaLabelingEngine",
    "compute_bet_size",
]

# ---------------------------------------------------------------------------
# 特徴量定義
# ---------------------------------------------------------------------------

#: MetaLabelingEngine が学習・推論に用いる特徴量カラム名。
#: pred_prob  : 一次モデルが出力した予測確率 (0.0〜1.0)
#: dxy        : ドルインデックス (DXY)
#: us10y      : 米国10年国債利回り
#: tailwind_score : 独自算出のテールウィンドスコア (マクロ環境の追い風/向かい風の強さ)
FEATURE_COLUMNS: Tuple[str, ...] = ("pred_prob", "dxy", "us10y", "tailwind_score")


# ---------------------------------------------------------------------------
# 1. メタラベル生成関数
# ---------------------------------------------------------------------------

def generate_meta_labels(
    pred_prob: Union[pd.Series, np.ndarray, Sequence[float]],
    true_label: Union[pd.Series, np.ndarray, Sequence[int]],
    threshold: float = 0.5,
) -> pd.Series:
    """一次モデルの予測確率と実約定ラベルからメタラベルを生成する。

    一次モデルは ``pred_prob >= threshold`` のとき「シグナル発火(サイド=1)」、
    それ以外を「シグナル非発火(サイド=0)」とみなす。実際の約定結果
    ``true_label`` (1: 上昇/利益方向に約定, 0: それ以外) と一致していれば
    メタラベル 1 (的中)、一致していなければメタラベル 0 (不的中) を返す。

    Parameters
    ----------
    pred_prob : array-like of float
        一次モデルが出力した予測確率 (0.0〜1.0)。
    true_label : array-like of int (0 or 1)
        実際の約定結果を表す二値ラベル。
    threshold : float, default 0.5
        一次モデルのシグナル発火判定に用いる閾値。

    Returns
    -------
    pd.Series
        メタラベル y_meta (1: 一次シグナルが正解, 0: 不正解)。
        入力が pd.Series の場合はそのインデックスを保持する。

    Raises
    ------
    ValueError
        pred_prob と true_label の長さが一致しない場合、
        または true_label が {0, 1} 以外の値を含む場合。
    """
    index = pred_prob.index if isinstance(pred_prob, pd.Series) else None

    prob_arr = np.asarray(pred_prob, dtype=float)
    label_arr = np.asarray(true_label, dtype=float)

    if prob_arr.shape[0] != label_arr.shape[0]:
        raise ValueError(
            f"pred_prob (len={prob_arr.shape[0]}) と true_label "
            f"(len={label_arr.shape[0]}) の長さが一致しません。"
        )

    unique_labels = set(np.unique(label_arr).tolist())
    if not unique_labels.issubset({0.0, 1.0}):
        raise ValueError(
            f"true_label は {{0, 1}} の二値である必要がありますが、"
            f"{unique_labels} が検出されました。"
        )

    primary_side = (prob_arr >= threshold).astype(int)
    y_meta = (primary_side == label_arr.astype(int)).astype(int)

    result = pd.Series(y_meta, index=index, name="y_meta")
    logger.info(
        "generate_meta_labels: n=%d, hit_rate=%.4f",
        len(result),
        float(result.mean()) if len(result) else float("nan"),
    )
    return result


# ---------------------------------------------------------------------------
# 2. MetaLabelingEngine
# ---------------------------------------------------------------------------

@dataclass
class MetaLabelingConfig:
    """MetaLabelingEngine の LightGBM ハイパーパラメータ設定。"""

    objective: str = "binary"
    metric: str = "auc"
    boosting_type: str = "gbdt"
    learning_rate: float = 0.05
    num_leaves: int = 31
    max_depth: int = -1
    min_data_in_leaf: int = 20
    feature_fraction: float = 0.8
    bagging_fraction: float = 0.8
    bagging_freq: int = 1
    lambda_l1: float = 0.0
    lambda_l2: float = 1.0
    verbosity: int = -1
    random_state: int = 42
    num_boost_round: int = 500
    early_stopping_rounds: int = 30

    def to_lgb_params(self) -> Dict[str, Any]:
        """lightgbm.train に渡すパラメータ辞書を生成する。"""
        return {
            "objective": self.objective,
            "metric": self.metric,
            "boosting_type": self.boosting_type,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "min_data_in_leaf": self.min_data_in_leaf,
            "feature_fraction": self.feature_fraction,
            "bagging_fraction": self.bagging_fraction,
            "bagging_freq": self.bagging_freq,
            "lambda_l1": self.lambda_l1,
            "lambda_l2": self.lambda_l2,
            "verbosity": self.verbosity,
            "seed": self.random_state,
        }


class MetaLabelingEngine:
    """LightGBM を用いたメタラベリングエンジン。

    一次モデルの予測確率 (pred_prob) とマクロ指標 (DXY, US10Y,
    テールウィンドスコア) を特徴量として、メタラベル (的中/不的中) を
    予測する二値分類器を学習・推論する。

    Purged K-Fold Cross-Validation (例: mlfinlab の PurgedKFold や
    自作の sklearn.model_selection.BaseCrossValidator 互換クラス) を
    ``fit`` の ``cv`` 引数にそのまま渡すことができ、時系列データの
    リーク(情報漏洩)を防ぎながら Out-of-Fold 予測と AUC を評価できる。

    Examples
    --------
    >>> engine = MetaLabelingEngine()
    >>> engine.fit(X_train, y_meta_train, cv=purged_kfold)
    >>> meta_prob = engine.predict_proba(X_test)
    """

    def __init__(
        self,
        feature_columns: Optional[Sequence[str]] = None,
        config: Optional[MetaLabelingConfig] = None,
        threshold: float = 0.5,
    ) -> None:
        """
        Parameters
        ----------
        feature_columns : Sequence[str], optional
            学習・推論に用いる特徴量カラム名。未指定の場合は
            ``FEATURE_COLUMNS`` (pred_prob, dxy, us10y, tailwind_score) を使用する。
        config : MetaLabelingConfig, optional
            LightGBM のハイパーパラメータ設定。未指定の場合はデフォルト値を使用する。
        threshold : float, default 0.5
            predict_meta_label でメタラベルを二値化する際の閾値。
        """
        self.feature_columns: Tuple[str, ...] = tuple(
            feature_columns if feature_columns is not None else FEATURE_COLUMNS
        )
        self.config: MetaLabelingConfig = config if config is not None else MetaLabelingConfig()
        self.threshold: float = threshold

        self._model: Optional[lgb.Booster] = None
        self._feature_importance_: Optional[pd.Series] = None
        self._oof_predictions_: Optional[pd.Series] = None
        self._cv_auc_: Optional[float] = None
        self._is_fitted: bool = False

    # -- public properties ---------------------------------------------

    @property
    def is_fitted(self) -> bool:
        """モデルが学習済みかどうか。"""
        return self._is_fitted

    @property
    def feature_importance_(self) -> pd.Series:
        """学習済みモデルの特徴量重要度 (gain ベース)。"""
        if not self._is_fitted or self._feature_importance_ is None:
            raise RuntimeError("モデルが未学習です。先に fit() を実行してください。")
        return self._feature_importance_

    @property
    def oof_predictions_(self) -> Optional[pd.Series]:
        """cv を指定して学習した場合の Out-of-Fold メタ確率予測。"""
        return self._oof_predictions_

    @property
    def cv_auc_(self) -> Optional[float]:
        """cv を指定して学習した場合の Out-of-Fold AUC スコア。"""
        return self._cv_auc_

    # -- internal helpers -------------------------------------------------

    def _build_feature_matrix(self, X: pd.DataFrame) -> pd.DataFrame:
        """特徴量カラムの存在を検証し、学習/推論用の行列を抽出する。"""
        missing = [col for col in self.feature_columns if col not in X.columns]
        if missing:
            raise ValueError(f"入力データに必要な特徴量が不足しています: {missing}")
        return X.loc[:, list(self.feature_columns)]

    def _train_booster(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        sample_weight: Optional[pd.Series] = None,
    ) -> lgb.Booster:
        """内部用: 1本の LightGBM Booster を学習する。"""
        train_set = lgb.Dataset(
            X_train,
            label=y_train,
            weight=sample_weight.loc[X_train.index] if sample_weight is not None else None,
            free_raw_data=False,
        )

        valid_sets: List[lgb.Dataset] = [train_set]
        valid_names: List[str] = ["train"]
        callbacks: List[Any] = [lgb.log_evaluation(period=0)]

        if X_valid is not None and y_valid is not None and len(X_valid) > 0:
            valid_set = lgb.Dataset(X_valid, label=y_valid, reference=train_set, free_raw_data=False)
            valid_sets.append(valid_set)
            valid_names.append("valid")
            callbacks.append(lgb.early_stopping(self.config.early_stopping_rounds, verbose=False))

        booster = lgb.train(
            params=self.config.to_lgb_params(),
            train_set=train_set,
            num_boost_round=self.config.num_boost_round,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks,
        )
        return booster

    # -- public API ---------------------------------------------------------

    def fit(
        self,
        X: pd.DataFrame,
        y_meta: pd.Series,
        cv: Optional[BaseCrossValidator] = None,
        sample_weight: Optional[pd.Series] = None,
    ) -> "MetaLabelingEngine":
        """メタラベリングモデルを学習する。

        Parameters
        ----------
        X : pd.DataFrame
            ``feature_columns`` を含む特徴量データフレーム
            (pred_prob, dxy, us10y, tailwind_score など)。
        y_meta : pd.Series
            ``generate_meta_labels`` で生成したメタラベル (0/1)。
        cv : sklearn.model_selection.BaseCrossValidator, optional
            Purged K-Fold 等の交差検証splitterインスタンス。
            ``split(X, y_meta)`` を呼び出せるオブジェクトであれば
            (mlfinlab の PurgedKFold 等) 自作クラスでも利用可能。
            指定した場合、Out-of-Fold 予測 (``oof_predictions_``) と
            OOF AUC (``cv_auc_``) を計算したうえで、最終的に全データで
            本番用モデルを再学習する。
        sample_weight : pd.Series, optional
            サンプルごとの学習ウェイト (例: リターンの大きさやユニーク性重み)。

        Returns
        -------
        MetaLabelingEngine
            学習済みの自分自身 (メソッドチェーン用)。
        """
        if len(X) != len(y_meta):
            raise ValueError("X と y_meta の長さが一致しません。")

        X_features = self._build_feature_matrix(X)
        y_meta = y_meta.loc[X_features.index]

        if cv is not None:
            oof_pred = pd.Series(index=X_features.index, dtype=float, name="oof_meta_prob")
            for fold_idx, (train_idx, valid_idx) in enumerate(cv.split(X_features, y_meta)):
                X_train = X_features.iloc[train_idx]
                y_train = y_meta.iloc[train_idx]
                X_valid = X_features.iloc[valid_idx]
                y_valid = y_meta.iloc[valid_idx]

                fold_booster = self._train_booster(
                    X_train, y_train, X_valid, y_valid, sample_weight=sample_weight
                )
                fold_pred = fold_booster.predict(
                    X_valid, num_iteration=fold_booster.best_iteration
                )
                oof_pred.iloc[valid_idx] = fold_pred

                logger.info(
                    "fold=%d train_n=%d valid_n=%d best_iter=%s",
                    fold_idx,
                    len(train_idx),
                    len(valid_idx),
                    fold_booster.best_iteration,
                )

            valid_mask = oof_pred.notna()
            if valid_mask.sum() > 0 and y_meta.loc[valid_mask].nunique() > 1:
                self._cv_auc_ = float(
                    roc_auc_score(y_meta.loc[valid_mask], oof_pred.loc[valid_mask])
                )
                logger.info("Purged CV OOF AUC = %.4f", self._cv_auc_)
            else:
                self._cv_auc_ = None
                logger.warning("OOF AUC を計算できませんでした (クラス数不足)。")

            self._oof_predictions_ = oof_pred

        # 最終モデルは全データで学習 (本番推論用)
        self._model = self._train_booster(X_features, y_meta, sample_weight=sample_weight)
        self._feature_importance_ = pd.Series(
            self._model.feature_importance(importance_type="gain"),
            index=self.feature_columns,
            name="feature_importance_gain",
        ).sort_values(ascending=False)
        self._is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """メタ確率 (一次シグナルが的中する確信度) を推論する。

        Parameters
        ----------
        X : pd.DataFrame
            ``feature_columns`` を含む特徴量データフレーム。

        Returns
        -------
        np.ndarray
            0.0〜1.0 のメタ確率配列。
        """
        if not self._is_fitted or self._model is None:
            raise RuntimeError("モデルが未学習です。先に fit() または load_from_file() を実行してください。")
        X_features = self._build_feature_matrix(X)
        best_iter = getattr(self._model, "best_iteration", None)
        if best_iter and best_iter > 0:
            return self._model.predict(X_features, num_iteration=best_iter)
        return self._model.predict(X_features)

    def predict_meta_label(
        self, X: pd.DataFrame, threshold: Optional[float] = None
    ) -> np.ndarray:
        """メタ確率を閾値で二値化し、メタラベル (0/1) を予測する。

        Parameters
        ----------
        X : pd.DataFrame
            特徴量データフレーム。
        threshold : float, optional
            二値化閾値。未指定時はコンストラクタの ``threshold`` を使用する。

        Returns
        -------
        np.ndarray
            0/1 のメタラベル予測配列。
        """
        th = threshold if threshold is not None else self.threshold
        proba = self.predict_proba(X)
        return (proba >= th).astype(int)

    def save_model(self, filepath: str) -> None:
        """学習済みモデルをファイルに保存する。"""
        if not self._is_fitted or self._model is None:
            raise RuntimeError("保存するモデルがありません。fit() を先に実行してください。")
        self._model.save_model(filepath)
        logger.info("MetaLabelingEngine モデルを %s に保存しました。", filepath)

    @classmethod
    def load_from_file(
        cls,
        filepath: str,
        feature_columns: Optional[Sequence[str]] = None,
        threshold: float = 0.5
    ) -> MetaLabelingEngine:
        """ファイルから保存済み LightGBM Booster をロードしてインスタンスを生成する。"""
        engine = cls(feature_columns=feature_columns, threshold=threshold)
        engine._model = lgb.Booster(model_file=filepath)
        engine._is_fitted = True
        logger.info("MetaLabelingEngine モデルを %s からロードしました。", filepath)
        return engine


# ---------------------------------------------------------------------------
# 3. ハーフケリー・ベッティングサイズ算出
# ---------------------------------------------------------------------------

def compute_bet_size(
    meta_prob: Union[float, np.ndarray, pd.Series],
    risk_reward_ratio: Union[float, np.ndarray, pd.Series],
    kelly_fraction: float = 0.5,
    min_bet_size: float = 0.0,
    max_bet_size: float = 1.0,
) -> Union[float, np.ndarray, pd.Series]:
    """メタ確率とリスクリワード比からハーフケリー基準の賭け金比率を算出する。

    ケリー基準の全額 (full Kelly) は次式で与えられる:

        f* = p - (1 - p) / b

    ここで ``p`` はメタ確率 (的中確信度)、``b`` はリスクリワード比
    (1単位のリスクに対する期待リターン、例えば利益幅/損失幅)。

    Lopez de Prado の推奨に従い、推定誤差やパラメータ不確実性を考慮して
    実際にはフルケリーの一部 (デフォルトではハーフケリー:
    ``kelly_fraction=0.5``) のみを賭けることで過剰レバレッジを防ぐ。

    期待値がマイナス (f* < 0) となる場合は賭けを行わないため、
    最終的な比率は ``[min_bet_size, max_bet_size]`` にクリップされる。

    Parameters
    ----------
    meta_prob : float or array-like
        MetaLabelingEngine が出力したメタ確率 (0.0〜1.0)。
    risk_reward_ratio : float or array-like
        リスクリワード比 b (> 0)。例: テイクプロフィット幅 / ストップロス幅。
    kelly_fraction : float, default 0.5
        フルケリーに対する掛け目の割合。0.5 でハーフケリーとなる。
    min_bet_size : float, default 0.0
        賭け金比率の下限 (通常は 0、負の期待値の場合は賭けない)。
    max_bet_size : float, default 1.0
        賭け金比率の上限 (資金管理上のハードキャップ)。

    Returns
    -------
    float, np.ndarray, or pd.Series
        0.0〜1.0 に収まる最適賭け金比率。入力の型・インデックスを保持する。

    Raises
    ------
    ValueError
        risk_reward_ratio に 0 以下の値が含まれる場合、
        または meta_prob が [0, 1] の範囲外の値を含む場合。
    """
    is_series = isinstance(meta_prob, pd.Series)
    series_index = meta_prob.index if is_series else None
    is_scalar = np.isscalar(meta_prob)

    p = np.asarray(meta_prob, dtype=float)
    b = np.asarray(risk_reward_ratio, dtype=float)

    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("meta_prob は 0.0〜1.0 の範囲でなければなりません。")
    if np.any(b <= 0.0):
        raise ValueError("risk_reward_ratio は正の値でなければなりません。")
    if not (0.0 < kelly_fraction <= 1.0):
        raise ValueError("kelly_fraction は (0.0, 1.0] の範囲でなければなりません。")

    full_kelly = p - (1.0 - p) / b
    half_kelly = kelly_fraction * full_kelly
    bet_size = np.clip(half_kelly, min_bet_size, max_bet_size)

    if is_scalar:
        return float(bet_size)
    if is_series:
        return pd.Series(bet_size, index=series_index, name="bet_size")
    return bet_size