"""
金先物（Gold Futures: GC=F）予測・バックテスト実行パイプライン
業界標準の投資指標（CAGR, Win Rate, Profit Factor, Risk-Reward, Max Drawdown, Sharpe, Calmar）を出力します。
"""

import sys
from pathlib import Path

# Windows UTF-8 出力対策
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.invest_engine.data_loader import fetch_historical_data
from src.invest_engine.feature_generator import generate_features
from src.invest_engine.model_trainer import GoldPredictorModel
from src.invest_engine.backtester import run_backtest


def main():
    symbol = "GC=F"
    period = "5y"
    interval = "1d"

    print("=" * 72)
    print(f"  [Quant Performance Report] Gold Futures Engine ({symbol})")
    print("=" * 72)

    # 1. データ取得
    print(f"\n[1/5] Fetching Market Data ({symbol}, Period: {period})...")
    raw_df = fetch_historical_data(symbol=symbol, period=period, interval=interval)
    print(f"  -> Bars Loaded: {len(raw_df)} ({raw_df.index[0].date()} ~ {raw_df.index[-1].date()})")
    print(f"  -> Latest Close: ${raw_df['Close'].iloc[-1]:.2f}")

    # 2. 特徴量生成
    print("\n[2/5] Feature Engineering (31 Momentum & Volatility Signals)...")
    clean_df, feature_cols = generate_features(raw_df)
    print(f"  -> Features Ready: {len(feature_cols)} features over {len(clean_df)} trading days")

    # 3. モデル学習
    print("\n[3/5] Walk-Forward LightGBM Training (Purged TimeSeriesSplit)...")
    predictor = GoldPredictorModel(n_splits=5)
    results = predictor.train_walk_forward(clean_df, feature_cols)

    print(f"  -> Out-of-Fold Accuracy:  {results['overall_accuracy'] * 100:.2f}%")
    print(f"  -> Model Precision:       {results['precision'] * 100:.2f}%")

    print("\n  [Top 5 Alpha Features]")
    for rank, item in enumerate(results["feature_importance_top10"][:5], 1):
        print(f"    {rank}. {item['feature']:<20} (Score: {item['importance']:.2f})")

    # 4. バックテスト
    print("\n[4/5] Running Realistic Backtest (Deducting Fees & Slippage)...")
    backtest_res = run_backtest(
        results["eval_df"],
        threshold_long=0.52,
        threshold_short=0.48,
        fee_pct=0.0003,
        allow_short=True
    )
    m = backtest_res["metrics"]

    print("\n" + "=" * 72)
    print("  ★ 業界標準パフォーマンス指標（TradingView / QuantConnect 準拠）")
    print("=" * 72)
    print(f"  ■ 検証期間 (Period):         {m['period_start']} ~ {m['period_end']} ({m['total_days']}日 / 約{m['years']}年)")
    print(f"  ■ 総トレード回数 (Trades):   {m['total_trades']} 回")
    print("-" * 72)
    print("  【収益性 (Profitability)】")
    print(f"    ・累計リターン (Total Return):  {m['total_return_pct']:+}%")
    print(f"    ・元本回収率 (Payout Rate):     {m['payout_rate_pct']}%  (100万円が{m['payout_rate_pct']:.1f}万円に)")
    print(f"    ・CAGR (年平均成長率・実質年利): {m['cagr_pct']:+}% / 年")
    print("-" * 72)
    print("  【勝率・取引効率 (Trade Efficiency)】")
    print(f"    ・勝率 (Win Rate):              {m['win_rate_pct']}%  (勝ちトレード比率)")
    print(f"    ・プロフィットファクター (PF):   {m['profit_factor']}  (総利益 ÷ 総損失: 1.0以上で黒字)")
    print(f"    ・リスクリワード比 (Payoff Ratio):{m['risk_reward_ratio']}  (平均利益 ÷ 平均損失)")
    print("-" * 72)
    print("  【リスク・耐久性 (Risk & Resilience)】")
    print(f"    ・最大ドローダウン (Max Drawdown): {m['max_drawdown_pct']}%  (ピークからの最大資産下落幅)")
    print(f"    ・シャープレシオ (Sharpe Ratio):   {m['sharpe_ratio']}  (価格変動に対する運用効率)")
    print(f"    ・カルマーレシオ (Calmar Ratio):   {m['calmar_ratio']}  (年平均成長率 ÷ 最大ドローダウン)")
    print("=" * 72)

    # 5. 最新予測
    print("\n[5/5] Generating Next Session Signal...")
    latest_bar = clean_df.iloc[-1]
    prediction = predictor.predict_next_day(latest_bar)

    print("=" * 72)
    print(f"  >>> 次回セッション 金先物 予測シグナル <<<")
    print(f"  基準データ日:      {clean_df.index[-1].date()}")
    print(f"  推奨ポジション:    {prediction['signal']}")
    print(f"  確信度 (Confidence):{prediction['confidence']}")
    print(f"  上昇予測確率 (UP):  {prediction['prob_up'] * 100:.2f}%")
    print(f"  下落予測確率 (DN):  {prediction['prob_down'] * 100:.2f}%")
    print("=" * 72)

    model_path = PROJECT_ROOT / "data" / "invest_models" / "gold_lgbm_model.txt"
    predictor.save(model_path)


if __name__ == "__main__":
    main()
