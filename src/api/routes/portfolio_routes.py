"""Portfolio, trade history, and position management endpoints."""

import logging
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from src.api.schemas.models import (
    ActionResponse,
    ManualPositionRequest,
    PortfolioResponse,
    TradeHistoryResponse,
)
from src.bot.risk.risk_manager import TradeState
from src.data.models.position import Position
from src.data.models.trade import Trade

logger = logging.getLogger(__name__)
portfolio_bp = Blueprint("portfolio", __name__)


def _s():
    return current_app.config["BOT_STATE"]


def _pos_dict(pos: Position) -> dict:
    """Serialise a Position to a plain dict."""
    return {
        "symbol": pos.symbol,
        "side": pos.side,
        "entry_price": pos.entry_price,
        "current_price": pos.current_price,
        "quantity": pos.quantity,
        "unrealized_pnl": pos.unrealized_pnl,
        "unrealized_pnl_pct": pos.unrealized_pnl_pct,
        "stop_loss": pos.stop_loss,
        "take_profit": pos.take_profit,
        "open_time": pos.open_time.isoformat(),
        "signal_type": pos.signal_type,
    }


@portfolio_bp.get("/api/portfolio")
def get_portfolio():
    s = _s()
    p = s.portfolio
    return jsonify(
        PortfolioResponse(
            initial_capital=p.initial_capital,
            current_capital=p.current_capital,
            daily_pnl=p.daily_pnl,
            total_pnl=p.total_pnl,
            total_pnl_pct=p.total_pnl_pct,
            daily_trades=p.daily_trades,
            total_trades=p.total_trades,
            win_rate=p.win_rate,
            position=_pos_dict(s.position) if s.position else None,
        ).model_dump()
    )


@portfolio_bp.get("/api/trades")
def get_trades():
    s = _s()
    trades = [
        {
            "trade_id": t.trade_id,
            "symbol": t.symbol,
            "side": t.side,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "fees": t.fees,
            "net_pnl": t.net_pnl,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "timestamp": t.timestamp.isoformat(),
            "signal_type": t.signal_type,
            "exit_reason": t.exit_reason,
        }
        for t in reversed(s.trades[-50:])
    ]
    return jsonify(
        TradeHistoryResponse(
            trades=trades,
            open_position=_pos_dict(s.position) if s.position else None,
        ).model_dump()
    )


@portfolio_bp.post("/api/position/manual")
def open_manual():
    s = _s()
    if s.position:
        return jsonify({"error": "Position already open"}), 400
    try:
        body = ManualPositionRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    client = s.get_client()
    try:
        price = client.get_price(s.settings.symbol)
    except Exception as exc:
        return jsonify({"error": f"Price fetch failed: {exc}"}), 500

    rm = s.risk_manager
    preset = s.preset

    # Sync RM config with current style before sizing
    rm.cfg.sl_atr_mult = preset.atr_sl_multiplier
    rm.cfg.tp_atr_mult = preset.atr_sl_multiplier * preset.risk_reward
    rm.cfg.risk_per_trade_pct = preset.risk_per_trade_pct / 100

    # Attempt ATR-based SL/TP via klines; fall back to fixed % if unavailable
    sl: float
    tp: float
    atr_val: float = 0.0
    try:
        from src.bot.bot_runner import _to_df
        df = _to_df(client.get_klines(s.settings.symbol, "1m", 200))
        sl, tp, atr_val = rm.calculate_dynamic_levels(df, price, body.side)
    except Exception as exc:
        logger.warning("ATR levels unavailable for manual order (%s) — using fixed %%", exc)
        offset_sl = price * (preset.stop_loss_pct / 100)
        offset_tp = offset_sl * preset.risk_reward
        if body.side == "LONG":
            sl = price - offset_sl
            tp = price + offset_tp
        else:
            sl = price + offset_sl
            tp = price - offset_tp

    qty = rm.calculate_position_size(price, sl)

    binance_side = "BUY" if body.side == "LONG" else "SELL"
    try:
        client.place_order(s.settings.symbol, binance_side, qty)
    except Exception as exc:
        return jsonify({"error": f"Order failed: {exc}"}), 500

    with s._lock:
        s.position = Position(
            symbol=s.settings.symbol,
            side=body.side,
            entry_price=price,
            current_price=price,
            quantity=qty,
            open_time=datetime.now(timezone.utc),
            stop_loss=sl,
            take_profit=tp,
            signal_type="MANUAL",
            atr_at_entry=atr_val,
        )
        s.portfolio.daily_trades += 1

    logger.info(
        "Manual %s opened @ %.2f qty=%.6f sl=%.2f tp=%.2f",
        body.side, price, qty, sl, tp,
    )
    return jsonify(
        ActionResponse(
            success=True,
            message=f"Opened {body.side} @ {price:.2f}  sl={sl:.2f}  tp={tp:.2f}",
        ).model_dump()
    )


@portfolio_bp.post("/api/position/close")
def close_position():
    s = _s()
    if not s.position:
        return jsonify({"error": "No open position"}), 400

    pos = s.position
    client = s.get_client()
    try:
        price = client.get_price(s.settings.symbol)
        binance_side = "SELL" if pos.side == "LONG" else "BUY"
        client.place_order(s.settings.symbol, binance_side, pos.quantity)
    except Exception as exc:
        return jsonify({"error": f"Close failed: {exc}"}), 500

    # Use RiskManager metrics for consistent fee + slippage accounting
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
        exit_reason="manual",
    )
    metrics = s.risk_manager.calculate_trade_metrics(closed_ts)
    pnl = pos.unrealized_pnl
    fees = metrics.get("fees_paid", 0.0)
    net = metrics.get("net_pnl", pnl)

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
        mode=s.mode,
        style=s.style,
        signal_type=pos.signal_type,
        exit_reason="manual",
    )
    with s._lock:
        s.portfolio.current_capital += net
        s.portfolio.daily_pnl += net
        s.portfolio.total_fees += fees
        s.portfolio.total_trades += 1
        if net > 0:
            s.portfolio.winning_trades += 1
        s.portfolio.update_drawdown()
        s.trades.append(trade)
        s.position = None

    s.risk_manager.record_trade_close(net)

    logger.info("Manual close @ %.2f pnl=%.4f fees=%.4f net=%.4f", price, pnl, fees, net)
    return jsonify(
        ActionResponse(
            success=True,
            message=f"Closed @ {price:.2f}  PnL={pnl:+.4f}  fees={fees:.4f}  net={net:+.4f}",
        ).model_dump()
    )
