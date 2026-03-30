"""Position dataclass representing an open trading position."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Position:
    """An open trading position."""

    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    current_price: float
    quantity: float
    open_time: datetime
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    signal_type: Optional[str] = None

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L in quote currency."""
        if self.side == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized P&L as a percentage of position cost."""
        cost = self.entry_price * self.quantity
        if cost == 0:
            return 0.0
        return (self.unrealized_pnl / cost) * 100
