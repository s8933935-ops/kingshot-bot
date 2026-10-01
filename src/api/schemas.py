"""
APIデータスキーマ定義 (Pydantic)
リクエストとレスポンスのデータ型を厳密に定義します。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    """新規仮想注文リクエスト"""
    user_id: str = Field(..., description="ユーザーID (例: 'user_01')")
    symbol: str = Field(default="GC=F", description="銘柄コード (例: 'GC=F')")
    side: str = Field(..., description="'BUY' または 'SELL'")
    amount: float = Field(..., gt=0, description="取引数量 (例: 10.0)")
    leverage: float = Field(default=1.0, ge=1.0, le=25.0, description="レバレッジ倍率")


class CloseOrderRequest(BaseModel):
    """ポジション決済リクエスト"""
    user_id: str = Field(..., description="ユーザーID")
    position_id: str = Field(..., description="決済するポジションID")


class AutopilotToggleRequest(BaseModel):
    """オートパイロットON/OFFリクエスト"""
    user_id: str = Field(..., description="ユーザーID")
    is_active: bool = Field(..., description="True: 起動, False: 停止")
    allocated_capital: float = Field(default=3_000_000.0, gt=0, description="運用割当資金 (円)")
    daily_max_loss_pct: float = Field(default=3.0, gt=0, le=20.0, description="日次最大許容損失率 (%)")
    strategy_style: str = Field(default="day_trade", description="戦術スタイル ('scalping', 'day_trade', 'swing', 'medium_term', 'long_term')")


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
