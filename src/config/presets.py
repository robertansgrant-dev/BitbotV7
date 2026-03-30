"""Frozen dataclass presets for each trading style."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class StylePreset:
    """Immutable trading style configuration."""

    name: str
    position_size_pct: float
    stop_loss_pct: float
    risk_reward: float
    max_daily_trades: int
    sma_fast: int
    sma_slow: int
    sma_trend: int
    htf_timeframe: str
    trailing_stop: bool


SCALPING = StylePreset(
    name="scalping",
    position_size_pct=20.0,
    stop_loss_pct=0.4,
    risk_reward=2.0,
    max_daily_trades=100,
    sma_fast=8,
    sma_slow=20,
    sma_trend=200,
    htf_timeframe="5m",
    trailing_stop=False,
)

DAY_TRADING = StylePreset(
    name="day_trading",
    position_size_pct=60.0,
    stop_loss_pct=1.5,
    risk_reward=2.5,
    max_daily_trades=8,
    sma_fast=20,
    sma_slow=50,
    sma_trend=200,
    htf_timeframe="4h",
    trailing_stop=True,
)

SWING_TRADING = StylePreset(
    name="swing_trading",
    position_size_pct=90.0,
    stop_loss_pct=3.5,
    risk_reward=4.0,
    max_daily_trades=3,
    sma_fast=30,
    sma_slow=100,
    sma_trend=200,
    htf_timeframe="1d",
    trailing_stop=True,
)

PRESETS: dict[str, StylePreset] = {
    "scalping": SCALPING,
    "day_trading": DAY_TRADING,
    "swing_trading": SWING_TRADING,
}


def get_preset(style: Literal["scalping", "day_trading", "swing_trading"]) -> StylePreset:
    """Return the preset for the given trading style."""
    return PRESETS[style]
