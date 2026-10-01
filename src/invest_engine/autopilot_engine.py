"""
AIオートパイロット（短期自動売買お任せ運用）エンジン
フェイルセーフ安全装置（日次最大許容損失ストップ、レバレッジ上限ガード、緊急全決済ボタン、透明な思考ログ）を備えた自動売買システム。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from .virtual_broker import VirtualAccount


# 戦術（トレードスタイル）プロファイル定義
STRATEGY_PROFILES: Dict[str, Dict[str, Any]] = {
    "scalping": {
        "name": "スキャルピング (秒〜分・超短期高頻度)",
        "take_profit_pct": 0.4,
        "stop_loss_pct": -0.2,
        "buy_threshold": 0.56,
        "sell_threshold": 0.44,
        "reversal_buy_exit": 0.50,
        "reversal_sell_exit": 0.50,
        "base_capital_ratio": 0.15,
        "max_leverage": 5.0,
    },
    "day_trade": {
        "name": "デイトレード (日中短期・波乗り)",
        "take_profit_pct": 1.2,
        "stop_loss_pct": -0.6,
        "buy_threshold": 0.60,
        "sell_threshold": 0.40,
        "reversal_buy_exit": 0.48,
        "reversal_sell_exit": 0.52,
        "base_capital_ratio": 0.20,
        "max_leverage": 3.0,
    },
    "swing": {
        "name": "スイングトレード (数日〜数週間・中期波乗り)",
        "take_profit_pct": 3.5,
        "stop_loss_pct": -1.8,
        "buy_threshold": 0.65,
        "sell_threshold": 0.35,
        "reversal_buy_exit": 0.45,
        "reversal_sell_exit": 0.55,
        "base_capital_ratio": 0.25,
        "max_leverage": 2.0,
    },
    "medium_term": {
        "name": "中期トレンド (数週間〜数ヶ月・マクロ重視)",
        "take_profit_pct": 8.0,
        "stop_loss_pct": -3.5,
        "buy_threshold": 0.68,
        "sell_threshold": 0.32,
        "reversal_buy_exit": 0.42,
        "reversal_sell_exit": 0.58,
        "base_capital_ratio": 0.30,
        "max_leverage": 1.5,
    },
    "long_term": {
        "name": "長期投資 (数ヶ月〜数年・資産形成・ハーフケリー)",
        "take_profit_pct": 20.0,
        "stop_loss_pct": -8.0,
        "buy_threshold": 0.70,
        "sell_threshold": 0.30,
        "reversal_buy_exit": 0.40,
        "reversal_sell_exit": 0.60,
        "base_capital_ratio": 0.40,
        "max_leverage": 1.0,
    }
}


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
        current_price = race_card["current_price"]
        prob_up = race_card["prob_up_pct"] / 100.0
        meta_bet_size = float(race_card.get("meta_bet_size_pct", 100.0))
        meta_conf = race_card.get("meta_confidence", "NORMAL")

        # 1. 安全装置チェック: 日次最大損失リミット
        current_eq = self.account.equity
        loss_pct = ((current_eq - self.config.base_equity_today) / self.config.base_equity_today) * 100.0
        if loss_pct <= -abs(self.config.daily_max_loss_pct):
            self.is_halted_by_killswitch = True
            self.config.is_active = False
            for pos_id, pos in list(self.account.positions.items()):
                self.account.close_position(pos_id, current_price)
            self._log_decision(symbol, "KILL_SWITCH", f"日次最大許容損失リミット (-{self.config.daily_max_loss_pct}%) に到達したため、全決済して本日の自動売買を強制停止しました。", current_price)
            return "KILL_SWITCH_TRIGGERED"

        # 2. 既存ポジションのエグジット判定 (戦術ごとの利確・損切り・反転)
        for pos_id, pos in list(self.account.positions.items()):
            if pos.symbol == symbol:
                unrealized = pos.unrealized_return_pct
                # 利確トリガー
                if unrealized >= profile["take_profit_pct"]:
                    self.account.close_position(pos_id, current_price)
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 目標利確に到達 (+{unrealized:.2f}% >= +{profile['take_profit_pct']}%)。利益確定決済。(+¥{pos.unrealized_pnl:,.0f})", current_price)
                    return "CLOSE_TAKE_PROFIT"
                # 損切りトリガー
                elif unrealized <= profile["stop_loss_pct"]:
                    self.account.close_position(pos_id, current_price)
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 損切りライン到達 ({unrealized:.2f}% <= {profile['stop_loss_pct']}%)。防衛的ロスカット。(¥{pos.unrealized_pnl:,.0f})", current_price)
                    return "CLOSE_STOP_LOSS"
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
                self._log_decision(symbol, "SKIP", f"[{profile['name']}] エントリー機会を検出も、マクロ危険水域 ({meta_conf}) のためロット0%で見送り。", current_price)
                return "SKIP_MACRO_RISK"

            # 戦術とハーフケリー基準に連動したポジションサイジング
            size_multiplier = meta_bet_size / 100.0
            trade_value = self.config.allocated_capital * profile["base_capital_ratio"] * size_multiplier
            amount = max(0.01, trade_value / current_price)
            lev = profile["max_leverage"]

            if prob_up >= profile["buy_threshold"]:
                self.account.open_position(symbol, "BUY", current_price, amount=round(amount, 2), leverage=lev)
                self._log_decision(symbol, "BUY", f"[{profile['name']}] BUYシグナル検出 ({prob_up*100:.1f}%)。ケリー推奨配分 {meta_bet_size:.1f}% で買いエントリー。", current_price)
                return "ORDER_BUY"
            elif prob_up <= profile["sell_threshold"]:
                self.account.open_position(symbol, "SELL", current_price, amount=round(amount, 2), leverage=lev)
                self._log_decision(symbol, "SELL", f"[{profile['name']}] SELLシグナル検出 (下落リスク {(1-prob_up)*100:.1f}%)。ケリー推奨配分 {meta_bet_size:.1f}% で売りエントリー。", current_price)
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
