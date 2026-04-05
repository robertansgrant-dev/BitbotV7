# Plan: Comprehensive Activity Logging for Bot Runner

## Problem Statement

The bot's activity feed shows no entries for 30+ minutes even though the bot is running. This occurs because several early-return paths in `_seek_entry()` and `_manage_position()` skip logging entirely, leaving the UI unaware of what's happening.

## Current Flow Analysis

```mermaid
flowchart TD
    A[Bot Tick] --> B{Emergency Stop?}
    B -->|Yes| C[Log Warning - Return]
    B -->|No| D[Check Daily Reset]
    D --> E[Get Price from API]
    E --> F{Price Fetch Failed?}
    F -->|Yes| G[Log Error to Console - Return NO UI UPDATE]
    F -->|No| H{Daily Loss Limit?}
    H -->|Yes| I[Activate Emergency Stop - Log]
    H -->|No| J{Has Position?}
    
    J -->|Yes| K[_manage_position]
    J -->|No| L[_seek_entry]
    
    L --> M{Daily Trades Maxed?}
    M -->|Yes| N[Return NO LOGGING]
    M -->|No| O{Valid Session?}
    O -->|No Off Hours| P[Return NO LOGGING]
    O -->|Yes| Q[Fetch Klines API]
    Q --> R{Klines Failed?}
    R -->|Yes| S[Log Error to Console - Return NO UI UPDATE]
    R -->|No| T[Get Signal]
    T --> U{Signal Found?}
    U -->|No| V[HOLD Log - OK]
    U -->|Yes| W[Open Position]
    
    K --> X{Position Exists?}
    X -->|No| Y[Return NO LOGGING]
    X -->|Z{Exit Condition Met?}
    Z -->|Yes| AA[Close Position - Log]
    Z -->|No| AB[Update Trailing Stop - No Log]
```

## Key Issues Identified

### Issue 1: Silent Returns in `_seek_entry()`
- **Line 211-212**: Daily trade limit reached → no log
- **Line 215-216**: Off-hours session → no log  
- **Line 223-225**: Klines API failure → only console log, no activity event

### Issue 2: Silent Returns in `_manage_position()`
- **Line 194-195**: Position is None (shouldn't happen but does) → no log
- **Line 197-200**: Trailing stop update → no activity logged

### Issue 3: Error Handling Swallows Exceptions
- API failures are logged to `logger` but don't create UI-visible activity events

## Proposed Solution

### Modified Flow

```mermaid
flowchart TD
    A[Bot Tick] --> B{Emergency Stop?}
    B -->|Yes| C[Log Activity Warning - Return]
    B -->|No| D[Check Daily Reset]
    D --> E[Get Price from API]
    E --> F{Price Fetch Failed?}
    F -->|Yes| G[Log Activity Error - Continue Tick]
    F -->|No| H{Daily Loss Limit?}
    H -->|Yes| I[Activate Emergency Stop - Log Activity]
    H -->|No| J{Has Position?}
    
    J -->|Yes| K[_manage_position]
    J -->|No| L[_seek_entry]
    
    L --> M{Daily Trades Maxed?}
    M -->|Yes| N[Log Activity Info - Return]
    M -->|No| O{Valid Session?}
    O -->|No Off Hours| P[Log Activity Info - Return]
    O -->|Yes| Q[Fetch Klines API]
    Q --> R{Klines Failed?}
    R -->|Yes| S[Log Activity Error - Continue Tick]
    R -->|No| T[Get Signal]
    T --> U{Signal Found?}
    U -->|No| V[HOLD Log Activity]
    U -->|Yes| W[Open Position - Log Activity]
    
    K --> X{Position Exists?}
    X -->|No| Y[Log Activity Warning - Return]
    X -->|Z{Exit Condition Met?}
    Z -->|Yes| AA[Close Position - Log Activity]
    Z -->|No| AB[Update Trailing Stop - Log Activity]
```

## Required Changes

### 1. Modify `_seek_entry()` to log all early returns

**Current code (lines 206-237):**
```python
def _seek_entry(self, client: BinanceClient, price: float) -> None:
    """Look for an entry signal and open a position if one is found."""
    state = self._state
    preset = state.preset

    if state.portfolio.daily_trades >= preset.max_daily_trades:
        return  # <-- ADD LOGGING HERE

    session = get_current_session()
    if session == "Off":
        return  # <-- ADD LOGGING HERE

    try:
        df = _to_df(client.get_klines(state.settings.symbol, "1m", 500))
        df_htf = _to_df(
            client.get_klines(state.settings.symbol, preset.htf_timeframe, 500)
        )
    except Exception as exc:
        logger.error("Klines fetch failed: %s", exc)
        return  # <-- ADD LOGGING HERE

    signal_type, direction = get_signal(df, df_htf, preset)
    if direction == "NONE":
        state.log_activity("SIGNAL", f"HOLD — no entry signal  price={price:.2f}", {"price": price})
        return

    # ... rest of function
```

**Required changes:**
- Add `state.log_activity()` before each early return with descriptive messages:
  - Daily trade limit: `"INFO", "Daily trade limit reached — no entry attempts"`
  - Off-hours session: `"INFO", f"Off-session hours — skipping entries (session={session})"`
  - API failure: `"ERROR", f"Klines fetch failed — {str(exc)}"`

### 2. Modify `_manage_position()` to log trailing stop updates

**Current code (lines 190-204):**
```python
def _manage_position(self, client: BinanceClient, price: float) -> None:
    """Update open position price/trailing stop and check exit conditions."""
    state = self._state
    pos = state.position
    if pos is None:
        return  # <-- ADD LOGGING HERE

    with state._lock:
        pos.current_price = price
        if state.preset.trailing_stop:
            pos.trailing_stop = update_trailing_stop(pos, price, state.preset)

    reason = should_close_position(pos, price, state.preset)
    if reason:
        self._close_position(client, price, reason)
```

**Required changes:**
- Add logging when position is None (shouldn't happen but log for safety)
- Add periodic activity logging when trailing stop is updated (e.g., every N ticks or on significant changes)

### 3. Consider adding heartbeat/logging interval

To ensure the UI always shows recent activity, consider:
- Logging a "heartbeat" event every N minutes regardless of other activity
- This ensures the feed never goes completely silent for extended periods

## Implementation Checklist

- [ ] Add logging to `_seek_entry()` daily trade limit check (line 211)
- [ ] Add logging to `_seek_entry()` session check (line 215)
- [ ] Add logging to `_seek_entry()` klines fetch exception (line 223)
- [ ] Add logging to `_manage_position()` None position check (line 194)
- [ ] Add periodic trailing stop update logging in `_manage_position()`
- [ ] Consider adding heartbeat mechanism for continuous activity feed

## Testing Recommendations

After implementation:
1. Verify all early-return paths now create activity events
2. Check that error conditions are visible in UI (not just console logs)
3. Confirm activity feed shows regular updates even during HOLD periods
4. Test with simulated API failures to verify error logging works

## Success Criteria

- [ ] No silent returns - every code path creates an activity event or log entry
- [ ] Activity feed never goes more than X minutes without entries (configurable)
- [ ] Error conditions visible in UI activity feed, not just console logs
- [ ] Clear distinction between INFO, WARNING, and ERROR level events
