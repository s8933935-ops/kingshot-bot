"""
仮想投資（ペーパートレード）口座＆約定管理エンジン
初期バーチャル資金（1,000万円）で、金先物・FX・株式の仮想売買、ポジション管理、
含み損益・確定損益の計算、および競馬風ランキング指標の集計を行います。
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import numpy as np


QUOTE_CURRENCIES = {
    "GC=F": "USD",     # COMEX金先物 (USD/oz)
    "BTC-USD": "USD",  # ビットコイン (USD/BTC)
    "NVDA": "USD",     # エヌビディア株 (USD/share)
    "USDJPY=X": "JPY", # ドル円為替 (JPY/USD)
}


@dataclass
class Position:
    """保有ポジション"""
    position_id: str
    symbol: str
    side: str  # 'BUY' (ロング) or 'SELL' (ショート)
    entry_price: float
    current_price: float
    amount: float  # 取引単位・数量 (例: 金1オンス単位)
    leverage: float = 1.0
    tp_price: Optional[float] = None  # 動的/固定 利確トリガー価格
    sl_price: Optional[float] = None  # 動的/固定 損切りトリガー価格
    opened_at: str = field(default_factory=lambda: datetime.now().isoformat())
    quote_currency: str = "USD"
    fx_rate: float = 1.0  # 日本円換算為替レート (USD建てならUSD/JPYレート、JPY建てなら1.0)

    @property
    def unrealized_pnl_quote(self) -> float:
        """原資産通貨建ての含み損益 (例: USD)"""
        multiplier = 1.0 if self.side == "BUY" else -1.0
        return (self.current_price - self.entry_price) * self.amount * multiplier

    @property
    def unrealized_pnl(self) -> float:
        """口座通貨 (日本円 JPY) 換算の含み損益"""
        return self.unrealized_pnl_quote * self.fx_rate

    @property
    def unrealized_return_pct(self) -> float:
        """含み損益率 (%)"""
        if self.entry_price <= 0:
            return 0.0
        multiplier = 1.0 if self.side == "BUY" else -1.0
        return ((self.current_price - self.entry_price) / self.entry_price) * multiplier * self.leverage * 100.0


@dataclass
class LimitOrder:
    """指値（リミット）注文"""
    order_id: str
    user_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    target_price: float
    amount: float
    leverage: float = 1.0
    source: str = "MANUAL"  # 'MANUAL' (手動発注) or 'AI' (AIオートパイロット)
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "PENDING"  # 'PENDING', 'FILLED', 'CANCELLED'


@dataclass
class TradeRecord:
    """決済完了トレード履歴（口座通貨 JPY 基準）"""
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    amount: float
    leverage: float
    gross_pnl: float          # JPY換算 粗損益
    fee: float                # JPY換算 手数料
    net_pnl: float            # JPY換算 純損益
    return_pct: float         # 投資利益率 (%)
    opened_at: str
    closed_at: str
    quote_currency: str = "USD"
    fx_rate: float = 1.0      # 決済時点の日本円換算レート
    gross_pnl_quote: float = 0.0 # 原資産通貨建て粗損益


class VirtualAccount:
    """
    ユーザーごとの仮想投資口座
    """

    def __init__(self, user_id: str, user_name: str, initial_cash: float = 10_000_000.0):
        self.user_id = user_id
        self.user_name = user_name
        self.initial_cash = initial_cash
        self.cash = initial_cash  # 利用可能現金残高 (日本円 JPY)
        self.positions: Dict[str, Position] = {}
        self.limit_orders: Dict[str, LimitOrder] = {}  # 待機中・約定済み指値注文
        self.trade_history: List[TradeRecord] = []
        self.fee_rate = 0.0003  # 片道成行手数料・スプレッド (0.03%)
        self.maker_fee_rate = 0.0001  # 指値（メイカー）優遇手数料 (0.01% - スリッページゼロ＆低手数料)
        self.equity_peak = initial_cash
        self.max_drawdown = 0.0
        self.latest_usd_jpy = 157.0  # 日本円換算用の米ドル/円為替レート (リアルタイム更新)

    def get_fx_rate(self, symbol: str) -> float:
        """銘柄に応じた日本円換算レートを返す（USD建てならUSD/JPYレート、JPY建てなら1.0）"""
        quote_ccy = QUOTE_CURRENCIES.get(symbol, "USD")
        if quote_ccy == "JPY":
            return 1.0
        return max(self.latest_usd_jpy, 50.0)

    @property
    def equity(self) -> float:
        """有効証拠金（現金 + 全ポジションの日本円換算含み損益）"""
        unrealized_total = sum(p.unrealized_pnl for p in self.positions.values())
        return self.cash + unrealized_total

    def update_market_price(self, symbol: str, current_price: float):
        """市場価格が動いた際に保有ポジションの現在値を更新し、ドローダウンを再計算"""
        if symbol == "USDJPY=X" and current_price > 0:
            self.latest_usd_jpy = current_price

        for pos in self.positions.values():
            if pos.symbol == symbol:
                pos.current_price = current_price
            # 全ポジションの為替レートも最新に同期
            pos.fx_rate = self.get_fx_rate(pos.symbol)

        # ドローダウン更新
        current_eq = self.equity
        if current_eq > self.equity_peak:
            self.equity_peak = current_eq
        dd = (current_eq - self.equity_peak) / (self.equity_peak + 1e-8)
        if dd < self.max_drawdown:
            self.max_drawdown = dd

    def open_position(
        self,
        symbol: str,
        side: str,
        current_price: float,
        amount: float,
        leverage: float = 1.0,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Position:
        """
        新規ポジションを成行でオープンする（米ドル建て銘柄は為替換算して日本円証拠金を拘束）。
        """
        side = side.upper()
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'.")

        fx_rate = self.get_fx_rate(symbol)
        quote_ccy = QUOTE_CURRENCIES.get(symbol, "USD")

        # 日本円換算の想定取引金額
        notional_jpy = (current_price * amount) * fx_rate
        required_margin = notional_jpy / leverage
        fee = notional_jpy * self.fee_rate

        if self.cash < (required_margin + fee):
            raise ValueError(f"資金不足: 必要証拠金+手数料 {required_margin + fee:.1f}円 に対して残高 {self.cash:.1f}円")

        # 手数料引き落とし (日本円)
        self.cash -= fee

        pos_id = str(uuid.uuid4())[:8]
        pos = Position(
            position_id=pos_id,
            symbol=symbol,
            side=side,
            entry_price=current_price,
            current_price=current_price,
            amount=amount,
            leverage=leverage,
            tp_price=tp_price,
            sl_price=sl_price,
            quote_currency=quote_ccy,
            fx_rate=fx_rate
        )
        self.positions[pos_id] = pos
        return pos

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        target_price: float,
        amount: float,
        leverage: float = 1.0,
        source: str = "MANUAL",
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> LimitOrder:
        """
        新規の指値（リミット）注文を発注・待機リストに登録する。
        """
        side = side.upper()
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'.")
        if target_price <= 0 or amount <= 0:
            raise ValueError("Target price and amount must be positive.")

        fx_rate = self.get_fx_rate(symbol)
        notional_jpy = (target_price * amount) * fx_rate
        required_margin = notional_jpy / leverage
        fee = notional_jpy * self.maker_fee_rate

        if self.cash < (required_margin + fee):
            raise ValueError(f"資金不足: 必要証拠金+手数料 {required_margin + fee:.1f}円 に対して残高 {self.cash:.1f}円")

        order_id = str(uuid.uuid4())[:8]
        order = LimitOrder(
            order_id=order_id,
            user_id=self.user_id,
            symbol=symbol,
            side=side,
            target_price=target_price,
            amount=amount,
            leverage=leverage,
            source=source,
            tp_price=tp_price,
            sl_price=sl_price,
            status="PENDING"
        )
        self.limit_orders[order_id] = order
        return order

    def cancel_limit_order(self, order_id: str) -> bool:
        """
        待機中の指値注文を取り消す。
        """
        if order_id in self.limit_orders and self.limit_orders[order_id].status == "PENDING":
            self.limit_orders[order_id].status = "CANCELLED"
            return True
        return False

    def check_and_match_limit_orders(self, current_prices: Dict[str, float]) -> List[Position]:
        """
        現在市場価格と突き合わせ、約定条件を満たした指値注文を約定（ポジション化）する。
        BUY指値: 現在値 <= target_price
        SELL指値: 現在値 >= target_price
        """
        filled_positions: List[Position] = []

        for order_id, order in list(self.limit_orders.items()):
            if order.status != "PENDING":
                continue

            current_price = current_prices.get(order.symbol)
            if not current_price or current_price <= 0:
                continue

            matched = False
            fill_price = order.target_price

            if order.side == "BUY" and current_price <= order.target_price:
                matched = True
                fill_price = min(order.target_price, current_price)
            elif order.side == "SELL" and current_price >= order.target_price:
                matched = True
                fill_price = max(order.target_price, current_price)

            if matched:
                fx_rate = self.get_fx_rate(order.symbol)
                quote_ccy = QUOTE_CURRENCIES.get(order.symbol, "USD")
                notional_jpy = (fill_price * order.amount) * fx_rate
                required_margin = notional_jpy / order.leverage
                fee = notional_jpy * self.maker_fee_rate

                if self.cash >= (required_margin + fee):
                    self.cash -= fee
                    pos_id = str(uuid.uuid4())[:8]
                    pos = Position(
                        position_id=pos_id,
                        symbol=order.symbol,
                        side=order.side,
                        entry_price=fill_price,
                        current_price=current_price,
                        amount=order.amount,
                        leverage=order.leverage,
                        tp_price=order.tp_price,
                        sl_price=order.sl_price,
                        quote_currency=quote_ccy,
                        fx_rate=fx_rate
                    )
                    self.positions[pos_id] = pos
                    order.status = "FILLED"
                    filled_positions.append(pos)
                else:
                    order.status = "CANCELLED"

        return filled_positions

    def close_position(self, position_id: str, current_price: float) -> TradeRecord:
        """
        保有ポジションを決済（エグジット）する（米ドル建て損益は為替レートで日本円換算）。
        """
        if position_id not in self.positions:
            raise KeyError(f"Position ID not found: {position_id}")

        pos = self.positions.pop(position_id)
        pos.current_price = current_price

        fx_rate = self.get_fx_rate(pos.symbol)
        multiplier = 1.0 if pos.side == "BUY" else -1.0

        # 原資産通貨建ての損益
        gross_pnl_quote = (current_price - pos.entry_price) * pos.amount * multiplier

        # 口座通貨 (日本円 JPY) 換算の損益・手数料
        gross_pnl_jpy = gross_pnl_quote * fx_rate
        exit_fee_jpy = (current_price * pos.amount * fx_rate) * self.fee_rate
        net_pnl_jpy = gross_pnl_jpy - exit_fee_jpy

        # 口座現金の反映 (日本円)
        self.cash += net_pnl_jpy

        trade_record = TradeRecord(
            trade_id=str(uuid.uuid4())[:8],
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=current_price,
            amount=pos.amount,
            leverage=pos.leverage,
            gross_pnl=round(gross_pnl_jpy, 2),
            fee=round(exit_fee_jpy, 2),
            net_pnl=round(net_pnl_jpy, 2),
            return_pct=round(pos.unrealized_return_pct, 2),
            opened_at=pos.opened_at,
            closed_at=datetime.now().isoformat(),
            quote_currency=pos.quote_currency,
            fx_rate=round(fx_rate, 4),
            gross_pnl_quote=round(gross_pnl_quote, 4)
        )
        self.trade_history.append(trade_record)

        # DBへ自動永続化（自己学習用データ蓄積）
        try:
            from .history_db import save_trade_record
            save_trade_record(
                user_id=self.user_id,
                trade=asdict(trade_record),
                source="AUTOPILOT" if "ai_" in self.user_id or "AI" in self.user_name else "USER"
            )
        except Exception:
            pass

        # ドローダウン再計算
        self.update_market_price(pos.symbol, current_price)
        return trade_record

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        競馬風ランキング用の総合パフォーマンス指標を集計する。
        """
        n_trades = len(self.trade_history)
        if n_trades == 0:
            return {
                "user_id": self.user_id,
                "user_name": self.user_name,
                "equity": round(self.equity, 2),
                "cash": round(self.cash, 2),
                "total_trades": 0,
                "payout_rate_pct": 100.0,  # 回収率 100% (元本同額)
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "grand_prix_score": 0.0,
                "certified_rank": "未認定 (ルーキー)"
            }

        # 勝ち/負け分析
        wins = [t.net_pnl for t in self.trade_history if t.net_pnl > 0]
        losses = [abs(t.net_pnl) for t in self.trade_history if t.net_pnl < 0]

        n_wins = len(wins)
        win_rate = (n_wins / n_trades) * 100.0

        total_gain = sum(wins)
        total_loss = sum(losses)
        pf = (total_gain / total_loss) if total_loss > 0 else (99.0 if total_gain > 0 else 1.0)

        # 累積回収率 (現在の有効証拠金 ÷ 初期資金 × 100)
        payout_rate = (self.equity / self.initial_cash * 100.0) if self.initial_cash > 0 else 100.0

        # AI作戦会議で採択された「グランプリ総合スコア (GP Score)」
        # 単純な大勝ちだけでなく、勝率・PF・ドローダウン耐性を掛け合わせた真の実力指標
        # スコア = (回収率 - 100) * min(PF, 3.0) * (1.0 - abs(self.max_drawdown))
        alpha = max(payout_rate - 100.0, -90.0)
        risk_penalty = max(1.0 - abs(self.max_drawdown), 0.1)
        gp_score = alpha * min(pf, 3.0) * risk_penalty

        # 認定称号（バッジ）
        if n_trades < 5:
            certified_rank = "見習い (最低5取引必要)"
        elif gp_score >= 100.0:
            certified_rank = "殿堂入り予想屋 (SS)"
        elif gp_score >= 50.0:
            certified_rank = "一流クオンツ (S)"
        elif gp_score >= 20.0:
            certified_rank = "実力派トレーダー (A)"
        elif gp_score >= 0.0:
            certified_rank = "黒字予想屋 (B)"
        else:
            certified_rank = "修行中 (C)"

        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "equity": round(self.equity, 2),
            "cash": round(self.cash, 2),
            "total_trades": n_trades,
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(pf, 2),
            "payout_rate_pct": round(payout_rate, 2),  # 回収率
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "grand_prix_score": round(gp_score, 2),
            "certified_rank": certified_rank
        }

    def reset(self, initial_cash: Optional[float] = None):
        """口座を初期状態に完全リセット（残高復元、ポジション・待機注文・履歴クリア）"""
        if initial_cash is not None:
            self.initial_cash = initial_cash
        self.cash = self.initial_cash
        self.positions.clear()
        self.limit_orders.clear()
        self.trade_history.clear()
        self.equity_peak = self.initial_cash
        self.max_drawdown = 0.0

