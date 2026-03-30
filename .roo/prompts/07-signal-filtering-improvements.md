# Prompt: Signal Filtering & Performance Tracking Improvements
Generated: 2026-03-30T10:15:00Z
Task Type: feature-enhancement

## Context

### Project Overview
This is a Bitcoin scalping bot running on Raspberry Pi 3B with real-time signal generation, risk management, and performance tracking.

### Current Performance (8-hour session)
- **Total P&L:** +$1.46 despite 42.86% win rate (positive expectancy confirmed)
- **Trades:** 7 total (3 wins, 4 losses)
- **Signal breakdown:**
  - CROSSOVER: 100% win rate (1/1) — +$1.61
  - PULLBACK: 60% win rate (3/5) — +$2.26
  - BREAKOUT: 0% win rate (0/1) — -$0.80

### Identified Issues
1. **BREAKOUT signal** — False breakout entries due to lack of volume/momentum confirmation
2. **PULLBACK signal** — Enters during actual reversals without RSI validation
3. **Missing tracking** — No per-signal statistics aggregation in session analyzer

---

## Task

Implement three interconnected improvements:

### 1. BREAKOUT Signal Filtering Enhancement
**File:** `src/bot/strategy/signal_generator.py`

Modify `_breakout()` function to add:
- Volume confirmation: current volume must be ≥1.5x the 20-bar average
- Momentum filter: body-to-candle ratio must be ≥60% (strong candle close)
- Increased minimum data requirement: 50 bars instead of 22

### 2. PULLBACK Signal Filtering Enhancement
**File:** `src/bot/strategy/signal_generator.py`

Modify `_pullback()` function to add:
- RSI filter: for LONG entries, RSI must be ≥40 (not oversold); for SHORT, RSI ≤60 (not overbought)
- Increased tolerance: 0.2% → 0.3% to avoid entering on minor wicks

### 3. Signal Statistics Tracking
**File:** `src/bot/analysis/session_analyzer.py`

Add new data structures and functions:
- `SignalStats` dataclass with trades, wins, losses, total_pnl properties
- `SignalStatsSummary` aggregating all signal types
- `compute_signal_statistics()` function to aggregate from trade logs
- `HourlyStats` and `HourlyStatsSummary` for time-of-day analysis
- `compute_hourly_statistics()` function

---

## Requirements

### Coding Standards (from `.roo/rules/01-coding-standards.md`)
- Type hints required for all function arguments and return types
- Docstrings using triple-quoted strings with args, returns descriptions
- Follow existing naming conventions (snake_case for functions)
- Maximum 100 character line length

### Architecture Standards (from `.roo/rules/02-architecture.md`)
- Single Responsibility Principle: each function has one clear purpose
- No breaking changes to existing APIs
- Additions should be modular and testable independently

---

## Code References

### Current BREAKOUT Implementation (to modify)
`src/bot/strategy/signal_generator.py` lines 93-104:
```python
def _breakout(df: pd.DataFrame, trend: Trend) -> Direction:
    """Price exceeds 20-bar high/low in the trend direction."""
    if len(df) < 22:
        return "NONE"
    prev_high = df["high"].iloc[-21:-1].max()
    prev_low = df["low"].iloc[-21:-1].min()
    price = df["close"].iloc[-1]
    if trend == "UP" and price > prev_high:
        return "LONG"
    if trend == "DOWN" and price < prev_low:
        return "SHORT"
    return "NONE"
```

### Current PULLBACK Implementation (to modify)
`src/bot/strategy/signal_generator.py` lines 48-67:
```python
def _pullback(df: pd.DataFrame, preset: StylePreset, trend: Trend) -> Direction:
    """Price pulls back to fast SMA and bounces."""
    if len(df) < preset.sma_slow + 2:
        return "NONE"
    close = df["close"]
    fast = sma(close, preset.sma_fast)
    slow = sma(close, preset.sma_slow)
    price = close.iloc[-1]
    prev = close.iloc[-2]
    fast_val = fast.iloc[-1]
    slow_val = slow.iloc[-1]
    tol = fast_val * 0.002

    if trend == "UP" and fast_val > slow_val:
        if prev <= fast_val + tol and price > prev:
            return "LONG"
    if trend == "DOWN" and fast_val < slow_val:
        if prev >= fast_val - tol and price < prev:
            return "SHORT"
    return "NONE"
```

### Current Session Analyzer (to extend)
`src/bot/analysis/session_analyzer.py` — add new classes and functions after existing code.

---

## Implementation Details

### Modified `_breakout()` Function Specification:
```python
def _breakout(df: pd.DataFrame, trend: Trend) -> Direction:
    """Price exceeds 20-bar high/low with volume and momentum confirmation."""
    if len(df) < 50:
        return "NONE"
    
    prev_high = df["high"].iloc[-21:-1].max()
    prev_low = df["low"].iloc[-21:-1].min()
    price = df["close"].iloc[-1]
    volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].iloc[-21:-1].mean()
    
    # Volume must be 1.5x average for breakout validation
    if volume < avg_volume * 1.5:
        return "NONE"
    
    # Momentum: current candle should be strong (close near high/low)
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    candle_range = df["high"].iloc[-1] - df["low"].iloc[-1]
    if candle_range == 0 or body / candle_range < 0.6:
        return "NONE"
    
    if trend == "UP" and price > prev_high:
        return "LONG"
    if trend == "DOWN" and price < prev_low:
        return "SHORT"
    return "NONE"
```

### Modified `_pullback()` Function Specification:
```python
def _pullback(df: pd.DataFrame, preset: StylePreset, trend: Trend) -> Direction:
    """Price pulls back to fast SMA and bounces with RSI confirmation."""
    if len(df) < preset.sma_slow + 2:
        return "NONE"
    
    close = df["close"]
    fast = sma(close, preset.sma_fast)
    slow = sma(close, preset.sma_slow)
    price = close.iloc[-1]
    prev = close.iloc[-2]
    fast_val = fast.iloc[-1]
    slow_val = slow.iloc[-1]
    tol = fast_val * 0.003  # Increased from 0.2% to 0.3%

    if trend == "UP" and fast_val > slow_val:
        rsi_val = rsi(close).iloc[-1]
        if rsi_val >= 40 and prev <= fast_val + tol and price > prev:
            return "LONG"
    if trend == "DOWN" and fast_val < slow val:
        rsi_val = rsi(close).iloc[-1]
        if rsi_val <= 60 and prev >= fast_val - tol and price < prev:
            return "SHORT"
    return "NONE"
```

### New Signal Statistics Classes for `session_analyzer.py`:
```python
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class SignalStats:
    """Statistics for a single signal type."""
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.trades * 100) if self.trades > 0 else 0.0
    
    @property
    def avg_pnl(self) -> float:
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
        return (self.wins / self.trades * 100) if self.trades > 0 else 0.0
    
    @property
    def avg_pnl(self) -> float:
        return self.total_pnl / self.trades if self.trades > 0 else 0.0

@dataclass
class HourlyStatsSummary:
    """Aggregated statistics across all UTC hours (0-23)."""
    data: Dict[int, HourlyStats] = field(default_factory=dict)
    
    def __post_init__(self):
        for hour in range(24):
            self.data[hour] = HourlyStats()

def compute_signal_statistics(trades: List[dict]) -> SignalStatsSummary:
    """Aggregate trade data by signal type."""
    summary = SignalStatsSummary()
    
    for trade in trades:
        signal = trade.get("signal_type", "")
        if signal not in ["CROSSOVER", "PULLBACK", "MOMENTUM", "BREAKOUT"]:
            continue
        
        pnl = float(trade.get("pnl", 0))
        
        if signal == "CROSSOVER":
            summary.crossover.trades += 1
            summary.crossover.total_pnl += pnl
            if pnl > 0:
                summary.crossover.wins += 1
            elif pnl < 0:
                summary.crossover.losses += 1
        elif signal == "PULLBACK":
            summary.pullback.trades += 1
            summary.pullback.total_pnl += pnl
            if pnl > 0:
                summary.pullback.wins += 1
            elif pnl < 0:
                summary.pullback.losses += 1
        elif signal == "MOMENTUM":
            summary.momentum.trades += 1
            summary.momentum.total_pnl += pnl
            if pnl > 0:
                summary.momentum.wins += 1
            elif pnl < 0:
                summary.momentum.losses += 1
        elif signal == "BREAKOUT":
            summary.breakout.trades += 1
            summary.breakout.total_pnl += pnl
            if pnl > 0:
                summary.breakout.wins += 1
            elif pnl < 0:
                summary.breakout.losses += 1
    
    return summary

def compute_hourly_statistics(trades: List[dict]) -> HourlyStatsSummary:
    """Aggregate trade data by entry hour (UTC)."""
    from datetime import datetime
    
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
```

---

## Success Criteria

### Signal Filtering Improvements:
- [ ] BREAKOUT requires volume ≥ 1.5x average (20-bar rolling)
- [ ] BREAKOUT requires candle body ≥ 60% of range
- [ ] PULLBACK tolerance increased to 0.3%
- [ ] PULLBACK rejects LONG entries when RSI < 40
- [ ] PULLBACK rejects SHORT entries when RSI > 60

### Statistics Tracking:
- [ ] SignalStats correctly tracks trades, wins, losses counts
- [ ] Win rate property returns correct percentage (0.0 if no trades)
- [ ] Avg P&L property returns correct average (0.0 if no trades)
- [ ] `compute_signal_statistics()` properly aggregates all signal types
- [ ] `compute_hourly_statistics()` extracts hour correctly from ISO timestamps
- [ ] All 24 hours initialized in HourlyStatsSummary

### Code Quality:
- [ ] All new functions have type hints
- [ ] All new classes and functions have docstrings
- [ ] No breaking changes to existing APIs
- [ ] Follows project's coding standards (PEP 8, line length ≤100)

---

## Notes for Implementation

1. Import `SignalStats` and related types from the updated `session_analyzer.py` if needed elsewhere
2. The RSI import is already present in `signal_generator.py` via `from src.bot.strategy.indicators import sma, rsi`
3. Ensure all new code uses 4-space indentation consistent with existing project style
4. Keep line length under 100 characters; break long expressions appropriately
