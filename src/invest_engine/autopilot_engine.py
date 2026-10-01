"""
AIオートパイロット（短期自動売買お任せ運用）エンジン
フェイルセーフ安全装置（日次最大許容損失ストップ、レバレッジ上限ガード、緊急全決済ボタン、透明な思考ログ）を備えた自動売買システム。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from .virtual_broker import VirtualAccount


# 戦術（トレードスタイル）プロファイル定義（動的ATRトリプルバリア対応）
STRATEGY_PROFILES: Dict[str, Dict[str, Any]] = {
    "scalping": {
        "name": "スキャルピング (秒〜分・超短期高頻度)",
        "barrier_type": "dynamic",
        "pt_factor": 2.0,           # 2.0 * ATR
        "sl_factor": 1.0,           # 1.0 * ATR
        "default_interval": "5m",
        "max_holding_bars": 12,     # 5m x 12 = 1時間
        "take_profit_pct": 0.4,
        "stop_loss_pct": -0.2,
        "buy_threshold": 0.55,
        "sell_threshold": 0.45,
        "reversal_buy_exit": 0.50,
        "reversal_sell_exit": 0.50,
        "base_capital_ratio": 0.15,
        "max_leverage": 5.0,
    },
    "day_trade": {
        "name": "デイトレード (日中短期・波乗り)",
        "barrier_type": "dynamic",
        "pt_factor": 2.5,           # 2.5 * ATR
        "sl_factor": 1.2,           # 1.2 * ATR
        "default_interval": "15m",
        "max_holding_bars": 16,     # 15m x 16 = 4時間
        "take_profit_pct": 1.2,
        "stop_loss_pct": -0.6,
        "buy_threshold": 0.58,
        "sell_threshold": 0.42,
        "reversal_buy_exit": 0.48,
        "reversal_sell_exit": 0.52,
        "base_capital_ratio": 0.20,
        "max_leverage": 3.0,
    },
    "swing": {
        "name": "スイングトレード (数日〜数週間・中期波乗り)",
        "barrier_type": "dynamic",
        "pt_factor": 3.0,           # 3.0 * ATR
        "sl_factor": 1.5,           # 1.5 * ATR
        "default_interval": "1h",
        "max_holding_bars": 40,     # 1h x 40 ≈ 5-7営業日
        "take_profit_pct": 3.5,
        "stop_loss_pct": -1.8,
        "buy_threshold": 0.62,
        "sell_threshold": 0.38,
        "reversal_buy_exit": 0.45,
        "reversal_sell_exit": 0.55,
        "base_capital_ratio": 0.25,
        "max_leverage": 2.0,
    },
    "medium_term": {
        "name": "中期トレンド (数週間〜数ヶ月・マクロ重視)",
        "barrier_type": "dynamic",
        "pt_factor": 3.5,           # 3.5 * ATR
        "sl_factor": 1.8,           # 1.8 * ATR
        "default_interval": "1d",
        "max_holding_bars": 30,     # 30営業日 ≈ 1.5ヶ月
        "take_profit_pct": 8.0,
        "stop_loss_pct": -3.5,
        "buy_threshold": 0.65,
        "sell_threshold": 0.35,
        "reversal_buy_exit": 0.42,
        "reversal_sell_exit": 0.58,
        "base_capital_ratio": 0.30,
        "max_leverage": 1.5,
    },
    "long_term": {
        "name": "長期投資 (数ヶ月〜数年・資産形成・ハーフケリー)",
        "barrier_type": "dynamic",
        "pt_factor": 4.0,           # 4.0 * ATR
        "sl_factor": 2.0,           # 2.0 * ATR
        "default_interval": "1d",
        "max_holding_bars": 90,     # 90営業日
        "take_profit_pct": 20.0,
        "stop_loss_pct": -8.0,
        "buy_threshold": 0.68,
        "sell_threshold": 0.32,
        "reversal_buy_exit": 0.40,
        "reversal_sell_exit": 0.60,
        "base_capital_ratio": 0.40,
        "max_leverage": 1.0,
    }
}


def compute_strategy_barriers(
    entry_price: float,
    current_atr: float,
    profile_or_pt: Any,
    sl_factor_or_pct: Optional[float] = None,
    position: int = 1,
    barrier_type: Optional[str] = None
) -> Dict[str, float]:
    """
    動的ATRトリプルバリアまたは固定%に基づいて利確・損切りのトリガー価格を計算する。

    Parameters:
    - entry_price: エントリー価格
    - current_atr: 現在のATR（価格単位）
    - profile_or_pt: 戦術辞書プロファイル、または直接のpt_factor / take_profit_pct
    - sl_factor_or_pct: 直接指定時のsl_factor / stop_loss_pct
    - position: 1 (LONG) または -1 (SHORT)
    - barrier_type: 'dynamic' または 'fixed' (指定時はプロファイルより優先)

    Returns:
    - Dict[str, float]: {"take_profit": tp_price, "stop_loss": sl_price}
    """
    if isinstance(profile_or_pt, dict):
        prof = profile_or_pt
        b_type = barrier_type or prof.get("barrier_type", "dynamic")
        pt_factor = float(prof.get("pt_factor", 2.0))
        sl_factor = float(prof.get("sl_factor", 1.0))
        tp_pct = abs(float(prof.get("take_profit_pct", 1.0)))
        sl_pct = abs(float(prof.get("stop_loss_pct", 0.5)))
        ratio_tp = tp_pct / 100.0
        ratio_sl = sl_pct / 100.0
    else:
        b_type = barrier_type or ("dynamic" if current_atr > 0 else "fixed")
        pt_factor = float(profile_or_pt)
        sl_factor = float(sl_factor_or_pct) if sl_factor_or_pct is not None else 1.0
        tp_pct = float(profile_or_pt)
        sl_pct = float(sl_factor_or_pct) if sl_factor_or_pct is not None else 0.5
        # 0.1以上なら百分率 (例: 0.4% -> 0.004, 2.0% -> 0.02)
        ratio_tp = (tp_pct / 100.0) if tp_pct >= 0.1 else tp_pct
        ratio_sl = (sl_pct / 100.0) if sl_pct >= 0.1 else sl_pct

    if b_type == "dynamic" and current_atr > 0:
        if position == 1:
            tp = entry_price + (pt_factor * current_atr)
            sl = entry_price - (sl_factor * current_atr)
        else:
            tp = entry_price - (pt_factor * current_atr)
            sl = entry_price + (sl_factor * current_atr)
    else:
        if position == 1:
            tp = entry_price * (1.0 + ratio_tp)
            sl = entry_price * (1.0 - ratio_sl)
        else:
            tp = entry_price * (1.0 - ratio_tp)
            sl = entry_price * (1.0 + ratio_sl)

    return {"take_profit": round(float(tp), 4), "stop_loss": round(float(sl), 4)}


@dataclass
class AutopilotConfig:
    """AIオートパイロット設定"""
    is_active: bool = False
    allocated_capital: float = 3_000_000.0  # オートパイロット運用割当資金 (例: 300万円)
    daily_max_loss_pct: float = 3.0         # 1日の最大許容損失率 (3%で強制停止)
    max_leverage: float = 3.0               # 安全レバレッジ上限 (最大3〜5倍固定)
    strategy_style: str = "day_trade"       # 'scalping', 'day_trade', 'swing', 'medium_term', 'long_term'
    base_equity_today: float = 3_000_000.0  # 当日の開始有効証拠金


@dataclass
class DecisionLog:
    """AI意思決定ログ（思考の可視化）"""
    timestamp: str
    symbol: str
    action: str  # 'BUY', 'SELL', 'CLOSE', 'HOLD', 'SKIP', 'EMERGENCY_STOP', 'KILL_SWITCH'
    reason: str
    price: float
    detail: Dict[str, Any] = field(default_factory=dict)


class AutopilotEngine:
    """
    ユーザーごとのAIオートパイロット実行マネージャー
    """

    def __init__(self, user_account: VirtualAccount):
        self.account = user_account
        self.config = AutopilotConfig()
        self.logs: List[DecisionLog] = []
        self.daily_pnl_today: float = 0.0
        self.is_halted_by_killswitch: bool = False

    def toggle(self, is_active: bool, allocated_capital: float = 3_000_000.0, daily_max_loss_pct: float = 3.0, strategy_style: str = "day_trade") -> Dict[str, Any]:
        """オートパイロットのON/OFF切り替えおよび戦術設定"""
        if is_active:
            self.config.is_active = True
            self.config.allocated_capital = min(allocated_capital, self.account.equity)
            self.config.daily_max_loss_pct = daily_max_loss_pct
            self.config.base_equity_today = self.config.allocated_capital
            if strategy_style in STRATEGY_PROFILES:
                self.config.strategy_style = strategy_style
                profile = STRATEGY_PROFILES[strategy_style]
                self.config.max_leverage = profile["max_leverage"]
            self.is_halted_by_killswitch = False
            strat_name = STRATEGY_PROFILES.get(self.config.strategy_style, {}).get("name", self.config.strategy_style)
            self._log_decision("SYSTEM", "AI_ENABLED", f"AIオートパイロット起動 [{strat_name}] (割当: ¥{self.config.allocated_capital:,.0f}, 日次損失上限: -{daily_max_loss_pct}%)", 0.0)
        else:
            self.config.is_active = False
            self._log_decision("SYSTEM", "AI_DISABLED", "ユーザー操作によりAIオートパイロットを停止しました。", 0.0)

        return self.get_status()

    def emergency_panic_stop(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        【フェイルセーフ】ワンクリック緊急全停止（パニックストップ）
        全オープンポジションを成行決済し、AI自動運転を即時OFFにします。
        """
        closed_trades = []
        for pos_id, pos in list(self.account.positions.items()):
            price = current_prices.get(pos.symbol, pos.current_price)
            trade = self.account.close_position(pos_id, price)
            closed_trades.append(trade)

        self.config.is_active = False
        self._log_decision("ALL", "EMERGENCY_STOP", f"緊急全停止を実行: {len(closed_trades)}件のポジションを即時決済し、AI運転を完全停止しました。", 0.0)

        return {
            "status": "PANIC_STOPPED",
            "closed_count": len(closed_trades),
            "current_equity": round(self.account.equity, 2),
            "is_active": False
        }

    def evaluate_and_execute(self, symbol: str, race_card: Dict[str, Any]) -> Optional[str]:
        """
        市場シグナルと口座状態を検証し、選択された戦術ルールに合致した場合のみ自動売買を実行。
        """
        if not self.config.is_active or self.is_halted_by_killswitch:
            return None

        profile = STRATEGY_PROFILES.get(self.config.strategy_style, STRATEGY_PROFILES["day_trade"])
        current_price = float(race_card.get("current_price", 0.0))
        if current_price <= 0.0:
            return None  # 価格不正時は即時見送り

        prob_up = float(race_card.get("prob_up_pct", 50.0)) / 100.0
        meta_bet_size = float(race_card.get("meta_bet_size_pct", 100.0))
        meta_conf = race_card.get("meta_confidence", "NORMAL")

        # 1. 安全装置チェック: 日次最大損失リミット
        current_eq = self.account.equity
        base_eq = self.config.base_equity_today
        loss_pct = ((current_eq - base_eq) / base_eq * 100.0) if base_eq > 0 else 0.0
        if loss_pct <= -abs(self.config.daily_max_loss_pct):
            self.is_halted_by_killswitch = True
            self.config.is_active = False
            for pos_id, pos in list(self.account.positions.items()):
                self.account.close_position(pos_id, current_price)
            self._log_decision(symbol, "KILL_SWITCH", f"日次最大許容損失リミット (-{self.config.daily_max_loss_pct}%) に到達したため、全決済して本日の自動売買を強制停止しました。", current_price)
            return "KILL_SWITCH_TRIGGERED"

        # 2. 既存ポジションのエグジット判定 (動的ATRバリアまたは固定%利確・損切り・反転)
        for pos_id, pos in list(self.account.positions.items()):
            if pos.symbol == symbol:
                unrealized = pos.unrealized_return_pct

                # 動的バリア (tp_price, sl_price) が設定されている場合を優先チェック
                hit_tp = False
                hit_sl = False
                if pos.tp_price is not None and pos.sl_price is not None:
                    if pos.side == "BUY":
                        hit_tp = current_price >= pos.tp_price
                        hit_sl = current_price <= pos.sl_price
                    else:
                        hit_tp = current_price <= pos.tp_price
                        hit_sl = current_price >= pos.sl_price
                else:
                    hit_tp = unrealized >= profile["take_profit_pct"]
                    hit_sl = unrealized <= profile["stop_loss_pct"]

                # 損切り最優先（Pessimistic Priority）
                if hit_sl:
                    self.account.close_position(pos_id, current_price)
                    sl_desc = f"{pos.sl_price:.2f}" if pos.sl_price else f"{profile['stop_loss_pct']}%"
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 損切り到達 (現在値: {current_price:.2f}, SL: {sl_desc})。防衛的ロスカット。(¥{pos.unrealized_pnl:,.0f})", current_price)
                    return "CLOSE_STOP_LOSS"
                elif hit_tp:
                    self.account.close_position(pos_id, current_price)
                    tp_desc = f"{pos.tp_price:.2f}" if pos.tp_price else f"{profile['take_profit_pct']}%"
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 目標利確到達 (現在値: {current_price:.2f}, TP: {tp_desc})。利益確定決済。(+¥{pos.unrealized_pnl:,.0f})", current_price)
                    return "CLOSE_TAKE_PROFIT"
                # 反転シグナル手仕舞い
                elif pos.side == "BUY" and prob_up < profile["reversal_buy_exit"]:
                    self.account.close_position(pos_id, current_price)
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 上昇期待反落 ({prob_up*100:.1f}%)。買いポジションを反転手仕舞い。(損益: {unrealized:+.1f}%)", current_price)
                    return "CLOSE_REVERSAL"
                elif pos.side == "SELL" and prob_up > profile["reversal_sell_exit"]:
                    self.account.close_position(pos_id, current_price)
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 下落期待反落 ({prob_up*100:.1f}%)。売りポジションを反転手仕舞い。(損益: {unrealized:+.1f}%)", current_price)
                    return "CLOSE_REVERSAL"

        # 3. 新規エントリー判定（ポジションが無い場合のみ）
        has_symbol_pos = any(p.symbol == symbol for p in self.account.positions.values())
        if not has_symbol_pos:
            # メタラベリング判定: ロット0%ならマクロ危険水域として見送り
            if meta_bet_size <= 0.0:
                self._log_decision(symbol, "SKIP_MACRO_RISK", f"[{profile['name']}] エントリー機会を検出も、マクロ危険水域 ({meta_conf}) のためロット0%で見送り。", current_price)
                return "SKIP_MACRO_RISK"

            # 戦術とハーフケリー基準に連動したポジションサイジング
            size_multiplier = meta_bet_size / 100.0
            trade_value = self.config.allocated_capital * profile["base_capital_ratio"] * size_multiplier
            amount = max(0.01, trade_value / current_price)
            lev = profile["max_leverage"]
            current_atr = float(race_card.get("current_atr", race_card.get("atr_14", 0.0)))
            # レジーム判定ゲート: 高頻度戦術(スキャルピング/デイトレ)におけるレンジ相場でのダマシ回避
            regime = race_card.get("regime_state", "NORMAL")
            if self.config.strategy_style in ["scalping", "day_trade"] and regime == "CHOPPY_RANGE":
                self._log_decision(symbol, "SKIP_CHOPPY_REGIME", f"[{profile['name']}] もみ合いレンジ相場 (CHOPPY_RANGE) のため、ブレイクアウトのダマシ回避で見送り。", current_price)
                return "SKIP_CHOPPY_REGIME"

            # 上位足(HTF)トレンド整合ゲート
            htf_trend = float(race_card.get("htf_daily_trend", 0.0))

            # 取引摩擦（往復手数料0.06% + スリッページ0.10% = 0.16%）
            friction = 0.0016

            if prob_up >= profile["buy_threshold"]:
                # 上位足が明確な下落トレンドの場合は順張り原則に基づき買い見送り
                if htf_trend < 0:
                    self._log_decision(symbol, "SKIP_HTF_ALIGNMENT", f"[{profile['name']}] BUYシグナル検出も、上位足(日足)下降トレンド逆行のため見送り。", current_price)
                    return "SKIP_HTF_ALIGNMENT"

                barriers = compute_strategy_barriers(current_price, current_atr, profile, position=1)
                tp_dist = (barriers["take_profit"] - current_price) / current_price
                sl_dist = (current_price - barriers["stop_loss"]) / current_price
                expected_val = prob_up * tp_dist - (1.0 - prob_up) * sl_dist - friction

                # 期待値フィルター: 摩擦控除後の期待値が正でない場合は見送り
                if expected_val <= 0:
                    self._log_decision(symbol, "SKIP_NEGATIVE_EXPECTANCY", f"[{profile['name']}] BUY期待値が取引摩擦負け水準 (EV={expected_val*100:+.2f}%) のため見送り。", current_price)
                    return "SKIP_NEGATIVE_EXPECTANCY"

                self.account.open_position(
                    symbol, "BUY", current_price, amount=round(amount, 2), leverage=lev,
                    tp_price=barriers["take_profit"], sl_price=barriers["stop_loss"]
                )
                self._log_decision(symbol, "BUY", f"[{profile['name']}] BUYシグナル検出 ({prob_up*100:.1f}%, EV={expected_val*100:+.2f}%)。TP: {barriers['take_profit']:.2f} / SL: {barriers['stop_loss']:.2f}。ケリー推奨配分 {meta_bet_size:.1f}% で買いエントリー。", current_price)
                return "ORDER_BUY"

            elif prob_up <= profile["sell_threshold"]:
                # 上位足が明確な上昇トレンドの場合は順張り原則に基づき売り見送り
                if htf_trend > 0:
                    self._log_decision(symbol, "SKIP_HTF_ALIGNMENT", f"[{profile['name']}] SELLシグナル検出も、上位足(日足)上昇トレンド逆行のため見送り。", current_price)
                    return "SKIP_HTF_ALIGNMENT"

                prob_down = 1.0 - prob_up
                barriers = compute_strategy_barriers(current_price, current_atr, profile, position=-1)
                tp_dist = (current_price - barriers["take_profit"]) / current_price
                sl_dist = (barriers["stop_loss"] - current_price) / current_price
                expected_val = prob_down * tp_dist - (1.0 - prob_down) * sl_dist - friction

                # 期待値フィルター: 摩擦控除後の期待値が正でない場合は見送り
                if expected_val <= 0:
                    self._log_decision(symbol, "SKIP_NEGATIVE_EXPECTANCY", f"[{profile['name']}] SELL期待値が取引摩擦負け水準 (EV={expected_val*100:+.2f}%) のため見送り。", current_price)
                    return "SKIP_NEGATIVE_EXPECTANCY"

                self.account.open_position(
                    symbol, "SELL", current_price, amount=round(amount, 2), leverage=lev,
                    tp_price=barriers["take_profit"], sl_price=barriers["stop_loss"]
                )
                self._log_decision(symbol, "SELL", f"[{profile['name']}] SELLシグナル検出 (下落確率 {prob_down*100:.1f}%, EV={expected_val*100:+.2f}%)。TP: {barriers['take_profit']:.2f} / SL: {barriers['stop_loss']:.2f}。ケリー推奨配分 {meta_bet_size:.1f}% で売りエントリー。", current_price)
                return "ORDER_SELL"

        return "HOLD"

    def _log_decision(self, symbol: str, action: str, reason: str, price: float):
        now_time = datetime.now().strftime("%H:%M:%S")
        self.logs.insert(0, DecisionLog(timestamp=now_time, symbol=symbol, action=action, reason=reason, price=price))
        if len(self.logs) > 30:
            self.logs = self.logs[:30]

    def get_status(self) -> Dict[str, Any]:
        """オートパイロットの状態サマリー"""
        strat_key = self.config.strategy_style
        strat_info = STRATEGY_PROFILES.get(strat_key, STRATEGY_PROFILES["day_trade"])
        return {
            "is_active": self.config.is_active,
            "strategy_style": strat_key,
            "strategy_name": strat_info["name"],
            "strategy_profile": strat_info,
            "allocated_capital": round(self.config.allocated_capital, 2),
            "daily_max_loss_pct": self.config.daily_max_loss_pct,
            "max_leverage": self.config.max_leverage,
            "is_halted_by_killswitch": self.is_halted_by_killswitch,
            "recent_logs": [asdict(l) for l in self.logs[:10]]
        }
