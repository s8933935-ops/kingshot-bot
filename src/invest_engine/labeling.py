import numpy as np
import pandas as pd


def _compute_atr(df: pd.DataFrame, window: int) -> pd.Series:
    """
    True Range / ATR (Average True Range) を計算するヘルパー関数。
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    """
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=window, min_periods=window).mean()
    return atr


def _compute_ewma_vol(df: pd.DataFrame, window: int) -> pd.Series:
    """
    日次リターンのEWMA(指数加重移動平均)標準偏差を計算するヘルパー関数。
    ボラティリティを「価格スケール」に揃えるため Close 価格を掛けて返す。
    """
    returns = df["Close"].pct_change()
    ewma_std = returns.ewm(span=window, min_periods=window).std()
    # リターン(比率)ベースのボラティリティを価格スケールに変換
    vol_in_price = ewma_std * df["Close"]
    return vol_in_price


def get_dynamic_volatility(
    df: pd.DataFrame,
    vol_window: int = 20,
    method: str = "atr",
) -> pd.Series:
    """
    動的ボラティリティを計算する。

    Parameters
    ----------
    df : pd.DataFrame
        Open, High, Low, Close, Volume を含むDataFrame。
    vol_window : int
        ボラティリティ計算に用いるウィンドウ幅(日数)。
    method : str
        'atr' または 'ewma' を指定。
        - 'atr'  : Average True Range(価格スケールのボラティリティ)
        - 'ewma' : 日次リターンのEWMA標準偏差を価格スケールに変換したもの

    Returns
    -------
    pd.Series
        価格スケールで表現された動的ボラティリティ(バリア幅の基準値)。
    """
    if method == "atr":
        vol = _compute_atr(df, vol_window)
    elif method == "ewma":
        vol = _compute_ewma_vol(df, vol_window)
    else:
        raise ValueError("method must be 'atr' or 'ewma'")
    return vol


def apply_triple_barrier(
    df: pd.DataFrame,
    pt_factor: float = 2.0,
    sl_factor: float = 1.0,
    max_holding_days: int = 5,
    vol_window: int = 20,
    vol_method: str = "atr",
) -> pd.DataFrame:
    """
    Marcos Lopez de Prado の Triple Barrier Method を実装する関数。

    各時点 t (イベント発生時点) について、以下の3本のバリアのうち
    最初にタッチしたものを判定し、ラベル・イベント日時・保有日数・
    リターン率を算出する。

    - 上部バリア (Profit-Taking) : entry_price * (1 + pt_factor * vol_ratio)
    - 下部バリア (Stop-Loss)     : entry_price * (1 - sl_factor * vol_ratio)
    - 垂直バリア (Vertical/Time) : t + max_holding_days 営業日後

    Parameters
    ----------
    df : pd.DataFrame
        DatetimeIndex を持ち、Open, High, Low, Close, Volume 列を含むDataFrame。
        時系列順(昇順)にソートされている必要がある。
    pt_factor : float
        利確バリアの幅を決めるボラティリティ倍率(Profit-Taking factor)。
    sl_factor : float
        損切りバリアの幅を決めるボラティリティ倍率(Stop-Loss factor)。
    max_holding_days : int
        垂直バリアまでの最長保有日数(営業日ベースのバー本数)。
    vol_window : int
        動的ボラティリティ計算に用いるウィンドウ幅。
    vol_method : str
        'atr' または 'ewma'。ボラティリティ計算方式の指定。

    Returns
    -------
    pd.DataFrame
        元のインデックス(イベント発生時点 t)を保持し、以下の列を追加した
        DataFrame:
        - entry_price   : イベント発生時点の終値(エントリー価格)
        - vol           : イベント発生時点の動的ボラティリティ
        - upper_barrier : 上部バリア価格
        - lower_barrier : 下部バリア価格
        - vertical_barrier_time : 垂直バリアの日時(タイムスタンプ)
        - touch_time    : 実際にタッチしたバリアの日時
        - holding_days  : エントリーからタッチまでの保有日数(バー数)
        - ret           : タッチ時点までのリターン率 (touch_price / entry_price - 1)
        - label         : 1 (上部バリア到達), 0 (下部バリア到達),
                           1 or 0 (垂直バリア到達時、リターンの正負で判定)
    """
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"DataFrameに必要な列が不足しています: {missing}")

    if not df.index.is_monotonic_increasing:
        raise ValueError("DataFrameのインデックスは時系列昇順である必要があります。")

    n = len(df)
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    index = df.index

    # 動的ボラティリティ(価格スケール)を計算
    vol_series = get_dynamic_volatility(df, vol_window=vol_window, method=vol_method)
    vol = vol_series.values

    # 結果格納用のリスト
    entry_prices = np.full(n, np.nan)
    vols = np.full(n, np.nan)
    upper_barriers = np.full(n, np.nan)
    lower_barriers = np.full(n, np.nan)
    vertical_barrier_times = np.full(n, np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    touch_times = np.full(n, np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    holding_days = np.full(n, np.nan)
    rets = np.full(n, np.nan)
    labels = np.full(n, np.nan)

    for t in range(n):
        # ボラティリティが計算できていない(ウォームアップ期間)場合はスキップ
        if np.isnan(vol[t]) or vol[t] <= 0:
            continue

        entry_price = close[t]
        v = vol[t]

        upper_barrier = entry_price + pt_factor * v
        lower_barrier = entry_price - sl_factor * v

        # 垂直バリア: t から max_holding_days 本先(データ末尾を超えない)
        vertical_idx = min(t + max_holding_days, n - 1)

        # 末尾に到達していて未来のバーが存在しない場合はイベント計算不可
        if vertical_idx == t:
            continue

        entry_prices[t] = entry_price
        vols[t] = v
        upper_barriers[t] = upper_barrier
        lower_barriers[t] = lower_barrier
        vertical_barrier_times[t] = index[vertical_idx]

        touch_idx = None
        touch_label = None

        # t+1 から vertical_idx まで、各バーの High/Low を走査し
        # 最初にどちらかのバリアにタッチした時点を探す
        for future_idx in range(t + 1, vertical_idx + 1):
            hit_upper = high[future_idx] >= upper_barrier
            hit_lower = low[future_idx] <= lower_barrier

            if hit_upper and hit_lower:
                # 同一バーで両方タッチした場合は、始値に近い側(保守的に損切り側)を優先
                # ※ 日中の値動き順序が不明なため、Lopez de Prado の実務慣行に倣い
                #   より安全側(Stop-Loss)を優先してラベル付けする
                touch_idx = future_idx
                touch_label = 0
                break
            elif hit_upper:
                touch_idx = future_idx
                touch_label = 1
                break
            elif hit_lower:
                touch_idx = future_idx
                touch_label = 0
                break

        if touch_idx is not None:
            # 上部 or 下部バリアにタッチ
            touch_price = upper_barrier if touch_label == 1 else lower_barrier
            touch_times[t] = index[touch_idx]
            holding_days[t] = touch_idx - t
            rets[t] = (touch_price / entry_price) - 1.0
            labels[t] = touch_label
        else:
            # 垂直バリアに到達(期限切れ) -> 終値ベースのリターンの正負でラベル付け
            exit_price = close[vertical_idx]
            touch_times[t] = index[vertical_idx]
            holding_days[t] = vertical_idx - t
            rets[t] = (exit_price / entry_price) - 1.0
            labels[t] = 1.0 if rets[t] > 0 else 0.0

    result = pd.DataFrame(
        {
            "entry_price": entry_prices,
            "vol": vols,
            "upper_barrier": upper_barriers,
            "lower_barrier": lower_barriers,
            "vertical_barrier_time": vertical_barrier_times,
            "touch_time": touch_times,
            "holding_days": holding_days,
            "ret": rets,
            "label": labels,
        },
        index=index,
    )

    # イベントが成立しなかった行(ウォームアップ・末尾で保有期間が取れない等)を除外
    result = result.dropna(subset=["entry_price", "touch_time"])

    # 型を整える
    result["holding_days"] = result["holding_days"].astype(int)
    result["label"] = result["label"].astype(int)

    return result


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # 動作確認用のサンプル(ダミーの価格データを生成してテスト)
    # ------------------------------------------------------------------
    np.random.seed(42)
    n_days = 200
    dates = pd.date_range("2023-01-01", periods=n_days, freq="B")

    # ランダムウォークで価格データを生成
    daily_returns = np.random.normal(loc=0.0003, scale=0.01, size=n_days)
    close_prices = 100 * np.cumprod(1 + daily_returns)

    open_prices = close_prices * (1 + np.random.normal(0, 0.001, n_days))
    high_prices = np.maximum(open_prices, close_prices) * (
        1 + np.abs(np.random.normal(0, 0.003, n_days))
    )
    low_prices = np.minimum(open_prices, close_prices) * (
        1 - np.abs(np.random.normal(0, 0.003, n_days))
    )
    volume = np.random.randint(1_000_000, 5_000_000, n_days)

    sample_df = pd.DataFrame(
        {
            "Open": open_prices,
            "High": high_prices,
            "Low": low_prices,
            "Close": close_prices,
            "Volume": volume,
        },
        index=dates,
    )

    events = apply_triple_barrier(
        sample_df,
        pt_factor=2.0,
        sl_factor=1.0,
        max_holding_days=5,
        vol_window=20,
        vol_method="atr",
    )

    print(events.head(20))
    print("\nラベル分布:")
    print(events["label"].value_counts())