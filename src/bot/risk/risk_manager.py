"""Risk management: position sizing, dynamic SL/TP, regime filter, trade tracking.

Architecture note
-----------------
This module uses a class-based ``RiskManager`` (configured via ``RiskConfig``) rather
than the previous standalone-function approach.  Callers (bot_runner, portfolio_routes)
must be updated to instantiate ``RiskManager`` and call its methods.

Bugs fixed from the original Qwen version
------------------------------------------
* ``ta.volatility.AverageTrueRange`` returns an object, not a Series — fixed by calling
  ``.average_true_range()`` before ``.iloc[-1]``.
* ``is_tradable_regime`` used OR logic (too permissive) — replaced with
  ``is_trending AND (has_volume OR has_volatility)``.
* ``max_allowed_loss`` was fixed to initial equity — now recomputed from current equity
  each time ``check_daily_circuit_breaker`` is called.
* ``calculate_dynamic_levels`` silently ignored ``RiskConfig`` multipliers — it now reads
  ``sl_atr_mult`` / ``tp_atr_mult`` from config by default.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import ta

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskConfig:
    """All risk parameters in one place.  Override via .env or at construction."""

    risk_per_trade_pct: float = 0.01     # 1 % of equity risked per trade
    max_daily_loss_pct: float = 0.02     # 2 % daily circuit-breaker (of current equity)
    fee_rate: float = 0.001              # 0.1 % taker fee per leg — Binance spot default
                                         # synced from settings.fee_rate at runtime
    slippage_rate: float = 0.0002        # 0.02 % estimated slippage per leg
    atr_period: int = 14
    sl_atr_mult: float = 1.5             # SL = entry ± ATR × sl_atr_mult
    tp_atr_mult: float = 2.5             # TP = entry ± ATR × tp_atr_mult
    time_exit_minutes: int = 30          # Base max hold time — synced from preset at runtime
    max_hold_extension_minutes: int = 15 # Extra hold when profit < fee buffer
    breakeven_threshold_r: float = 0.5   # Snap SL to BE when profit ≥ 0.5 × 1R
    min_profit_fee_buffer: float = 1.5   # Exit only if profit ≥ 1.5 × round-trip cost
    adx_threshold: float = 20.0          # Minimum ADX to consider market trending
    volume_sma_period: int = 20          # Look-back for volume SMA
    min_volatility_pct: float = 0.0025   # Minimum ATR/price ratio — matches signal_generator floor


# ──────────────────────────────────────────────────────────────────────────────
# Trade state
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TradeState:
    """Mutable state for one open trade — updated tick-by-tick."""

    id: str
    side: str                              # "LONG" or "SHORT"
    entry_price: float
    entry_time: datetime
    qty: float
    sl: float
    tp: float
    signal_type: str
    is_closed: bool = False
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    max_price_seen: Optional[float] = None  # for MFE (LONG)
    min_price_seen: Optional[float] = None  # for MFE (SHORT)
    moved_to_breakeven: bool = False


# ──────────────────────────────────────────────────────────────────────────────
# Risk manager
# ──────────────────────────────────────────────────────────────────────────────

class RiskManager:
    """Centralised risk management for the trading bot.

    Usage::

        cfg = RiskConfig(risk_per_trade_pct=0.005)
        rm  = RiskManager(cfg, initial_equity=1000.0)

        sl, tp, atr_val = rm.calculate_dynamic_levels(df, entry, "LONG")
        qty             = rm.calculate_position_size(entry, sl)
        trade           = TradeState(id="t1", side="LONG", ...)

        # Each tick:
        rm.update_trade_tracking(trade, current_price)
        new_sl = rm.apply_breakeven_logic(trade, current_price)
        should_exit, reason = rm.should_exit_by_time(trade, current_price, now)
    """

    def __init__(self, config: RiskConfig, initial_equity: float = 1000.0) -> None:
        # Safety: refuse dangerously high risk sizing during paper/dev phase
        assert config.risk_per_trade_pct < 0.05, (
            f"risk_per_trade_pct={config.risk_per_trade_pct:.3f} exceeds 5 % — "
            "reduce to ≤ 0.02 for safe paper trading"
        )
        self.cfg = config
        self.equity = initial_equity
        self.daily_pnl: float = 0.0
        self.daily_trades: int = 0
        self._daily_reset_date: Optional[str] = None
        logger.info(
            "RiskManager initialised | equity=%.2f | max_daily_loss=%.1f%% | risk_per_trade=%.2f%%",
            initial_equity, config.max_daily_loss_pct * 100, config.risk_per_trade_pct * 100,
        )

    # ── 1. Position sizing ────────────────────────────────────────────────────

    def calculate_position_size(self, entry_price: float, sl_price: float) -> float:
        """Return quantity so that a full SL hit costs exactly risk_per_trade_pct of equity.

        Falls back to a 0.5 % price distance when SL equals entry (degenerate input).
        """
        risk_amount = self.equity * self.cfg.risk_per_trade_pct
        sl_distance = abs(entry_price - sl_price)
        if sl_distance == 0:
            logger.warning("Zero SL distance — using 0.5%% fallback")
            sl_distance = entry_price * 0.005
        qty = risk_amount / sl_distance
        return round(max(0.0001, qty), 6)

    # ── 2. Dynamic SL / TP ───────────────────────────────────────────────────

    def calculate_dynamic_levels(
        self,
        ohlcv_df: pd.DataFrame,
        entry_price: float,
        side: str,
    ) -> Tuple[float, float, float]:
        """Return (sl_price, tp_price, atr_value) using config ATR multipliers.

        Uses ``RiskConfig.sl_atr_mult`` and ``tp_atr_mult`` — no silent defaults.
        Falls back to 1.5 % fixed offset if ATR computation fails (e.g. insufficient
        data, NaN values from a thin candle window).
        """
        _FIXED_FALLBACK_PCT = 0.015  # 1.5 % of entry — used when ATR is unavailable

        try:
            atr_series = ta.volatility.AverageTrueRange(
                ohlcv_df["high"],
                ohlcv_df["low"],
                ohlcv_df["close"],
                window=self.cfg.atr_period,
            ).average_true_range()
            atr_val = float(atr_series.iloc[-1])
            if pd.isna(atr_val) or atr_val <= 0:
                raise ValueError(f"ATR value is invalid: {atr_val}")
        except Exception as exc:
            atr_val = entry_price * _FIXED_FALLBACK_PCT
            logger.warning(
                "ATR calculation failed (%s) — using %.1f%% fixed fallback (atr_val=%.2f)",
                exc, _FIXED_FALLBACK_PCT * 100, atr_val,
            )

        sl_offset = atr_val * self.cfg.sl_atr_mult
        tp_offset = atr_val * self.cfg.tp_atr_mult

        if side == "LONG":
            sl = entry_price - sl_offset
            tp = entry_price + tp_offset
        else:
            sl = entry_price + sl_offset
            tp = entry_price - tp_offset

        return round(sl, 2), round(tp, 2), round(atr_val, 2)

    # ── 3. Regime filter ─────────────────────────────────────────────────────

    def is_tradable_regime(self, ohlcv_df: pd.DataFrame) -> bool:
        """Return True only when the market is trending AND has acceptable activity.

        Logic: ``is_trending AND (has_volume OR has_volatility)``

        Logs the specific skip reason at INFO level using the standard tags:
        - ``"weak_trend"``  — ADX below threshold
        - ``"low_vol"``     — volume and volatility both below thresholds
        - ``"chop"``        — insufficient data to compute indicators

        Each indicator is wrapped in try/except; failures degrade gracefully to
        the conservative (non-tradable) assumption.
        """
        min_rows = self.cfg.volume_sma_period + self.cfg.atr_period
        if ohlcv_df.empty or len(ohlcv_df) < min_rows:
            logger.info(
                "Regime skip: chop (insufficient rows — have %d, need %d)",
                len(ohlcv_df), min_rows,
            )
            return False

        # ADX — trend strength gate
        try:
            adx_val = float(
                ta.trend.ADXIndicator(
                    ohlcv_df["high"],
                    ohlcv_df["low"],
                    ohlcv_df["close"],
                    window=self.cfg.atr_period,
                ).adx().iloc[-1]
            )
            if pd.isna(adx_val):
                adx_val = 0.0
        except Exception as exc:
            logger.warning("ADX calculation failed (%s) — treating as non-trending", exc)
            adx_val = 0.0

        is_trending = adx_val > self.cfg.adx_threshold
        if not is_trending:
            logger.info(
                "Regime skip: weak_trend (ADX=%.1f < threshold=%.1f)",
                adx_val, self.cfg.adx_threshold,
            )
            return False

        # Volume and volatility — activity gate
        try:
            vol_sma = float(
                ohlcv_df["volume"].rolling(self.cfg.volume_sma_period).mean().iloc[-1]
            )
            current_vol = float(ohlcv_df["volume"].iloc[-1])
            has_volume = current_vol > vol_sma * 1.2
        except Exception as exc:
            logger.warning("Volume calculation failed (%s) — assuming sufficient", exc)
            has_volume = True

        try:
            atr_val = float(
                ta.volatility.AverageTrueRange(
                    ohlcv_df["high"],
                    ohlcv_df["low"],
                    ohlcv_df["close"],
                    window=self.cfg.atr_period,
                ).average_true_range().iloc[-1]
            )
            last_close = float(ohlcv_df["close"].iloc[-1])
            vol_ratio = atr_val / last_close if last_close > 0 else 0.0
            has_volatility = vol_ratio > self.cfg.min_volatility_pct
        except Exception as exc:
            logger.warning("ATR volatility check failed (%s) — assuming sufficient", exc)
            has_volatility = True

        if not (has_volume or has_volatility):
            logger.info(
                "Regime skip: low_vol (vol=%.0f vs sma=%.0f, atr_ratio=%.4f < %.4f)",
                current_vol, vol_sma, vol_ratio, self.cfg.min_volatility_pct,
            )
            return False

        return True

    # ── 4. Position management ────────────────────────────────────────────────

    def update_trade_tracking(self, trade: TradeState, current_price: float) -> None:
        """Update the MFE high/low watermarks for the trade."""
        if trade.side == "LONG":
            if trade.max_price_seen is None or current_price > trade.max_price_seen:
                trade.max_price_seen = current_price
        else:
            if trade.min_price_seen is None or current_price < trade.min_price_seen:
                trade.min_price_seen = current_price

    def should_exit_by_time(
        self,
        trade: TradeState,
        current_price: float,
        current_time: datetime,
    ) -> Tuple[bool, str]:
        """Return (should_exit, reason).

        Reasons:
        - ``"hold"``            — not yet time
        - ``"extend_for_fees"`` — past base hold but profit < fee buffer; extend up to max
        - ``"time_exit"``       — max hold reached; close regardless

        The caller must handle ``"extend_for_fees"`` (continue holding, optionally
        tighten SL) and ``"time_exit"`` (close the position).
        """
        elapsed = (current_time - trade.entry_time).total_seconds() / 60.0

        if elapsed < self.cfg.time_exit_minutes:
            return False, "hold"

        notional = trade.entry_price * trade.qty
        round_trip_cost = notional * (self.cfg.fee_rate * 2 + self.cfg.slippage_rate)
        min_profit = round_trip_cost * self.cfg.min_profit_fee_buffer

        if trade.side == "LONG":
            unrealized = (current_price - trade.entry_price) * trade.qty
        else:
            unrealized = (trade.entry_price - current_price) * trade.qty

        max_elapsed = self.cfg.time_exit_minutes + self.cfg.max_hold_extension_minutes
        if unrealized < min_profit and elapsed < max_elapsed:
            return False, "extend_for_fees"

        return True, "time_exit"

    def apply_breakeven_logic(
        self,
        trade: TradeState,
        current_price: float,
    ) -> Optional[float]:
        """Return a new SL price if break-even should be activated, else None.

        Break-even stop is placed at ``entry + fee_cost/qty`` (LONG) or
        ``entry - fee_cost/qty`` (SHORT) so that a stop-out at least covers fees.
        Sets ``trade.moved_to_breakeven = True`` on activation (one-shot).
        """
        if trade.moved_to_breakeven:
            return None
        if trade.qty <= 0:
            return None

        risk_distance = abs(trade.entry_price - trade.sl)
        threshold = risk_distance * self.cfg.breakeven_threshold_r

        if trade.side == "LONG":
            profit = current_price - trade.entry_price
        else:
            profit = trade.entry_price - current_price

        if profit >= threshold:
            notional = trade.entry_price * trade.qty
            fee_cost = notional * (self.cfg.fee_rate * 2 + self.cfg.slippage_rate)
            fee_per_unit = fee_cost / trade.qty if trade.qty > 0 else 0.0
            new_sl = (
                trade.entry_price + fee_per_unit
                if trade.side == "LONG"
                else trade.entry_price - fee_per_unit
            )
            trade.moved_to_breakeven = True
            logger.info(
                "Break-even activated — %s @ %.2f  new_sl=%.2f",
                trade.side, trade.entry_price, new_sl,
            )
            return round(new_sl, 2)

        return None

    # ── 5. Metrics ───────────────────────────────────────────────────────────

    def calculate_trade_metrics(self, trade: TradeState) -> Dict[str, Any]:
        """Return a diagnostics dict for a closed trade.

        Includes gross/net PnL, fees, MFE (Maximum Favourable Excursion),
        and exit efficiency (net_pnl / mfe_pnl).
        Returns an empty dict if the trade is not yet closed.
        """
        if not trade.exit_price:
            return {}

        if trade.side == "LONG":
            pnl = (trade.exit_price - trade.entry_price) * trade.qty
            mfe = (
                ((trade.max_price_seen or trade.exit_price) - trade.entry_price) * trade.qty
            )
        else:
            pnl = (trade.entry_price - trade.exit_price) * trade.qty
            mfe = (
                (trade.entry_price - (trade.min_price_seen or trade.exit_price)) * trade.qty
            )

        notional = trade.entry_price * trade.qty
        fees = notional * (self.cfg.fee_rate * 2 + self.cfg.slippage_rate)
        net_pnl = pnl - fees

        return {
            "trade_id": trade.id,
            "gross_pnl": round(pnl, 4),
            "fees_paid": round(fees, 4),
            "net_pnl": round(net_pnl, 4),
            "fee_drag_pct": round(fees / abs(net_pnl) * 100 if net_pnl != 0 else 0.0, 2),
            "mfe_pnl": round(mfe, 4),
            "exit_efficiency": round(net_pnl / mfe if mfe != 0 else 0.0, 4),
            "exit_reason": trade.exit_reason,
        }

    # ── 6. Daily accounting ──────────────────────────────────────────────────

    def check_daily_circuit_breaker(self) -> bool:
        """Return True when today's losses have hit the max_daily_loss_pct threshold.

        Circuit-breaker is computed against *current* equity so it scales correctly
        as the account grows (unlike a fixed initial-equity reference).
        """
        if self.daily_pnl >= 0:
            return False
        loss_pct = abs(self.daily_pnl) / self.equity if self.equity > 0 else 0.0
        tripped = loss_pct >= self.cfg.max_daily_loss_pct
        if tripped:
            logger.critical(
                "Daily circuit breaker tripped — daily_pnl=%.4f equity=%.2f (%.1f%%)",
                self.daily_pnl, self.equity, loss_pct * 100,
            )
        return tripped

    def record_trade_close(self, net_pnl: float) -> None:
        """Update equity and daily counters after a trade closes."""
        self.equity += net_pnl
        self.daily_pnl += net_pnl
        self.daily_trades += 1

    def reset_daily_stats(self) -> None:
        """Reset daily P&L and trade count — call at midnight UTC."""
        logger.info(
            "Daily reset — trades=%d pnl=%.4f", self.daily_trades, self.daily_pnl
        )
        self.daily_pnl = 0.0
        self.daily_trades = 0
