"""
Zero-Leakage Strict Audit Suite for Autopilot Strategies
=========================================================

Zero-Leakage & Anti-Overfit System（5大鉄壁防壁）を用いて、
5大戦術の真のパフォーマンス、勝率、回収率、過学習判定（DSR）を決定論的に検証する。

実施内容:
1. Point-in-Time 特徴量監査（未来リーク検知）
2. Purged K-Fold with Embargo による完全 OOF 予測コンテナの発行（インサンプル完全排除）
3. ペシミスティック約定（同一バー内SL優先、スリッページ・手数料控除）
4. Bailey & Lopez de Prado (2014) の Deflated Sharpe Ratio (DSR) による統計的過学習検定
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import numpy as np
import pandas as pd
import lightgbm as lgb

from src.invest_engine.data_loader import fetch_historical_data
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.purged_cv import PurgedKFold
from src.invest_engine.autopilot_engine import STRATEGY_PROFILES
from src.invest_engine.zero_leakage_engine import (
    PointInTimeAuditor,
    OOFProvenanceToken,
    StrictOOFContainer,
    PessimisticExecutionEngine,
    calculate_deflated_sharpe_ratio,
    ZeroLeakageGuard,
    FeatureLeakageViolation,
    InSampleLeakageViolation
)


def run_zero_leakage_audit():
    print("=" * 70)
    print("Zero-Leakage Anti-Overfit System: 5大戦術 厳格監査開始")
    print("=" * 70)

    # 1. データ準備
    raw_df = fetch_historical_data("GC=F", period="2y", interval="1d")
    labeled_df, feature_cols = generate_features(raw_df)
    labeled_df = labeled_df.dropna().copy()

    print(f"[Step 1] 特徴量数: {len(feature_cols)}, 総サンプル数: {len(labeled_df)}")

    # 2. Invariant 1: 特徴量 Point-in-Time 監査
    print("\n--- [Invariant 1] 特徴量 Point-in-Time 監査実行 ---")
    auditor = PointInTimeAuditor()
    audit_report = auditor.audit_features(labeled_df, feature_cols)
    print(f"特徴量監査判定: {'合格 (PASS)' if audit_report['audit_passed'] else '不合格 (FAIL)'}")

    # 3. Invariant 2 & 3: Purged K-Fold with Embargo による厳格 OOF 予測生成
    print("\n--- [Invariant 2 & 3] Purged K-Fold OOF 予測生成 ＆ 出所証明トークン発行 ---")
    n_splits = 5
    pct_embargo = 0.01

    if "target_holding_days" in labeled_df.columns:
        t1 = labeled_df.index + pd.to_timedelta(labeled_df["target_holding_days"].fillna(1).astype(int), unit="D")
    else:
        t1 = labeled_df.index + pd.to_timedelta(1, unit="D")

    cv = PurgedKFold(n_splits=n_splits, t1=pd.Series(t1, index=labeled_df.index), pct_embargo=pct_embargo)
    splits = list(cv.split(labeled_df[feature_cols], labeled_df["target_binary"]))

    X = labeled_df[feature_cols].values
    y = labeled_df["target_binary"].values

    oof_probs = np.zeros(len(labeled_df))
    oof_folds = np.full(len(labeled_df), -1)
    train_indices = []

    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "n_estimators": 100,
        "learning_rate": 0.03,
        "max_depth": 3,
        "num_leaves": 8,
        "min_child_samples": 30,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "verbose": -1
    }

    for fold, (train_idx, val_idx) in enumerate(splits):
        train_indices.append(train_idx)
        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]

        clf = lgb.LGBMClassifier(**lgb_params)
        clf.fit(X_train, y_train)
        preds = clf.predict_proba(X_val)[:, 1]

        oof_probs[val_idx] = preds
        oof_folds[val_idx] = fold

    # OOF 証明書トークン生成
    token = OOFProvenanceToken.create(
        cv_method="PurgedKFold",
        n_splits=n_splits,
        embargo_pct=pct_embargo,
        total_samples=len(labeled_df),
        fold_train_indices=train_indices
    )

    eval_df = labeled_df.copy()
    eval_df["pred_prob"] = oof_probs
    eval_df["_oof_fold"] = oof_folds

    # 未検証の行（パージ等で評価対象外となった行）を除外
    eval_df = eval_df[eval_df["_oof_fold"] >= 0].copy()

    oof_container = StrictOOFContainer(eval_df, token)
    print(f"OOF 出所証明トークン発行完了: Signature={token.signature[:16]}...")
    print(f"有効 OOF 検証サンプル数: {len(eval_df)}")

    # 4. Invariant 4 & 5: ペシミスティック約定 ＆ Deflated Sharpe 検定
    print("\n--- [Invariant 4 & 5] ペシミスティック約定 ＆ DSR 統計的過学習検定 ---")
    pessimistic_engine = PessimisticExecutionEngine()
    guard = ZeroLeakageGuard(num_trials=len(STRATEGY_PROFILES))
    audit_results = {}

    # 戦術ごとの保有期間マッピング（日足ベース）
    holding_bars_map = {
        "scalping": 1,
        "day_trade": 2,
        "swing": 5,
        "medium_term": 20,
        "long_term": 60
    }

    for style_name, prof in STRATEGY_PROFILES.items():
        tp_pct = abs(prof["take_profit_pct"]) / 100.0
        sl_pct = abs(prof["stop_loss_pct"]) / 100.0
        buy_thresh = prof["buy_threshold"]
        max_bars = holding_bars_map.get(style_name, 5)

        def simulate_strategy(data: pd.DataFrame) -> dict:
            n = len(data)
            closes = data["Close"].values
            highs = data["High"].values
            lows = data["Low"].values
            probs = data["pred_prob"].values

            trades = []
            trade_returns = []
            i = 0

            while i < n - 1:
                prob = probs[i]
                if prob >= buy_thresh:
                    # 次の足の始値でエントリー
                    entry_price = closes[i]
                    tp_price = entry_price * (1.0 + tp_pct)
                    sl_price = entry_price * (1.0 - sl_pct)

                    closed = False
                    exit_price = entry_price
                    exit_reason = "TIMEOUT"

                    for hold_bar in range(1, min(max_bars + 1, n - i)):
                        bar_idx = i + hold_bar
                        b_high = highs[bar_idx]
                        b_low = lows[bar_idx]
                        b_close = closes[bar_idx]

                        # ペシミスティック約定（SL最優先、スリッページ0.05%、手数料0.03%）
                        is_c, px, reason = pessimistic_engine.evaluate_bar(
                            entry_price=entry_price,
                            position=1,
                            bar_high=b_high,
                            bar_low=b_low,
                            bar_close=b_close,
                            tp_price=tp_price,
                            sl_price=sl_price,
                            slippage_pct=0.0005,
                            fee_pct=0.0003
                        )
                        if is_c:
                            closed = True
                            exit_price = px
                            exit_reason = reason
                            i = bar_idx
                            break

                    if not closed:
                        # タイムアウト決済（終値決済 - スリッページ）
                        timeout_bar = min(i + max_bars, n - 1)
                        exit_price = closes[timeout_bar] * (1.0 - 0.0008)
                        exit_reason = "TIMEOUT_CLOSE"
                        i = timeout_bar

                    ret = (exit_price - entry_price) / entry_price
                    trade_returns.append(ret)
                    trades.append({
                        "entry_idx": i,
                        "entry_price": float(entry_price),
                        "exit_price": float(exit_price),
                        "return": float(ret),
                        "reason": exit_reason,
                        "win": ret > 0
                    })
                i += 1

            ret_arr = np.array(trade_returns)
            n_trades = len(ret_arr)
            wins = np.sum(ret_arr > 0)
            losses = np.sum(ret_arr < 0)
            win_rate = (wins / n_trades * 100) if n_trades > 0 else 0.0
            
            # 回収率 (Profit Factor / Return on Investment)
            gross_profit = np.sum(ret_arr[ret_arr > 0]) if wins > 0 else 0.0
            gross_loss = np.abs(np.sum(ret_arr[ret_arr < 0])) if losses > 0 else 1e-6
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            total_return_pct = (np.prod(1.0 + ret_arr) - 1.0) * 100 if n_trades > 0 else 0.0

            return {
                "n_trades": int(n_trades),
                "wins": int(wins),
                "losses": int(losses),
                "win_rate_pct": float(win_rate),
                "profit_factor": float(profit_factor),
                "total_return_pct": float(total_return_pct),
                "trade_returns": ret_arr
            }

        # ZeroLeakageGuard による保護実行 ＆ DSR過学習判定
        res = guard.verify_and_protect_backtest(
            container=oof_container,
            strategy_func=simulate_strategy,
            features=feature_cols
        )

        dsr = res["deflated_sharpe_analysis"]
        audit_results[style_name] = {
            "style_name": prof["name"],
            "take_profit_pct": tp_pct * 100,
            "stop_loss_pct": sl_pct * 100,
            "total_trades": res["n_trades"],
            "win_rate_pct": round(res["win_rate_pct"], 2),
            "profit_factor": round(res["profit_factor"], 2),
            "total_return_pct": round(res["total_return_pct"], 2),
            "sharpe_ratio": round(dsr["sharpe_ratio"], 2),
            "deflated_sharpe_ratio": round(dsr["deflated_sharpe_ratio"], 4),
            "p_value": round(dsr["p_value"], 4),
            "is_statistically_significant": dsr["is_statistically_significant"],
            "zero_leakage_certified": res["zero_leakage_certified"]
        }

        print(f"\n[{prof['name']}] (TP: +{tp_pct*100}%, SL: -{sl_pct*100}%)")
        print(f"  約定回数: {res['n_trades']} 回")
        print(f"  厳格勝率: {res['win_rate_pct']:.2f}% | プロフィットファクター: {res['profit_factor']:.2f}")
        print(f"  累積リターン: {res['total_return_pct']:.2f}%")
        print(f"  Sharpe: {dsr['sharpe_ratio']:.2f} | DSR: {dsr['deflated_sharpe_ratio']:.4f} (p={dsr['p_value']:.4f})")
        print(f"  過学習判定: {'[PASS] 統計的有意 (過学習なし)' if dsr['is_statistically_significant'] else '[REJECT] 過学習/優位性なし'}")

    # 結果保存
    out_path = Path("data/consortium/zero_leakage_audit_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, ensure_ascii=False, indent=2)

    print(f"\n[Zero-Leakage 監査完了] 結果保存先: {out_path}")
    return audit_results


if __name__ == "__main__":
    run_zero_leakage_audit()
