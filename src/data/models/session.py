"""Session dataclass representing a market session analysis snapshot."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Session:
    """Market session analysis snapshot."""

    start_time: datetime
    end_time: Optional[datetime]
    trades_count: int
    avg_volatility: float
    recommendation: str
    session_name: Literal["Asian", "EU", "US", "Off"]
    atr: float = 0.0
    volume_ratio: float = 1.0
