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

    if use_cache and cache_path.exists():
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            if not df.empty and len(df) > 5:
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                return df
        except Exception:
            pass  # キャッシュ読み込み失敗時は再取得

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)

    if df.empty:
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


if __name__ == "__main__":
    # 簡易動作テスト
    test_symbol = "SPY"
    print(f"Fetching data for {test_symbol}...")
    df = fetch_historical_data(symbol=test_symbol, period="1y", interval="1d")
    print(f"Loaded {len(df)} rows. Range: {df.index[0]} to {df.index[-1]}")
    print(df.tail(3))
