"""BotState (shared state) and BotRunner (daemon thread loop)."""

import logging
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pandas as pd

from src.bot.analysis.session_analyzer import get_current_session
from src.bot.execution.binance_client import BinanceClient
from src.bot.risk.risk_manager import RiskConfig, RiskManager, TradeState
from src.bot.strategy.signal_generator import get_signal
from src.config.presets import StylePreset, get_preset
from src.config.settings import Settings
from src.data.models.portfolio import Portfolio
from src.data.models.position import Position
from src.data.models.trade import Trade

logger = logging.getLogger(__name__)


def _pos_to_trade_state(pos: Position) -> TradeState:
    """Build a TradeState from the current Position for RiskManager calls."""
    return TradeState(
        id=pos.signal_type or "unknown",
        side=pos.side,
        entry_price=pos.entry_price,
        entry_time=pos.open_time,
        qty=pos.quantity,
        sl=pos.stop_loss,
        tp=pos.take_profit,
        signal_type=pos.signal_type or "",
        moved_to_breakeven=pos.break_even_activated,
    )


def _check_sl_tp(pos: Position, price: float, preset: StylePreset) -> Optional[str]:
    """Return 'stop_loss' or 'take_profit' if a hard limit is hit, else None."""
    effective_stop = (
        pos.trailing_stop
        if preset.trailing_stop and pos.trailing_stop
        else pos.stop_loss
    )
    if pos.side == "LONG":
        if price <= effective_stop:
            return "stop_loss"
        if price >= pos.take_profit:
            return "take_profit"
    else:
        if price >= effective_stop:
            return "stop_loss"
        if price <= pos.take_profit:
            return "take_profit"
    return None


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
        self._entry_cooldown_until: Optional[datetime] = None
        # Set by daily circuit-breaker; signal generation is paused until this time
        self._signal_pause_until: Optional[datetime] = None

        # RiskManager — config is synced with the active preset before each trade
        self.risk_manager = RiskManager(
            config=RiskConfig(
                fee_rate=settings.fee_rate,
                max_daily_loss_pct=settings.max_daily_loss_pct / 100,
            ),
            initial_equity=settings.initial_capital,
        )

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

        if state.risk_manager.check_daily_circuit_breaker():
            pause_until = datetime.now(timezone.utc) + timedelta(hours=4)
            with state._lock:
                state._signal_pause_until = pause_until
            msg = f"Daily circuit breaker — signals paused 4 h (until {pause_until.strftime('%H:%M')} UTC)"
            logger.warning(msg)
            state.log_activity("RISK", msg, {"pause_until": pause_until.isoformat()})
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
            state.risk_manager.reset_daily_stats()
            logger.info("Daily reset for %s", today)

    def _manage_position(self, client: BinanceClient, price: float) -> None:
        """Update open position and check all exit conditions."""
        state = self._state
        pos = state.position
        if pos is None:
            return

        rm = state.risk_manager
        preset = state.preset

        with state._lock:
            pos.current_price = price

            # MFE watermark — tick-by-tick high/low for exit efficiency metric
            if pos.side == "LONG":
                if pos.max_price_seen is None or price > pos.max_price_seen:
                    pos.max_price_seen = price
            else:
                if pos.min_price_seen is None or price < pos.min_price_seen:
                    pos.min_price_seen = price

            # Break-even snap via RiskManager (one-shot, propagated back to Position)
            ts = _pos_to_trade_state(pos)
            new_sl = rm.apply_breakeven_logic(ts, price)
            if new_sl is not None:
                pos.stop_loss = new_sl
                pos.break_even_activated = True

            # Trailing stop (ratchets in profit direction after BE is set)
            if preset.trailing_stop:
                atr_dist = (
                    pos.atr_at_entry * preset.atr_sl_multiplier
                    if pos.atr_at_entry > 0
                    else pos.entry_price * (preset.stop_loss_pct / 100)
                )
                current_trail = pos.trailing_stop or pos.stop_loss
                if pos.side == "LONG":
                    pos.trailing_stop = max(current_trail, price - atr_dist)
                else:
                    pos.trailing_stop = min(current_trail, price + atr_dist)

        # Hard SL / TP — checked before time logic for safety
        hard_reason = _check_sl_tp(pos, price, preset)
        if hard_reason:
            self._close_position(client, price, hard_reason)
            return

        # Time-based exit delegated to RiskManager
        ts = _pos_to_trade_state(pos)
        should_exit, time_reason = rm.should_exit_by_time(ts, price, datetime.now(timezone.utc))
        if should_exit:
            self._close_position(client, price, "time_exit")
        elif time_reason == "extend_for_fees":
            self._tighten_sl_for_extension(pos, rm)

    def _tighten_sl_for_extension(self, pos: Position, rm: RiskManager) -> None:
        """Snap SL to break-even + fees when the RM grants a fee-buffer extension.

        Called once per extension window.  All Position mutations are inside the lock.
        Rationale: the extension buys more time only if the trade is near profitable;
        snapping the stop to entry + round-trip-fee-per-unit ensures a stop-out during
        the extension window loses at most the fee cost, not an additional full 1R.
        """
        state = self._state
        with state._lock:
            if pos.break_even_activated:
                return  # already snapped — nothing to do
            if pos.quantity <= 0:
                return
            notional = pos.entry_price * pos.quantity
            round_trip_cost = notional * (rm.cfg.fee_rate * 2 + rm.cfg.slippage_rate)
            fee_per_unit = round_trip_cost / pos.quantity
            if pos.side == "LONG":
                be_sl = pos.entry_price + fee_per_unit
            else:
                be_sl = pos.entry_price - fee_per_unit
            pos.stop_loss = be_sl
            pos.break_even_activated = True
        elapsed = (datetime.now(timezone.utc) - pos.open_time).total_seconds() / 60
        logger.info(
            "Extending hold: SL tightened to breakeven+fee @ %.2f (elapsed=%.1f min)",
            be_sl, elapsed,
        )

    def _seek_entry(self, client: BinanceClient, price: float) -> None:
        """Look for an entry signal and open a position if one is found."""
        state = self._state
        preset = state.preset
        rm = state.risk_manager

        with state._lock:
            cooldown = state._entry_cooldown_until
            pause_until = state._signal_pause_until
        if cooldown and datetime.now(timezone.utc) < cooldown:
            return
        if pause_until and datetime.now(timezone.utc) < pause_until:
            logger.debug("Signal generation paused by circuit breaker until %s UTC", pause_until.strftime("%H:%M"))
            return

        if state.portfolio.daily_trades >= preset.max_daily_trades:
            logger.info("Daily trade limit reached — no entry attempts")
            return

        session = get_current_session()
        if session == "Off":
            logger.info("Off-session hours — skipping entries")
            return

        try:
            df = _to_df(client.get_klines(state.settings.symbol, "1m", 500))
            df_htf = _to_df(
                client.get_klines(state.settings.symbol, preset.htf_timeframe, 500)
            )
        except Exception as exc:
            error_msg = f"Klines fetch failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            state.log_activity("ERROR", error_msg, {"symbol": state.settings.symbol})
            return

        # Sync RiskManager config with the active style preset before any checks
        rm.cfg.sl_atr_mult = preset.atr_sl_multiplier
        rm.cfg.tp_atr_mult = preset.atr_sl_multiplier * preset.risk_reward
        rm.cfg.risk_per_trade_pct = preset.risk_per_trade_pct / 100
        rm.cfg.time_exit_minutes = preset.max_hold_minutes
        rm.cfg.max_hold_extension_minutes = 5 if preset.name == "scalping" else 15
        rm.cfg.fee_rate = state.settings.fee_rate

        # Regime gate — RiskManager must confirm the market is tradable
        if not rm.is_tradable_regime(df):
            logger.debug("RiskManager: market not tradable — skipping entry")
            return

        signal_type, direction = get_signal(df, df_htf, preset)
        if direction == "NONE":
            return

        state.log_activity(
            "SIGNAL",
            f"{direction} signal={signal_type}  price={price:.2f}",
            {"direction": direction, "signal": signal_type, "price": price},
        )
        self._open_position(client, df, price, direction, signal_type)

    def _open_position(
        self,
        client: BinanceClient,
        df: pd.DataFrame,
        price: float,
        side: str,
        signal_type: str,
    ) -> None:
        """Open a new position — SL/TP/sizing all delegated to RiskManager."""
        state = self._state

        # ── PAPER MODE ENFORCEMENT ───────────────────────────────────────────
        # Remove this block only when explicitly ready for live execution.
        if state.mode == "live":
            raise RuntimeError(
                "Live execution blocked: bot is in paper/development mode. "
                "Remove the guard in _open_position to enable live trading."
            )
        # ─────────────────────────────────────────────────────────────────────

        rm = state.risk_manager

        # RiskManager computes ATR-based SL, TP, and current ATR value
        try:
            sl, tp, atr_val = rm.calculate_dynamic_levels(df, price, side)
        except Exception as exc:
            logger.error("calculate_dynamic_levels failed: %s", exc)
            return

        qty = rm.calculate_position_size(price, sl)

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
                atr_at_entry=atr_val,
            )
            state.portfolio.daily_trades += 1

        logger.info(
            "Opened %s @ %.2f qty=%.6f signal=%s sl=%.2f tp=%.2f atr=%.2f",
            side, price, qty, signal_type, sl, tp, atr_val,
        )
        state.log_activity(
            "POSITION_OPENED",
            (
                f"Opened {side} @ {price:.2f}  qty={qty:.6f}  signal={signal_type}"
                f"  sl={sl:.2f}  tp={tp:.2f}  atr={atr_val:.2f}"
            ),
            {
                "side": side, "price": price, "qty": qty, "signal": signal_type,
                "sl": sl, "tp": tp, "atr": atr_val,
            },
        )

    def _close_position(
        self, client: BinanceClient, price: float, reason: str
    ) -> None:
        """Close the current position, record the trade, update portfolio and RiskManager."""
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

        # Use RiskManager metrics for fees + net PnL (includes slippage model)
        closed_ts = TradeState(
            id=str(uuid.uuid4())[:8],
            side=pos.side,
            entry_price=pos.entry_price,
            entry_time=pos.open_time,
            qty=pos.quantity,
            sl=pos.stop_loss,
            tp=pos.take_profit,
            signal_type=pos.signal_type or "",
            exit_price=price,
            exit_reason=reason,
        )
        # Pass MFE watermarks so calculate_trade_metrics can compute exit_efficiency
        closed_ts.max_price_seen = pos.max_price_seen
        closed_ts.min_price_seen = pos.min_price_seen

        metrics = state.risk_manager.calculate_trade_metrics(closed_ts)
        pnl = pos.unrealized_pnl
        fees = metrics.get("fees_paid", 0.0)
        net = metrics.get("net_pnl", pnl)
        eff = metrics.get("exit_efficiency", 0.0)
        drag = metrics.get("fee_drag_pct", 0.0)
        mfe = metrics.get("mfe_pnl", 0.0)

        trade = Trade(
            trade_id=closed_ts.id,
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=price,
            quantity=pos.quantity,
            timestamp=datetime.now(timezone.utc),
            pnl=pnl,
            fees=fees,
            entry_time=pos.open_time,
            mode=state.mode,
            style=state.style,
            signal_type=pos.signal_type,
            exit_reason=reason,
        )

        with state._lock:
            state.portfolio.current_capital += net
            state.portfolio.daily_pnl += net
            state.portfolio.total_fees += fees
            state.portfolio.total_trades += 1
            if net > 0:
                state.portfolio.winning_trades += 1
            state.portfolio.update_drawdown()
            state.trades.append(trade)
            state.position = None
            if reason == "take_profit":
                state._entry_cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=5)
            elif reason == "stop_loss":
                state._entry_cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=3)

        # Keep RiskManager equity in sync with portfolio
        state.risk_manager.record_trade_close(net)

        logger.info(
            "Closed %s @ %.2f  pnl=%.4f  fees=%.4f  net=%.4f  mfe=%.4f  eff=%.2f  drag=%.1f%%  [%s]",
            pos.side, price, pnl, fees, net, mfe, eff, drag, reason,
        )
        state.log_activity(
            "POSITION_CLOSED",
            (
                f"Closed {pos.side} @ {price:.2f}  net={net:+.4f}"
                f"  eff={eff:.2f}  drag={drag:.1f}%  [{reason}]"
            ),
            {
                "side": pos.side, "entry": pos.entry_price, "exit": price,
                "pnl": pnl, "fees": fees, "net": net,
                "exit_efficiency": eff, "fee_drag_pct": drag, "mfe_pnl": mfe,
                "reason": reason,
            },
        )


def _to_df(klines: list[dict]) -> pd.DataFrame:
    """Convert a klines list to a DataFrame with standard column names."""
    return pd.DataFrame(klines)
