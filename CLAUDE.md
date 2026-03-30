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

To push code changes to the Pi, use paramiko SFTP then restart the service.

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
│   ├── models/   Trade, Position, Portfolio, Session dataclasses
│   └── storage/  Thread-safe JSON/CSV persistence
├── bot/
│   ├── strategy/ Signal generation (CROSSOVER/PULLBACK/MOMENTUM/BREAKOUT)
│   ├── execution/ Binance API client (paper/testnet/live)
│   ├── risk/     Position sizing, daily loss, emergency stop
│   ├── analysis/ Session detection (Asian/EU/US), ATR, volume
│   └── bot_runner.py  BotState + BotRunner (daemon thread)
├── api/
│   ├── schemas/  Pydantic request/response models
│   └── routes/   REST endpoints (bot, market, portfolio, config, activity)
├── ui/
│   ├── app.py    Flask app factory (threaded=True for SSE support)
│   └── templates/ Jinja2 dashboard (Chart.js, Bootstrap 5)
└── main.py       Entry point
```

## Modes
| Mode | Market Data | Orders |
|------|------------|--------|
| paper | Binance public API (no auth) | Simulated |
| testnet | Binance testnet | Requires TESTNET_API_KEY |
| live | Binance live | Requires LIVE_API_KEY |

Mode switching is **in-memory only** — never written to disk.

## Trading Style Presets
| | Scalping | Day Trading | Swing Trading |
|---|---|---|---|
| Position size | 20% | 60% | 90% |
| Stop loss | 0.4% | 1.5% | 3.5% |
| R:R | 2.0 | 2.5 | 4.0 |
| Max trades/day | 100 | 8 | 3 |
| SMA fast/slow/trend | 8/20/200 | 20/50/200 | 30/100/200 |

## Key Design Decisions
- Bot loop runs in a daemon thread; Flask serves the UI in the main thread (`threaded=True`)
- All mutable state lives in `BotState`, protected by `threading.Lock`
- `BotState.activity_events` is a `deque(maxlen=300)` ring buffer for the live activity feed
- Paper mode calls Binance public endpoints for real price data
- Emergency stop halts all trading; clear via POST `/api/bot/reset`
- `os.getenv()` only allowed in `src/config/settings.py`
- Chart endpoint fetches 500 candles, computes indicators over full history, then trims to last 200 for display — ensures SMA 200 trend line is fully populated

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
GET  /api/portfolio          Capital, position, P&L
GET  /api/trades             Trade history (last 50, newest first)
POST /api/position/manual    Open manual LONG/SHORT
POST /api/position/close     Close current position
GET  /api/config             Current trading config
POST /api/config/update      Update style/risk params
POST /api/logs/clear         Delete log files
GET  /api/stream/activity    SSE stream of live bot activity events
GET  /api/activity?since=<id> Polling fallback for activity events
```

## UI Features
- **Collapsible panels** — all cards collapse/expand; state persisted in `localStorage`
- **Chart colours** — Price: blue `#58a6ff`, SMA Fast: orange `#f0883e`, SMA Slow: green `#3fb950`, SMA Trend: yellow `#e3b341`
- **Entry/exit markers** — green/red dots plotted on price chart from trade history and open position
- **Trade Log** — entry/exit prices + timestamps, duration, filter by side/date, sort by time/P&L/duration, summary stats
- **Live Bot Activity** — terminal-style panel with SSE real-time updates; shows signals, position opens/closes, risk events
- **Metrics strip** — price, ATR, vol ratio, session, daily trades, day P&L
- **Favicon** — inline SVG orange circle with white B
- **Manual Trade** buttons in Bot Controls panel (below Style dropdown)

## Coding Standards
- PEP 8, 4-space indent, max 100-char lines
- Type hints on all functions (`mypy --strict`)
- `logging` only — no `print()`
- Functions under 50 lines
