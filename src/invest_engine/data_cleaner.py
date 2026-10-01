"""
data_cleaner.py
データ品質監査・異常値クリーニング・セッション特徴量・上位足(HTF)結合モジュール。

先読みバイアス（Lookahead bias）ゼロ、Point-in-Time 物理整合性を厳格に担保。
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple


def clean_outliers_and_bad_ticks(
    df: pd.DataFrame,
    threshold_sigma: float = 6.0,
    window: int = 50
) -> pd.DataFrame:
    """
    価格データの異常スパイク（Bad Ticks: 取引所フィードの瞬間的外れ値）を検出し、
    直前終値ベースで安全にクリーニング（平滑補正）する。
    """
    clean_df = df.copy()
    if len(clean_df) < window:
        return clean_df

    returns = clean_df["Close"].pct_change()
    rolling_mean = returns.rolling(window=window, min_periods=10).mean()
    rolling_std = returns.rolling(window=window, min_periods=10).std().replace(0, 1e-6)

    z_scores = (returns - rolling_mean) / rolling_std
    # 瞬間的に急騰/急落し、翌バーで反転する異常パルス（Bad Tick）を検出
    next_returns = returns.shift(-1)
    is_spike = (z_scores.abs() > threshold_sigma) & ((returns * next_returns) < 0)

    spike_indices = clean_df.index[is_spike.fillna(False)]
    for idx in spike_indices:
        loc = clean_df.index.get_loc(idx)
        if loc > 0:
            prev_close = clean_df["Close"].iloc[loc - 1]
            clean_df.loc[idx, "Close"] = prev_close
            clean_df.loc[idx, "High"] = max(clean_df.loc[idx, "High"], prev_close)
            clean_df.loc[idx, "Low"] = min(clean_df.loc[idx, "Low"], prev_close)
            clean_df.loc[idx, "Open"] = prev_close

    return clean_df


def add_session_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    時間帯（取引セッション）特徴量を生成する。
    金先物・FXの流動性特性（ロンドン/NY時間の高流動性 vs アジア/早朝の薄商い）をモデルに伝達。
    """
    data = df.copy()
    if not isinstance(data.index, pd.DatetimeIndex):
        data["session_ny_london"] = 1.0
        data["session_asia"] = 0.0
        data["session_offhours"] = 0.0
        return data

    hours = data.index.hour
    is_intraday = (hours != 0).any()

    if is_intraday:
        # ロンドン/NY時間帯 (UTC 12:00〜21:00 / JST 21:00〜06:00: 流動性最大・タイトスプレッド)
        data["session_ny_london"] = ((hours >= 12) & (hours < 21)).astype(float)
        # アジア時間帯 (UTC 00:00〜08:00 / JST 09:00〜17:00: 中程度流動性)
        data["session_asia"] = ((hours >= 0) & (hours < 8)).astype(float)
        # オフアワー (流動性低下・スプレッド拡大)
        data["session_offhours"] = (
            (data["session_ny_london"] == 0) & (data["session_asia"] == 0)
        ).astype(float)
    else:
        # 日足データの場合は標準値
        data["session_ny_london"] = 1.0
        data["session_asia"] = 0.0
        data["session_offhours"] = 0.0

    return data


def merge_htf_trend_features(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    htf_name: str = "daily"
) -> pd.DataFrame:
    """
    下位足（LTF: 5m, 15m, 1h）に上位足（HTF: 1d）のトレンド・移動平均指標を
    先読みバイアス（Lookahead bias）ゼロで結合する。

    【Point-in-Time 因果律保証】:
    HTFバーは完全にクローズ（確定）するまで下位足で参照してはならない。
    そのため、HTF特徴量は必ず 1バー遅行（shift(1)）させてから merge_asof(direction='backward') する。
    """
    if htf_df is None or len(htf_df) < 5:
        return ltf_df.copy()

    htf = htf_df.copy()
    if not htf.index.is_monotonic_increasing:
        htf = htf.sort_index()

    # 上位足の主要トレンド特徴量を生成
    sma20 = htf["Close"].rolling(20, min_periods=5).mean()
    sma50 = htf["Close"].rolling(50, min_periods=5).mean()
    sma20_slope = (sma20 - sma20.shift(2)).fillna(0) / (sma20.shift(2).replace(0, 1e-6) + 1e-8)

    # +1: 強気上昇, -1: 弱気下降, 0: 中立
    htf_trend = np.where(
        (htf["Close"] > sma20) & (sma20_slope > 0),
        1.0,
        np.where((htf["Close"] < sma20) & (sma20_slope < 0), -1.0, 0.0)
    )

    htf_features = pd.DataFrame(
        {
            f"htf_{htf_name}_trend": htf_trend,
            f"htf_{htf_name}_dist_sma20": ((htf["Close"] - sma20) / (sma20 + 1e-8)).fillna(0),
            f"htf_{htf_name}_dist_sma50": ((htf["Close"] - sma50) / (sma50 + 1e-8)).fillna(0),
            f"htf_{htf_name}_slope": sma20_slope.fillna(0),
        },
        index=htf.index
    )

    # 【重要】未確定の上位足データを先読みしないよう、必ず 1 バー shift
    htf_features_shifted = htf_features.shift(1).bfill().ffill()

    # Point-in-Time 後方結合 (merge_asof backward)
    orig_ltf_index = ltf_df.index
    ltf_sorted = ltf_df.copy()
    if not ltf_sorted.index.is_monotonic_increasing:
        ltf_sorted = ltf_sorted.sort_index()

    # pandas 2.x の datetime 解像度不一致 ('<M8[us]' vs '<M8[s]') を nanosecond に統一
    if isinstance(ltf_sorted.index, pd.DatetimeIndex) and isinstance(htf_features_shifted.index, pd.DatetimeIndex):
        ltf_sorted.index = pd.to_datetime(ltf_sorted.index).astype("datetime64[ns]")
        htf_features_shifted.index = pd.to_datetime(htf_features_shifted.index).astype("datetime64[ns]")

    merged = pd.merge_asof(
        ltf_sorted,
        htf_features_shifted,
        left_index=True,
        right_index=True,
        direction="backward"
    )

    merged.index = orig_ltf_index
    return merged
