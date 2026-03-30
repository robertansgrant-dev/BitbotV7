"""Bot control endpoints: status, start, stop, reset, mode switch."""

import logging

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from src.api.schemas.models import ActionResponse, StatusResponse, SwitchModeRequest

logger = logging.getLogger(__name__)
bot_bp = Blueprint("bot", __name__)


def _s():
    return current_app.config["BOT_STATE"]


def _r():
    return current_app.config["BOT_RUNNER"]


@bot_bp.get("/api/status")
def get_status():
    s = _s()
    return jsonify(
        StatusResponse(
            running=s.running,
            mode=s.mode,
            style=s.style,
            emergency_stop=s.emergency_stop,
            last_error=s.last_error,
            last_price=s.last_price,
        ).model_dump()
    )


@bot_bp.post("/api/bot/start")
def start_bot():
    ok = _r().start()
    return jsonify(
        ActionResponse(
            success=ok,
            message="Bot started" if ok else "Already running",
        ).model_dump()
    )


@bot_bp.post("/api/bot/stop")
def stop_bot():
    ok = _r().stop()
    return jsonify(
        ActionResponse(
            success=ok,
            message="Bot stopped" if ok else "Not running",
        ).model_dump()
    )


@bot_bp.post("/api/bot/reset")
def reset_bot():
    s = _s()
    with s._lock:
        s.portfolio.current_capital = s.settings.initial_capital
        s.portfolio.daily_pnl = 0.0
        s.portfolio.daily_loss_pct = 0.0
        s.portfolio.daily_trades = 0
        s.portfolio.total_trades = 0
        s.portfolio.winning_trades = 0
        s.position = None
        s.emergency_stop = False
        s.last_error = None
        s.trades.clear()
    return jsonify(ActionResponse(success=True, message="Portfolio reset").model_dump())


@bot_bp.post("/api/mode/switch")
def switch_mode():
    try:
        body = SwitchModeRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    s = _s()
    with s._lock:
        s.mode = body.mode
    return jsonify(
        ActionResponse(success=True, message=f"Mode switched to {body.mode}").model_dump()
    )
