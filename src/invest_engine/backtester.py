"""
バックテスト & パフォーマンス検証モジュール
プロの投資家・クオンツ・専業トレーダーが実際に重視する世界標準の投資パフォーマンス指標を網羅して算出します。
(TradingView / MetaTrader / QuantConnect 準拠)
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def run_backtest(
    eval_df: pd.DataFrame,
    threshold_long: float = 0.52,
    threshold_short: float = 0.48,
    fee_pct: float = 0.0003,  # 片道取引コスト (スプレッド + 手数料: 0.03%)
    allow_short: bool = True
) -> Dict[str, Any]:
    """
    検証データに対して、業界標準指標を網羅したバックテストを実行する。

    Parameters:
    - eval_df: 'pred_prob', 'target_future_return', 'Close' を含むDataFrame
    - threshold_long: ロング（買い）を行う予測確率
    - threshold_short: ショート（空売り）を行う予測確率
    - fee_pct: 片道あたりの取引コスト
    - allow_short: 空売りを有効にするか

    Returns:
    - Dict[str, Any]: 業界標準パフォーマンス指標の辞書および資産推移データ
    """
    df = eval_df.copy()

    # 1. シグナル判定: 1 (Long), -1 (Short), 0 (Cash/Neutral)
    positions = []
    for prob in df["pred_prob"]:
        if prob >= threshold_long:
            positions.append(1)
        elif allow_short and prob <= threshold_short:
            positions.append(-1)
        else:
            positions.append(0)

    df["position"] = positions

    # 2. ポジション変更時の取引コスト
    df["pos_change"] = df["position"].diff().abs().fillna(df["position"].abs())
    cost = df["pos_change"] * fee_pct

    # 3. 戦略リターン vs ベンチマークリターン
    df["strategy_return"] = (df["position"] * df["target_future_return"]) - cost
    df["benchmark_return"] = df["target_future_return"]

    # 4. 累積資産推移
    df["cumulative_strategy"] = (1.0 + df["strategy_return"]).cumprod()
    df["cumulative_benchmark"] = (1.0 + df["benchmark_return"]).cumprod()

    # 5. ドローダウン分析
    cum_max = df["cumulative_strategy"].cummax()
    drawdown = (df["cumulative_strategy"] - cum_max) / cum_max
    max_drawdown = float(drawdown.min())

    # 6. 取引損益分析 (個別トレード単位)
    trade_returns = df.loc[df["position"] != 0, "strategy_return"]
    n_trades = len(trade_returns)
    win_trades = trade_returns[trade_returns > 0]
    loss_trades = trade_returns[trade_returns < 0]

    n_wins = len(win_trades)
    n_losses = len(loss_trades)
    win_rate = float(n_wins / n_trades) if n_trades > 0 else 0.0

    gross_profit = float(win_trades.sum())
    gross_loss = float(abs(loss_trades.sum()))
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    # リスクリワード比 (損益比: 平均利益 ÷ 平均損失)
    avg_win = float(win_trades.mean()) if n_wins > 0 else 0.0
    avg_loss = float(abs(loss_trades.mean())) if n_losses > 0 else 0.0
    risk_reward_ratio = float(avg_win / avg_loss) if avg_loss > 0 else 0.0

    # 7. 年率換算指標 (年平均252営業日)
    total_days = len(df)
    years = max(total_days / 252.0, 0.1)

    total_return_strategy = float(df["cumulative_strategy"].iloc[-1] - 1.0)
    total_return_benchmark = float(df["cumulative_benchmark"].iloc[-1] - 1.0)

    # CAGR (年平均成長率: 実質年利)
    cagr = float((1.0 + total_return_strategy) ** (1.0 / years) - 1.0) if total_return_strategy > -1.0 else -1.0
    benchmark_cagr = float((1.0 + total_return_benchmark) ** (1.0 / years) - 1.0) if total_return_benchmark > -1.0 else -1.0

    # シャープレシオ (リスクフリーレート 0% 前提の年率換算)
    daily_mean = float(df["strategy_return"].mean()) if len(df) > 0 else 0.0
    daily_std = float(df["strategy_return"].std()) if len(df) > 1 else 0.0
    if np.isnan(daily_std) or daily_std == 0.0:
        sharpe_ratio = 0.0
    else:
        sharpe_ratio = float((daily_mean / (daily_std + 1e-8)) * np.sqrt(252))

    # カルマーレシオ (年率リターン ÷ 最大ドローダウン)
    # プロがドローダウンに耐える価値があるか測る最重要指標
    calmar_ratio = float(cagr / abs(max_drawdown)) if abs(max_drawdown) > 0 else 0.0

    # 回収率（元本比率 %）
    payout_rate = float((1.0 + total_return_strategy) * 100.0)

    # 業界標準メトリクスサマリー
    metrics = {
        # 基本期間
        "period_start": str(df.index[0].date()),
        "period_end": str(df.index[-1].date()),
        "total_days": int(total_days),
        "years": round(years, 2),
        "total_trades": int(n_trades),

        # 収益性指標
        "total_return_pct": round(total_return_strategy * 100, 2),
        "payout_rate_pct": round(payout_rate, 2),  # 回収率
        "cagr_pct": round(cagr * 100, 2),          # 年平均利回り

        # トレード勝率・効率
        "win_rate_pct": round(win_rate * 100, 2),                # 勝率
        "profit_factor": round(profit_factor, 2),                # プロフィットファクター (PF)
        "risk_reward_ratio": round(risk_reward_ratio, 2),        # リスクリワード比 (損益比)

        # リスク・安定性指標
        "max_drawdown_pct": round(max_drawdown * 100, 2),        # 最大ドローダウン (MDD)
        "sharpe_ratio": round(sharpe_ratio, 2),                  # シャープレシオ
        "calmar_ratio": round(calmar_ratio, 2),                  # カルマーレシオ

        # ベンチマーク比較
        "benchmark_return_pct": round(total_return_benchmark * 100, 2),
        "benchmark_cagr_pct": round(benchmark_cagr * 100, 2),
        "alpha_pct": round((total_return_strategy - total_return_benchmark) * 100, 2)
    }

    return {
        "metrics": metrics,
        "history_df": df[["Close", "pred_prob", "position", "strategy_return", "cumulative_strategy", "cumulative_benchmark"]]
    }


def run_event_driven_backtest(
    eval_df: pd.DataFrame,
    threshold_long: float = 0.52,
    threshold_short: float = 0.48,
    fee_pct: float = 0.0003,  # 片道手数料 (往復0.06%)
    allow_short: bool = True
) -> Dict[str, Any]:
    """
    トリプルバリア法イベント駆動型バックテスト。
    重複エントリーを排除し、各トレードをエントリーからバリア接触までの一意なライフサイクルとして会計する。
    """
    df = eval_df.copy().sort_index()
    n = len(df)
    
    # トレード履歴
    trades = []
    daily_returns = np.zeros(n)
    
    i = 0
    while i < n:
        prob = df["pred_prob"].iloc[i]
        pos = 0
        if prob >= threshold_long:
            pos = 1
        elif allow_short and prob <= threshold_short:
            pos = -1

        if pos != 0:
            entry_date = df.index[i]
            entry_price = df["Close"].iloc[i]
            
            # 保有日数 (target_holding_days が存在すればそれを使い、なければ1日)
            holding_days = int(df["target_holding_days"].iloc[i]) if "target_holding_days" in df.columns else 1
            holding_days = max(1, min(holding_days, n - 1 - i))
            
            exit_idx = min(i + holding_days, n - 1)
            exit_date = df.index[exit_idx]
            
            # トレードの生の gross return
            raw_ret = df["target_future_return"].iloc[i] if "target_future_return" in df.columns else (df["Close"].iloc[exit_idx] / entry_price - 1.0)
            strategy_pnl = float(pos * raw_ret - (fee_pct * 2))  # 往復手数料控除
            
            trade_record = {
                "entry_date": entry_date,
                "exit_date": exit_date,
                "direction": "LONG" if pos == 1 else "SHORT",
                "holding_days": holding_days,
                "raw_return": float(raw_ret),
                "net_pnl": strategy_pnl,
                "is_win": strategy_pnl > 0
            }
            trades.append(trade_record)
            
            # 決済日にリターンを反映
            daily_returns[exit_idx] = strategy_pnl
            
            # 保有期間中は次のエントリーを見送る（非重複制御：決済日の翌営業日以降に新規エントリー）
            i = max(i + 1, exit_idx + 1)
        else:
            i += 1

    # 資産曲線の計算
    cumulative = np.cumprod(1.0 + daily_returns)
    benchmark = np.cumprod(1.0 + df["Close"].pct_change().fillna(0.0).values)

    df["strategy_return"] = daily_returns
    df["cumulative_strategy"] = cumulative
    df["cumulative_benchmark"] = benchmark

    # 指標算出
    total_trades = len(trades)
    if total_trades > 0:
        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]
        win_rate = len(wins) / total_trades
        
        gross_profit = sum(t["net_pnl"] for t in wins) if wins else 0.0
        gross_loss = abs(sum(t["net_pnl"] for t in losses)) if losses else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        
        avg_win = gross_profit / len(wins) if wins else 0.0
        avg_loss = gross_loss / len(losses) if losses else 0.0
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    else:
        win_rate = 0.0
        profit_factor = 0.0
        risk_reward_ratio = 0.0

    # ドローダウン
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / peak
    max_drawdown = float(drawdown.min())

    total_return_strategy = float(cumulative[-1] - 1.0)
    total_return_benchmark = float(benchmark[-1] - 1.0)

    total_days = (df.index[-1] - df.index[0]).days
    years = max(total_days / 365.25, 0.1)
    cagr = float((1.0 + total_return_strategy) ** (1.0 / years) - 1.0) if total_return_strategy > -1.0 else -1.0
    benchmark_cagr = float((1.0 + total_return_benchmark) ** (1.0 / years) - 1.0) if total_return_benchmark > -1.0 else -1.0

    daily_mean = df["strategy_return"].mean()
    daily_std = df["strategy_return"].std()
    sharpe_ratio = float((daily_mean / (daily_std + 1e-8)) * np.sqrt(252))
    calmar_ratio = float(cagr / abs(max_drawdown)) if abs(max_drawdown) > 0 else 0.0

    metrics = {
        "period_start": str(df.index[0].date()),
        "period_end": str(df.index[-1].date()),
        "total_days": int(total_days),
        "years": round(years, 2),
        "total_trades": int(total_trades),
        "total_return_pct": round(total_return_strategy * 100, 2),
        "payout_rate_pct": round((1.0 + total_return_strategy) * 100.0, 2),
        "cagr_pct": round(cagr * 100, 2),
        "win_rate_pct": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 2),
        "risk_reward_ratio": round(risk_reward_ratio, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "benchmark_return_pct": round(total_return_benchmark * 100, 2),
        "benchmark_cagr_pct": round(benchmark_cagr * 100, 2),
        "alpha_pct": round((total_return_strategy - total_return_benchmark) * 100, 2)
    }

    return {
        "metrics": metrics,
        "trades": trades,
        "history_df": df[["Close", "pred_prob", "strategy_return", "cumulative_strategy", "cumulative_benchmark"]]
    }

