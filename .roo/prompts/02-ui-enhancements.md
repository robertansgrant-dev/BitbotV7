# Prompt: UI Enhancements - Collapsible Panels & Live Code Panel
Generated: 2026-03-29T23:15:00Z
Task Type: feature

## Context

### Project Overview
BitbotV7 is a cryptocurrency trading bot with a Flask web interface. The current UI displays:
- Price chart with indicators (MACD, SMAs)
- Portfolio statistics and open position details
- Trade history table
- Bot controls and configuration

### Current Implementation State
The existing [`src/ui/templates/index.html`](../src/ui/templates/index.html:1) has a basic two-panel layout but lacks:
- Collapsible sections for better space management
- Detailed trade entry/exit logging with timestamps
- A live code execution panel to visualize bot decisions in real-time

### Relevant Code References
- [`src/ui/app.py`](../src/ui/app.py:1) - Flask application setup and routes
- [`src/bot/bot_runner.py`](../src/bot/bot_runner.py:1) - Main bot logic that generates signals
- [`src/data/models/trade.py`](../src/data/models/trade.py:1) - Trade data model with entry/exit details

## Task

Enhance the BitbotV7 web interface with three major improvements:

### 1. Collapsible Panels
Make all informational panels collapsible to allow users to focus on relevant sections and maximize screen space.

**Requirements:**
- Add collapse toggle buttons (chevron icons) to each card header
- Use Bootstrap's collapse component for smooth animations
- Persist panel states in localStorage so preferences survive page refreshes
- Default state: all panels collapsed except Price, Chart, and Open Position

### 2. Enhanced Trade Logging Display
Replace the basic trade history table with a detailed view showing entry/exit information.

**Requirements:**
- Create a new "Trade Log" section below the chart area
- Display each completed trade with:
  - Trade ID (clickable, links to details if available)
  - Side (LONG/SHORT) with color coding
  - Entry price and timestamp
  - Exit price and timestamp
  - Quantity traded
  - Realized P&L with color coding
  - Signal type that triggered the trade
  - Duration of the trade (time between entry and exit)
- Add filtering options:
  - Filter by side (ALL/LONG/SHORT)
  - Filter by date range (today, last 7 days, custom)
  - Sort by P&L, duration, or timestamp
- Show summary statistics above the log:
  - Total trades today/week/month
  - Win rate for each period
  - Average trade duration
  - Best/worst performing trades

### 3. Live Code Execution Panel
Add a new panel that displays real-time bot decision-making process.

**Requirements:**
- Create a dedicated "Live Bot Activity" section with the following subsections:
  
  **a) Signal Generation Log:**
  - Display each signal generation event as it happens
  - Show: timestamp, signal type (BUY/SELL/HOLD), confidence level, triggering indicators
  - Format as a scrollable terminal-like output
  
  **b) Risk Assessment Results:**
  - When the bot evaluates a potential trade, show:
    - Current position size vs. risk limits
    - Stop loss and take profit calculations
    - Risk/reward ratio being proposed
    - Whether the trade passes risk checks
  
  **c) Position Management Events:**
  - Log when positions are opened/closed
  - Show: entry/exit prices, quantities, reasons for closure (TP hit, SL hit, manual, time-based)
  
  **d) Real-time Metrics Display:**
  - Current ATR value
  - Volume ratio compared to average
  - RSI reading
  - MACD histogram value
  - Current trend direction (based on SMA alignment)

**Technical Implementation:**
- Use WebSocket or Server-Sent Events (SSE) for real-time updates
- If WebSockets are not feasible, implement a lightweight polling mechanism with shorter intervals (1-2 seconds)
- Create new API endpoints in [`src/ui/app.py`](../src/ui/app.py:1):
  - `/api/stream/activity` - SSE endpoint for live activity feed
  - `/api/stream/metrics` - SSE endpoint for real-time metrics
- Add CSS styling to make the code panel look like a terminal/IDE:
  - Dark background with monospace font
  - Syntax highlighting for different event types
  - Auto-scroll to latest entries
  - Timestamp formatting consistent with trading conventions

## Requirements

### Coding Standards (from `.roo/rules/01-coding-standards.md`)
- Follow PEP 8 style guidelines
- Maximum line length: 100 characters
- Type hints required for all function arguments and return types
- All public functions must have docstrings
- Use meaningful variable names

### Architecture Constraints (from `.roo/rules/02-architecture.md`)
- Keep changes within the `src/ui/` directory where possible
- If adding new API endpoints, ensure they follow existing patterns
- No circular imports
- Configuration should remain in environment variables

### Testing Requirements
- No unit tests required for UI changes (handled by browser testing)
- Ensure all interactive elements work correctly across browsers
- Test collapsible panel state persistence

## Code Reference Section

### Files to Modify
1. **Primary:** [`src/ui/templates/index.html`](../src/ui/templates/index.html:1)
   - Add collapse functionality to existing cards
   - Create new Trade Log section structure
   - Create Live Bot Activity panel structure
   - Add JavaScript for real-time updates

2. **Secondary:** [`src/ui/app.py`](../src/ui/app.py:1)
   - Add SSE endpoints for live activity streaming
   - Ensure trade data includes full entry/exit details

3. **Optional Enhancement:** [`src/bot/bot_runner.py`](../src/bot/bot_runner.py:1)
   - May need to emit additional logging events for the activity panel

### Existing Patterns to Follow
- Bootstrap 5 collapse component:
```html
<div class="card">
  <div class="card-header" data-bs-toggle="collapse" data-bs-target="#panelId">
    Panel Title
  </div>
  <div id="panelId" class="collapse">Content</div>
</div>
```
- Bootstrap collapse with show/hide classes for custom toggles
- localStorage API for state persistence:
```javascript
localStorage.setItem('collapsedPanels', JSON.stringify(['panel1', 'panel2']));
```

## Success Criteria

### Functional Requirements
- [ ] All panels can be collapsed and expanded via click on header
- [ ] Panel collapse states persist across page refreshes
- [ ] Trade log displays all required entry/exit information
- [ ] Trade log filtering works correctly (side, date range)
- [ ] Live Bot Activity panel updates in real-time without manual refresh
- [ ] All new UI elements are responsive and work on mobile devices

### Visual Requirements
- [ ] Collapsible panels have smooth transition animations
- [ ] Trade log is readable with clear visual hierarchy
- [ ] Live activity panel has terminal-like appearance
- [ ] Color coding is consistent (green for positive, red for negative)
- [ ] All text is legible against dark background

### Performance Requirements
- [ ] Real-time updates do not cause UI lag or freezing
- [ ] Trade log can handle 100+ entries without performance degradation
- [ ] Page load time increases by less than 500ms due to new features

## Additional Notes

### Design Considerations
- The Live Bot Activity panel should be scrollable and auto-scroll to show latest events
- Consider adding a "clear" button for the activity log (optional)
- Trade log entries should have hover states showing additional details in tooltips
- Consider adding keyboard shortcuts for collapsing/expanding all panels

### Future Enhancements (not required now)
- Export trade history to CSV
- Save custom panel layouts as presets
- Add chart annotations showing entry/exit points based on trades