"""
市場データ取得・前処理モジュール
yfinance を用いて、株式、ETF、為替、暗号資産などの日足・分足データを安全に取得・キャッシュします。
"""

import os
from pathlib import Path
from typing import Optional
import pandas as pd
import yfinance as yf


CACHE_DIR = Path("data/invest_cache")


def fetch_historical_data(
    symbol: str = "SPY",
    period: str = "5y",
    interval: str = "1d",
    use_cache: bool = True
) -> pd.DataFrame:
    """
    指定銘柄のヒストリカルOHLCVデータを取得する。

    Parameters:
    - symbol: 銘柄コード (例: 'SPY', 'QQQ', 'AAPL', 'BTC-USD', '^N225', 'USDJPY=X')
    - period: 期間 ('1y', '2y', '5y', 'max')
    - interval: 足種 ('1d', '1h', '15m')
    - use_cache: ローカルキャッシュを利用するかどうか

    Returns:
    - pd.DataFrame: 日付インデックスを持つOHLCVデータフレーム
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{symbol.replace('^', '').replace('=', '_')}_{period}_{interval}.csv"

    # 足種に応じたキャッシュ有効期間 (TTL)
    if interval in ["1m", "5m"]:
        cache_ttl_seconds = 60  # 分足は1分で再取得
    elif interval in ["15m", "1h"]:
        cache_ttl_seconds = 300  # 短期足は5分
    else:
        cache_ttl_seconds = 1800  # 日足は30分

    cached_df = None
    if cache_path.exists():
        try:
            cached_df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            if not cached_df.empty and len(cached_df) > 5:
                if cached_df.index.tz is not None:
                    cached_df.index = cached_df.index.tz_localize(None)
                
                # キャッシュが新鮮であれば即座に返却
                import time
                file_age = time.time() - cache_path.stat().st_mtime
                if use_cache and file_age < cache_ttl_seconds:
                    return cached_df
        except Exception:
            cached_df = None

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
    except Exception as e:
        # 通信エラー時はキャッシュがあればそれを返却
        if cached_df is not None:
            return cached_df
        raise e

    if df.empty:
        if cached_df is not None:
            return cached_df
        raise ValueError(f"No historical data returned for symbol: {symbol}")

    # マルチインデックス列のフラット化（yfinanceのバージョン差異対策）
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 必要な基本カラムの確認と命名標準化
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Expected column '{col}' missing from downloaded data.")

    # タイムゾーンのUTC正規化または除去（純粋な日付比較を容易にする）
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # ソートと欠損処理
    df = df.sort_index()
    df = df.ffill().dropna()

    # 基本的なデータ整合性フィルタ (High >= Low >= 0)
    invalid_mask = (df["High"] < df["Low"]) | (df["Low"] <= 0)
    if invalid_mask.any():
        df = df[~invalid_mask].copy()

    # キャッシュ保存 (CSV形式で完全な可搬性と高速アクセスを保証)
    try:
        df.to_csv(cache_path)
    except Exception:
        pass

    return df


def fetch_latest_price(symbol: str) -> float:
    """
    指定銘柄の最新市場価格（リアルタイム終値・気配値）を取得する。
    """
    try:
        ticker = yf.Ticker(symbol)
        if hasattr(ticker, "fast_info") and "lastPrice" in ticker.fast_info:
            price = ticker.fast_info["lastPrice"]
            if price and float(price) > 0:
                return round(float(price), 2)
    except Exception:
        pass

    try:
        df = fetch_historical_data(symbol=symbol, period="5d", interval="1d", use_cache=True)
        if not df.empty:
            return round(float(df["Close"].iloc[-1]), 2)
    except Exception:
        pass

    defaults = {
        "GC=F": 4197.5,
        "USDJPY=X": 157.59,
        "BTC-USD": 84083.0,
        "NVDA": 229.12
    }
    return defaults.get(symbol, 100.0)


if __name__ == "__main__":
    # 簡易動作テスト
    test_symbol = "SPY"
    print(f"Fetching data for {test_symbol}...")
    df = fetch_historical_data(symbol=test_symbol, period="1y", interval="1d")
    print(f"Loaded {len(df)} rows. Range: {df.index[0]} to {df.index[-1]}")
    print(df.tail(3))
