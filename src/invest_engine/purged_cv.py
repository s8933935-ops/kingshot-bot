"""
Purged K-Fold Cross-Validation with Embargo
=============================================

Marcos Lopez de Prado, "Advances in Financial Machine Learning" (2018)
Chapter 7: Cross-Validation in Finance

金融機械学習における情報漏洩（Lookahead Bias / Leakage）を防ぐための
scikit-learn 互換 CrossValidator 実装。

主な情報漏洩の原因:
1. 訓練サンプルとテストサンプルのラベル期間（t_entry 〜 t_exit）が
   時間的にオーバーラップしている場合、訓練データがテストデータの
   情報を「先読み」してしまう（Lookahead Bias）。
   -> Purging（パージ）でオーバーラップする訓練サンプルを除去する。

2. パージ後も、金融時系列データは自己相関（serial correlation）を
   持つため、テスト期間の直後に隣接する訓練サンプルが依然として
   情報漏洩の経路となり得る。
   -> Embargo（エンバーゴ）でテスト期間終了直後の一定区間の
      訓練サンプルも追加で除去する。

参考: de Prado (2018), Section 7.4 "Purging and Embargoing"
"""

from __future__ import annotations

from typing import Generator, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import BaseCrossValidator


class PurgedKFold(BaseCrossValidator):
    """
    Purged K-Fold Cross-Validator（Embargo 付き）。

    通常の K-Fold と異なり、各イベントが「開始時刻（t_entry）」から
    「終了時刻（t_exit）」までの区間（ラベルの評価期間）を持つ
    金融時系列データを対象とする。

    このクラスは以下の2段階でリーク（情報漏洩）を排除する:

    1. Purge（パージ）:
       テストセットの時間区間 [test_start, test_end] と、
       訓練サンプルのラベル区間 [t_entry_i, t_exit_i] が
       少しでもオーバーラップする場合、その訓練サンプル i を
       訓練セットから除外する。

    2. Embargo（エンバーゴ）:
       テストセット終了時刻 test_end の直後、一定の "embargo幅"
       （全サンプル数に対する割合 pct_embargo、またはバー数）の
       期間に開始時刻を持つ訓練サンプルも、自己相関によるリーク
       防止のためにさらに除外する。

    Parameters
    ----------
    n_splits : int, default=5
        分割数（Fold数）。

    t1 : pd.Series
        インデックスがイベントの開始時刻（t_entry）、値がイベントの
        終了時刻（t_exit: バリア接触時刻 or 垂直バリア時刻）である
        pandas Series。X の行と同じ順序・同じ長さでなければならない。
        （= de Prado の実装でいう `t1`）

    pct_embargo : float, default=0.0
        エンバーゴ幅を「全サンプル数に対する割合」で指定する
        （例: 0.01 = 1%, 0.02 = 2%）。0 の場合はエンバーゴなし。
        embargo_bars が指定された場合はそちらが優先される。

    embargo_bars : Optional[int], default=None
        エンバーゴ幅を「バー数（サンプル数）」で直接指定する場合に使用。
        指定された場合、pct_embargo よりも優先される。

    Attributes
    ----------
    n_samples_ : int
        fit 時に決定されるサンプル数。

    Notes
    -----
    - X, y は split() 呼び出し時に渡され、そのインデックス順序が
      t1 のインデックス順序と一致している必要がある（時系列順を想定）。
    - t1 の値（t_exit）が NaT のサンプルは「まだバリアに到達していない
      / 評価期間が確定していない」ものとして扱われ、パージ判定は
      max(t_exit, t_entry) の考え方で保守的に処理される
      （NaT は "無限大" とみなし、常に将来と重なるとみなす）。
    """

    def __init__(
        self,
        n_splits: int = 5,
        t1: Optional[pd.Series] = None,
        pct_embargo: float = 0.0,
        embargo_bars: Optional[int] = None,
    ) -> None:
        if t1 is None:
            raise ValueError(
                "t1 (イベント終了時刻を表す pandas.Series) を指定してください。"
            )
        if not isinstance(t1, pd.Series):
            raise TypeError("t1 は pandas.Series 型である必要があります。")
        if n_splits < 2:
            raise ValueError("n_splits は 2 以上である必要があります。")
        if not (0.0 <= pct_embargo < 1.0):
            raise ValueError("pct_embargo は [0.0, 1.0) の範囲で指定してください。")

        self.n_splits: int = n_splits
        self.t1: pd.Series = t1
        self.pct_embargo: float = pct_embargo
        self.embargo_bars: Optional[int] = embargo_bars

    def get_n_splits(
        self,
        X: Optional[pd.DataFrame] = None,
        y: Optional[pd.Series] = None,
        groups: Optional[Iterable] = None,
    ) -> int:
        """Fold 数を返す（scikit-learn 互換インターフェース）。"""
        return self.n_splits

    def _get_embargo_width(self, n_samples: int) -> int:
        """エンバーゴ幅をサンプル数（バー数）として算出する。"""
        if self.embargo_bars is not None:
            return max(0, int(self.embargo_bars))
        return int(n_samples * self.pct_embargo)

    def split(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        groups: Optional[Iterable] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        train_indices, test_indices を yield するジェネレータ。

        Parameters
        ----------
        X : pd.DataFrame
            特徴量。インデックスが t1 のインデックス（= イベント開始
            時刻 t_entry）と一致している必要がある。
        y : Optional[pd.Series]
            ラベル（本メソッドでは未使用だが sklearn 互換のため受け取る）。
        groups : Optional[Iterable]
            未使用（sklearn 互換のため受け取る）。

        Yields
        ------
        Tuple[np.ndarray, np.ndarray]
            (train_indices, test_indices) の整数位置インデックス配列。
        """
        if not X.index.equals(self.t1.index):
            raise ValueError(
                "X のインデックスと t1 のインデックスが一致していません。"
                "イベントの開始時刻（t_entry）順に揃えてください。"
            )

        n_samples: int = X.shape[0]
        indices: np.ndarray = np.arange(n_samples)
        embargo_width: int = self._get_embargo_width(n_samples)

        # 各サンプルの t_entry（開始時刻）と t_exit（終了時刻）を
        # 整数位置ベースで扱うための配列を準備する。
        # t_exit が NaT（未確定）の場合は「無限大」に相当する値として
        # 扱い、常に将来のテストセットとオーバーラップするとみなす
        # （保守的にパージする = 安全側に倒す）。
        t_entry: pd.Series = self.t1.index.to_series()
        t_exit: pd.Series = self.t1.copy()
        t_exit_filled: pd.Series = t_exit.fillna(pd.Timestamp.max)

        # 通常の K-Fold と同様に、時系列順のまま test set を
        # n_splits 個の連続したブロックに分割する
        # （時系列データでは shuffle しないのが原則）。
        test_blocks = np.array_split(indices, self.n_splits)

        for test_indices in test_blocks:
            if len(test_indices) == 0:
                continue

            # --- テストセットの時間区間を決定する ---
            test_start_time = t_entry.iloc[test_indices[0]]
            test_end_time = t_exit_filled.iloc[test_indices].max()

            # --- 1. Purge: テスト区間とオーバーラップする訓練サンプルを除去 ---
            train_mask = self._purge(
                t_entry=t_entry,
                t_exit_filled=t_exit_filled,
                test_start_time=test_start_time,
                test_end_time=test_end_time,
            )

            # テストセット自体は訓練データから除外
            train_mask[test_indices] = False

            # --- 2. Embargo: テスト終了直後の一定区間も追加除外 ---
            if embargo_width > 0:
                train_mask = self._embargo(
                    train_mask=train_mask,
                    test_indices=test_indices,
                    n_samples=n_samples,
                    embargo_width=embargo_width,
                )

            train_indices: np.ndarray = indices[train_mask]

            if len(train_indices) == 0:
                raise ValueError(
                    "Purge/Embargo の結果、訓練セットが空になりました。"
                    "n_splits や pct_embargo/embargo_bars の値を見直してください。"
                )

            yield train_indices, test_indices

    @staticmethod
    def _purge(
        t_entry: pd.Series,
        t_exit_filled: pd.Series,
        test_start_time: pd.Timestamp,
        test_end_time: pd.Timestamp,
    ) -> np.ndarray:
        """
        訓練候補サンプルのうち、テスト区間 [test_start_time, test_end_time]
        とラベル区間 [t_entry_i, t_exit_i] がオーバーラップするものを
        False（除外）とするブールマスクを返す。

        オーバーラップ条件（区間交差判定）:
            NOT (t_exit_i < test_start_time OR t_entry_i > test_end_time)
        すなわち、以下のいずれかに該当する場合はオーバーラップとみなし
        パージ対象とする:
            (a) 訓練サンプルの開始がテスト区間内にある
                test_start <= t_entry_i <= test_end
            (b) 訓練サンプルの終了がテスト区間内にある
                test_start <= t_exit_i <= test_end
            (c) 訓練サンプルがテスト区間を完全に包含する
                t_entry_i <= test_start AND t_exit_i >= test_end
        """
        overlap_start = (t_entry >= test_start_time) & (t_entry <= test_end_time)
        overlap_end = (t_exit_filled >= test_start_time) & (
            t_exit_filled <= test_end_time
        )
        overlap_envelope = (t_entry <= test_start_time) & (
            t_exit_filled >= test_end_time
        )

        is_overlapping = overlap_start | overlap_end | overlap_envelope
        train_mask = ~is_overlapping.to_numpy()
        return train_mask

    @staticmethod
    def _embargo(
        train_mask: np.ndarray,
        test_indices: np.ndarray,
        n_samples: int,
        embargo_width: int,
    ) -> np.ndarray:
        """
        テストセット終了位置（整数インデックス上）の直後
        embargo_width 個分の訓練サンプルを追加でパージする。

        時系列データは自己相関を持つため、テスト期間の直後に
        隣接するサンプルは（ラベル区間としては非重複でも）
        情報が漏洩している可能性がある。これを防ぐための処理。
        """
        test_end_idx = int(test_indices.max())
        embargo_end_idx = min(test_end_idx + embargo_width + 1, n_samples)

        if embargo_end_idx > test_end_idx + 1:
            train_mask[test_end_idx + 1 : embargo_end_idx] = False

        return train_mask


def purged_cross_val_score(
    estimator,
    X: pd.DataFrame,
    y: pd.Series,
    cv: PurgedKFold,
    scoring=None,
    sample_weight: Optional[pd.Series] = None,
) -> np.ndarray:
    """
    PurgedKFold を用いてクロスバリデーションのスコアを計算するユーティリティ関数。

    scikit-learn の cross_val_score は内部で StratifiedKFold 等の
    デフォルト CV を強制的に使おうとするケースがあるため、
    PurgedKFold を確実に使うための簡易ラッパーを用意する。

    Parameters
    ----------
    estimator : sklearn 互換の推定器（fit/predict または predict_proba を持つ）。
    X : pd.DataFrame
        特徴量。
    y : pd.Series
        ラベル。
    cv : PurgedKFold
        本モジュールの PurgedKFold インスタンス。
    scoring : Callable[[estimator, X, y], float], optional
        スコア関数。None の場合は estimator.score を使用する。
    sample_weight : Optional[pd.Series]
        サンプルウェイト（de Prado 推奨: リターンの絶対値や
        ユニークネスに基づく重み付け）。

    Returns
    -------
    np.ndarray
        各 Fold のスコアを格納した配列。
    """
    scores = []

    for train_idx, test_idx in cv.split(X=X, y=y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        fit_kwargs = {}
        if sample_weight is not None:
            fit_kwargs["sample_weight"] = sample_weight.iloc[train_idx].to_numpy()

        estimator.fit(X_train, y_train, **fit_kwargs)

        if scoring is not None:
            score = scoring(estimator, X_test, y_test)
        else:
            score = estimator.score(X_test, y_test)

        scores.append(score)

    return np.array(scores)


if __name__ == "__main__":
    # --- 使用例（動作確認用のダミーデータ） ---
    rng = np.random.default_rng(seed=42)

    n_obs = 1000
    dates = pd.date_range("2020-01-01", periods=n_obs, freq="1h")

    # 各イベントは開始時刻から 1〜24時間後にバリアに到達すると仮定
    holding_hours = rng.integers(low=1, high=24, size=n_obs)
    t_exit_values = dates + pd.to_timedelta(holding_hours, unit="h")

    t1 = pd.Series(data=t_exit_values, index=dates, name="t1")

    X_dummy = pd.DataFrame(
        data=rng.normal(size=(n_obs, 5)),
        index=dates,
        columns=[f"feature_{i}" for i in range(5)],
    )
    y_dummy = pd.Series(
        data=rng.integers(low=0, high=2, size=n_obs), index=dates, name="label"
    )

    pkf = PurgedKFold(n_splits=5, t1=t1, pct_embargo=0.01)

    for fold_i, (train_idx, test_idx) in enumerate(pkf.split(X_dummy, y_dummy)):
        print(
            f"[Fold {fold_i}] "
            f"train_size={len(train_idx)}, test_size={len(test_idx)}, "
            f"purged/embargoed={n_obs - len(train_idx) - len(test_idx)}"
        )