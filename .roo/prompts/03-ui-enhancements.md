# Prompt: UI Enhancements - BitbotV7 Renaming & Layout Improvements
Generated: 2026-03-29T23:56:00Z
Task Type: feature

## Context

### Project Overview
BitbotV7 is a Bitcoin trading bot with a Flask web UI and REST API. The project features:
- Three trading styles: scalping, day trading, swing trading
- Three modes: paper (simulated), testnet (Binance testnet), live
- Web dashboard at **http://localhost:8000**

### Current Implementation State
The UI is built with Bootstrap 5 and Chart.js. The main template is `src/ui/templates/index.html`.

### Relevant Code References
- Navbar brand: [`index.html`](src/ui/templates/index.html:81-83)
- Bot Controls section: [`index.html`](src/ui/templates/index.html:111-148)
- Manual Trade section (to be moved): [`index.html`](src/ui/templates/index.html:274-292)
- Timescale buttons: [`index.html`](src/ui/templates/index.html:228-235)
- Chart loading function: [`index.html`](src/ui/templates/index.html:732-742)

## Task Description

Perform the following UI enhancements:

### 1. Rename BitbotV7 → BitbotV7 (Remove "B" prefix, merge logo with text)
Replace the separate Bitcoin icon and text with a single unified element.

**Changes:**
- Update `<title>` tag from `BitbotV7` to `BitbotV7`
- Replace navbar brand markup:
  ```html
  <!-- BEFORE -->
  <span class="navbar-brand fw-bold">
    <i class="bi bi-currency-bitcoin text-warning"></i> BitbotV7
  </span>
  
  <!-- AFTER -->
  <span class="navbar-brand fw-bold">BitbotV7</span>
  ```
- Add CSS styling to make the "B" in "BitbotV7" appear as a Bitcoin symbol:
  ```css
  .navbar-brand .btc-symbol {
    color: #f7931a;
    font-weight: bold;
    font-size: 1.2em;
    text-shadow: 0 0 4px rgba(247, 147, 26, 0.5);
  }
  ```
- Update the brand HTML to use the styled span:
  ```html
  <span class="navbar-brand fw-bold">
    <span class="btc-symbol">B</span>itcoinV7
  </span>
  ```

### 2. Move Manual Trade Buttons to Bot Controls
Relocate manual trade buttons from the right panel into the Bot Controls section, placed directly below the Style dropdown.

**Changes:**
- Remove the entire "Manual Trade" card (lines 274-292 in index.html)
- Add the following markup after line 145 (after `</select>` closing tag of Style dropdown):
  ```html
  <div class="mt-3">
    <label class="stat-label mb-1">Manual Trade</label>
    <div class="d-flex gap-2">
      <button class="btn btn-success btn-sm" onclick="openManual('LONG')">
        <i class="bi bi-arrow-up-circle"></i> Long
      </button>
      <button class="btn btn-danger btn-sm" onclick="openManual('SHORT')">
        <i class="bi bi-arrow-down-circle"></i> Short
      </button>
    </div>
  </div>
  ```

### 3. Fix Timescale Button Highlighting
Ensure the selected timescale button maintains its "active" visual state when clicked.

**Root Cause:** The `loadChart()` function removes active class from all buttons but doesn't properly add it to the clicked button because of event handling issues.

**Changes:**
- Modify the `loadChart()` function in the script section:
  ```javascript
  // BEFORE (lines 732-742)
  async function loadChart(tf, btn) {
    currentTf = tf;
    document.querySelectorAll('.btn-group .btn').forEach(b => {
      if (b.closest('#priceChart, [data-panel="priceChart"]')) b.classList.remove('active');
    });
    if (btn) btn.classList.add('active');
  }
  
  // AFTER
  async function loadChart(tf, btn) {
    currentTf = tf;
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    try {
      const data = await api(`/api/chart/${tf}`);
      renderChart(data);
    } catch(e) { console.error('Chart error:', e); }
  }
  ```
- Also update the `renderTradeLog()` function to properly handle button highlighting:
  ```javascript
  // In renderTradeLog(), ensure buttons get proper active state
  document.querySelectorAll('.btn-group .btn').forEach(b => {
    b.classList.remove('active');
  });
  btn.classList.add('active');
  ```

### 4. Update CLAUDE.md
Update the project overview to reflect the new name "BitbotV7".

**Changes:**
- Line 1: Change `# Claude Project Context — BitbotV7` to `# Claude Project Context — BitbotV7`
- Line 3: Change `BitbotV7 is a Bitcoin trading bot...` to `BitbotV7 is a Bitcoin trading bot...`

## Requirements

### Coding Standards (from .roo/rules/01-coding-standards.md)
- PEP 8, 4-space indent, max 100-char lines
- Type hints on all functions (`mypy --strict`)
- `logging` only — no `print()`
- Functions under 50 lines

### Architecture Constraints (from .roo/rules/02-architecture.md)
- All source code lives in `src/`
- Templates go in `src/ui/templates/`
- No hardcoded values - use config where applicable

## Code References

### File: src/ui/templates/index.html

#### Navbar Brand (lines 81-83)
```html
<span class="navbar-brand fw-bold">
  <i class="bi bi-currency-bitcoin text-warning"></i> BitbotV7
</span>
```

#### Bot Controls Section (lines 111-148)
```html
<div id="botControls" class="collapse show">
  <!-- Mode selection -->
  <div class="mb-3">
    <label class="stat-label">Mode</label>
    <select class="form-select form-select-sm" onchange="switchMode(this.value)">
      <option value="paper" selected>Paper (Simulated)</option>
      <option value="testnet">Testnet</option>
      <option value="live">Live</option>
    </select>
  </div>
  
  <!-- Style selection -->
  <div class="mb-3">
    <label class="stat-label">Style</label>
    <select class="form-select form-select-sm" onchange="switchMode(this.value)">
      <option value="scalping" selected>Scalping</option>
      <option value="daytrading">Day Trading</option>
      <option value="swingtrading">Swing Trading</option>
    </select>
  </div>
  
  <!-- Manual Trade buttons will be added here -->
</div>
```

#### Timescale Buttons (lines 228-235)
```html
<div class="btn-group btn-group-sm" role="group">
  <button type="button" class="btn btn-outline-light active" data-panel="priceChart" onclick="loadChart('1m', this)">1m</button>
  <button type="button" class="btn btn-outline-light" data-panel="priceChart" onclick="loadChart('5m', this)">5m</button>
  <button type="button" class="btn btn-outline-light" data-panel="priceChart" onclick="loadChart('15m', this)">15m</button>
  <button type="button" class="btn btn-outline-light" data-panel="priceChart" onclick="loadChart('1h', this)">1h</button>
  <button type="button" class="btn btn-outline-light" data-panel="priceChart" onclick="loadChart('4h', this)">4h</button>
  <button type="button" class="btn btn-outline-light" data-panel="priceChart" onclick="loadChart('1d', this)">1d</button>
</div>
```

#### Manual Trade Section (lines 274-292) - TO BE REMOVED
```html
<div class="card mb-3">
  <div class="card-header bg-transparent border-bottom text-white">
    <h6 class="mb-0">Manual Trade</h6>
  </div>
  <div class="card-body p-2">
    <button class="btn btn-success btn-sm w-100 mb-1" onclick="openManual('LONG')">
      <i class="bi bi-arrow-up-circle"></i> Open Long
    </button>
    <button class="btn btn-danger btn-sm w-100" onclick="openManual('SHORT')">
      <i class="bi bi-arrow-down-circle"></i> Open Short
    </button>
  </div>
</div>
```

#### loadChart Function (lines 732-742)
```javascript
async function loadChart(tf, btn) {
  currentTf = tf;
  document.querySelectorAll('.btn-group .btn').forEach(b => {
    if (b.closest('#priceChart, [data-panel="priceChart"]')) b.classList.remove('active');
  });
  if (btn) btn.classList.add('active');
  try {
    const data = await api(`/api/chart/${tf}`);
    renderChart(data);
  } catch(e) { console.error('Chart error:', e); }
}
```

## Success Criteria

### Visual Changes
- [ ] Navbar displays "BitbotV7" with the "B" styled as a Bitcoin symbol (orange color, slightly larger)
- [ ] Manual trade buttons appear in Bot Controls section below Style dropdown
- [ ] Timescale buttons maintain their "active" class when clicked and remain highlighted
- [ ] Right panel no longer shows the separate "Manual Trade" card

### Functional Changes
- [ ] Clicking timescale buttons properly switches charts AND maintains visual highlight
- [ ] Manual trade buttons function correctly (open LONG/SHORT positions)
- [ ] All existing functionality remains intact

### Documentation Updates
- [ ] CLAUDE.md updated to reference "BitbotV7" instead of "BitbotV7"

## Testing Checklist
1. Start the bot: `python src/main.py`
2. Navigate to http://localhost:8000
3. Verify navbar shows "BitbotV7" with styled "B"
4. Click each timescale button and verify:
   - Chart updates correctly
   - Button remains highlighted (has "active" class)
5. Verify manual trade buttons appear in Bot Controls
6. Test manual LONG/SHORT buttons work correctly
7. Verify no console errors related to chart loading or button clicks
