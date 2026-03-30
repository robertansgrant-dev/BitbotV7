"""Session detection and market analysis utilities."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal

import pandas as pd

from src.bot.strategy.indicators import atr

logger = logging.getLogger(__name__)

SessionName = Literal["Asian", "EU", "US", "Off"]

# UTC hour ranges (inclusive start, exclusive end)
_SESSION_HOURS: dict[str, tuple[int, int]] = {
    "US": (13, 22),
    "EU": (7, 16),
    "Asian": (0, 8),
}


def get_current_session() -> SessionName:
    """Return the active trading session based on UTC time."""
    hour = datetime.now(timezone.utc).hour
    for name, (start, end) in _SESSION_HOURS.items():
        if start <= hour < end:
            return name  # type: ignore[return-value]
    return "Off"


def calculate_atr_value(df: pd.DataFrame, period: int = 14) -> float:
    """Return the latest ATR value, or 0.0 if insufficient data."""
    if len(df) < period + 1:
        return 0.0
    series = atr(df, period)
    val = series.iloc[-1]
    return float(val) if not pd.isna(val) else 0.0


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    """Return current volume divided by the rolling average volume."""
    if len(df) < period + 1:
        return 1.0
    avg = df["volume"].iloc[-period - 1: -1].mean()
    current = df["volume"].iloc[-1]
    return float(current / avg) if avg > 0 else 1.0


def get_session_recommendation(
    session: SessionName, atr_val: float, volume_ratio: float
) -> str:
    """Produce a plain-text trading recommendation for the session."""
    if session == "Off":
        return "Off-hours — low liquidity, avoid trading"
    activity = (
        "high volume" if volume_ratio > 1.5
        else ("low volume" if volume_ratio < 0.7 else "normal volume")
    )
    messages = {
        "Asian": f"Asian session — range-bound, {activity}",
        "EU": f"EU session — trending likely, {activity}",
        "US": f"US session — high volatility expected, {activity}",
    }
    return messages.get(session, f"{session} session")


@dataclass
class SignalStats:
    """Statistics for a single signal type."""

    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0

    @property
    def win_rate(self) -> float:
        """Win rate as a percentage (0.0 if no trades)."""
        return (self.wins / self.trades * 100) if self.trades > 0 else 0.0

    @property
    def avg_pnl(self) -> float:
        """Average P&L per trade (0.0 if no trades)."""
        return self.total_pnl / self.trades if self.trades > 0 else 0.0


@dataclass
class SignalStatsSummary:
    """Aggregated statistics across all signal types."""

    crossover: SignalStats = field(default_factory=SignalStats)
    pullback: SignalStats = field(default_factory=SignalStats)
    momentum: SignalStats = field(default_factory=SignalStats)
    breakout: SignalStats = field(default_factory=SignalStats)


@dataclass
class HourlyStats:
    """Statistics for a single UTC hour."""

    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0

    @property
    def win_rate(self) -> float:
        """Win rate as a percentage (0.0 if no trades)."""
        return (self.wins / self.trades * 100) if self.trades > 0 else 0.0

    @property
    def avg_pnl(self) -> float:
        """Average P&L per trade (0.0 if no trades)."""
        return self.total_pnl / self.trades if self.trades > 0 else 0.0


@dataclass
class HourlyStatsSummary:
    """Aggregated statistics across all UTC hours (0-23)."""

    data: Dict[int, HourlyStats] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for hour in range(24):
            self.data[hour] = HourlyStats()


def compute_signal_statistics(trades: List[dict]) -> SignalStatsSummary:
    """Aggregate trade data by signal type.

    Args:
        trades: List of trade dicts with 'signal_type' and 'pnl' keys.

    Returns:
        SignalStatsSummary with per-signal win/loss/P&L totals.
    """
    summary = SignalStatsSummary()
    signal_map = {
        "CROSSOVER": summary.crossover,
        "PULLBACK": summary.pullback,
        "MOMENTUM": summary.momentum,
        "BREAKOUT": summary.breakout,
    }

    for trade in trades:
        signal = trade.get("signal_type", "")
        stats = signal_map.get(signal)
        if stats is None:
            continue
        pnl = float(trade.get("pnl", 0))
        stats.trades += 1
        stats.total_pnl += pnl
        if pnl > 0:
            stats.wins += 1
        elif pnl < 0:
            stats.losses += 1

    return summary


def compute_hourly_statistics(trades: List[dict]) -> HourlyStatsSummary:
    """Aggregate trade data by entry hour (UTC).

    Args:
        trades: List of trade dicts with 'timestamp' (ISO 8601) and 'pnl' keys.

    Returns:
        HourlyStatsSummary with per-hour win/loss/P&L totals for hours 0-23.
    """
    summary = HourlyStatsSummary()

    for trade in trades:
        timestamp = trade.get("timestamp", "")
        if not timestamp:
            continue
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            hour = dt.hour
        except ValueError:
            continue
        pnl = float(trade.get("pnl", 0))
        summary.data[hour].trades += 1
        summary.data[hour].total_pnl += pnl
        if pnl > 0:
            summary.data[hour].wins += 1
        elif pnl < 0:
            summary.data[hour].losses += 1

    return summary
