"""Pydantic request/response schemas for the REST API."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    running: bool
    mode: str
    style: str
    emergency_stop: bool
    last_error: Optional[str]
    last_price: float
    circuit_breaker_active: bool = False
    circuit_breaker_until: Optional[str] = None  # ISO timestamp or None
    entry_cooldown_until: Optional[str] = None   # ISO timestamp or None


class ActionResponse(BaseModel):
    success: bool
    message: str


class SwitchModeRequest(BaseModel):
    mode: Literal["paper", "testnet", "live"]


class MarketResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float


class CandleData(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    sma_fast: Optional[float] = None
    sma_slow: Optional[float] = None
    sma_trend: Optional[float] = None


class ChartResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: list[CandleData]
    macd: list[dict[str, Any]]


class SessionResponse(BaseModel):
    session: str
    recommendation: str
    atr: float
    volume_ratio: float


class PortfolioResponse(BaseModel):
    initial_capital: float
    current_capital: float
    daily_pnl: float
    total_pnl: float
    total_pnl_pct: float
    daily_trades: int
    total_trades: int
    win_rate: float
    position: Optional[dict[str, Any]] = None


class TradeHistoryResponse(BaseModel):
    trades: list[dict[str, Any]]
    open_position: Optional[dict[str, Any]] = None


class ManualPositionRequest(BaseModel):
    side: Literal["LONG", "SHORT"]


class ConfigResponse(BaseModel):
    style: str
    position_size_pct: float
    stop_loss_pct: float
    risk_reward: float
    max_daily_trades: int
    sma_fast: int
    sma_slow: int
    sma_trend: int
    htf_timeframe: str
    trailing_stop: bool


class ConfigUpdateRequest(BaseModel):
    style: Optional[Literal["scalping", "day_trading", "swing_trading"]] = None
    max_daily_loss_pct: Optional[float] = Field(default=None, ge=0.1, le=50.0)
