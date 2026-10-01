"""
特徴量エンジニアリングモジュール（金先物 / FX / コモディティ対応）
OHLCVデータから、金融時系列予測に特化したテクニカル指標・モメンタム・ボラティリティ特徴量を生成します。
未来データの漏洩（Lookahead bias）を厳格に防ぐため、当日終値までの確定値のみを使用します。
"""

from typing import Optional, Tuple, List
import numpy as np
import pandas as pd
from src.invest_engine.labeling import apply_triple_barrier
from src.invest_engine.regime_detector import detect_market_regime
from src.invest_engine.data_cleaner import clean_outliers_and_bad_ticks, add_session_features, merge_htf_trend_features


def generate_features(
    df: pd.DataFrame,
    target_horizon: int = 1,
    threshold_pct: float = 0.0,
    use_triple_barrier: bool = True,
    pt_factor: float = 2.0,
    sl_factor: float = 1.0,
    max_holding_days: int = 5,
    htf_df: Optional[pd.DataFrame] = None
) -> Tuple[pd.DataFrame, list]:
    """
    OHLCVデータから予測用特徴量とターゲットラベルを生成する。

    Parameters:
    - df: OHLCV DataFrame ('Open', 'High', 'Low', 'Close', 'Volume')
    - target_horizon: 何足先を予測するか（デフォルト 1足先）
    - threshold_pct: 上昇/下落とみなす最小変動幅（例: 0.001 = 0.1%）
    - htf_df: 上位足DataFrame（オプション: 5m/15m足に日足トレンドを結合）

    Returns:
    - Tuple[pd.DataFrame, list]: (特徴量 + ターゲットを含むデータフレーム, 特徴量名リスト)
    """
    # 0. データ品質クリーニング（異常値・Bad Ticksの自動除去）
    data = clean_outliers_and_bad_ticks(df)

    # 1. リターン指標
    data["return_1d"] = data["Close"].pct_change(1)
    data["return_3d"] = data["Close"].pct_change(3)
    data["return_5d"] = data["Close"].pct_change(5)
    data["return_10d"] = data["Close"].pct_change(10)
    data["return_20d"] = data["Close"].pct_change(20)

    # 2. 移動平均線（SMA / EMA）と価格乖離率
    for window in [5, 10, 20, 50, 100]:
        sma = data["Close"].rolling(window=window).mean()
        data[f"sma_{window}"] = sma
        data[f"dist_sma_{window}"] = (data["Close"] - sma) / (sma + 1e-8)

    data["ema_12"] = data["Close"].ewm(span=12, adjust=False).mean()
    data["ema_26"] = data["Close"].ewm(span=26, adjust=False).mean()

    # 3. MACD
    data["macd"] = data["ema_12"] - data["ema_26"]
    data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()
    data["macd_hist"] = data["macd"] - data["macd_signal"]

    # 4. 相対力指数 (RSI - 14)
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-8)
    data["rsi_14"] = 100 - (100 / (1 + rs))

    # 5. ボリンジャーバンド (20日, 2σ)
    bb_mean = data["Close"].rolling(window=20).mean()
    bb_std = data["Close"].rolling(window=20).std()
    data["bb_upper"] = bb_mean + 2 * bb_std
    data["bb_lower"] = bb_mean - 2 * bb_std
    data["bb_pct"] = (data["Close"] - data["bb_lower"]) / (data["bb_upper"] - data["bb_lower"] + 1e-8)
    data["bb_width"] = (data["bb_upper"] - data["bb_lower"]) / (bb_mean + 1e-8)

    # 6. ボラティリティ (ATR: Average True Range - 14日)
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift(1)).abs()
    low_close = (data["Low"] - data["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["atr_14"] = tr.rolling(window=14).mean()
    data["atr_pct"] = data["atr_14"] / data["Close"]

    # 7. 日中ローソク足の形状（ヒゲ・実体比率）
    candle_body = (data["Close"] - data["Open"]).abs()
    candle_range = data["High"] - data["Low"]
    data["body_to_range"] = candle_body / (candle_range + 1e-8)
    data["upper_shadow"] = (data["High"] - data[["Open", "Close"]].max(axis=1)) / (candle_range + 1e-8)
    data["lower_shadow"] = (data[["Open", "Close"]].min(axis=1) - data["Low"]) / (candle_range + 1e-8)

    # 8. 出来高指標 (Volume Change & Volume Moving Average)
    if "Volume" in data.columns and (data["Volume"] > 0).any():
        vol_ma = data["Volume"].rolling(window=20).mean()
        data["vol_ratio_20"] = data["Volume"] / (vol_ma + 1e-8)
    else:
        data["vol_ratio_20"] = 1.0

    # 9. 相場レジーム指標（ADX, EMAスロープ, BB帯域幅）
    regime_res = detect_market_regime(data, adx_threshold=22.0)
    data["adx"] = regime_res["adx"]
    data["plus_di"] = regime_res["plus_di"]
    data["minus_di"] = regime_res["minus_di"]
    data["ema_fast_slope"] = regime_res["ema_fast_slope"]
    data["ema_spread_pct"] = regime_res["ema_spread_pct"]
    data["regime_state"] = regime_res["regime"]
    data["regime_encoded"] = data["regime_state"].map({
        "BULL_TREND": 1.0,
        "BEAR_TREND": -1.0,
        "CHOPPY_RANGE": 0.0,
        "HIGH_VOL_BREAKOUT": 2.0
    }).fillna(0.0)

    # 10. セッション特徴量（NY/ロンドン、アジア、オフアワー）
    data = add_session_features(data)

    # 11. 上位足（HTF）特徴量の結合（Point-in-Time 物理整合性担保）
    if htf_df is not None:
        data = merge_htf_trend_features(data, htf_df, htf_name="daily")

    # ================= 予測ターゲットの生成 =================
    if use_triple_barrier:
        # マルコス・ロペス・デ・プラドのトリプルバリア法
        tb_events = apply_triple_barrier(
            data,
            pt_factor=pt_factor,
            sl_factor=sl_factor,
            max_holding_days=max_holding_days,
            vol_window=20,
            vol_method="atr"
        )
        data["target_binary"] = tb_events["label"]
        data["target_future_return"] = tb_events["ret"]
        data["target_holding_days"] = tb_events["holding_days"]
        data["touch_time"] = tb_events["touch_time"]
    else:
        # 従来の固定時間リターン
        future_return = data["Close"].shift(-target_horizon) / data["Close"] - 1.0
        data["target_future_return"] = future_return
        data["target_binary"] = (future_return > threshold_pct).astype(int)

    # 特徴量列一覧（予測時・学習時に使う入力変数：ターゲットおよび未来情報は厳格除外）
    exclude_cols = [
        "Open", "High", "Low", "Close", "Volume",
        "Stock Splits", "Capital Gains", "Dividends",
        "target_future_return", "target_binary", "target_holding_days",
        "entry_price", "vol", "upper_barrier", "lower_barrier",
        "vertical_barrier_time", "touch_time", "regime_state"
    ]
    feature_cols = [c for c in data.columns if c not in exclude_cols]

    # NaN（ローリング初期値や未来バリア未到達行）を除去
    clean_data = data.dropna().copy()
    if "target_binary" in clean_data.columns:
        clean_data["target_binary"] = clean_data["target_binary"].astype(int)

    return clean_data, feature_cols


if __name__ == "__main__":
    from src.invest_engine.data_loader import fetch_historical_data

    symbol = "GC=F"  # 金先物
    print(f"Loading data for {symbol}...")
    df = fetch_historical_data(symbol=symbol, period="5y", interval="1d")
    clean_df, features = generate_features(df)
    print(f"Generated {len(features)} features for {len(clean_df)} trading days.")
    print("Feature columns preview:", features[:8])
    print(clean_df[["Close", "rsi_14", "macd", "target_binary", "target_future_return"]].tail(3))
