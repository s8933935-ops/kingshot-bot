"""
macro_loader.py
外部マクロ指標データ取得・Point-in-Time結合モジュール。
米ドル指数（DXY）および米10年債利回り（US10Y）の確定データを取得し、
先読みバイアス（Lookahead bias）ゼロで価格データにマージします。
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
import yfinance as yf


CACHE_DIR = Path("data/cache/macro")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MACRO_TICKERS = {
    "DXY": "DX-Y.NYB",   # 米ドル指数 (US Dollar Index)
    "US10Y": "^TNX",      # 米10年債利回り (CBOE 10 Year Treasury Note Yield)
}


def fetch_macro_series(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
    use_cache: bool = True
) -> pd.DataFrame:
    """
    マクロ指標のOHLCV時系列データを取得・キャッシュする。
    """
    safe_ticker = ticker.replace("^", "").replace("=", "_").replace("-", "_")
    cache_file = CACHE_DIR / f"{safe_ticker}_{period}_{interval}.csv"

    import time
    if use_cache and cache_file.exists():
        # キャッシュ有効期限 (TTL: 12時間) を設定し、陳腐化を防止
        file_age_sec = time.time() - cache_file.stat().st_mtime
        if file_age_sec < 43200:
            try:
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                if not df.empty:
                    return df
            except Exception:
                pass

    # yfinance からダウンロード
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # タイムゾーンをUTCまたはnaiveに統一
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    try:
        df.to_csv(cache_file)
    except Exception:
        pass
    return df


def generate_macro_features(
    period: str = "5y",
    interval: str = "1d"
) -> pd.DataFrame:
    """
    DXY および US10Y からクオンツ予測用のモメンタム・スロープ特徴量を生成する。
    すべて当日引け確定値のみを使用（Point-in-Time）。
    """
    df_dxy = fetch_macro_series(MACRO_TICKERS["DXY"], period=period, interval=interval)
    df_us10y = fetch_macro_series(MACRO_TICKERS["US10Y"], period=period, interval=interval)

    # 共通日付インデックスを作成
    all_dates = df_dxy.index.union(df_us10y.index).sort_values()
    macro_df = pd.DataFrame(index=all_dates)

    # 1. 米ドル指数 (DXY) 特徴量
    dxy_close = df_dxy["Close"].reindex(all_dates).ffill()
    macro_df["dxy_close"] = dxy_close
    macro_df["dxy_ret_1d"] = dxy_close.pct_change(1)
    macro_df["dxy_ret_5d"] = dxy_close.pct_change(5)
    macro_df["dxy_mom_20"] = (dxy_close / dxy_close.rolling(20).mean()) - 1.0
    macro_df["dxy_rsi_14"] = _compute_rsi(dxy_close, 14)

    # 2. 米10年債利回り (US10Y) 特徴量
    us10y_close = df_us10y["Close"].reindex(all_dates).ffill()
    macro_df["us10y_yield"] = us10y_close
    macro_df["us10y_diff_1d"] = us10y_close.diff(1)
    macro_df["us10y_diff_5d"] = us10y_close.diff(5)
    macro_df["us10y_slope_20"] = (us10y_close - us10y_close.shift(20)) / 20.0

    # 3. マクロ総合レジーム（ドル安 & 低金利 = コモディティ・ゴールドへの最大追い風指標）
    # DXYが20日MAを下回り、かつ10年債金利が低下している局面を +1、逆を -1
    dxy_bear = macro_df["dxy_mom_20"] < 0
    yield_fall = macro_df["us10y_slope_20"] < 0
    
    macro_regime = np.zeros(len(macro_df))
    macro_regime[dxy_bear & yield_fall] = 1.0   # ゴールド・リスク資産への強力な追い風
    macro_regime[(~dxy_bear) & (~yield_fall)] = -1.0 # 強力な逆風 (ドル高・金利高)
    macro_df["macro_tailwind_score"] = macro_regime

    return macro_df.dropna()


def merge_macro_with_market_data(
    market_df: pd.DataFrame,
    macro_df: Optional[pd.DataFrame] = None
) -> Tuple[pd.DataFrame, list[str]]:
    """
    対象市場データ（Gold, BTC等）にマクロ特徴量をPoint-in-Timeで正確にマージする。
    休場日や時差による先読みを防ぐため、休場日は過去の最新確定値（ffill）を適用。
    """
    if macro_df is None:
        macro_df = generate_macro_features()

    # 日時タイムゾーンを揃える
    m_df = market_df.copy()
    if m_df.index.tz is not None:
        m_df.index = m_df.index.tz_localize(None)

    mac_df = macro_df.copy()
    if mac_df.index.tz is not None:
        mac_df.index = mac_df.index.tz_localize(None)

    # 市場データのインデックス基準で左結合 (Point-in-Time: 未来データによる先読み防止のためbfillは完全排除)
    macro_cols = [c for c in mac_df.columns if c not in ["dxy_close", "us10y_yield"]]
    merged = m_df.join(mac_df[macro_cols], how="left").ffill().dropna()

    return merged, macro_cols


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-8)
    return 100.0 - (100.0 / (1.0 + rs))


if __name__ == "__main__":
    df_macro = generate_macro_features()
    print("=== Macro Features Generated ===")
    print("Shape:", df_macro.shape)
    print(df_macro.tail(3))
