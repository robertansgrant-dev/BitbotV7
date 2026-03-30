# Prompt: SMA Trend Line Color Change to Yellow
Generated: 2026-03-30T00:29:00Z
Task Type: bugfix

## Context
The price chart shows only 3 lines but should display 4. The SMA Trend line is not visible because it uses an orange color (#f7931a) that blends with the SMA Fast line (also orange-ish #f0883e).

## Problem Analysis
Looking at `src/ui/templates/index.html` chart configuration:
- **Price**: `#58a6ff` (blue) - visible ✓
- **SMA Fast**: `#f0883e` (orange-red) - visible but similar to trend
- **SMA Slow**: `#3fb950` (green) - visible ✓  
- **SMA Trend**: `#f7931a` (orange) - NOT VISIBLE, blends with SMA Fast

Both SMA Fast and SMA Trend use orange colors making them indistinguishable.

## Task
Change the SMA Trend line color from orange to yellow so it's clearly distinguishable.

## Requirements
- Make minimal change - only modify the color value
- Use yellow/gold color that matches your UI theme (`#e3b341` is already used for signal badges)

## Code Reference
File: `src/ui/templates/index.html`, line 801

Current code (line 801):
```javascript
{ label: 'SMA Trend', data: smat, borderColor: '#f7931a', borderWidth: 1,
```

Required change:
```javascript
{ label: 'SMA Trend', data: smat, borderColor: '#e3b341', borderWidth: 1,
```

## Success Criteria
- SMA Trend line appears as yellow/gold on the chart
- Clearly distinguishable from SMA Fast (orange-red) and SMA Slow (green)
- All four lines visible: Price (blue), SMA Fast (orange-red), SMA Slow (green), SMA Trend (yellow)
- No other visual elements affected
