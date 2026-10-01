"""
eval_meta_labeling_pipeline.py
Step 3: メタラベリング ＆ マクロ指標直交統合パイプラインのPurged CV検証＆ブロックブートストラップ監査。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from src.invest_engine.data_loader import fetch_historical_data
from src.invest_engine.macro_loader import generate_macro_features, merge_macro_with_market_data
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.model_trainer import GoldPredictorModel
from src.invest_engine.meta_model import (
    MetaLabelingEngine,
    generate_meta_labels,
    compute_bet_size
)
from src.invest_engine.purged_cv import PurgedKFold


def run_meta_pipeline():
    print("=== 6大AI総力戦: メタラベリング ＆ マクロ指標直交統合 実証検証 ===")
    
    # 1. データ取得
    df_raw = fetch_historical_data("GC=F", period="5y", interval="1d")
    df_macro = generate_macro_features(period="5y", interval="1d")
    
    # 2. 特徴量生成（基本テクニカル + レジーム指標 + トリプルバリア）
    clean_df, feature_cols = generate_features(
        df_raw,
        use_triple_barrier=True,
        pt_factor=1.5,
        sl_factor=1.0,
        max_holding_days=5
    )
    
    # マクロ指標を Point-in-Time 結合
    merged_df, macro_cols = merge_macro_with_market_data(clean_df, df_macro)
    all_feature_cols = feature_cols + macro_cols
    print(f"データ件数: {len(merged_df)} 取引日, 一次特徴量数: {len(all_feature_cols)} 個")

    # 3. 一次モデルの Purged CV 学習
    print("\n[Step 3.1] 一次モデル (Primary Direction Model) 学習中...")
    primary_model = GoldPredictorModel(n_splits=5)
    train_res = primary_model.train_walk_forward(
        merged_df,
        all_feature_cols,
        use_purged_cv=True,
        pct_embargo=0.01
    )
    eval_df = train_res["eval_df"]
    print(f"一次モデル Purged CV 総合正解率: {train_res['overall_accuracy']:.2%}, AUC: {train_res['overall_auc']:.4f}")

    # 4. メタラベルの生成
    print("\n[Step 3.2] メタラベル (Meta-Labels) 生成中...")
    threshold_entry = 0.52
    meta_df = eval_df.copy()
    
    meta_labels = generate_meta_labels(
        pred_prob=meta_df["pred_prob"],
        true_label=meta_df["target_binary"],
        threshold=threshold_entry
    )
    meta_df["y_meta"] = meta_labels

    # 5. 二次メタモデルの Purged CV 学習
    print("[Step 3.3] 二次メタモデル (Meta Bet-Sizing Model) 学習中...")
    meta_feature_names = ["pred_prob", "dxy_ret_5d", "us10y_slope_20", "macro_tailwind_score"]
    
    # meta_df のカラム名を meta_feature_names に合わせる
    X_meta = pd.DataFrame(index=meta_df.index)
    X_meta["pred_prob"] = meta_df["pred_prob"]
    X_meta["dxy"] = meta_df["dxy_ret_5d"] if "dxy_ret_5d" in meta_df.columns else 0.0
    X_meta["us10y"] = meta_df["us10y_slope_20"] if "us10y_slope_20" in meta_df.columns else 0.0
    X_meta["tailwind_score"] = meta_df["macro_tailwind_score"] if "macro_tailwind_score" in meta_df.columns else 0.0

    meta_engine = MetaLabelingEngine(threshold=0.50)
    
    # Purged K-Fold でメタ確率を予測
    t1_meta = meta_df.index + pd.to_timedelta(meta_df["target_holding_days"].fillna(1).astype(int), unit="D")
    pkf_meta = PurgedKFold(n_splits=5, t1=pd.Series(t1_meta, index=meta_df.index), pct_embargo=0.01)
    
    meta_engine.fit(X_meta, meta_df["y_meta"], cv=pkf_meta)
    meta_probs = meta_engine.oof_predictions_.fillna(0.50)
    meta_df["meta_prob"] = meta_probs

    # 6. ハーフケリー基準による最適賭け金比率 (Bet Size) 算出
    # リスクリワード比 b = 1.5 (pt_factor / sl_factor)
    rr_ratio = 1.5
    bet_sizes = compute_bet_size(
        meta_prob=meta_probs,
        risk_reward_ratio=rr_ratio,
        kelly_fraction=0.5,
        min_bet_size=0.0,
        max_bet_size=1.0
    )
    meta_df["bet_size"] = bet_sizes

    # 7. バックテスト比較シミュレーション (単一固定サイズ vs メタサイズ最適化)
    fee_pct = 0.0003  # 片道 3 bps (往復 6 bps)
    
    def simulate_trades(df_input, use_meta_sizing=False):
        trades = []
        n = len(df_input)
        i = 0
        while i < n:
            prob = df_input["pred_prob"].iloc[i]
            if prob >= threshold_entry:
                holding_days = int(df_input["target_holding_days"].iloc[i]) if "target_holding_days" in df_input.columns else 1
                holding_days = max(1, min(holding_days, n - 1 - i))
                exit_idx = min(i + holding_days, n - 1)
                
                raw_ret = float(df_input["target_future_return"].iloc[i])
                net_pnl_unit = raw_ret - (fee_pct * 2)
                
                if use_meta_sizing:
                    size = float(df_input["bet_size"].iloc[i])
                else:
                    size = 1.0

                if size > 0.0:  # サイズ0%（見送り）以外を実行
                    realized_pnl = net_pnl_unit * size
                    trades.append({
                        "entry_idx": i,
                        "exit_idx": exit_idx,
                        "raw_ret": raw_ret,
                        "size": size,
                        "pnl": realized_pnl,
                        "is_win": net_pnl_unit > 0
                    })
                i = max(i + 1, exit_idx + 1)
            else:
                i += 1
        return trades

    trades_fixed = simulate_trades(meta_df, use_meta_sizing=False)
    trades_meta = simulate_trades(meta_df, use_meta_sizing=True)

    def calc_metrics(trades, label):
        if not trades:
            return {"label": label, "count": 0, "win_rate": 0, "pf": 0, "mdd": 0, "total_ret": 0}
        
        pnls = [t["pnl"] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        pf = gross_profit / gross_loss if gross_loss > 0 else 99.0
        win_rate = len(wins) / len(trades)
        
        cumulative = np.cumprod(1.0 + np.array(pnls))
        peak = np.maximum.accumulate(cumulative)
        dd = (cumulative - peak) / peak
        mdd = float(dd.min())
        total_ret = float(cumulative[-1] - 1.0)
        
        return {
            "label": label,
            "count": len(trades),
            "win_rate": win_rate,
            "pf": pf,
            "mdd": mdd,
            "total_ret": total_ret,
            "pnls": pnls
        }

    m_fix = calc_metrics(trades_fixed, "単一モデル (固定ロット 1.0)")
    m_meta = calc_metrics(trades_meta, "メタラベリング統合 (動的ケリーロット)")

    # 8. ブロックブートストラップ (1,000回試行) によるテールリスク・破産確率試算
    def block_bootstrap_ruin(pnls, block_size=5, n_sims=1000):
        if not pnls:
            return 0.0
        pnls_arr = np.array(pnls)
        n = len(pnls_arr)
        ruin_count = 0
        n_blocks = int(np.ceil(n / block_size))
        
        for _ in range(n_sims):
            # ランダムにブロックをサンプリング
            sampled_blocks = [
                pnls_arr[s:s+block_size]
                for s in np.random.randint(0, max(1, n - block_size), size=n_blocks)
            ]
            sim_pnls = np.concatenate(sampled_blocks)[:n]
            equity = np.cumprod(1.0 + sim_pnls)
            if equity.min() < 0.70:  # 30%ドローダウンを破産と定義
                ruin_count += 1
        return ruin_count / n_sims

    ruin_fix = block_bootstrap_ruin(m_fix["pnls"])
    ruin_meta = block_bootstrap_ruin(m_meta["pnls"])

    print("\n--- 【実証結果サマリー】 ---")
    header = f"{'指標':<30} | {'単一固定モデル':<18} | {'メタラベリング統合 (Step 3成果)':<22}"
    print(header)
    print("-" * len(header))
    print(f"{'トレード回数':<30} | {m_fix['count']:<18} | {m_meta['count']:<22}")
    print(f"{'勝率 (Win Rate)':<30} | {m_fix['win_rate']:<17.2%} | {m_meta['win_rate']:<21.2%}")
    print(f"{'プロフィットファクター (PF)':<30} | {m_fix['pf']:<18.2f} | {m_meta['pf']:<22.2f}")
    print(f"{'最大ドローダウン (MDD)':<30} | {m_fix['mdd']:<17.2%} | {m_meta['mdd']:<21.2%}")
    print(f"{'累積損益 (往復手数料控除後)':<30} | {m_fix['total_ret']:<17.2%} | {m_meta['total_ret']:<21.2%}")
    print(f"{'破産確率 (ブロックブートストラップ)':<30} | {ruin_fix:<17.2%} | {ruin_meta:<21.2%}")

    # メタモデルを本番保存
    meta_engine._model.save_model("data/invest_models/meta_lgbm_model.txt")
    print("\n本番メタモデルを data/invest_models/meta_lgbm_model.txt に保存完了。")


if __name__ == "__main__":
    run_meta_pipeline()
