"""
APIデータスキーマ定義 (Pydantic)
リクエストとレスポンスのデータ型を厳密に定義します。
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    """新規仮想注文リクエスト"""
    user_id: str = Field(..., min_length=1, max_length=50, description="ユーザーID (例: 'user_01')")
    symbol: str = Field(default="GC=F", min_length=1, max_length=20, description="銘柄コード (例: 'GC=F')")
    side: Literal["BUY", "SELL"] = Field(..., description="'BUY' または 'SELL'")
    amount: float = Field(..., gt=0, description="取引数量 (例: 10.0)")
    leverage: float = Field(default=1.0, ge=1.0, le=25.0, description="レバレッジ倍率")


class CloseOrderRequest(BaseModel):
    """ポジション決済リクエスト"""
    user_id: str = Field(..., min_length=1, max_length=50, description="ユーザーID")
    position_id: str = Field(..., min_length=1, description="決済するポジションID")


class LimitOrderRequest(BaseModel):
    """指値注文リクエスト"""
    user_id: str = Field(..., min_length=1, max_length=50, description="ユーザーID")
    symbol: str = Field(default="GC=F", min_length=1, max_length=20, description="銘柄コード")
    side: Literal["BUY", "SELL"] = Field(..., description="'BUY' または 'SELL'")
    target_price: float = Field(..., gt=0, description="指値価格")
    amount: float = Field(..., gt=0, description="取引数量")
    leverage: float = Field(default=1.0, ge=1.0, le=25.0, description="レバレッジ倍率")
    tp_price: Optional[float] = Field(default=None, description="目標利確価格")
    sl_price: Optional[float] = Field(default=None, description="損切り価格")


class CancelLimitOrderRequest(BaseModel):
    """指値注文取消リクエスト"""
    user_id: str = Field(..., min_length=1, max_length=50, description="ユーザーID")
    order_id: str = Field(..., min_length=1, description="取消対象の注文ID")


class SymbolAutopilotConfigRequest(BaseModel):
    """個別銘柄AIオートパイロット設定リクエスト"""
    user_id: str = Field(..., min_length=1, max_length=50, description="ユーザーID")
    symbol: str = Field(..., min_length=1, max_length=20, description="銘柄コード")
    is_active: bool = Field(..., description="個別AI稼働フラグ")
    strategy_style: Literal["scalping", "day_trade", "swing", "medium_term", "long_term"] = Field(
        default="day_trade",
        description="戦術スタイル"
    )
    allocated_capital: float = Field(default=1_000_000.0, gt=0, description="銘柄別割当資金 (円)")
    use_limit_orders: bool = Field(default=True, description="AI指値注文を活用するか (スリッページゼロ戦略)")


class AutopilotToggleRequest(BaseModel):
    """オートパイロットON/OFFリクエスト"""
    user_id: str = Field(..., min_length=1, max_length=50, description="ユーザーID")
    is_active: bool = Field(..., description="True: 起動, False: 停止")
    allocated_capital: float = Field(default=3_000_000.0, gt=0, description="運用割当資金 (円)")
    daily_max_loss_pct: float = Field(default=3.0, gt=0, le=20.0, description="日次最大許容損失率 (%)")
    strategy_style: Literal["scalping", "day_trade", "swing", "medium_term", "long_term"] = Field(
        default="day_trade",
        description="戦術スタイル ('scalping', 'day_trade', 'swing', 'medium_term', 'long_term')"
    )
    use_limit_orders: bool = Field(default=True, description="全銘柄一括指値戦略フラグ")


class PanicStopRequest(BaseModel):
    """緊急全停止リクエスト"""
    user_id: str = Field(..., description="ユーザーID")


class RaceCardResponse(BaseModel):
    """競馬新聞風 出走表レスポンス"""
    symbol: str
    target_date: str
    current_price: float
    ai_mark: str
    ai_stance: str
    confidence: str
    prob_up_pct: float
    prob_down_pct: float
    paddock_comment: str
    rsi_14: float
    macd: float
    return_1d_pct: float
    current_atr: float = 0.0
    atr_pct: float = 0.0
    regime_state: str = "NORMAL"
    htf_daily_trend: float = 0.0
    meta_bet_size_pct: float = 100.0
    meta_confidence: str = "NORMAL"


class UserStatsResponse(BaseModel):
    """ユーザー口座・成績レスポンス"""
    user_id: str
    user_name: str
    equity: float
    cash: float
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    payout_rate_pct: float
    max_drawdown_pct: float
    grand_prix_score: float
    certified_rank: str


class LeaderboardItem(UserStatsResponse):
    """ランキング一覧用アイテム"""
    rank: int


class ResetAccountRequest(BaseModel):
    """口座リセットリクエスト"""
    user_id: str = "trader_1"
    initial_cash: float = 10_000_000.0


class SetStrategyRequest(BaseModel):
    """AI戦略変更リクエスト"""
    user_id: str = "trader_1"
    strategy_style: str = "day_trade"

