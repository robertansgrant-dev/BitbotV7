# Prompt: Remove Duplicated Metrics from Live Bot Activity Terminal
Generated: 2026-03-30T11:47:00Z
Task Type: refactor

## Context

### Project Overview
This is a cryptocurrency trading bot with a Flask-based web UI that displays real-time metrics, charts, and activity logs. The UI uses Bootstrap 5 for styling and Chart.js for market data visualization.

### Current State
The "Live Bot Activity" section in the UI contains significant visual clutter due to duplicated information. The terminal's metrics strip shows **6 different metrics** that are already displayed prominently elsewhere in the interface:

| Metric | Displayed Here (Line 384-409) | Also Shown In |
|--------|-------------------------------|---------------|
| Current Price | `mPrice` element | Left panel price card (line 102) |
| ATR Value | `mATR` element | Session card (line 225) |
| Volume Ratio | `mVolRatio` element | Session card (line 229) |
| Trading Session | `mSession` element | Session card (line 211) |
| Daily Trades Count | `mDailyTrades` element | Portfolio card (line 189) |
| Daily P&L | `mDayPnl` element | Portfolio card (line 181) |

### Relevant Files
- [`src/ui/templates/index.html`](src/ui/templates/index.html:384) - Main UI template with the "Live Bot Activity" section
- [`src/api/routes/activity_routes.py`](src/api/routes/activity_routes.py) - Backend API for activity events (no changes needed)

## Task

Remove the duplicated metrics strip from the "Live Bot Activity" terminal section to reduce visual clutter, especially on mobile devices. Keep only the terminal log which shows unique real-time events (BOT startup/shutdown, SIGNAL generation, POSITION_OPENED/POSITION_CLOSED, RISK alerts).

### Scope
**Include:**
- Remove the entire `.metrics-strip` div from the "Live Bot Activity" panel
- Update JavaScript to remove references to removed elements (`mPrice`, `mATR`, `mVolRatio`, `mSession`, `mDailyTrades`, `mDayPnl`)
- Keep the terminal log functionality intact (event filtering, clear button, auto-scroll)

**Exclude:**
- Do not modify the backend activity routes
- Do not change other panels that display these metrics (they should remain unchanged)
- Do not remove the terminal log itself - only the metrics strip above it

### Success Criteria
1. The "Live Bot Activity" section no longer displays a metrics strip with duplicated information
2. The terminal log continues to function correctly, showing real-time bot events
3. All JavaScript references to removed elements are cleaned up (no console errors)
4. The UI is cleaner and less cluttered, especially on mobile devices
5. No functionality is broken - the page loads without errors

## Requirements

### Coding Standards (from `.roo/rules/01-coding-standards.md`)
- Follow existing code style in `index.html`
- Maintain proper HTML structure and indentation
- Keep JavaScript organized with clear comments
- No trailing whitespace
- Maximum 100 characters per line where applicable

### Architecture Constraints (from `.roo/rules/02-architecture.md`)
- Single Responsibility Principle: This change only affects the "Live Bot Activity" section
- Configuration separation: No hardcoded values to add
- Keep UI components modular - don't break existing panel structure

### Testing Requirements
- Verify page loads without JavaScript errors in browser console
- Verify terminal log still shows events correctly
- Verify clear button functionality works
- Test on mobile viewport (responsive design)

## Code References

### Current "Live Bot Activity" Section (lines 384-409)
```html
<!-- Live Bot Activity Terminal -->
<div class="panel">
  <div class="panel-header">
    <h2><i class="fas fa-terminal"></i> Live Bot Activity</h2>
    <button id="clearActivityBtn" class="btn btn-sm btn-secondary" title="Clear log"><i class="fas fa-trash"></i></button>
  </div>
  <!-- Metrics Strip (DUPLICATED INFO) -->
  <div class="metrics-strip">
    <span><i class="fas fa-chart-line"></i> Price: <strong id="mPrice">$—</strong></span>
    <span><i class="fas fa-arrows-up-down"></i> ATR: <strong id="mATR">$—</strong></span>
    <span><i class="fas fa-volume-bar"></i> Vol Ratio: <strong id="mVolRatio">—</strong></span>
    <span><i class="fas fa-clock"></i> Session: <strong id="mSession">—</strong></span>
    <span><i class="fas fa-exchange-alt"></i> Daily Trades: <strong id="mDailyTrades">0</strong></span>
    <span><i class="fas fa-dollar-sign"></i> Day P&L: <strong id="mDayPnl">$—</strong></span>
  </div>
  <!-- Terminal Log -->
  <div class="activity-log" id="activityLog">
    ...
  </div>
  ...
</div>
```

### JavaScript References to Remove (lines ~500-600)
Look for these element references in the `updateMetrics()` function and related code:
- `document.getElementById('mPrice')`
- `document.getElementById('mATR')`
- `document.getElementById('mVolRatio')`
- `document.getElementById('mSession')`
- `document.getElementById('mDailyTrades')`
- `document.getElementById('mDayPnl')`

## Implementation Steps

1. **Remove HTML metrics strip** (lines 384-409)
   - Delete the `.metrics-strip` div and its contents
   - Keep the panel header, terminal log container, and clear button section

2. **Clean up JavaScript references**
   - Remove or comment out code that updates the removed elements in `updateMetrics()` function
   - Ensure no console errors are introduced

3. **Verify functionality**
   - Test page loads without errors
   - Verify terminal log still works correctly
   - Check responsive design on mobile viewport

## Success Checklist

- [ ] Metrics strip HTML removed from "Live Bot Activity" section
- [ ] JavaScript references to `mPrice`, `mATR`, `mVolRatio`, `mSession`, `mDailyTrades`, `mDayPnl` cleaned up
- [ ] No console errors when page loads
- [ ] Terminal log still displays events correctly
- [ ] Clear button functionality preserved
- [ ] UI is cleaner and less cluttered
- [ ] Mobile viewport tested (responsive design)
