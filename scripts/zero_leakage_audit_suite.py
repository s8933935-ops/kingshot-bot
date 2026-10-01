"""
Zero-Leakage Multi-Timeframe High-Frequency & Dynamic ATR Audit Suite
=====================================================================

Zero-Leakage & Anti-Overfit System（5大鉄壁防壁）を用いて、
5大戦術を高頻度マルチタイムフレーム（5m / 15m / 1h / 1d）および
動的ATRトリプルバリア法（Dynamic ATR Triple Barrier）で厳格監査する。

実施内容:
1. 各戦術のネイティブ足種（スキャルピング: 5m, デイトレード: 15m, スイング: 1h, 中期/長期: 1d）でのデータ取得
2. Point-in-Time 特徴量監査（未来リーク検知）
3. Purged K-Fold with Embargo による完全 OOF 予測コンテナの発行（インサンプル完全排除）
4. 動的ATRトリプルバリア vs 固定%バリアのペシミスティック約定（同一バー内SL優先、スリッページ・手数料控除）
5. Bailey & Lopez de Prado (2014) の Deflated Sharpe Ratio (DSR) による統計的過学習検定
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
from src.invest_engine.autopilot_engine import STRATEGY_PROFILES, compute_strategy_barriers
from src.invest_engine.zero_leakage_engine import (
    PointInTimeAuditor,
    OOFProvenanceToken,
    StrictOOFContainer,
    PessimisticExecutionEngine,
    ZeroLeakageGuard,
    FeatureLeakageViolation,
    InSampleLeakageViolation
)


TIMEFRAME_CONFIG = {
    "scalping": {"interval": "5m", "period": "5d"},
    "day_trade": {"interval": "15m", "period": "30d"},
    "swing": {"interval": "1h", "period": "60d"},
    "medium_term": {"interval": "1d", "period": "5y"},
    "long_term": {"interval": "1d", "period": "5y"},
}


def audit_single_strategy(style_name: str, prof: dict, symbol: str = "GC=F") -> dict:
    """単一戦術に対する厳格監査（動的ATRトリプルバリア ＆ ネイティブ足種）"""
    tf_cfg = TIMEFRAME_CONFIG.get(style_name, {"interval": "1d", "period": "2y"})
    interval = tf_cfg["interval"]
    period = tf_cfg["period"]
    max_holding_bars = prof.get("max_holding_bars", 10)
    pt_factor = prof.get("pt_factor", 2.0)
    sl_factor = prof.get("sl_factor", 1.0)
    buy_thresh = prof["buy_threshold"]

    print(f"\n{'='*70}")
    print(f"監査実行: [{prof['name']}] (足種: {interval}, 期間: {period})")
    print(f"  動的ATRバリア倍率: TP = {pt_factor}*ATR, SL = {sl_factor}*ATR | 最長保有: {max_holding_bars} bars")
    print(f"{'='*70}")

    # 1. データ取得
    raw_df = fetch_historical_data(symbol, period=period, interval=interval)
    htf_df = None
    if interval in ["5m", "15m", "1h"]:
        htf_df = fetch_historical_data(symbol, period="5y", interval="1d")

    labeled_df, feature_cols = generate_features(
        raw_df,
        pt_factor=pt_factor,
        sl_factor=sl_factor,
        max_holding_days=max_holding_bars,
        htf_df=htf_df
    )
    labeled_df = labeled_df.dropna().copy()
    n_samples = len(labeled_df)
    print(f"[Step 1] サンプル数: {n_samples}, 特徴量数: {len(feature_cols)} (HTF統合: {'あり' if htf_df is not None else 'なし'})")

    # 2. Invariant 1: 特徴量 Point-in-Time 監査
    auditor = PointInTimeAuditor()
    audit_report = auditor.audit_features(labeled_df, feature_cols)
    if not audit_report["audit_passed"]:
        raise FeatureLeakageViolation(f"特徴量リークが検知されました: {audit_report}")
    print("  [Invariant 1] Point-in-Time 監査: 合格 (PASS) - 未来リーク相関 0 件")

    # 3. Invariant 2 & 3: Purged K-Fold with Embargo による完全 OOF 予測生成
    n_splits = 5
    pct_embargo = 0.01

    if "touch_time" in labeled_df.columns:
        t1 = pd.to_datetime(labeled_df["touch_time"])
    elif "target_holding_days" in labeled_df.columns:
        t1 = labeled_df.index + pd.to_timedelta(labeled_df["target_holding_days"].fillna(1).astype(int), unit="m")
    else:
        t1 = labeled_df.index

    cv = PurgedKFold(n_splits=n_splits, t1=pd.Series(t1, index=labeled_df.index), pct_embargo=pct_embargo)
    splits = list(cv.split(labeled_df[feature_cols], labeled_df["target_binary"]))

    X = labeled_df[feature_cols].values
    y = labeled_df["target_binary"].values

    oof_probs = np.zeros(n_samples)
    oof_folds = np.full(n_samples, -1)
    train_indices = []

    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "n_estimators": 80,
        "learning_rate": 0.03,
        "max_depth": 3,
        "num_leaves": 8,
        "min_child_samples": 20,
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
        total_samples=n_samples,
        fold_train_indices=train_indices
    )

    eval_df = labeled_df.copy()
    eval_df["pred_prob"] = oof_probs
    eval_df["_oof_fold"] = oof_folds
    eval_df = eval_df[eval_df["_oof_fold"] >= 0].copy()

    oof_container = StrictOOFContainer(eval_df, token)
    print(f"  [Invariant 2 & 3] Purged OOF トークン発行: Signature={token.signature[:12]}...")

    # 4. Invariant 4 & 5: ペシミスティック約定 ＆ Deflated Sharpe 検定
    pessimistic_engine = PessimisticExecutionEngine()
    guard = ZeroLeakageGuard(num_trials=len(STRATEGY_PROFILES))

    def simulate_strategy_execution(data: pd.DataFrame, use_dynamic: bool = True) -> dict:
        n = len(data)
        closes = data["Close"].values
        highs = data["High"].values
        lows = data["Low"].values
        atrs = data["atr_14"].values if "atr_14" in data.columns else np.zeros(n)
        probs = data["pred_prob"].values
        regimes = data["regime_state"].values if "regime_state" in data.columns else np.array(["NORMAL"] * n)
        htf_trends = data["htf_daily_trend"].values if "htf_daily_trend" in data.columns else np.zeros(n)
        friction = 0.0016

        trade_returns = []
        trades = []
        i = 0

        while i < n - 1:
            prob = probs[i]
            if prob >= buy_thresh:
                entry_price = closes[i]
                cur_atr = atrs[i]

                # 1. レジーム判定ゲート (CHOPPYレンジ相場遮断)
                if style_name in ["scalping", "day_trade"] and regimes[i] == "CHOPPY_RANGE":
                    i += 1
                    continue

                # 2. 上位足(HTF)トレンド整合ゲート (日足逆行買い遮断)
                if htf_trends[i] < 0:
                    i += 1
                    continue

                if use_dynamic and cur_atr > 0:
                    barriers = compute_strategy_barriers(entry_price, cur_atr, prof, position=1, barrier_type="dynamic")
                else:
                    barriers = compute_strategy_barriers(entry_price, cur_atr, prof, position=1, barrier_type="fixed")

                tp_price = barriers["take_profit"]
                sl_price = barriers["stop_loss"]

                # 3. 期待値フィルター (取引摩擦0.16%差引後EV <= 0 遮断)
                tp_dist = (tp_price - entry_price) / entry_price
                sl_dist = (entry_price - sl_price) / entry_price
                ev = prob * tp_dist - (1.0 - prob) * sl_dist - friction
                if ev <= 0:
                    i += 1
                    continue

                closed = False
                exit_price = entry_price
                exit_reason = "TIMEOUT"

                for hold_bar in range(1, min(max_holding_bars + 1, n - i)):
                    bar_idx = i + hold_bar
                    b_high = highs[bar_idx]
                    b_low = lows[bar_idx]
                    b_close = closes[bar_idx]

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
                    timeout_bar = min(i + max_holding_bars, n - 1)
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

    default_dsr = {
        "sharpe_ratio": 0.0,
        "deflated_sharpe_ratio": 0.0,
        "p_value": 1.0,
        "is_statistically_significant": False,
        "skewness": 0.0,
        "kurtosis": 3.0,
        "expected_max_sr": 0.0,
        "n_samples": 0,
        "num_trials_penalized": len(STRATEGY_PROFILES)
    }

    # 1. 動的ATRトリプルバリアでの実行
    res_dynamic = guard.verify_and_protect_backtest(
        container=oof_container,
        strategy_func=lambda d: simulate_strategy_execution(d, use_dynamic=True),
        features=feature_cols
    )
    dsr_dyn = res_dynamic.get("deflated_sharpe_analysis", default_dsr)

    # 2. 固定%バリアでの比較実行
    res_fixed = guard.verify_and_protect_backtest(
        container=oof_container,
        strategy_func=lambda d: simulate_strategy_execution(d, use_dynamic=False),
        features=feature_cols
    )
    dsr_fix = res_fixed.get("deflated_sharpe_analysis", default_dsr)

    print("  [Invariant 4 & 5] 厳格約定＆DSR過学習検定結果:")
    print(f"    ▶ 動的ATRバリア: 約定={res_dynamic['n_trades']}回 | 勝率={res_dynamic['win_rate_pct']:.1f}% | PF={res_dynamic['profit_factor']:.2f} | リターン={res_dynamic['total_return_pct']:+.2f}% | DSR={dsr_dyn['deflated_sharpe_ratio']:.4f} (p={dsr_dyn['p_value']:.4f})")
    print(f"    ▶ 固定%バリア  : 約定={res_fixed['n_trades']}回 | 勝率={res_fixed['win_rate_pct']:.1f}% | PF={res_fixed['profit_factor']:.2f} | リターン={res_fixed['total_return_pct']:+.2f}% | DSR={dsr_fix['deflated_sharpe_ratio']:.4f} (p={dsr_fix['p_value']:.4f})")
    print(f"    ▶ 過学習判定: {'[PASS] 統計的有意 (過学習なし)' if dsr_dyn['is_statistically_significant'] else '[REJECT] 統計的優位性未達'}")

    return {
        "style_name": prof["name"],
        "interval": interval,
        "period": period,
        "barrier_type": "dynamic_atr",
        "pt_factor": pt_factor,
        "sl_factor": sl_factor,
        "dynamic_atr_results": {
            "total_trades": res_dynamic["n_trades"],
            "win_rate_pct": round(res_dynamic["win_rate_pct"], 2),
            "profit_factor": round(res_dynamic["profit_factor"], 2),
            "total_return_pct": round(res_dynamic["total_return_pct"], 2),
            "sharpe_ratio": round(dsr_dyn["sharpe_ratio"], 2),
            "deflated_sharpe_ratio": round(dsr_dyn["deflated_sharpe_ratio"], 4),
            "p_value": round(dsr_dyn["p_value"], 4),
            "is_statistically_significant": dsr_dyn["is_statistically_significant"],
            "zero_leakage_certified": res_dynamic["zero_leakage_certified"]
        },
        "fixed_pct_results": {
            "total_trades": res_fixed["n_trades"],
            "win_rate_pct": round(res_fixed["win_rate_pct"], 2),
            "profit_factor": round(res_fixed["profit_factor"], 2),
            "total_return_pct": round(res_fixed["total_return_pct"], 2),
            "sharpe_ratio": round(dsr_fix["sharpe_ratio"], 2),
            "deflated_sharpe_ratio": round(dsr_fix["deflated_sharpe_ratio"], 4),
            "p_value": round(dsr_fix["p_value"], 4),
            "is_statistically_significant": dsr_fix["is_statistically_significant"]
        }
    }


def run_zero_leakage_audit():
    print("=" * 75)
    print("🚀 Zero-Leakage & Anti-Overfit System: 高頻度マルチタイムフレーム＆動的ATR厳格監査")
    print("=" * 75)

    all_audit_results = {}
    for style_name, prof in STRATEGY_PROFILES.items():
        try:
            res = audit_single_strategy(style_name, prof, symbol="GC=F")
            all_audit_results[style_name] = res
        except Exception as e:
            print(f"[{style_name}] 監査エラー: {e}")
            all_audit_results[style_name] = {"error": str(e)}

    # 保存
    out_path = Path("data/consortium/zero_leakage_audit_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_audit_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*75}")
    print(f"[Zero-Leakage 監査完了] 監査証明書 JSON 保存先: {out_path}")
    print(f"{'='*75}")
    return all_audit_results


if __name__ == "__main__":
    run_zero_leakage_audit()
