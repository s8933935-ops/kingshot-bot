"""
5大戦術（スキャルピング、デイトレ、スイング、中期トレンド、長期投資）
包括的バックテスト＆性能評価スクリプト

過去のヒストリカルデータと予測シグナル、およびHigh/Lowバー内価格変動に基づき、
各戦術の利確・損切り・反転決済ロジックを忠実に再現して勝率と回収率を厳密に測定します。
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows cp932対策
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.invest_engine.data_loader import fetch_historical_data
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.model_trainer import GoldPredictorModel
from src.invest_engine.autopilot_engine import STRATEGY_PROFILES
from src.invest_engine.macro_loader import generate_macro_features
from src.invest_engine.meta_model import MetaLabelingEngine, compute_bet_size


def run_strategy_backtest(df: pd.DataFrame, strategy_key: str, profile: dict, meta_engine: MetaLabelingEngine = None, fee_rate: float = 0.0004) -> dict:
    """
    指定された戦術プロファイルに従って時系列バックテストを実行
    """
    tp_pct = profile["take_profit_pct"] / 100.0
    sl_pct = abs(profile["stop_loss_pct"]) / 100.0  # 正の値として扱う
    buy_th = profile["buy_threshold"]
    sell_th = profile["sell_threshold"]
    rev_buy = profile["reversal_buy_exit"]
    rev_sell = profile["reversal_sell_exit"]
    lev = profile["max_leverage"]
    capital_ratio = profile["base_capital_ratio"]

    initial_capital = 10_000_000.0
    current_cash = initial_capital
    equity_curve = [initial_capital]

    trades = []
    current_pos = None  # {'side': 'BUY'/'SELL', 'entry_price': float, 'amount': float, 'entry_idx': int, 'meta_size': float}

    for i in range(len(df)):
        row = df.iloc[i]
        open_p = float(row["Open"])
        high_p = float(row["High"])
        low_p = float(row["Low"])
        close_p = float(row["Close"])
        prob_up = float(row["pred_prob"])
        meta_size = float(row.get("meta_size", 1.0))

        # 1. 既存ポジションのエグジット判定
        if current_pos is not None:
            side = current_pos["side"]
            entry_p = current_pos["entry_price"]
            amt = current_pos["amount"]
            closed = False
            exit_p = close_p
            exit_reason = ""

            if side == "BUY":
                # Highで利確判定
                if (high_p - entry_p) / entry_p >= tp_pct:
                    exit_p = entry_p * (1.0 + tp_pct)
                    closed = True
                    exit_reason = "TAKE_PROFIT"
                # Lowで損切り判定
                elif (entry_p - low_p) / entry_p >= sl_pct:
                    exit_p = entry_p * (1.0 - sl_pct)
                    closed = True
                    exit_reason = "STOP_LOSS"
                # 反転手仕舞い判定
                elif prob_up < rev_buy:
                    exit_p = close_p
                    closed = True
                    exit_reason = "REVERSAL"

                if closed:
                    gross_pnl = (exit_p - entry_p) * amt * lev
                    fee = (entry_p + exit_p) * amt * lev * fee_rate
                    net_pnl = gross_pnl - fee
                    ret_pct = ((exit_p - entry_p) / entry_p) * lev * 100.0
                    current_cash += net_pnl
                    trades.append({
                        "side": side,
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "net_pnl": net_pnl,
                        "return_pct": ret_pct,
                        "holding_bars": i - current_pos["entry_idx"],
                        "reason": exit_reason
                    })
                    current_pos = None

            elif side == "SELL":
                # Lowで利確判定
                if (entry_p - low_p) / entry_p >= tp_pct:
                    exit_p = entry_p * (1.0 - tp_pct)
                    closed = True
                    exit_reason = "TAKE_PROFIT"
                # Highで損切り判定
                elif (high_p - entry_p) / entry_p >= sl_pct:
                    exit_p = entry_p * (1.0 + sl_pct)
                    closed = True
                    exit_reason = "STOP_LOSS"
                # 反転手仕舞い判定
                elif prob_up > rev_sell:
                    exit_p = close_p
                    closed = True
                    exit_reason = "REVERSAL"

                if closed:
                    gross_pnl = (entry_p - exit_p) * amt * lev
                    fee = (entry_p + exit_p) * amt * lev * fee_rate
                    net_pnl = gross_pnl - fee
                    ret_pct = ((entry_p - exit_p) / entry_p) * lev * 100.0
                    current_cash += net_pnl
                    trades.append({
                        "side": side,
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "net_pnl": net_pnl,
                        "return_pct": ret_pct,
                        "holding_bars": i - current_pos["entry_idx"],
                        "reason": exit_reason
                    })
                    current_pos = None

        # 2. 新規エントリー判定（ノーポジション時）
        if current_pos is None and meta_size > 0.0:
            trade_capital = current_cash * capital_ratio * meta_size
            amt = trade_capital / open_p

            if prob_up >= buy_th:
                current_pos = {
                    "side": "BUY",
                    "entry_price": open_p,
                    "amount": amt,
                    "entry_idx": i,
                    "meta_size": meta_size
                }
            elif prob_up <= sell_th:
                current_pos = {
                    "side": "SELL",
                    "entry_price": open_p,
                    "amount": amt,
                    "entry_idx": i,
                    "meta_size": meta_size
                }

        # 資産推移記録
        unrealized = 0.0
        if current_pos is not None:
            mult = 1.0 if current_pos["side"] == "BUY" else -1.0
            unrealized = (close_p - current_pos["entry_price"]) * current_pos["amount"] * mult * lev
        equity_curve.append(current_cash + unrealized)

    # パフォーマンス集計
    total_trades = len(trades)
    if total_trades > 0:
        trades_df = pd.DataFrame(trades)
        wins = trades_df[trades_df["net_pnl"] > 0]
        losses = trades_df[trades_df["net_pnl"] <= 0]
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = (n_wins / total_trades) * 100.0
        total_pnl = trades_df["net_pnl"].sum()
        gross_profit = wins["net_pnl"].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses["net_pnl"].sum()) if len(losses) > 0 else 1e-6
        profit_factor = gross_profit / gross_loss
        avg_win = wins["net_pnl"].mean() if len(wins) > 0 else 0.0
        avg_loss = abs(losses["net_pnl"].mean()) if len(losses) > 0 else 1e-6
        risk_reward = avg_win / avg_loss
        avg_bars = trades_df["holding_bars"].mean()
    else:
        win_rate = 0.0
        total_pnl = 0.0
        profit_factor = 0.0
        risk_reward = 0.0
        avg_bars = 0.0

    eq_arr = np.array(equity_curve)
    cum_max = np.maximum.accumulate(eq_arr)
    drawdowns = (eq_arr - cum_max) / cum_max
    max_dd = abs(float(drawdowns.min())) * 100.0

    total_return_pct = ((equity_curve[-1] - initial_capital) / initial_capital) * 100.0
    payout_rate_pct = 100.0 + total_return_pct  # 競馬風回収率（100%基準）

    return {
        "strategy": strategy_key,
        "name": profile["name"],
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 2),
        "payout_rate_pct": round(payout_rate_pct, 2),
        "total_return_pct": round(total_return_pct, 2),
        "total_pnl": round(total_pnl, 0),
        "profit_factor": round(profit_factor, 2),
        "risk_reward_ratio": round(risk_reward, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_holding_bars": round(avg_bars, 1),
        "final_equity": round(equity_curve[-1], 0)
    }


def main():
    print("=" * 75)
    print(" 🚀 5大戦術（スタイル別）クオンツ・バックテスト＆性能評価 実行中")
    print("=" * 75)

    symbol = "GC=F"
    print(f"📊 データ取得中: {symbol} (過去2年・日足データ)...")
    raw_df = fetch_historical_data(symbol=symbol, period="2y", interval="1d")
    clean_df, feature_cols = generate_features(raw_df)

    print("🧠 一次モデル（LightGBM）ウォークフォワード予測生成中...")
    predictor = GoldPredictorModel(n_splits=3)
    cv_scores = predictor.train_walk_forward(clean_df, feature_cols)

    # テスト期間（直近1年）の予測確率を生成
    probs = []
    for idx in range(len(clean_df)):
        row = clean_df.iloc[idx]
        res = predictor.predict_next_day(row)
        probs.append(res["prob_up"])

    clean_df["pred_prob"] = probs

    # メタラベリングモデルのロード（存在する場合）
    meta_model_path = Path("data/invest_models/meta_lgbm_model.txt")
    meta_engine = None
    if meta_model_path.exists():
        try:
            meta_engine = MetaLabelingEngine.load_from_file(str(meta_model_path))
            print("✅ メタラベリング・二次モデルをロードしました。")
            macro_df = generate_macro_features()
            # 日時結合
            merged_macro = clean_df.index.to_frame().merge(macro_df, left_index=True, right_index=True, how="left").ffill().bfill()
            X_meta = pd.DataFrame({
                "pred_prob": clean_df["pred_prob"],
                "dxy": merged_macro.get("dxy_ret_5d", 0.0),
                "us10y": merged_macro.get("us10y_slope_20", 0.0),
                "tailwind_score": merged_macro.get("macro_tailwind_score", 0.0)
            })
            meta_probs = meta_engine.predict_proba(X_meta)
            meta_sizes = [compute_bet_size(p, risk_reward_ratio=1.5, kelly_fraction=0.5) for p in meta_probs]
            clean_df["meta_size"] = meta_sizes
        except Exception as e:
            print(f"⚠️ メタモデル適用エラー: {e}。通常サイズ(1.0)を使用します。")
            clean_df["meta_size"] = 1.0
    else:
        clean_df["meta_size"] = 1.0

    # バックテスト対象期間: 直近250営業日
    test_df = clean_df.iloc[-250:].copy()

    results = []
    for strat_key, profile in STRATEGY_PROFILES.items():
        res = run_strategy_backtest(test_df, strat_key, profile)
        results.append(res)

    print("\n" + "=" * 75)
    print(" 🏆 【5大戦術 バックテスト評価レポート（直近250営業日・金先物 GC=F）】")
    print("=" * 75)
    print(f"{'戦術名':<26} | {'勝率':>7} | {'回収率':>8} | {'PF':>6} | {'RR比':>6} | {'最大DD':>7} | {'取引数':>6}")
    print("-" * 75)

    for r in results:
        print(f"{r['name']:<24} | {r['win_rate_pct']:>6.1f}% | {r['payout_rate_pct']:>7.1f}% | {r['profit_factor']:>6.2f} | {r['risk_reward_ratio']:>6.2f} | {r['max_drawdown_pct']:>6.2f}% | {r['total_trades']:>6}回")

    print("=" * 75)

    # 結果をJSONとして保存
    import json
    out_path = Path("data/consortium/strategy_backtest_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 結果を保存しました: {out_path}")


if __name__ == "__main__":
    main()
