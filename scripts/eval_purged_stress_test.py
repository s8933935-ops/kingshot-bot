"""
eval_purged_stress_test.py
Step 3: Purged K-Fold CV（時系列漏洩排除）とスリッページ負荷ストレステスト。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from src.invest_engine.data_loader import fetch_historical_data
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.model_trainer import GoldPredictorModel
from src.invest_engine.backtester import run_event_driven_backtest


def run_purged_stress_test():
    print("=== Step 3: Purged K-Fold CV & スリッページ負荷ストレステスト ===")
    df = fetch_historical_data("GC=F", period="5y", interval="1d")

    # 1. 特徴量生成（レジーム指標内蔵 ＋ トリプルバリア法）
    clean_df, features = generate_features(
        df,
        use_triple_barrier=True,
        pt_factor=1.5,
        sl_factor=1.0,
        max_holding_days=5
    )
    print(f"データ総数: {len(clean_df)} 日分, 入力特徴量数: {len(features)} 個")

    # 2. Purged K-Fold CV による厳格学習（過学習・情報漏洩 0%）
    model = GoldPredictorModel(n_splits=5)
    train_res = model.train_walk_forward(clean_df, features, use_purged_cv=True, pct_embargo=0.01)
    eval_df = train_res["eval_df"]

    print(f"Purged CV 総合正解率 (Acc): {train_res['overall_accuracy']:.2%}")
    print(f"Purged CV 総合 AUC: {train_res['overall_auc']:.4f}")
    print("\n【特徴量重要度 Top 5】")
    for feat in train_res["feature_importance_top10"][:5]:
        print(f"  - {feat['feature']:<20}: {feat['importance']:.1f}")

    # 3. スリッページ負荷ストレステスト
    stress_scenarios = [
        ("標準コスト (片道0.03% / 往復0.06%)", 0.0003),
        ("高スリッページ (片道0.08% / 往復0.16%)", 0.0008),
        ("過酷環境 (片道0.12% / 往復0.24%)", 0.0012)
    ]

    print("\n--- 【スリッページ負荷ストレステスト結果】 ---")
    header = f"{'シナリオ':<36} | {'トレード数':<10} | {'勝率':<10} | {'PF':<8} | {'RR比':<8} | {'MDD':<10} | {'累積リターン':<12}"
    print(header)
    print("-" * len(header))

    for name, fee in stress_scenarios:
        perf = run_event_driven_backtest(
            eval_df,
            threshold_long=0.52,
            threshold_short=0.48,
            fee_pct=fee
        )
        m = perf["metrics"]
        print(f"{name:<36} | {m['total_trades']:<10} | {m['win_rate_pct']:<9.1f}% | {m['profit_factor']:<8.2f} | {m['risk_reward_ratio']:<8.2f} | {m['max_drawdown_pct']:<9.1f}% | {m['total_return_pct']:<11.1f}%")

    # モデルを本番保存
    model.save()
    print("\nPurged CV 最適化モデルを data/invest_models/gold_lgbm_model.txt に本番保存完了。")


if __name__ == "__main__":
    run_purged_stress_test()
