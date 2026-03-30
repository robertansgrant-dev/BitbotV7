"""BotState (shared state) and BotRunner (daemon thread loop)."""

import logging
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from src.bot.analysis.session_analyzer import (
    calculate_atr_value,
    calculate_volume_ratio,
    get_current_session,
    get_session_recommendation,
)
from src.bot.execution.binance_client import BinanceClient
from src.bot.risk.risk_manager import (
    calculate_position_size,
    calculate_stop_loss,
    calculate_take_profit,
    check_daily_loss,
    should_close_position,
    update_trailing_stop,
)
from src.bot.strategy.signal_generator import get_signal
from src.config.presets import StylePreset, get_preset
from src.config.settings import Settings
from src.data.models.portfolio import Portfolio
from src.data.models.position import Position
from src.data.models.trade import Trade

logger = logging.getLogger(__name__)


class BotState:
    """Central mutable state shared between the bot loop and API layer."""

    def __init__(self, settings: Settings) -> None:
        """Initialise from settings."""
        self.settings = settings
        self.mode: str = settings.default_mode
        self.style: str = settings.default_style
        self.running: bool = False
        self.emergency_stop: bool = settings.emergency_stop
        self.portfolio = Portfolio(
            initial_capital=settings.initial_capital,
            current_capital=settings.initial_capital,
        )
        self.position: Optional[Position] = None
        self.last_price: float = 0.0
        self.last_error: Optional[str] = None
        self.trades: list[Trade] = []
        self._lock = threading.Lock()
        self._daily_reset_date: Optional[str] = None
        self.activity_events: deque[dict[str, Any]] = deque(maxlen=300)
        self._activity_counter: int = 0

    def log_activity(self, event_type: str, message: str, data: Optional[dict] = None) -> None:
        """Append an activity event to the ring buffer (thread-safe, lock-free for deque)."""
        with self._lock:
            self._activity_counter += 1
            self.activity_events.append({
                "id": self._activity_counter,
                "type": event_type,
                "message": message,
                "ts": datetime.now(timezone.utc).isoformat(),
                "data": data or {},
            })

    @property
    def preset(self) -> StylePreset:
        """Return the current trading style preset."""
        return get_preset(self.style)  # type: ignore[arg-type]

    def get_client(self) -> BinanceClient:
        """Create a Binance client configured for the current mode."""
        paper = self.mode == "paper"
        testnet = self.mode == "testnet"
        api_key = (
            self.settings.testnet_api_key if testnet else self.settings.live_api_key
        )
        secret = (
            self.settings.testnet_secret_key if testnet else self.settings.live_secret_key
        )
        return BinanceClient(
            api_key=api_key, secret_key=secret, testnet=testnet, paper=paper
        )


class BotRunner:
    """Manages the trading bot loop in a background daemon thread."""

    def __init__(self, state: BotState) -> None:
        """Initialise with shared state."""
        self._state = state
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """Start the bot loop. Returns False if already running."""
        with self._state._lock:
            if self._state.running:
                return False
            self._state.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="BotLoop"
        )
        self._thread.start()
        logger.info("Bot started — mode=%s style=%s", self._state.mode, self._state.style)
        self._state.log_activity(
            "BOT", f"Bot started  mode={self._state.mode}  style={self._state.style}", {}
        )
        return True

    def stop(self) -> bool:
        """Stop the bot loop. Returns False if not running."""
        with self._state._lock:
            if not self._state.running:
                return False
            self._state.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=15)
        logger.info("Bot stopped")
        self._state.log_activity("BOT", "Bot stopped", {})
        return True

    # ------------------------------------------------------------------ #
    # Internal loop                                                        #
    # ------------------------------------------------------------------ #

    def _loop(self) -> None:
        """Main bot loop — runs until stop_event is set."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.error("Bot loop error: %s", exc, exc_info=True)
                with self._state._lock:
                    self._state.last_error = str(exc)
            self._stop_event.wait(timeout=self._state.settings.update_interval)

    def _tick(self) -> None:
        """Execute one iteration of the bot loop."""
        state = self._state

        if state.emergency_stop:
            logger.warning("Emergency stop active — trading suspended")
            return

        self._check_daily_reset()

        client = state.get_client()
        try:
            price = client.get_price(state.settings.symbol)
        except Exception as exc:
            logger.error("Price fetch failed: %s", exc)
            return

        with state._lock:
            state.last_price = price

        if check_daily_loss(state.portfolio, state.settings):
            logger.warning("Daily loss limit reached — activating emergency stop")
            with state._lock:
                state.emergency_stop = True
            state.log_activity("RISK", "Daily loss limit reached — emergency stop activated", {})
            return

        if state.position:
            self._manage_position(client, price)
        else:
            self._seek_entry(client, price)

    def _check_daily_reset(self) -> None:
        """Reset daily stats at midnight UTC."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = self._state
        if state._daily_reset_date != today:
            with state._lock:
                state.portfolio.daily_pnl = 0.0
                state.portfolio.daily_loss_pct = 0.0
                state.portfolio.daily_trades = 0
                state._daily_reset_date = today
            logger.info("Daily reset for %s", today)

    def _manage_position(self, client: BinanceClient, price: float) -> None:
        """Update open position price/trailing stop and check exit conditions."""
        state = self._state
        pos = state.position
        if pos is None:
            return

        with state._lock:
            pos.current_price = price
            if state.preset.trailing_stop:
                pos.trailing_stop = update_trailing_stop(pos, price, state.preset)

        reason = should_close_position(pos, price, state.preset)
        if reason:
            self._close_position(client, price, reason)

    def _seek_entry(self, client: BinanceClient, price: float) -> None:
        """Look for an entry signal and open a position if one is found."""
        state = self._state
        preset = state.preset

        if state.portfolio.daily_trades >= preset.max_daily_trades:
            return

        session = get_current_session()
        if session == "Off":
            return

        try:
            df = _to_df(client.get_klines(state.settings.symbol, "1m", 500))
            df_htf = _to_df(
                client.get_klines(state.settings.symbol, preset.htf_timeframe, 500)
            )
        except Exception as exc:
            logger.error("Klines fetch failed: %s", exc)
            return

        signal_type, direction = get_signal(df, df_htf, preset)
        if direction == "NONE":
            state.log_activity("SIGNAL", f"HOLD — no entry signal  price={price:.2f}", {"price": price})
            return

        state.log_activity(
            "SIGNAL",
            f"{direction} signal={signal_type}  price={price:.2f}",
            {"direction": direction, "signal": signal_type, "price": price},
        )
        self._open_position(client, price, direction, signal_type)

    def _open_position(
        self, client: BinanceClient, price: float, side: str, signal_type: str
    ) -> None:
        """Open a new position after placing an order."""
        state = self._state
        qty = calculate_position_size(
            state.portfolio.current_capital, price, state.preset, state.settings
        )
        sl = calculate_stop_loss(price, side, state.preset)
        tp = calculate_take_profit(price, side, state.preset)

        binance_side = "BUY" if side == "LONG" else "SELL"
        try:
            client.place_order(state.settings.symbol, binance_side, qty)
        except Exception as exc:
            logger.error("Order failed: %s", exc)
            return

        with state._lock:
            state.position = Position(
                symbol=state.settings.symbol,
                side=side,  # type: ignore[arg-type]
                entry_price=price,
                current_price=price,
                quantity=qty,
                open_time=datetime.now(timezone.utc),
                stop_loss=sl,
                take_profit=tp,
                signal_type=signal_type,
            )
            state.portfolio.daily_trades += 1

        logger.info(
            "Opened %s @ %.2f qty=%.6f signal=%s sl=%.2f tp=%.2f",
            side, price, qty, signal_type, sl, tp,
        )
        state.log_activity(
            "POSITION_OPENED",
            f"Opened {side} @ {price:.2f}  qty={qty:.6f}  signal={signal_type}  sl={sl:.2f}  tp={tp:.2f}",
            {"side": side, "price": price, "qty": qty, "signal": signal_type, "sl": sl, "tp": tp},
        )

    def _close_position(
        self, client: BinanceClient, price: float, reason: str
    ) -> None:
        """Close the current position, record the trade, update portfolio."""
        state = self._state
        pos = state.position
        if pos is None:
            return

        binance_side = "SELL" if pos.side == "LONG" else "BUY"
        try:
            client.place_order(state.settings.symbol, binance_side, pos.quantity)
        except Exception as exc:
            logger.error("Close order failed: %s", exc)
            return

        pnl = pos.unrealized_pnl
        trade = Trade(
            trade_id=str(uuid.uuid4())[:8],
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=price,
            quantity=pos.quantity,
            timestamp=datetime.now(timezone.utc),
            pnl=pnl,
            entry_time=pos.open_time,
            mode=state.mode,
            style=state.style,
            signal_type=pos.signal_type,
        )

        with state._lock:
            state.portfolio.current_capital += pnl
            state.portfolio.daily_pnl += pnl
            state.portfolio.total_trades += 1
            if pnl > 0:
                state.portfolio.winning_trades += 1
            state.trades.append(trade)
            state.position = None

        logger.info(
            "Closed %s @ %.2f pnl=%.4f reason=%s", pos.side, price, pnl, reason
        )
        state.log_activity(
            "POSITION_CLOSED",
            f"Closed {pos.side} @ {price:.2f}  PnL={pnl:+.4f}  reason={reason}",
            {"side": pos.side, "entry": pos.entry_price, "exit": price, "pnl": pnl, "reason": reason},
        )


def _to_df(klines: list[dict]) -> pd.DataFrame:
    """Convert a klines list to a DataFrame with standard column names."""
    return pd.DataFrame(klines)
