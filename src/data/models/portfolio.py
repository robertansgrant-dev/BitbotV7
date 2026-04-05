"""Portfolio dataclass representing capital and trade statistics."""

from dataclasses import dataclass


@dataclass
class Portfolio:
    """Trading portfolio state."""

    initial_capital: float
    current_capital: float
    daily_pnl: float = 0.0
    daily_loss_pct: float = 0.0
    daily_trades: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    # Fee and drawdown tracking
    total_fees: float = 0.0
    peak_capital: float = 0.0   # highest capital reached; initialised to initial_capital on first update
    max_drawdown: float = 0.0   # largest peak-to-trough drop (absolute, positive number)

    @property
    def total_pnl(self) -> float:
        """Total P&L from initial capital."""
        return self.current_capital - self.initial_capital

    @property
    def total_pnl_pct(self) -> float:
        """Total P&L as a percentage of initial capital."""
        if self.initial_capital == 0:
            return 0.0
        return (self.total_pnl / self.initial_capital) * 100

    @property
    def win_rate(self) -> float:
        """Percentage of winning trades."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def update_drawdown(self) -> None:
        """Recalculate peak and max drawdown after each capital change."""
        if self.peak_capital == 0.0:
            self.peak_capital = self.initial_capital
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        drawdown = self.peak_capital - self.current_capital
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
