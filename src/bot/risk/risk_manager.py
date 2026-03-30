"""Risk management: position sizing, stop levels, daily loss enforcement."""

import logging
from typing import Optional

from src.config.presets import StylePreset
from src.config.settings import Settings
from src.data.models.portfolio import Portfolio
from src.data.models.position import Position

logger = logging.getLogger(__name__)


def calculate_position_size(
    capital: float,
    price: float,
    preset: StylePreset,
    settings: Settings,
) -> float:
    """Return position quantity based on style preset and capital."""
    target_value = capital * (preset.position_size_pct / 100)
    max_value = capital * (settings.max_position_value_pct / 100)
    position_value = min(target_value, max_value)
    return position_value / price if price > 0 else 0.0


def calculate_stop_loss(entry: float, side: str, preset: StylePreset) -> float:
    """Return stop-loss price for a given entry and side."""
    factor = preset.stop_loss_pct / 100
    return entry * (1 - factor) if side == "LONG" else entry * (1 + factor)


def calculate_take_profit(entry: float, side: str, preset: StylePreset) -> float:
    """Return take-profit price based on risk:reward ratio."""
    factor = (preset.stop_loss_pct / 100) * preset.risk_reward
    return entry * (1 + factor) if side == "LONG" else entry * (1 - factor)


def update_trailing_stop(
    position: Position, current_price: float, preset: StylePreset
) -> float:
    """Return an updated trailing stop price (moves only in profit direction)."""
    if not preset.trailing_stop:
        return position.stop_loss
    factor = preset.stop_loss_pct / 100
    current_trailing = position.trailing_stop if position.trailing_stop else position.stop_loss
    if position.side == "LONG":
        new_stop = current_price * (1 - factor)
        return max(current_trailing, new_stop)
    new_stop = current_price * (1 + factor)
    return min(current_trailing, new_stop)


def check_daily_loss(portfolio: Portfolio, settings: Settings) -> bool:
    """Return True if the daily loss limit has been breached."""
    if portfolio.initial_capital == 0:
        return False
    loss_pct = abs(min(portfolio.daily_pnl, 0)) / portfolio.initial_capital * 100
    return loss_pct >= settings.max_daily_loss_pct


def should_close_position(
    position: Position, current_price: float, preset: StylePreset
) -> Optional[str]:
    """Return the close reason ('stop_loss' or 'take_profit'), or None."""
    effective_stop = (
        position.trailing_stop
        if preset.trailing_stop and position.trailing_stop
        else position.stop_loss
    )
    if position.side == "LONG":
        if current_price <= effective_stop:
            return "stop_loss"
        if current_price >= position.take_profit:
            return "take_profit"
    else:
        if current_price >= effective_stop:
            return "stop_loss"
        if current_price <= position.take_profit:
            return "take_profit"
    return None
