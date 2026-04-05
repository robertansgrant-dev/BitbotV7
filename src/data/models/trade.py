"""Trade dataclass representing a completed trade."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Trade:
    """A completed (closed) trade."""

    trade_id: str
    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    exit_price: float
    quantity: float
    timestamp: datetime
    pnl: float
    entry_time: Optional[datetime] = None
    mode: str = "paper"
    style: str = "scalping"
    signal_type: Optional[str] = None
    exit_reason: Optional[str] = None
    # Round-trip fees (entry + exit) at the configured fee_rate
    fees: float = 0.0

    @property
    def net_pnl(self) -> float:
        """PnL after deducting round-trip fees."""
        return self.pnl - self.fees
