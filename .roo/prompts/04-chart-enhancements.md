# Prompt: Chart Enhancements - SMA Trend Color & Entry/Exit Points
Generated: 2026-03-30T00:15:00Z
Task Type: feature

## Context

### Project Overview
BitbotV7 is a cryptocurrency trading bot with a web-based UI that displays real-time price charts, technical indicators (SMA, MACD), portfolio metrics, and trade history. The bot supports multiple trading styles (scalping, day_trading, swing_trading) and modes (paper, testnet, live).

### Current Implementation State
The chart rendering is in [`src/ui/templates/index.html`](src/ui/templates/index.html:731-799). Currently:
- SMA Trend line exists but uses gray color (`#8b949e`)
- Entry/exit points are not visually marked on the price chart
- Trade log shows entry/exit prices in table format but no visual markers on chart

## Task

### 1. Change SMA Trend Line Color to Yellow
**Location**: [`src/ui/templates/index.html`](src/ui/templates/index.html:752)

Change the SMA Trend dataset color from gray (`#8b949e`) to yellow (`#f7931a` - Bitcoin orange/yellow).

```javascript
// Current (line 752):
{ label: 'SMA Trend', data: smat, borderColor: '#8b949e', borderWidth: 1,
  pointRadius: 0, fill: false, borderDash: [8,4] },

// Change to:
{ label: 'SMA Trend', data: smat, borderColor: '#f7931a', borderWidth: 1,
  pointRadius: 0, fill: false, borderDash: [8,4] },
```

### 2. Add Entry/Exit Point Markers to Price Chart
**Location**: [`src/ui/templates/index.html`](src/ui/templates/index.html:731-769)

Add visual markers for entry and exit points on the price chart using Chart.js annotation plugin or custom drawing.

#### Implementation Approach:
Use Chart.js built-in point rendering by adding a secondary dataset that overlays markers at specific candle indices where trades occurred.

**Steps:**
1. Create a mapping of trade timestamps to candle indices in `renderChart()`
2. Add two new datasets for entry/exit markers:
   - Entry points: Green circles (`#3fb950`)
   - Exit points: Red circles (`#f85149`)

**Code to add after line 754 (after SMA Trend dataset):**
```javascript
// Add entry/exit marker datasets
const entryIndices = []; // Will be populated with candle indices where entries occurred
const exitIndices = [];  // Will be populated with candle indices where exits occurred
const entryValues = new Array(data.candles.length).fill(null);
const exitValues = new Array(data.candles.length).fill(null);

// Match trades to candles (simplified - needs actual trade data)
// For now, use placeholder markers at fixed positions
// In production, this should match against active position data
if (activePosition) {
  // Find entry candle index based on entry_time
  const entryTime = new Date(activePosition.entry_time).getTime();
  for (let i = 0; i < data.candles.length; i++) {
    const candleTime = new Date(data.candles[i].time).getTime();
    if (Math.abs(candleTime - entryTime) < 60000) { // within 1 minute
      entryIndices.push(i);
      entryValues[i] = data.candles[i].close;
      break;
    }
  }
}

// Add marker datasets to the chart config
datasets: [
  // ... existing price, SMA Fast, SMA Slow, SMA Trend ...
  {
    label: 'Entry',
    data: entryValues,
    type: 'line',
    borderColor: '#3fb950',
    borderWidth: 2,
    pointRadius: 6,
    pointBackgroundColor: '#3fb950',
    pointBorderColor: '#ffffff',
    pointBorderWidth: 2,
    fill: false,
    showLine: true,
    spanGaps: false,
    order: 10
  },
  {
    label: 'Exit',
    data: exitValues,
    type: 'line',
    borderColor: '#f85149',
    borderWidth: 2,
    pointRadius: 6,
    pointBackgroundColor: '#f85149',
    pointBorderColor: '#ffffff',
    pointBorderWidth: 2,
    fill: false,
    showLine: true,
    spanGaps: false,
    order: 10
  }
]
```

**Alternative simpler approach using Chart.js annotation plugin:**
If the above is too complex, use a tooltip-based approach where hovering over candles shows entry/exit info.

### 3. Add Entry/Exit Info Display Panel
**Location**: [`src/ui/templates/index.html`](src/ui/templates/index.html:200-250) - Session panel area

Add a new section below the session analysis that displays current position details:

```html
<!-- Add after line ~230 (after session recommendation) -->
<div class="mt-2">
  <div id="positionInfo" style="display:none;">
    <div class="small text-secondary">Position:</div>
    <div class="fw-semibold mb-1"><span id="posSide"></span> @ $<span id="posEntry"></span></div>
    <div class="small text-secondary">Exit: $<span id="posTarget"></span></div>
  </div>
</div>
```

Update the JavaScript to populate this panel when a position is active.

## Requirements

### Coding Standards (from `.roo/rules/01-coding-standards.md`)
- Line length: maximum 100 characters
- Type hints required for Python functions
- Use meaningful variable names
- Add comments explaining WHY, not WHAT

### Architecture Constraints (from `.roo/rules/02-architecture.md`)
- UI changes only in `src/ui/templates/index.html`
- No new dependencies without approval
- Keep changes minimal and focused

## Success Criteria

1. SMA Trend line displays in yellow/orange color (`#f7931a`)
2. Entry points appear as green markers on the price chart
3. Exit points appear as red markers on the price chart
4. Current position entry/exit info displayed in a panel below session analysis
5. Chart remains responsive and performs well with additional datasets
6. No breaking changes to existing functionality

## Code References

- Main chart rendering: [`src/ui/templates/index.html`](src/ui/templates/index.html:731-799)
- SMA Trend color definition: [`src/ui/templates/index.html`](src/ui/templates/index.html:752)
- Bot controls section: [`src/ui/templates/index.html`](src/ui/templates/index.html:109-158)
- Session panel: [`src/ui/templates/index.html`](src/ui/templates/index.html:200-250)

## Notes

The entry/exit markers should only appear when there's an active position. Consider adding a legend toggle or making the markers optional via settings for users who prefer cleaner charts.
