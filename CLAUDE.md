# Claude Project Context — BitbotV7

## Project Overview
BitbotV7 is a Bitcoin trading bot with a Flask web UI and REST API.
- Three trading styles: scalping, day trading, swing trading
- Three modes: paper (simulated), testnet (Binance testnet), live
- Web dashboard at **http://localhost:8000** (local) or **http://192.168.1.112:8000** (Raspberry Pi 3B)

## Deployment
The bot runs as a systemd service on a Raspberry Pi 3B (`BitBot`, `192.168.1.112`).
- SSH: `ssh robbiegrant@192.168.1.112`
- Service: `sudo systemctl restart bitbot.service`
- Logs: `journalctl -u bitbot.service -f`
- Project path on Pi: `~/BitbotV7`

Deploy changed files via paramiko SFTP, then restart the service. Password is in memory.

## Quick Start
```bash
pip install -r requirements.txt
copy .env.example .env   # then fill in keys if needed
python src/main.py
```

## Architecture
```
src/
├── config/       Pydantic BaseSettings + frozen style presets
├── data/
│   ├── models/   Trade, Position, Portfolio dataclasses
│   └── storage/  Thread-safe JSON/CSV persistence
├── bot/
│   ├── strategy/ Signal generation (CROSSOVER/PULLBACK/MOMENTUM/BREAKOUT)
│   ├── execution/ Binance API client (paper/testnet/live)
│   ├── risk/     RiskManager class (ATR sizing, dynamic SL/TP, regime filter)
│   ├── analysis/ Session detection (Asian/EU/US), ATR, volume
│   └── bot_runner.py  BotState + BotRunner (daemon thread)
├── api/
│   ├── schemas/  Pydantic request/response models
│   └── routes/   REST endpoints (bot, market, portfolio, config, activity, analysis)
├── ui/
│   ├── app.py    Flask app factory (threaded=True for SSE support)
│   └── templates/ Jinja2 dashboard (Chart.js, Bootstrap 5)
├── main.py       Entry point
config.yaml       All tunable parameters with rationale (not hot-reloaded)
tests/
└── test_risk_manager.py  16-trade replay harness (run: python -m tests.test_risk_manager)
```

## Modes
| Mode | Market Data | Orders |
|------|------------|--------|
| paper | Binance public API (no auth) | Simulated |
| testnet | Binance testnet | Requires TESTNET_API_KEY |
| live | Binance live | Requires LIVE_API_KEY |

Mode switching is **in-memory only** — never written to disk.
**Live mode is blocked** by a `RuntimeError` guard in `_open_position` — remove it explicitly to enable.

## Trading Style Presets
| | Scalping | Day Trading | Swing Trading |
|---|---|---|---|
| Position size (fallback) | 20% | 60% | 90% |
| Stop loss (fallback %) | 0.4% | 1.5% | 3.5% |
| R:R | 2.0 | 2.5 | 4.0 |
| Max trades/day | 100 | 8 | 3 |
| SMA fast/slow/trend | 8/20/200 | 20/50/200 | 30/100/200 |
| Max hold (minutes) | 30 | 240 | 1440 |
| risk_per_trade_pct | 0.5% | 1.0% | 1.5% |
| atr_sl_multiplier | 1.5× | 2.0× | 3.0× |

Position sizing and SL/TP are **ATR-based** when klines are available. Fixed-% values above are fallbacks only.

## Risk Manager (`src/bot/risk/risk_manager.py`)
Class-based `RiskManager` configured via `RiskConfig` dataclass. One instance lives on `BotState`.

**Key RiskConfig fields** (all synced from preset/settings before each entry attempt):
- `risk_per_trade_pct` — synced from `preset.risk_per_trade_pct / 100`
- `sl_atr_mult` / `tp_atr_mult` — synced from `preset.atr_sl_multiplier` and `× risk_reward`
- `time_exit_minutes` — synced from `preset.max_hold_minutes`
- `max_hold_extension_minutes` — 5 min for scalping, 15 min for other styles
- `fee_rate` — synced from `settings.fee_rate` (default 0.001 = 0.1% Binance spot)
- `min_volatility_pct` — 0.0025 (matches `_VOLATILITY_FLOOR` in signal_generator)

**Methods used by bot_runner:**
- `calculate_dynamic_levels(df, entry, side)` → `(sl, tp, atr_val)` — ATR-based, falls back to 1.5% fixed if ATR fails
- `calculate_position_size(entry, sl)` → qty — risk-per-trade: sizes so SL hit = `risk_per_trade_pct` of equity
- `is_tradable_regime(df)` → bool — requires ADX > 20 AND (volume OR volatility above thresholds); logs skip reason
- `apply_breakeven_logic(trade, price)` → Optional[float] — one-shot; activates at +0.5R; snaps SL to entry + fee/unit
- `should_exit_by_time(trade, price, now)` → `(bool, reason)` — reasons: `"hold"`, `"extend_for_fees"`, `"time_exit"`
- `calculate_trade_metrics(trade)` → dict — includes `gross_pnl`, `fees_paid`, `net_pnl`, `fee_drag_pct`, `mfe_pnl`, `exit_efficiency`
- `check_daily_circuit_breaker()` → bool — trips at `max_daily_loss_pct` of current equity
- `record_trade_close(net_pnl)` — keeps RM equity in sync with portfolio
- `reset_daily_stats()` — called at midnight UTC by `_check_daily_reset`

## Key Design Decisions

### Threading & State
- Bot loop runs in a daemon thread; Flask serves the UI in the main thread (`threaded=True`)
- All mutable state lives in `BotState`, protected by `threading.Lock`
- All `Position` mutations in `_manage_position` occur inside `with state._lock:`
- `BotState.activity_events` is a `deque(maxlen=300)` ring buffer — only trading events logged (SIGNAL, POSITION_OPENED, POSITION_CLOSED, RISK, ERROR, BOT)

### Entry Gating
- `BotState._entry_cooldown_until` — set after any close; `_seek_entry` skips until elapsed
  - TP hit → 5 min cooldown; SL hit → 3 min cooldown
- `BotState._signal_pause_until` — set for 4 hours when daily circuit-breaker trips; softer than emergency_stop; resets at next daily reset

### Signal Filters (applied in order in `get_signal`)
1. **HTF trend** — must be UP or DOWN (NEUTRAL → `weak_trend` skip)
2. **Volume gate** — current vol must be ≥ 70% of 20-bar SMA (`low_vol` skip)
3. **Dead market floor** — `ATR(14)/price < 0.0025` → `dead_market` skip — hard floor that overrides PULLBACK exemption; at this ATR level 1R barely covers round-trip costs
4. **ATR regime** (`_is_market_trending`) — CROSSOVER/MOMENTUM/BREAKOUT suppressed when ATR < 70% of 30-bar mean (`chop` skip); PULLBACK still runs but is blocked by the dead_market check above
5. **ADX gate on PULLBACK** — requires ADX ≥ 20 (`weak_trend` skip)
6. **RM regime gate** (`rm.is_tradable_regime`) — called in `_seek_entry` before `get_signal`; also logs `weak_trend`/`low_vol`/`chop`

### Exit Logic
- SL/TP checked first (hard limits via `_check_sl_tp` in `bot_runner.py`)
- Time exit via `rm.should_exit_by_time`:
  - Hard cap at `max_hold_minutes`
  - **`extend_for_fees`**: past base hold but profit < 1.5× round-trip cost → extends up to `max_hold_extension_minutes` AND tightens `pos.stop_loss` to `entry + fee_per_unit` (atomic, inside lock). This bounds the extension-window loss to fee cost only
- Break-even: once +0.5R profit, `pos.stop_loss` snapped to `entry + fee_per_unit` (covers round-trip)
- Trailing stop: after break-even, ratchets at `ATR × atr_sl_multiplier` distance from price (styles with `trailing_stop=True`)

### Fee & PnL Accounting
- Fees: `(entry_notional + exit_notional) × fee_rate` — both legs charged
- Slippage: `notional × slippage_rate` added to round-trip cost
- `Portfolio.current_capital` and `daily_pnl` are updated with **net PnL** (after fees)
- `Portfolio.total_fees`, `peak_capital`, `max_drawdown` tracked; `update_drawdown()` called on every close
- `Trade.fees` and `Trade.net_pnl` (property) available on every closed trade

### Other
- `os.getenv()` only allowed in `src/config/settings.py`
- Chart endpoint fetches 500 candles, computes indicators over full history, then trims to last 200 for display
- Pullback RSI thresholds: LONG requires `rsi >= 45`, SHORT requires `rsi <= 55`
- CROSSOVER min gap: fast/slow gap ≥ 0.05% of price after cross
- MOMENTUM min distance: price ≥ 0.15% beyond fast SMA
- `Trade.exit_reason`: `"take_profit"`, `"stop_loss"`, `"time_exit"`, or `"manual"`

## API Endpoints
```
GET  /api/status             Bot state, mode, style
POST /api/bot/start          Start bot loop
POST /api/bot/stop           Stop bot loop
POST /api/bot/reset          Reset portfolio
POST /api/mode/switch        Switch mode (in-memory)
GET  /api/market             Price, 24h stats
GET  /api/chart/<timeframe>  OHLCV + SMAs (fast/slow/trend) + MACD
GET  /api/session            Session analysis (Asian/EU/US), ATR, vol ratio
GET  /api/portfolio          Capital, position, P&L, max_drawdown, total_fees
GET  /api/trades             Trade history (last 50, newest first) — includes fees, net_pnl
POST /api/position/manual    Open manual LONG/SHORT (fetches klines for ATR levels)
POST /api/position/close     Close current position
GET  /api/config             Current trading config
POST /api/config/update      Update style/risk params
POST /api/logs/clear         Delete log files
GET  /api/stream/activity    SSE stream of live bot activity events
GET  /api/activity?since=<id> Polling fallback for activity events
GET  /api/analysis           Per-signal and per-exit-reason breakdown + profit_factor,
                             expectancy, avg_win, avg_loss, total_fees, fee_drag_pct
```

## UI Features
- **Collapsible panels** — all cards collapse/expand; state persisted in `localStorage`
- **Chart colours** — Price: blue `#58a6ff`, SMA Fast: orange `#f0883e`, SMA Slow: green `#3fb950`, SMA Trend: yellow `#e3b341`
- **Entry/exit markers** — green/red dots plotted on price chart from trade history and open position
- **Trade Log** — entry/exit prices + timestamps, duration, fees, net PnL; filter by side/date; sort by time/P&L/duration; Signal/Exit column colour-coded (TP=green, SL=red, time=yellow); clipboard copy
- **Session Analysis panel** — breakdown by signal and exit reason + profit_factor, expectancy, fee_drag_pct; refreshes every 10 s
- **Live Bot Activity** — terminal-style panel with SSE real-time updates; shows signals, opens/closes with exit_efficiency and fee_drag%; clipboard copy
- **Metrics strip** — price, ATR, vol ratio, session, daily trades, day P&L
- **Favicon** — inline SVG orange circle with white B
- **Manual Trade** buttons in Bot Controls panel

## Coding Standards
- PEP 8, 4-space indent, max 100-char lines
- Type hints on all functions (`mypy --strict`)
- `logging` only — no `print()`
- Functions under 50 lines
- All Position mutations inside `with state._lock:`
- No `os.getenv()` outside `src/config/settings.py`
