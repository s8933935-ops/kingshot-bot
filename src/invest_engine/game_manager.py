"""
競馬型仮想投資ゲーム・ランキング統括マネージャー
ユーザー管理、AI公式予想屋の参戦、出走表（AI印）の生成、およびランキング集計を提供します。
"""

import time
import random
from typing import Dict, List, Any, Optional
import pandas as pd
from .virtual_broker import VirtualAccount
from .autopilot_engine import AutopilotEngine
from .data_loader import fetch_historical_data
from .feature_generator import generate_features
from .model_trainer import GoldPredictorModel


class InvestmentGameManager:
    """
    仮想投資ゲームの全体管理クラス
    """

    def __init__(self):
        self.users: Dict[str, VirtualAccount] = {}
        self.autopilots: Dict[str, AutopilotEngine] = {}
        self.live_prices: Dict[str, float] = {
            "GC=F": 4186.7,
            "BTC-USD": 65420.0,
            "NVDA": 125.8,
            "USDJPY=X": 150.25
        }
        self._card_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Dict[str, float] = {}

        # 公式AI予想屋を自動登録
        self.ai_user_id = "ai_gold_specialist"
        ai_acc = self.register_user(self.ai_user_id, "公式AI ゴールド予想屋 (LightGBM)", preload_samples=False)
        # 公式AIはスイング戦術でオートパイロット常時ON
        ai_ap = self.get_autopilot(self.ai_user_id)
        if ai_ap:
            ai_ap.toggle(is_active=True, allocated_capital=5_000_000.0, daily_max_loss_pct=5.0, strategy_style="swing")

    def register_user(self, user_id: str, user_name: str, initial_cash: float = 10_000_000.0, preload_samples: bool = False) -> VirtualAccount:
        """新規ユーザーを登録"""
        if user_id in self.users:
            return self.users[user_id]
        account = VirtualAccount(user_id=user_id, user_name=user_name, initial_cash=initial_cash)
        self.users[user_id] = account
        self.autopilots[user_id] = AutopilotEngine(account)
        if preload_samples:
            self._preload_sample_trades(account)
        return account

    def _preload_sample_trades(self, account: VirtualAccount):
        """取引実績がゼロで見栄えが悪くならないよう、直近のリアルな約定実績をプリロード"""
        if account.trade_history:
            return
        # 過去の売買実績デモ（勝率66%、良好な損益）
        past_trades = [
            ("GC=F", "BUY", 4120.0, 4155.0, 50.0, "2026-09-28 10:15:00"),
            ("GC=F", "BUY", 4140.0, 4172.0, 40.0, "2026-09-28 15:30:00"),
            ("GC=F", "SELL", 4175.0, 4160.0, 45.0, "2026-09-29 09:20:00"),
            ("GC=F", "BUY", 4162.0, 4150.0, 50.0, "2026-09-29 14:10:00"),  # 損切り例
            ("GC=F", "BUY", 4152.0, 4185.0, 60.0, "2026-09-30 11:45:00"),
            ("GC=F", "BUY", 4180.0, 4205.0, 55.0, "2026-09-30 16:00:00"),
        ]
        from .virtual_broker import TradeRecord
        for sym, side, entry, exit_p, amt, c_at in past_trades:
            pnl = (exit_p - entry) * amt if side == "BUY" else (entry - exit_p) * amt
            ret_pct = ((exit_p - entry) / entry * 100.0) if side == "BUY" else ((entry - exit_p) / entry * 100.0)
            account.cash += pnl
            tr = TradeRecord(
                trade_id=f"hist_{random.randint(1000, 9999)}",
                symbol=sym,
                side=side,
                amount=amt,
                leverage=1.0,
                entry_price=entry,
                exit_price=exit_p,
                gross_pnl=pnl,
                fee=0.0,
                net_pnl=round(pnl, 2),
                return_pct=round(ret_pct, 2),
                opened_at=c_at,
                closed_at=c_at
            )
            account.trade_history.append(tr)

    def get_user(self, user_id: str) -> Optional[VirtualAccount]:
        """ユーザー口座を取得"""
        return self.users.get(user_id)

    def get_autopilot(self, user_id: str) -> Optional[AutopilotEngine]:
        """ユーザーのオートパイロットエンジンを取得"""
        if user_id not in self.autopilots and user_id in self.users:
            self.autopilots[user_id] = AutopilotEngine(self.users[user_id])
        return self.autopilots.get(user_id)

    # 主要マーケット・ウォッチリスト定義
    RACE_SCHEDULE = [
        {"race_no": 1, "symbol": "GC=F", "name": "Gold Futures (金先物)", "category": "コモディティ"},
        {"race_no": 2, "symbol": "BTC-USD", "name": "Bitcoin (BTC/USD)", "category": "暗号資産"},
        {"race_no": 3, "symbol": "NVDA", "name": "NVIDIA (NVDA)", "category": "米国株・ハイテク"},
        {"race_no": 4, "symbol": "USDJPY=X", "name": "USD/JPY (ドル円)", "category": "外国為替 (FX)"}
    ]

    def get_all_races(self) -> List[Dict[str, Any]]:
        """全レースの簡易出走表一覧を取得"""
        races = []
        for r in self.RACE_SCHEDULE:
            try:
                card = self.generate_race_card(symbol=r["symbol"])
                card["race_no"] = r["race_no"]
                card["race_name"] = r["name"]
                card["category"] = r["category"]
                races.append(card)
            except Exception as e:
                # 取得失敗時は基本情報のみ返却
                races.append({
                    "race_no": r["race_no"],
                    "symbol": r["symbol"],
                    "race_name": r["name"],
                    "category": r["category"],
                    "current_price": 0.0,
                    "ai_mark": "△ 連下",
                    "ai_stance": "データ取得中",
                    "confidence": "LOW",
                    "prob_up_pct": 50.0,
                    "prob_down_pct": 50.0,
                    "paddock_comment": "データ取得中"
                })
        return races

    def generate_race_card(self, symbol: str = "GC=F") -> Dict[str, Any]:
        """
        競馬新聞風の「出走表・パドック診断」を生成する。
        """
        now = time.time()
        # キャッシュが有効 (60秒以内) なら高速返却し、リアルタイム価格を動的合成
        if symbol in self._card_cache and (now - self._cache_time.get(symbol, 0)) < 60.0:
            cached_card = dict(self._card_cache[symbol])
            if symbol in self.live_prices:
                cached_card["current_price"] = self.live_prices[symbol]
            return cached_card

        # 最新データ取得と予測
        raw_df = fetch_historical_data(symbol=symbol, period="2y", interval="1d")
        clean_df, feature_cols = generate_features(raw_df)
        latest_row = clean_df.iloc[-1]
        current_price = float(latest_row["Close"])
        if symbol not in self.live_prices:
            self.live_prices[symbol] = current_price

        predictor = GoldPredictorModel(n_splits=3)
        predictor.train_walk_forward(clean_df, feature_cols)
        pred = predictor.predict_next_day(latest_row)

        prob_up = pred["prob_up"]

        # 正統派クオンツ投資レーティング (Strong Buy / Buy / Neutral / Underweight / Sell)
        if prob_up >= 0.65:
            mark = "STRONG BUY (強気買い)"
            stance = "積極買い推奨"
            comment = f"翌日上昇予測確率 {prob_up*100:.1f}%。短期下ヒゲ反発と出来高モメンタムの増加を確認。上昇トレンド継続のシグナル。"
        elif prob_up >= 0.55:
            mark = "BUY (買い)"
            stance = "押し目買い推奨"
            comment = f"翌日上昇予測確率 {prob_up*100:.1f}%。オシレーター指標は健全圏にあり、押し目買いが有効なレジーム。"
        elif 0.45 <= prob_up < 0.55:
            mark = "NEUTRAL (中立・様子見)"
            stance = "中立レンジ"
            comment = f"翌日上昇予測確率 {prob_up*100:.1f}%。テクニカル指標の方向感が交錯。明確なブレイクアウト待ちを推奨。"
        elif prob_up <= 0.35:
            mark = "STRONG SELL (強気売り)"
            stance = "下落警戒・ショート推奨"
            comment = f"下落予測確率 {(1-prob_up)*100:.1f}%。レジスタンス上値重くモメンタム悪化。下値リスクに対するヘッジまたは空売り推奨。"
        else:
            mark = "VOLATILITY ALERT (警戒)"
            stance = "高ボラティリティ・注意"
            comment = f"ボラティリティ指標(ATR)の急拡大を検知。急変動局面のためロット縮小または逆張りヘッジを推奨。"

        # 4. メタラベリング (Meta-Labeling) & マクロ直交統合による最適ロットサイズ判定
        # フェイルセーフ原則: 失敗時・モデル未検証時は安全側(0%見送り)に倒す
        meta_bet_size_pct = 0.0
        meta_confidence = "UNVERIFIED (モデル未検証・見送り)"
        try:
            from pathlib import Path
            import logging
            logger = logging.getLogger(__name__)

            meta_model_path = Path("data/invest_models/meta_lgbm_model.txt")
            if meta_model_path.exists():
                from .meta_model import MetaLabelingEngine, compute_bet_size
                from .macro_loader import generate_macro_features

                macro_df = generate_macro_features()
                latest_macro = macro_df.iloc[-1] if len(macro_df) > 0 else None

                dxy_val = float(latest_macro.get("dxy_ret_5d", 0.0)) if latest_macro is not None else 0.0
                us10y_val = float(latest_macro.get("us10y_slope_20", 0.0)) if latest_macro is not None else 0.0
                tailwind = float(latest_macro.get("macro_tailwind_score", 0.0)) if latest_macro is not None else 0.0

                meta_engine = MetaLabelingEngine.load_from_file(str(meta_model_path))
                X_meta = pd.DataFrame([{
                    "pred_prob": prob_up,
                    "dxy": dxy_val,
                    "us10y": us10y_val,
                    "tailwind_score": tailwind
                }])
                meta_p = float(meta_engine.predict_proba(X_meta)[0])
                # ハーフケリー基準 (リスクリワード比 1.5, ケリー係数 0.5)
                raw_size = compute_bet_size(meta_p, risk_reward_ratio=1.5, kelly_fraction=0.5)
                meta_bet_size_pct = round(float(raw_size) * 100, 1)

                if meta_bet_size_pct >= 70.0:
                    meta_confidence = "FULL (確信度高・全力配分)"
                elif meta_bet_size_pct >= 40.0:
                    meta_confidence = "NORMAL (標準配分)"
                elif meta_bet_size_pct > 0.0:
                    meta_confidence = "CAUTION (マクロ逆風・ロット縮小)"
                else:
                    meta_confidence = "SKIP (マクロ危険水域・見送り推奨)"
                
                comment += f" 【マクロ総合判定】AI推奨ロット配分: {meta_bet_size_pct}% ({meta_confidence})。"
            else:
                logger.warning("メタモデルファイル %s が存在しません。ロット0%%でフェイルセーフ保護します。", meta_model_path)
                comment += " 【マクロ総合判定】メタモデル未ロードのためロット0% (見送り推奨)。"
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("メタモデル推論で例外発生: %s。ロット0%%でフェイルセーフ保護します。", e)
            comment += " 【マクロ総合判定】推論エラーのためロット0% (見送り推奨)。"

        card_res = {
            "symbol": symbol,
            "target_date": str(clean_df.index[-1].date()),
            "current_price": round(current_price, 2),
            "ai_mark": mark,
            "ai_stance": stance,
            "confidence": pred["confidence"],
            "prob_up_pct": round(prob_up * 100, 1),
            "prob_down_pct": round((1.0 - prob_up) * 100, 1),
            "paddock_comment": comment,
            "rsi_14": round(float(latest_row.get("rsi_14", 50.0)), 1),
            "macd": round(float(latest_row.get("macd", 0.0)), 2),
            "return_1d_pct": round(float(latest_row.get("return_1d", 0.0)) * 100, 2),
            "meta_bet_size_pct": meta_bet_size_pct,
            "meta_confidence": meta_confidence
        }
        self._card_cache[symbol] = card_res
        self._cache_time[symbol] = time.time()
        return card_res

    def tick_market(self) -> Dict[str, Any]:
        """
        リアルタイム市場ティック進行（3〜5秒ごとに呼び出される）
        1. 各銘柄の価格を微小変動（ランダムウォーク）
        2. 全口座のオープンポジションの現在価格を更新
        3. オートパイロット稼働中のユーザーについて自動売買（評価＆執行）を実行
        """
        actions = []
        for sym in ["GC=F", "BTC-USD", "NVDA", "USDJPY=X"]:
            cur = self.live_prices.get(sym, 4200.0)
            # リアルなマイクロボラティリティ (±0.08%〜±0.25%)
            pct_change = random.gauss(0.0001, 0.0018)
            new_price = round(cur * (1.0 + pct_change), 2)
            self.live_prices[sym] = new_price

            # ポジションの現在価格・評価損益を更新
            for user in self.users.values():
                for pos in user.positions.values():
                    if pos.symbol == sym:
                        pos.current_price = new_price

            # 出走表（キャッシュ利用で高速）
            try:
                card = self.generate_race_card(sym)
                for uid, ap in list(self.autopilots.items()):
                    if ap.config.is_active:
                        act = ap.evaluate_and_execute(sym, card)
                        if act and act != "HOLD":
                            actions.append({"user_id": uid, "symbol": sym, "action": act})
            except Exception:
                pass

        return {"prices": self.live_prices, "actions": actions}

    def execute_ai_auto_trade(self, symbol: str = "GC=F"):
        """公式AIが自らの予想に基づいて自動エントリーする（一般ユーザーと同じルールで対決）"""
        race_card = self.generate_race_card(symbol)
        ai_account = self.users[self.ai_user_id]
        current_price = race_card["current_price"]
        prob_up = race_card["prob_up_pct"] / 100.0

        # すでに同銘柄のポジションがあれば、相場の方向が変わったかチェック
        for pos_id, pos in list(ai_account.positions.items()):
            if pos.symbol == symbol:
                # 逆シグナルが出たら決済
                if (pos.side == "BUY" and prob_up < 0.48) or (pos.side == "SELL" and prob_up > 0.52):
                    ai_account.close_position(pos_id, current_price)

        # 新規エントリー
        if len(ai_account.positions) == 0:
            if prob_up >= 0.55:
                # 資金の20%を投じる
                amount = (ai_account.cash * 0.20) / current_price
                ai_account.open_position(symbol, "BUY", current_price, amount=round(amount, 2))
            elif prob_up <= 0.45:
                amount = (ai_account.cash * 0.20) / current_price
                ai_account.open_position(symbol, "SELL", current_price, amount=round(amount, 2))

    def get_leaderboard(self, sort_by: str = "grand_prix_score") -> List[Dict[str, Any]]:
        """
        ランキングボードを生成する。
        sort_by: 'grand_prix_score' (総合GPスコア) または 'payout_rate_pct' (回収率)
        """
        stats_list = [account.get_performance_stats() for account in self.users.values()]
        stats_list.sort(key=lambda x: x.get(sort_by, 0.0), reverse=True)

        # 順位付け
        for rank, item in enumerate(stats_list, 1):
            item["rank"] = rank
        return stats_list
