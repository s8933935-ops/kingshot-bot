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
        "reversal_buy_exit": 0.35,
        "reversal_sell_exit": 0.65,
        "base_capital_ratio": 0.15,
        "max_leverage": 5.0,
        "cooldown_ticks": 1,        # 決済後も即座に次のサヤを狙う高頻度
        "allow_reversal_exit": True,
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
        "reversal_buy_exit": 0.35,
        "reversal_sell_exit": 0.65,
        "base_capital_ratio": 0.20,
        "max_leverage": 3.0,
        "cooldown_ticks": 6,        # 決済後、次のバー確定まで一定時間待機
        "allow_reversal_exit": True,
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
        "reversal_buy_exit": 0.30,
        "reversal_sell_exit": 0.70,
        "base_capital_ratio": 0.25,
        "max_leverage": 2.0,
        "cooldown_ticks": 20,       # 決済後、一定期間じっくり構える
        "allow_reversal_exit": False,  # 小波のブレでは逃げずホールド
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
        "reversal_buy_exit": 0.25,
        "reversal_sell_exit": 0.75,
        "base_capital_ratio": 0.30,
        "max_leverage": 1.5,
        "cooldown_ticks": 40,       # 長期的な環境認識を待つ
        "allow_reversal_exit": False,
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
        "reversal_buy_exit": 0.20,
        "reversal_sell_exit": 0.80,
        "base_capital_ratio": 0.40,
        "max_leverage": 1.0,
        "cooldown_ticks": 60,       # 長期投資は小まめに売買せずじっくり待機
        "allow_reversal_exit": False,  # 小波のノイズによる早期手仕舞いを完全遮断
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
class SymbolAutopilotConfig:
    """銘柄別個別AIオートパイロット設定"""
    symbol: str
    is_active: bool = False
    strategy_style: str = "day_trade"
    allocated_capital: float = 1_000_000.0
    use_limit_orders: bool = False  # 指値注文を活用してスリッページを削減するか (デフォルト成行)
    limit_offset_pct: float = 0.15  # 押し目/戻りの指値オフセット (%)
    allowed_side: str = "BOTH"      # 'BOTH', 'BUY_ONLY' (買い専用・現物/積立), 'SELL_ONLY' (売り専用)
    max_positions: int = 1         # 同一銘柄の最大ポジション数 (1〜3: 買い増し・ピラミッディング許容)


@dataclass
class AutopilotConfig:
    """AIオートパイロット設定"""
    is_active: bool = False
    allocated_capital: float = 3_000_000.0  # 全体またはデフォルト割当資金 (例: 300万円)
    daily_max_loss_pct: float = 3.0         # 1日の最大許容損失率 (3%で強制停止)
    max_leverage: float = 3.0               # 安全レバレッジ上限 (最大3〜5倍固定)
    strategy_style: str = "day_trade"       # 'scalping', 'day_trade', 'swing', 'medium_term', 'long_term'
    base_equity_today: float = 3_000_000.0  # 当日の開始有効証拠金
    use_limit_orders: bool = False          # 全体デフォルト指値フラグ (デフォルト成行)
    allowed_side: str = "BOTH"              # 全体デフォルト売買方向 ('BOTH', 'BUY_ONLY', 'SELL_ONLY')
    max_positions: int = 1                  # 全体デフォルト最大ポジション数
    focused_symbol: Optional[str] = None    # 特定銘柄専従モード (例: 'GC=F' ならゴールド以外完全スキップ)
    symbol_configs: Dict[str, SymbolAutopilotConfig] = field(default_factory=dict)



@dataclass
class DecisionLog:
    """AI意思決定ログ（思考の可視化）"""
    timestamp: str
    symbol: str
    action: str  # 'BUY', 'SELL', 'CLOSE', 'HOLD', 'SKIP', 'EMERGENCY_STOP', 'KILL_SWITCH', 'LIMIT_BUY', 'LIMIT_SELL', 'LIMIT_FILLED'
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
        self.last_exit_tick: Dict[str, int] = {}
        self.current_tick_count: int = 0

        # 4大主要銘柄のデフォルト個別設定を初期化
        default_symbols = ["GC=F", "USDJPY=X", "BTC-USD", "NVDA"]
        for sym in default_symbols:
            self.config.symbol_configs[sym] = SymbolAutopilotConfig(
                symbol=sym,
                is_active=False,
                strategy_style="day_trade",
                allocated_capital=1_000_000.0,
                use_limit_orders=False
            )

    def update_symbol_config(
        self,
        symbol: str,
        is_active: bool,
        strategy_style: str = "day_trade",
        allocated_capital: float = 1_000_000.0,
        use_limit_orders: bool = False,
        allowed_side: str = "BOTH",
        max_positions: int = 1
    ) -> SymbolAutopilotConfig:
        """特定銘柄のオートパイロット個別設定を更新"""
        if symbol not in self.config.symbol_configs:
            self.config.symbol_configs[symbol] = SymbolAutopilotConfig(symbol=symbol)

        cfg = self.config.symbol_configs[symbol]
        cfg.is_active = is_active
        cfg.strategy_style = strategy_style if strategy_style in STRATEGY_PROFILES else "day_trade"
        cfg.allocated_capital = min(allocated_capital, self.account.equity)
        cfg.use_limit_orders = use_limit_orders
        if allowed_side in ["BOTH", "BUY_ONLY", "SELL_ONLY"]:
            cfg.allowed_side = allowed_side
        cfg.max_positions = max(1, min(5, int(max_positions)))

        # もし1つでも個別銘柄がアクティブなら全体もアクティブとみなす
        if any(c.is_active for c in self.config.symbol_configs.values()):
            self.config.is_active = True

        state_str = "ON (自動稼働)" if is_active else "OFF (待機)"
        limit_str = "指値運用" if use_limit_orders else "成行"
        side_str = "📈 買いのみ" if cfg.allowed_side == "BUY_ONLY" else ("📉 売りのみ" if cfg.allowed_side == "SELL_ONLY" else "🔄 両方")
        self._log_decision(symbol, "CONFIG_UPDATE", f"[{symbol}] 個別AI設定更新: {state_str} (戦術: {cfg.strategy_style}, 割当: ¥{cfg.allocated_capital:,.0f}, {limit_str}, 方向: {side_str}, 最大ポジ: {cfg.max_positions})", 0.0)
        return cfg

    def set_focused_symbol(self, symbol: Optional[str]) -> Dict[str, Any]:
        """特定銘柄専従モードの切り替え (例: 'GC=F' ならゴールド専従、Noneなら全銘柄解除)"""
        self.config.focused_symbol = symbol
        if symbol:
            # 専従銘柄以外を個別停止し、専従銘柄のみアクティブに
            for s, sc in self.config.symbol_configs.items():
                sc.is_active = (s == symbol)
            self._log_decision("SYSTEM", "FOCUS_ENABLED", f"🏆 【単一銘柄専従モード有効】 [{symbol}] 専門運用に切り替えました（他銘柄は完全スキップ）。", 0.0)
        else:
            self._log_decision("SYSTEM", "FOCUS_DISABLED", "🌐 単一銘柄専従モードを解除しました（全銘柄の運用を許可）。", 0.0)
        return self.get_status()

    def set_side_direction(self, allowed_side: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """売買方向の指定 ('BOTH', 'BUY_ONLY', 'SELL_ONLY')"""
        if allowed_side not in ["BOTH", "BUY_ONLY", "SELL_ONLY"]:
            allowed_side = "BOTH"

        if symbol and symbol in self.config.symbol_configs:
            self.config.symbol_configs[symbol].allowed_side = allowed_side
        else:
            self.config.allowed_side = allowed_side
            for sc in self.config.symbol_configs.values():
                sc.allowed_side = allowed_side

        side_label = "📈 買いのみ (Long Only)" if allowed_side == "BUY_ONLY" else ("📉 売りのみ (Short Only)" if allowed_side == "SELL_ONLY" else "🔄 買い＆売り両方")
        target_label = f"[{symbol}]" if symbol else "全銘柄"
        self._log_decision("SYSTEM", "SIDE_UPDATE", f"🧭 {target_label} の売買方向を「{side_label}」に固定設定しました。", 0.0)
        return self.get_status()


    def toggle(self, is_active: bool, allocated_capital: float = 3_000_000.0, daily_max_loss_pct: float = 3.0, strategy_style: str = "day_trade", use_limit_orders: bool = False) -> Dict[str, Any]:
        """全銘柄一括オートパイロットのON/OFF切り替えおよび戦術設定"""
        if is_active:
            self.config.is_active = True
            self.config.allocated_capital = min(allocated_capital, self.account.equity)
            self.config.daily_max_loss_pct = daily_max_loss_pct
            self.config.base_equity_today = self.config.allocated_capital
            self.config.use_limit_orders = use_limit_orders
            if strategy_style in STRATEGY_PROFILES:
                self.config.strategy_style = strategy_style
                profile = STRATEGY_PROFILES[strategy_style]
                self.config.max_leverage = profile["max_leverage"]
            self.is_halted_by_killswitch = False

            # 個別銘柄も一括で有効化
            for sym_cfg in self.config.symbol_configs.values():
                sym_cfg.is_active = True
                sym_cfg.strategy_style = self.config.strategy_style
                sym_cfg.allocated_capital = self.config.allocated_capital
                sym_cfg.use_limit_orders = use_limit_orders

            strat_name = STRATEGY_PROFILES.get(self.config.strategy_style, {}).get("name", self.config.strategy_style)
            limit_desc = "AI指値注文有効 (スリッページゼロ)" if use_limit_orders else "成行注文"
            self._log_decision("SYSTEM", "AI_ENABLED", f"AIオートパイロット全銘柄一括起動 [{strat_name}] (割当: ¥{self.config.allocated_capital:,.0f}, 日次損失上限: -{daily_max_loss_pct}%, {limit_desc})", 0.0)
        else:
            self.config.is_active = False
            for sym_cfg in self.config.symbol_configs.values():
                sym_cfg.is_active = False
            self._log_decision("SYSTEM", "AI_DISABLED", "ユーザー操作によりAIオートパイロットを全銘柄停止しました。", 0.0)

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
        指値マッチング、銘柄別設定、AIスマート指値注文に対応。
        """
        self.current_tick_count += 1
        current_price = float(race_card.get("current_price", 0.0))
        if current_price <= 0.0:
            return None  # 価格不正時は即時見送り

        # 0. 待機中指値注文のマッチング判定（約定検査）
        matched_positions = self.account.check_and_match_limit_orders({symbol: current_price})
        for mp in matched_positions:
            self._log_decision(symbol, "LIMIT_FILLED", f"待機中指値が市場価格に到達し約定完了。(約定値: {mp.entry_price:.2f}, 数量: {mp.amount}, メイカー優遇手数料適用)", mp.entry_price)

        # 銘柄別の稼働判定
        # 専従銘柄チェック (特定銘柄専従モード有効時、それ以外は完全スキップ)
        if self.config.focused_symbol and symbol != self.config.focused_symbol:
            return None

        sym_cfg = self.config.symbol_configs.get(symbol)
        is_sym_active = (sym_cfg.is_active if sym_cfg else False) or self.config.is_active
        if not is_sym_active or self.is_halted_by_killswitch:
            return None

        active_strat = sym_cfg.strategy_style if sym_cfg else self.config.strategy_style
        profile = STRATEGY_PROFILES.get(active_strat, STRATEGY_PROFILES["day_trade"])
        allocated_cap = sym_cfg.allocated_capital if sym_cfg else self.config.allocated_capital
        use_limit = sym_cfg.use_limit_orders if sym_cfg else self.config.use_limit_orders
        offset_pct = sym_cfg.limit_offset_pct if sym_cfg else 0.15

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
            for s_cfg in self.config.symbol_configs.values():
                s_cfg.is_active = False
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
                    self.last_exit_tick[symbol] = self.current_tick_count
                    sl_desc = f"{pos.sl_price:.2f}" if pos.sl_price else f"{profile['stop_loss_pct']}%"
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 損切り到達 (現在値: {current_price:.2f}, SL: {sl_desc})。防衛的ロスカット。(¥{pos.unrealized_pnl:,.0f})", current_price)
                    return "CLOSE_STOP_LOSS"
                elif hit_tp:
                    self.account.close_position(pos_id, current_price)
                    self.last_exit_tick[symbol] = self.current_tick_count
                    tp_desc = f"{pos.tp_price:.2f}" if pos.tp_price else f"{profile['take_profit_pct']}%"
                    self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 目標利確到達 (現在値: {current_price:.2f}, TP: {tp_desc})。利益確定決済。(+¥{pos.unrealized_pnl:,.0f})", current_price)
                    return "CLOSE_TAKE_PROFIT"
                # 反転シグナル手仕舞い（スキャルピング/デイトレのみ許可。スイング・長期は小波で逃げずホールド）
                elif profile.get("allow_reversal_exit", False):
                    if pos.side == "BUY" and prob_up < profile["reversal_buy_exit"]:
                        self.account.close_position(pos_id, current_price)
                        self.last_exit_tick[symbol] = self.current_tick_count
                        self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 上昇期待反落 ({prob_up*100:.1f}%)。買いポジションを反転手仕舞い。(損益: {unrealized:+.1f}%)", current_price)
                        return "CLOSE_REVERSAL"
                    elif pos.side == "SELL" and prob_up > profile["reversal_sell_exit"]:
                        self.account.close_position(pos_id, current_price)
                        self.last_exit_tick[symbol] = self.current_tick_count
                        self._log_decision(symbol, "CLOSE", f"[{profile['name']}] 下落期待反落 ({prob_up*100:.1f}%)。売りポジションを反転手仕舞い。(損益: {unrealized:+.1f}%)", current_price)
                        return "CLOSE_REVERSAL"

        # 3. 新規エントリー判定（許容ポジション数上限未満、かつ未約定AI指値が無い場合）
        current_symbol_positions = [p for p in self.account.positions.values() if p.symbol == symbol]
        symbol_pos_count = len(current_symbol_positions)
        max_pos_allowed = sym_cfg.max_positions if sym_cfg else self.config.max_positions
        allowed_side = sym_cfg.allowed_side if sym_cfg else self.config.allowed_side
        has_pending_ai_order = any(o.symbol == symbol and o.status == "PENDING" and o.source == "AI" for o in self.account.limit_orders.values())

        if symbol_pos_count < max_pos_allowed and not has_pending_ai_order:
            # 戦略別再エントリークールダウン（長期投資等のマシンガン売買を遮断）
            last_exit = self.last_exit_tick.get(symbol, -9999)
            cooldown_req = profile.get("cooldown_ticks", 2)
            if (self.current_tick_count - last_exit) < cooldown_req:
                return "COOLDOWN_WAIT"

            # メタラベリング判定: ロット0%ならマクロ危険水域として見送り
            if meta_bet_size <= 0.0:
                self._log_decision(symbol, "SKIP_MACRO_RISK", f"[{profile['name']}] エントリー機会を検出も、マクロ危険水域 ({meta_conf}) のためロット0%で見送り。", current_price)
                return "SKIP_MACRO_RISK"

            # 戦術とハーフケリー基準に連動したポジションサイジング (日本円換算)
            size_multiplier = meta_bet_size / 100.0
            trade_value = allocated_cap * profile["base_capital_ratio"] * size_multiplier
            fx_rate = self.account.get_fx_rate(symbol)
            unit_price_jpy = current_price * fx_rate
            amount = max(0.01, trade_value / unit_price_jpy)
            lev = profile["max_leverage"]
            current_atr = float(race_card.get("current_atr", race_card.get("atr_14", 0.0)))

            # レジーム判定ゲート: 高頻度戦術(スキャルピング/デイトレ)におけるレンジ相場でのダマシ回避
            regime = race_card.get("regime_state", "NORMAL")
            if active_strat in ["scalping", "day_trade"] and regime == "CHOPPY_RANGE":
                self._log_decision(symbol, "SKIP_CHOPPY_REGIME", f"[{profile['name']}] もみ合いレンジ相場 (CHOPPY_RANGE) のため、ブレイクアウトのダマシ回避で見送り。", current_price)
                return "SKIP_CHOPPY_REGIME"

            # 上位足(HTF)トレンド整合ゲート
            htf_trend = float(race_card.get("htf_daily_trend", 0.0))

            # 取引摩擦（往復手数料0.06% + スリッページ0.10% = 0.16%、指値なら0.02%）
            friction = 0.0002 if use_limit else 0.0016

            if prob_up >= profile["buy_threshold"]:
                # 売買方向フィルター（SELL_ONLY時は買いを見送り）
                if allowed_side == "SELL_ONLY":
                    self._log_decision(symbol, "SKIP_SIDE_FILTER", f"[{profile['name']}] BUYシグナル検出も、売買方向「売りのみ (SELL_ONLY)」設定のため見送り。", current_price)
                    return "SKIP_SIDE_FILTER"

                # 買い増し時の安全検査（既存の買いポジションと同じ高値圏で掴まないよう、有利な価格または押し目を待つ）
                if symbol_pos_count > 0:
                    recent_buy_price = min(p.entry_price for p in current_symbol_positions if p.side == "BUY") if any(p.side == "BUY" for p in current_symbol_positions) else current_price
                    if current_price > recent_buy_price * 1.01:
                        self._log_decision(symbol, "SKIP_PYRAMIDING_HIGH", f"[{profile['name']}] 買い増し判定: 直近買い単価 ({recent_buy_price:.2f}) より高値圏のため、押し目を待機。", current_price)
                        return "SKIP_PYRAMIDING_HIGH"

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

                add_str = f" [買い増し {symbol_pos_count+1}/{max_pos_allowed}ポジ]" if symbol_pos_count > 0 else ""
                if use_limit:
                    # AIスマート指値（押し目買い指値: 現在値よりoffset_pct安い価格で指す）
                    limit_target = round(current_price * (1.0 - offset_pct / 100.0), 2)
                    self.account.place_limit_order(
                        symbol, "BUY", limit_target, amount=round(amount, 2), leverage=lev,
                        source="AI", tp_price=barriers["take_profit"], sl_price=barriers["stop_loss"]
                    )
                    self._log_decision(symbol, "LIMIT_BUY", f"[{profile['name']}] BUYシグナル検出 ({prob_up*100:.1f}%){add_str}。有利な押し目指値を発注 (指値: {limit_target:.2f} / 現在値: {current_price:.2f}, スリッページゼロ戦略)。", limit_target)
                    return "ORDER_LIMIT_BUY"
                else:
                    self.account.open_position(
                        symbol, "BUY", current_price, amount=round(amount, 2), leverage=lev,
                        tp_price=barriers["take_profit"], sl_price=barriers["stop_loss"]
                    )
                    self._log_decision(symbol, "BUY", f"[{profile['name']}] BUYシグナル検出 ({prob_up*100:.1f}%, EV={expected_val*100:+.2f}%){add_str}。TP: {barriers['take_profit']:.2f} / SL: {barriers['stop_loss']:.2f}。ケリー推奨配分 {meta_bet_size:.1f}% で成行買いエントリー。", current_price)
                    return "ORDER_BUY"

            elif prob_up <= profile["sell_threshold"]:
                # 売買方向フィルター（BUY_ONLY時は売りを完全見送り）
                if allowed_side == "BUY_ONLY":
                    self._log_decision(symbol, "SKIP_SIDE_FILTER", f"[{profile['name']}] SELLシグナル検出も、売買方向「買いのみ (BUY_ONLY)」固定のため見送り（下落トレンド時は静観）。", current_price)
                    return "SKIP_SIDE_FILTER"

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

                add_str = f" [売り増し {symbol_pos_count+1}/{max_pos_allowed}ポジ]" if symbol_pos_count > 0 else ""
                if use_limit:
                    # AIスマート指値（戻り売り指値: 現在値よりoffset_pct高い価格で指す）
                    limit_target = round(current_price * (1.0 + offset_pct / 100.0), 2)
                    self.account.place_limit_order(
                        symbol, "SELL", limit_target, amount=round(amount, 2), leverage=lev,
                        source="AI", tp_price=barriers["take_profit"], sl_price=barriers["stop_loss"]
                    )
                    self._log_decision(symbol, "LIMIT_SELL", f"[{profile['name']}] SELLシグナル検出 (下落確率 {prob_down*100:.1f}%){add_str}。有利な戻り売り指値を発注 (指値: {limit_target:.2f} / 現在値: {current_price:.2f}, スリッページゼロ戦略)。", limit_target)
                    return "ORDER_LIMIT_SELL"
                else:
                    self.account.open_position(
                        symbol, "SELL", current_price, amount=round(amount, 2), leverage=lev,
                        tp_price=barriers["take_profit"], sl_price=barriers["stop_loss"]
                    )
                    self._log_decision(symbol, "SELL", f"[{profile['name']}] SELLシグナル検出 (下落確率 {prob_down*100:.1f}%, EV={expected_val*100:+.2f}%){add_str}。TP: {barriers['take_profit']:.2f} / SL: {barriers['stop_loss']:.2f}。ケリー推奨配分 {meta_bet_size:.1f}% で成行売りエントリー。", current_price)
                    return "ORDER_SELL"

        return "HOLD"

    def _log_decision(
        self,
        symbol: str,
        action: str,
        reason: str,
        price: float,
        prob_up: Optional[float] = None,
        regime: Optional[str] = None,
        htf_trend: Optional[float] = None,
        meta_bet_size: Optional[float] = None,
        features: Optional[Dict[str, Any]] = None
    ):
        now_time = datetime.now().strftime("%H:%M:%S")
        self.logs.insert(0, DecisionLog(timestamp=now_time, symbol=symbol, action=action, reason=reason, price=price))
        if len(self.logs) > 30:
            self.logs = self.logs[:30]

        # SQLiteへ自動永続化保存（自己学習・メタラベリング再学習用データセット蓄積）
        try:
            from .history_db import save_ai_decision
            save_ai_decision(
                user_id=self.account.user_id,
                symbol=symbol,
                action=action,
                reason=reason,
                price=price,
                prob_up=prob_up,
                regime=regime,
                htf_trend=htf_trend,
                meta_bet_size=meta_bet_size,
                features=features
            )
        except Exception:
            pass

    def set_strategy(self, strategy_style: str):
        """全体のデフォルト戦略スタイルを即時更新"""
        if strategy_style in STRATEGY_PROFILES:
            self.config.strategy_style = strategy_style
            prof = STRATEGY_PROFILES[strategy_style]
            self.config.max_leverage = prof["max_leverage"]
            # 個別設定のうちアクティブでないものも同期
            for s_cfg in self.config.symbol_configs.values():
                if not s_cfg.is_active:
                    s_cfg.strategy_style = strategy_style

    def reset(self):
        """オートパイロットのキルスイッチ・日次損益・ログを完全リセット"""
        self.daily_pnl_today = 0.0
        self.is_halted_by_killswitch = False
        self.logs.clear()

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
            "use_limit_orders": self.config.use_limit_orders,
            "allowed_side": self.config.allowed_side,
            "max_positions": self.config.max_positions,
            "focused_symbol": self.config.focused_symbol,
            "is_halted_by_killswitch": self.is_halted_by_killswitch,
            "symbol_configs": {s: asdict(c) for s, c in self.config.symbol_configs.items()},
            "pending_limit_orders": [asdict(o) for o in self.account.limit_orders.values() if o.status == "PENDING"],
            "recent_logs": [asdict(l) for l in self.logs[:15]]
        }
