"""
src/invest_engine/regime_detector.py

金融時系列の相場レジーム判別モジュール。

主な機能
--------
1. ADX (Average Directional Index) によるトレンド強度判定
   - ADX >= adx_threshold(既定22, 要件では25も選択可)         : トレンド
   - ADX < 20                                                  : レンジ/チョッピー
2. EMA20 / EMA50 の傾き・乖離によるトレンド方向判定（上昇/下降）
3. ボリンジャーバンド帯域幅（Bandwidth）によるスクイーズ/エクスパンション判定
4. 上記を統合し、各バーに以下を付与する:
   - regime      : 1 (TREND_BULL) / -1 (TREND_BEAR) / 0 (RANGE_CHOPPY)
   - allow_entry : bool（スクイーズ中やレンジ相場ではエントリーを抑制）

設計方針
--------
- 計算過程は「指標算出クラス群（オブジェクト指向）」として分離し、
  各指標が独立してテスト可能な形にする。
- 最終的な統合ロジックは純粋関数 `detect_market_regime` として提供し、
  DataFrame -> DataFrame の副作用のない変換にする（関数型的アプローチ）。
- 外部依存は pandas / numpy のみ。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# 定数・列挙型
# --------------------------------------------------------------------------

class MarketRegime(IntEnum):
    """相場レジーム分類。"""

    TREND_BEAR = -1
    RANGE_CHOPPY = 0
    TREND_BULL = 1


REQUIRED_COLUMNS: Final[tuple[str, ...]] = ("high", "low", "close")

# デフォルトパラメータ
DEFAULT_ADX_PERIOD: Final[int] = 14
DEFAULT_ADX_RANGE_THRESHOLD: Final[float] = 20.0  # これ未満はチョッピー
DEFAULT_EMA_FAST_PERIOD: Final[int] = 20
DEFAULT_EMA_SLOW_PERIOD: Final[int] = 50
DEFAULT_EMA_SLOPE_LOOKBACK: Final[int] = 5
DEFAULT_BB_PERIOD: Final[int] = 20
DEFAULT_BB_STD: Final[float] = 2.0
DEFAULT_BANDWIDTH_SQUEEZE_PERCENTILE: Final[float] = 0.20  # 下位20%をスクイーズと判定


def _get_col(df: pd.DataFrame, col_name: str) -> pd.Series:
    """大文字・小文字を吸収して対応するカラムSeriesを返す。"""
    if col_name in df.columns:
        return df[col_name]
    title_name = col_name.capitalize()
    if title_name in df.columns:
        return df[title_name]
    upper_name = col_name.upper()
    if upper_name in df.columns:
        return df[upper_name]
    raise KeyError(f"列 '{col_name}' (または '{title_name}') がDataFrameに見つかりません。")


def _validate_ohlc(df: pd.DataFrame) -> None:
    """OHLC データとして最低限必要な列が揃っているか検証する（大文字小文字両対応）。"""
    for c in REQUIRED_COLUMNS:
        _get_col(df, c)
    if len(df) == 0:
        raise ValueError("空の DataFrame が渡されました。")


def _wilder_smoothing(series: pd.Series, period: int) -> pd.Series:
    """Wilder のスムージング（EMA の一種、alpha = 1/period）を適用する。"""
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


# --------------------------------------------------------------------------
# 1. ADX 計算（トレンド強度）
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ADXResult:
    """ADX 計算結果を保持するデータクラス。"""

    plus_di: pd.Series
    minus_di: pd.Series
    adx: pd.Series


class ADXCalculator:
    """Average Directional Index (ADX) を計算するクラス。

    Wilder の原著に基づく実装（True Range / +DM / -DM を
    Wilder のスムージングで平滑化する方式）。
    """

    def __init__(self, period: int = DEFAULT_ADX_PERIOD) -> None:
        if period <= 1:
            raise ValueError("ADX の period は 2 以上である必要があります。")
        self.period = period

    def compute(self, df: pd.DataFrame) -> ADXResult:
        high = _get_col(df, "high")
        low = _get_col(df, "low")
        close = _get_col(df, "close")

        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)

        # True Range
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        # Directional Movement
        up_move = high - prev_high
        down_move = prev_low - low

        plus_dm = pd.Series(
            np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
            index=df.index,
        )
        minus_dm = pd.Series(
            np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
            index=df.index,
        )

        atr = _wilder_smoothing(tr, self.period)
        smoothed_plus_dm = _wilder_smoothing(plus_dm, self.period)
        smoothed_minus_dm = _wilder_smoothing(minus_dm, self.period)

        # ゼロ割り回避
        safe_atr = atr.replace(0.0, np.nan)

        plus_di = 100.0 * (smoothed_plus_dm / safe_atr)
        minus_di = 100.0 * (smoothed_minus_dm / safe_atr)

        di_sum = (plus_di + minus_di).replace(0.0, np.nan)
        dx = 100.0 * (plus_di - minus_di).abs() / di_sum
        adx = _wilder_smoothing(dx, self.period)

        return ADXResult(
            plus_di=plus_di.rename("plus_di"),
            minus_di=minus_di.rename("minus_di"),
            adx=adx.rename("adx"),
        )


# --------------------------------------------------------------------------
# 2. EMA 傾き・乖離によるトレンド方向判定
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EMATrendResult:
    """EMA トレンド方向判定の結果を保持するデータクラス。"""

    ema_fast: pd.Series
    ema_slow: pd.Series
    ema_fast_slope: pd.Series
    ema_spread_pct: pd.Series
    direction: pd.Series  # 1: 上昇, -1: 下降, 0: 中立


class EMATrendAnalyzer:
    """短期/長期 EMA の傾きと乖離率からトレンド方向を判定するクラス。

    判定ロジック:
    - 短期EMA (fast) が長期EMA (slow) を上回り、かつ短期EMAの傾きが正
      -> 上昇トレンド (1)
    - 短期EMAが長期EMAを下回り、かつ短期EMAの傾きが負
      -> 下降トレンド (-1)
    - それ以外（EMAクロス直後やフラットな局面）-> 中立 (0)
    """

    def __init__(
        self,
        fast_period: int = DEFAULT_EMA_FAST_PERIOD,
        slow_period: int = DEFAULT_EMA_SLOW_PERIOD,
        slope_lookback: int = DEFAULT_EMA_SLOPE_LOOKBACK,
    ) -> None:
        if fast_period >= slow_period:
            raise ValueError("fast_period は slow_period より小さい必要があります。")
        if slope_lookback < 1:
            raise ValueError("slope_lookback は 1 以上である必要があります。")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.slope_lookback = slope_lookback

    def compute(self, df: pd.DataFrame) -> EMATrendResult:
        close = _get_col(df, "close")

        ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()

        # 傾き: lookback 期間での変化率（%）
        ema_fast_slope = ema_fast.pct_change(periods=self.slope_lookback) * 100.0

        # 乖離率（%）: 短期EMAが長期EMAに対してどれだけ離れているか
        ema_spread_pct = (ema_fast - ema_slow) / ema_slow.replace(0.0, np.nan) * 100.0

        bullish = (ema_fast > ema_slow) & (ema_fast_slope > 0)
        bearish = (ema_fast < ema_slow) & (ema_fast_slope < 0)

        direction = pd.Series(0, index=df.index, dtype=int)
        direction[bullish] = 1
        direction[bearish] = -1

        return EMATrendResult(
            ema_fast=ema_fast.rename("ema_fast"),
            ema_slow=ema_slow.rename("ema_slow"),
            ema_fast_slope=ema_fast_slope.rename("ema_fast_slope"),
            ema_spread_pct=ema_spread_pct.rename("ema_spread_pct"),
            direction=direction.rename("ema_direction"),
        )


# --------------------------------------------------------------------------
# 3. ボリンジャーバンド帯域幅によるスクイーズ/エクスパンション判定
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class BollingerBandwidthResult:
    """ボリンジャーバンド帯域幅の計算結果を保持するデータクラス。"""

    middle_band: pd.Series
    upper_band: pd.Series
    lower_band: pd.Series
    bandwidth_pct: pd.Series  # (upper - lower) / middle * 100
    is_squeeze: pd.Series  # 過去N本比で下位パーセンタイルに入っているか


class BollingerBandwidthAnalyzer:
    """ボリンジャーバンドの帯域幅からスクイーズ/エクスパンションを判定するクラス。

    帯域幅（Bandwidth）は (Upper - Lower) / Middle * 100 (%) で定義し、
    過去 `lookback` 本のローリングウィンドウ内でのパーセンタイル順位が
    `squeeze_percentile` 以下であればスクイーズ（ボラティリティ収縮）と判定する。
    """

    def __init__(
        self,
        period: int = DEFAULT_BB_PERIOD,
        num_std: float = DEFAULT_BB_STD,
        lookback: int = 120,
        squeeze_percentile: float = DEFAULT_BANDWIDTH_SQUEEZE_PERCENTILE,
    ) -> None:
        if period <= 1:
            raise ValueError("period は 2 以上である必要があります。")
        if num_std <= 0:
            raise ValueError("num_std は正の値である必要があります。")
        if not (0.0 < squeeze_percentile < 1.0):
            raise ValueError("squeeze_percentile は 0〜1 の範囲で指定してください。")
        self.period = period
        self.num_std = num_std
        self.lookback = max(lookback, period)
        self.squeeze_percentile = squeeze_percentile

    def compute(self, df: pd.DataFrame) -> BollingerBandwidthResult:
        close = _get_col(df, "close")

        middle = close.rolling(window=self.period, min_periods=self.period).mean()
        std = close.rolling(window=self.period, min_periods=self.period).std(ddof=0)

        upper = middle + self.num_std * std
        lower = middle - self.num_std * std

        bandwidth_pct = (upper - lower) / middle.replace(0.0, np.nan) * 100.0

        # 直近 lookback 本の中で、現在のバンド幅が下位何パーセンタイルかを算出
        rank_pct = bandwidth_pct.rolling(
            window=self.lookback, min_periods=self.period
        ).apply(self._percentile_rank_of_last, raw=True)

        is_squeeze = rank_pct <= self.squeeze_percentile

        return BollingerBandwidthResult(
            middle_band=middle.rename("bb_middle"),
            upper_band=upper.rename("bb_upper"),
            lower_band=lower.rename("bb_lower"),
            bandwidth_pct=bandwidth_pct.rename("bb_bandwidth_pct"),
            is_squeeze=is_squeeze.fillna(False).rename("bb_is_squeeze"),
        )

    @staticmethod
    def _percentile_rank_of_last(window: np.ndarray) -> float:
        """ウィンドウ内での最終値のパーセンタイル順位 (0.0〜1.0) を返す。"""
        last_value = window[-1]
        if np.isnan(last_value):
            return np.nan
        valid = window[~np.isnan(window)]
        if valid.size == 0:
            return np.nan
        return float(np.mean(valid <= last_value))


# --------------------------------------------------------------------------
# 4. 統合レジーム判定
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeDetectorConfig:
    """detect_market_regime の挙動を制御する設定値をまとめたデータクラス。"""

    adx_threshold: float = 22.0
    adx_range_threshold: float = DEFAULT_ADX_RANGE_THRESHOLD
    adx_period: int = DEFAULT_ADX_PERIOD
    ema_fast_period: int = DEFAULT_EMA_FAST_PERIOD
    ema_slow_period: int = DEFAULT_EMA_SLOW_PERIOD
    ema_slope_lookback: int = DEFAULT_EMA_SLOPE_LOOKBACK
    bb_period: int = DEFAULT_BB_PERIOD
    bb_std: float = DEFAULT_BB_STD
    bb_lookback: int = 120
    bb_squeeze_percentile: float = DEFAULT_BANDWIDTH_SQUEEZE_PERCENTILE

    def __post_init__(self) -> None:
        if self.adx_range_threshold >= self.adx_threshold:
            raise ValueError(
                "adx_range_threshold は adx_threshold より小さい必要があります "
                f"(range={self.adx_range_threshold}, trend={self.adx_threshold})."
            )


class MarketRegimeDetector:
    """ADX / EMA / ボリンジャーバンド帯域幅を統合し、相場レジームを判定するクラス。

    判定ロジックの概要
    -------------------
    1. ADX が adx_threshold 以上 -> トレンド相場候補
       ADX が adx_range_threshold 未満 -> 明確なレンジ/チョッピー
       その中間はやや弱いトレンド継続（前段の方向判定を尊重）として扱う
    2. トレンド候補の中で EMA 方向が上昇/下降を示していれば
       TREND_BULL / TREND_BEAR を確定。方向が中立なら RANGE_CHOPPY。
    3. entry 許可は「明確なトレンド」かつ「バンドがスクイーズ中でない」
       （＝ボラティリティが十分にある）場合のみ True とする。
       スクイーズ中は「これからブレイクする可能性がある」段階であり、
       方向未確定のエントリーはリスクが高いため抑制する。
    """

    def __init__(self, config: RegimeDetectorConfig | None = None) -> None:
        self.config = config or RegimeDetectorConfig()

        self._adx_calculator = ADXCalculator(period=self.config.adx_period)
        self._ema_analyzer = EMATrendAnalyzer(
            fast_period=self.config.ema_fast_period,
            slow_period=self.config.ema_slow_period,
            slope_lookback=self.config.ema_slope_lookback,
        )
        self._bb_analyzer = BollingerBandwidthAnalyzer(
            period=self.config.bb_period,
            num_std=self.config.bb_std,
            lookback=self.config.bb_lookback,
            squeeze_percentile=self.config.bb_squeeze_percentile,
        )

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        _validate_ohlc(df)

        result = df.copy()

        adx_result = self._adx_calculator.compute(df)
        ema_result = self._ema_analyzer.compute(df)
        bb_result = self._bb_analyzer.compute(df)

        # 指標列をまとめて付与
        result["adx"] = adx_result.adx
        result["plus_di"] = adx_result.plus_di
        result["minus_di"] = adx_result.minus_di

        result["ema_fast"] = ema_result.ema_fast
        result["ema_slow"] = ema_result.ema_slow
        result["ema_fast_slope"] = ema_result.ema_fast_slope
        result["ema_spread_pct"] = ema_result.ema_spread_pct
        result["ema_direction"] = ema_result.direction

        result["bb_middle"] = bb_result.middle_band
        result["bb_upper"] = bb_result.upper_band
        result["bb_lower"] = bb_result.lower_band
        result["bb_bandwidth_pct"] = bb_result.bandwidth_pct
        result["bb_is_squeeze"] = bb_result.is_squeeze

        regime = self._classify_regime(
            adx=result["adx"],
            ema_direction=result["ema_direction"],
        )
        result["regime"] = regime.astype(int)
        result["regime_label"] = result["regime"].map(
            {
                MarketRegime.TREND_BULL: "TREND_BULL",
                MarketRegime.TREND_BEAR: "TREND_BEAR",
                MarketRegime.RANGE_CHOPPY: "RANGE_CHOPPY",
            }
        )

        result["allow_entry"] = self._determine_entry_permission(
            regime=result["regime"],
            is_squeeze=result["bb_is_squeeze"],
            adx=result["adx"],
        )

        return result

    def _classify_regime(
        self, adx: pd.Series, ema_direction: pd.Series
    ) -> pd.Series:
        cfg = self.config

        is_trending = adx >= cfg.adx_threshold
        is_choppy = adx < cfg.adx_range_threshold

        regime = pd.Series(
            MarketRegime.RANGE_CHOPPY.value, index=adx.index, dtype=int
        )

        # 明確なトレンド強度があり、かつ方向が一致する場合のみトレンド確定
        bull_mask = is_trending & (ema_direction == 1)
        bear_mask = is_trending & (ema_direction == -1)

        regime[bull_mask] = MarketRegime.TREND_BULL.value
        regime[bear_mask] = MarketRegime.TREND_BEAR.value

        # ADX が明確にチョッピー域なら、方向判定に関わらずレンジとして扱う
        regime[is_choppy] = MarketRegime.RANGE_CHOPPY.value

        # ADX が算出不能（NaN）な区間はレンジ扱い（保守的なデフォルト）
        regime[adx.isna()] = MarketRegime.RANGE_CHOPPY.value

        return regime

    @staticmethod
    def _determine_entry_permission(
        regime: pd.Series, is_squeeze: pd.Series, adx: pd.Series
    ) -> pd.Series:
        is_trend_regime = regime != MarketRegime.RANGE_CHOPPY.value
        has_valid_adx = adx.notna()

        allow_entry = is_trend_regime & has_valid_adx & (~is_squeeze.fillna(False))
        return allow_entry.astype(bool)


# --------------------------------------------------------------------------
# 公開 API（関数型インターフェース）
# --------------------------------------------------------------------------

def detect_market_regime(
    df: pd.DataFrame,
    adx_threshold: float = 22.0,
    *,
    adx_range_threshold: float = DEFAULT_ADX_RANGE_THRESHOLD,
    adx_period: int = DEFAULT_ADX_PERIOD,
    ema_fast_period: int = DEFAULT_EMA_FAST_PERIOD,
    ema_slow_period: int = DEFAULT_EMA_SLOW_PERIOD,
    ema_slope_lookback: int = DEFAULT_EMA_SLOPE_LOOKBACK,
    bb_period: int = DEFAULT_BB_PERIOD,
    bb_std: float = DEFAULT_BB_STD,
    bb_lookback: int = 120,
    bb_squeeze_percentile: float = DEFAULT_BANDWIDTH_SQUEEZE_PERCENTILE,
) -> pd.DataFrame:
    """OHLC(V) データフレームから相場レジームを判定し、列を付与した DataFrame を返す。

    元の DataFrame は変更されず（副作用なし）、新しい DataFrame が返される。

    Parameters
    ----------
    df : pd.DataFrame
        少なくとも "high", "low", "close" 列を含む時系列データ。
        インデックスは日時であることを推奨（必須ではない）。
    adx_threshold : float, default 22.0
        この値以上の ADX をトレンドとみなす閾値。
        要件上の「ADX >= 25 はトレンド」を使いたい場合は 25.0 を指定する。
    adx_range_threshold : float, default 20.0
        この値未満の ADX を明確なレンジ/チョッピーとみなす閾値。
        adx_threshold より小さい値である必要がある。
    adx_period : int, default 14
        ADX 計算に用いる期間（Wilder のスムージング期間）。
    ema_fast_period, ema_slow_period : int, default 20, 50
        トレンド方向判定に用いる短期/長期 EMA の期間。
    ema_slope_lookback : int, default 5
        短期EMAの傾き（変化率）を計算する際の参照本数。
    bb_period : int, default 20
        ボリンジャーバンド計算に用いる期間。
    bb_std : float, default 2.0
        ボリンジャーバンドの標準偏差の乗数。
    bb_lookback : int, default 120
        バンド幅のパーセンタイル順位を計算する際のローリングウィンドウ幅。
    bb_squeeze_percentile : float, default 0.20
        バンド幅がこのパーセンタイル以下であればスクイーズと判定する。

    Returns
    -------
    pd.DataFrame
        元の列に加え、以下の列が付与された DataFrame:

        - adx, plus_di, minus_di            : ADX 関連指標
        - ema_fast, ema_slow                : EMA20 / EMA50
        - ema_fast_slope, ema_spread_pct     : 傾き(%) / 乖離率(%)
        - ema_direction                      : 1(上昇) / -1(下降) / 0(中立)
        - bb_middle, bb_upper, bb_lower      : ボリンジャーバンド
        - bb_bandwidth_pct                   : 帯域幅(%)
        - bb_is_squeeze                      : スクイーズ中かどうか (bool)
        - regime                             : 1(TREND_BULL) / -1(TREND_BEAR) / 0(RANGE_CHOPPY)
        - regime_label                       : 上記の文字列ラベル
        - allow_entry                        : エントリー許可フラグ (bool)

    Raises
    ------
    ValueError
        必須列が欠けている場合、または閾値の大小関係が不正な場合。

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     "high": [...],
    ...     "low": [...],
    ...     "close": [...],
    ... })
    >>> result = detect_market_regime(df, adx_threshold=25.0)
    >>> result[["regime_label", "allow_entry"]].tail()
    """
    config = RegimeDetectorConfig(
        adx_threshold=adx_threshold,
        adx_range_threshold=adx_range_threshold,
        adx_period=adx_period,
        ema_fast_period=ema_fast_period,
        ema_slow_period=ema_slow_period,
        ema_slope_lookback=ema_slope_lookback,
        bb_period=bb_period,
        bb_std=bb_std,
        bb_lookback=bb_lookback,
        bb_squeeze_percentile=bb_squeeze_percentile,
    )
    detector = MarketRegimeDetector(config=config)
    return detector.detect(df)


__all__ = [
    "MarketRegime",
    "ADXResult",
    "ADXCalculator",
    "EMATrendResult",
    "EMATrendAnalyzer",
    "BollingerBandwidthResult",
    "BollingerBandwidthAnalyzer",
    "RegimeDetectorConfig",
    "MarketRegimeDetector",
    "detect_market_regime",
]


if __name__ == "__main__":
    # 簡易動作確認用（ランダムウォークで OHLC を生成）
    rng = np.random.default_rng(seed=42)
    n = 300
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    returns = rng.normal(loc=0.0005, scale=0.01, size=n)
    close = 100 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(rng.normal(0, 0.003, size=n)))
    low = close * (1 - np.abs(rng.normal(0, 0.003, size=n)))

    sample_df = pd.DataFrame(
        {"high": high, "low": low, "close": close}, index=dates
    )

    regime_df = detect_market_regime(sample_df, adx_threshold=25.0)
    print(
        regime_df[
            ["close", "adx", "ema_direction", "bb_is_squeeze", "regime_label", "allow_entry"]
        ].tail(10)
    )