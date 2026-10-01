"""
eval_triple_barrier.py
Step 1（トリプルバリア法）および Step 2（相場レジームフィルター）の統合バックテスト評価。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from src.invest_engine.data_loader import fetch_historical_data
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.model_trainer import GoldPredictorModel
from src.invest_engine.backtester import run_backtest, run_event_driven_backtest
from src.invest_engine.regime_detector import detect_market_regime, MarketRegime


def run_comparison():
    print("=== Step 1 & Step 2: トリプルバリア法 ＆ 相場レジームフィルター統合検証 ===")
    df = fetch_historical_data("GC=F", period="5y", interval="1d")

    # 1. 従来手法 (Fixed Horizon)
    clean_df_fixed, features_fixed = generate_features(df, use_triple_barrier=False)
    model_fixed = GoldPredictorModel(n_splits=5)
    res_fixed = model_fixed.train_walk_forward(clean_df_fixed, features_fixed)
    perf_fixed = run_backtest(res_fixed["eval_df"], threshold_long=0.53, threshold_short=0.47)

    # 2. トリプルバリア法 単体 (フィルターなし)
    clean_df_tb, features_tb = generate_features(
        df,
        use_triple_barrier=True,
        pt_factor=1.5,
        sl_factor=1.0,
        max_holding_days=5
    )
    model_tb = GoldPredictorModel(n_splits=5)
    res_tb = model_tb.train_walk_forward(clean_df_tb, features_tb)
    perf_tb_raw = run_event_driven_backtest(res_tb["eval_df"], threshold_long=0.53, threshold_short=0.47)

    # 3. トリプルバリア法 ＋ 相場レジームフィルター (Step 2 成果物)
    eval_df_filtered = res_tb["eval_df"].copy()
    regime_df = detect_market_regime(eval_df_filtered, adx_threshold=22.0)
    
    # レジーム判定に基づき、エントリー不適格（レンジ/スクイーズ/逆トレンド）の場合はシグナルを中立(0.50)にリセット
    filtered_probs = eval_df_filtered["pred_prob"].copy()
    for idx in eval_df_filtered.index:
        allow = regime_df.loc[idx, "allow_entry"]
        regime = regime_df.loc[idx, "regime"]
        p = filtered_probs.loc[idx]

        # 許可フラグがFalse（レンジ相場やスクイーズ）なら見送り
        if not allow:
            filtered_probs.loc[idx] = 0.50
        # 上昇トレンドなのにShortシグナル、または下降トレンドなのにLongシグナルの逆張りは抑制
        elif regime == MarketRegime.TREND_BULL and p < 0.50:
            filtered_probs.loc[idx] = 0.50
        elif regime == MarketRegime.TREND_BEAR and p > 0.50:
            filtered_probs.loc[idx] = 0.50

    eval_df_filtered["pred_prob"] = filtered_probs
    perf_tb_regime = run_event_driven_backtest(eval_df_filtered, threshold_long=0.53, threshold_short=0.47)

    print("\n--- 【実験結果サマリー】 ---")
    header = f"{'指標':<26} | {'従来 (Fixed 1D)':<16} | {'TB単体 (No Filter)':<18} | {'TB + レジームフィルター (Step 2)':<22}"
    print(header)
    print("-" * len(header))
    
    m_fix = perf_fixed['metrics']
    m_raw = perf_tb_raw['metrics']
    m_reg = perf_tb_regime['metrics']

    print(f"{'総トレード回数':<26} | {m_fix['total_trades']:<16} | {m_raw['total_trades']:<18} | {m_reg['total_trades']:<22}")
    print(f"{'勝率 (Win Rate)':<26} | {m_fix['win_rate_pct']:<15.2f}% | {m_raw['win_rate_pct']:<17.2f}% | {m_reg['win_rate_pct']:<21.2f}%")
    print(f"{'プロフィットファクター (PF)':<26} | {m_fix['profit_factor']:<16.2f} | {m_raw['profit_factor']:<18.2f} | {m_reg['profit_factor']:<22.2f}")
    print(f"{'リスクリワード比 (RR比)':<26} | {m_fix['risk_reward_ratio']:<16.2f} | {m_raw['risk_reward_ratio']:<18.2f} | {m_reg['risk_reward_ratio']:<22.2f}")
    print(f"{'最大ドローダウン (MDD)':<26} | {m_fix['max_drawdown_pct']:<15.2f}% | {m_raw['max_drawdown_pct']:<17.2f}% | {m_reg['max_drawdown_pct']:<21.2f}%")
    print(f"{'累積リターン':<26} | {m_fix['total_return_pct']:<15.2f}% | {m_raw['total_return_pct']:<17.2f}% | {m_reg['total_return_pct']:<21.2f}%")
    print(f"{'シャープレシオ':<26} | {m_fix['sharpe_ratio']:<16.2f} | {m_raw['sharpe_ratio']:<18.2f} | {m_reg['sharpe_ratio']:<22.2f}")


if __name__ == "__main__":
    run_comparison()
