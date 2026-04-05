# Prompt: Comprehensive Activity Logging for Bot Runner
Generated: 2026-03-30T13:00:00Z
Task Type: bugfix

## Context

### Problem Description
The bot's activity feed shows no entries for 30+ minutes even though the bot is running. This occurs because several early-return paths in `_seek_entry()` and `_manage_position()` skip logging entirely, leaving the UI unaware of what's happening.

### Current Implementation State
- Bot runs successfully but silently fails to log certain conditions
- Activity events are only logged when:
  - Position opens/closes
  - A signal is found (HOLD state)
  - Emergency stop activates
- Early returns in `_seek_entry()` and `_manage_position()` do NOT create activity events

### Relevant Code References
- [`src/bot/bot_runner.py`](src/bot/bot_runner.py:206-237): `_seek_entry()` method with silent early returns
- [`src/bot/bot_runner.py`](src/bot/bot_runner.py:190-204): `_manage_position()` method with silent early returns
- [`src/bot/analysis/session_analyzer.py`](src/bot/analysis/session_analyzer.py:24-30): Session detection logic

## Task

Modify the bot runner to ensure ALL code paths create activity events, including:
1. Daily trade limit reached (no entry attempts)
2. Off-hours session detected (skipping entries)
3. API/klines fetch failures
4. Trailing stop updates during position management
5. Any unexpected None position states

## Requirements

### Coding Standards (from .roo/rules/01-coding-standards.md)
- Follow PEP 8 with maximum 100 character line length
- Use type hints for all function arguments and return types
- Add docstrings to any new helper functions
- Log messages should explain WHY, not WHAT

### Architecture Constraints (from .roo/rules/02-architecture.md)
- Keep changes within `src/bot/bot_runner.py`
- Maintain thread-safety with existing locking patterns
- Use existing `state.log_activity()` method for UI-visible events
- Use `logger.info/warning/error` for console-only logs

### Logging Levels to Use
| Event Type | Level | Purpose |
|------------|-------|---------|
| Daily trade limit reached | INFO | Informative, expected behavior |
| Off-hours session | INFO | Informative, expected behavior |
| API/klines fetch failure | ERROR | Actionable, indicates problem |
| Trailing stop update | DEBUG | Detailed tracking (optional) |
| Unexpected None position | WARNING | Investigate potential bug |

### Specific Code Changes Required

#### 1. Modify `_seek_entry()` - Daily Trade Limit Check
**Location:** Line 211-212 in `src/bot/bot_runner.py`

**Current code:**
```python
if state.portfolio.daily_trades >= preset.max_daily_trades:
    return
```

**New code should be:**
```python
if state.portfolio.daily_trades >= preset.max_daily_trades:
    logger.info("Daily trade limit reached — no entry attempts")
    state.log_activity(
        "INFO", 
        f"Daily trade limit ({preset.max_daily_trades}) reached — no entry attempts",
        {"daily_trades": state.portfolio.daily_trades, "max_trades": preset.max_daily_trades}
    )
    return
```

#### 2. Modify `_seek_entry()` - Session Check
**Location:** Line 215-216 in `src/bot/bot_runner.py`

**Current code:**
```python
session = get_current_session()
if session == "Off":
    return
```

**New code should be:**
```python
session = get_current_session()
if session == "Off":
    logger.info("Off-session hours — skipping entries")
    state.log_activity(
        "INFO", 
        f"Off-session hours — skipping entries (session={session})",
        {"session": session}
    )
    return
```

#### 3. Modify `_seek_entry()` - Klines Fetch Exception
**Location:** Line 223-225 in `src/bot/bot_runner.py`

**Current code:**
```python
except Exception as exc:
    logger.error("Klines fetch failed: %s", exc)
    return
```

**New code should be:**
```python
except Exception as exc:
    error_msg = f"Klines fetch failed: {str(exc)}"
    logger.error(error_msg, exc_info=True)
    state.log_activity(
        "ERROR", 
        error_msg,
        {"symbol": state.settings.symbol}
    )
    return
```

#### 4. Modify `_manage_position()` - None Position Check
**Location:** Line 194-195 in `src/bot/bot_runner.py`

**Current code:**
```python
if pos is None:
    return
```

**New code should be:**
```python
if pos is None:
    logger.warning("Position unexpectedly None in _manage_position")
    state.log_activity(
        "WARNING", 
        "Unexpected position state — position is None during management check",
        {}
    )
    return
```

#### 5. Add Periodic Trailing Stop Update Logging (Optional Enhancement)
**Location:** After line 200 in `src/bot/bot_runner.py`

Add a heartbeat-style log for trailing stop updates:
```python
with state._lock:
    pos.current_price = price
    if state.preset.trailing_stop:
        old_stop = pos.trailing_stop
        pos.trailing_stop = update_trailing_stop(pos, price, state.preset)
        
        # Log significant trailing stop changes (every 5 ticks or on change > threshold)
        if self._tick_count % 5 == 0 and old_stop != pos.trailing_stop:
            state.log_activity(
                "INFO", 
                f"Trailing stop updated: {old_stop:.2f} → {pos.trailing_stop:.2f}",
                {"old_stop": old_stop, "new_stop": pos.trailing_stop, "price": price}
            )
```

Note: You'll need to add `self._tick_count = 0` in `__init__` and increment it in the loop.

## Success Criteria

- [ ] All early-return paths in `_seek_entry()` create activity events
- [ ] All early-return paths in `_manage_position()` create activity events  
- [ ] Activity feed shows regular updates even during HOLD periods
- [ ] Error conditions visible in UI activity feed (not just console logs)
- [ ] No silent returns - every code path creates an activity event or log entry

## Testing Recommendations

After implementation:
1. Verify all early-return paths now create activity events by checking the UI
2. Check that error conditions are visible in UI (not just console logs)
3. Confirm activity feed shows regular updates even during HOLD periods
4. Test with simulated API failures to verify error logging works
5. Monitor for any unexpected None position warnings

## Additional Notes

- The `state.log_activity()` method already handles thread-safety internally
- Activity events are stored in a deque with maxlen=300 (ring buffer)
- Consider adding a heartbeat mechanism if activity still goes silent after these changes
- Line numbers may shift slightly as you make changes - verify context before editing
