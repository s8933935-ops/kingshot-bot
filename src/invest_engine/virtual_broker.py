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

    @property
    def unrealized_pnl(self) -> float:
        """含み損益 (円/ドル)"""
        multiplier = 1.0 if self.side == "BUY" else -1.0
        return (self.current_price - self.entry_price) * self.amount * multiplier * self.leverage

    @property
    def unrealized_return_pct(self) -> float:
        """含み損益率 (%)"""
        if self.entry_price <= 0:
            return 0.0
        multiplier = 1.0 if self.side == "BUY" else -1.0
        return ((self.current_price - self.entry_price) / self.entry_price) * multiplier * self.leverage * 100.0


@dataclass
class TradeRecord:
    """決済完了トレード履歴"""
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    amount: float
    leverage: float
    gross_pnl: float
    fee: float
    net_pnl: float
    return_pct: float
    opened_at: str
    closed_at: str


class VirtualAccount:
    """
    ユーザーごとの仮想投資口座
    """

    def __init__(self, user_id: str, user_name: str, initial_cash: float = 10_000_000.0):
        self.user_id = user_id
        self.user_name = user_name
        self.initial_cash = initial_cash
        self.cash = initial_cash  # 利用可能現金残高
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeRecord] = []
        self.fee_rate = 0.0003  # 片道取引手数料・スプレッド (0.03%)
        self.equity_peak = initial_cash
        self.max_drawdown = 0.0

    @property
    def equity(self) -> float:
        """有効証拠金（現金 + 全ポジションの含み損益）"""
        unrealized_total = sum(p.unrealized_pnl for p in self.positions.values())
        return self.cash + unrealized_total

    def update_market_price(self, symbol: str, current_price: float):
        """市場価格が動いた際に保有ポジションの現在値を更新し、ドローダウンを再計算"""
        for pos in self.positions.values():
            if pos.symbol == symbol:
                pos.current_price = current_price

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
        新規ポジションを成行でオープンする。
        """
        side = side.upper()
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'.")

        required_margin = (current_price * amount) / leverage
        fee = (current_price * amount) * self.fee_rate

        if self.cash < (required_margin + fee):
            raise ValueError(f"資金不足: 必要証拠金+手数料 {required_margin + fee:.1f} に対して残高 {self.cash:.1f}")

        # 手数料引き落とし
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
            sl_price=sl_price
        )
        self.positions[pos_id] = pos
        return pos

    def close_position(self, position_id: str, current_price: float) -> TradeRecord:
        """
        保有ポジションを決済（エグジット）する。
        """
        if position_id not in self.positions:
            raise KeyError(f"Position ID not found: {position_id}")

        pos = self.positions.pop(position_id)
        pos.current_price = current_price

        multiplier = 1.0 if pos.side == "BUY" else -1.0
        gross_pnl = (current_price - pos.entry_price) * pos.amount * multiplier * pos.leverage
        exit_fee = (current_price * pos.amount) * self.fee_rate
        net_pnl = gross_pnl - exit_fee

        # 口座現金の反映
        self.cash += net_pnl

        trade_record = TradeRecord(
            trade_id=str(uuid.uuid4())[:8],
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=current_price,
            amount=pos.amount,
            leverage=pos.leverage,
            gross_pnl=round(gross_pnl, 2),
            fee=round(exit_fee, 2),
            net_pnl=round(net_pnl, 2),
            return_pct=round(pos.unrealized_return_pct, 2),
            opened_at=pos.opened_at,
            closed_at=datetime.now().isoformat()
        )
        self.trade_history.append(trade_record)

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
        payout_rate = (self.equity / self.initial_cash) * 100.0

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
