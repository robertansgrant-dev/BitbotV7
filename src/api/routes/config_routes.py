"""Config and log management endpoints."""

import logging
import shutil
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from src.api.schemas.models import ActionResponse, ConfigResponse, ConfigUpdateRequest

logger = logging.getLogger(__name__)
config_bp = Blueprint("config", __name__)


def _s():
    return current_app.config["BOT_STATE"]


@config_bp.get("/api/config")
def get_config():
    s = _s()
    p = s.preset
    return jsonify(
        ConfigResponse(
            style=s.style,
            position_size_pct=p.position_size_pct,
            stop_loss_pct=p.stop_loss_pct,
            risk_reward=p.risk_reward,
            max_daily_trades=p.max_daily_trades,
            sma_fast=p.sma_fast,
            sma_slow=p.sma_slow,
            sma_trend=p.sma_trend,
            htf_timeframe=p.htf_timeframe,
            trailing_stop=p.trailing_stop,
        ).model_dump()
    )


@config_bp.post("/api/config/update")
def update_config():
    try:
        body = ConfigUpdateRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    s = _s()
    with s._lock:
        if body.style:
            s.style = body.style
        if body.max_daily_loss_pct is not None:
            s.settings.max_daily_loss_pct = body.max_daily_loss_pct

    return jsonify(ActionResponse(success=True, message="Config updated").model_dump())


@config_bp.post("/api/logs/clear")
def clear_logs():
    log_dir = Path("logs")
    if log_dir.exists():
        shutil.rmtree(log_dir)
        log_dir.mkdir(exist_ok=True)
    return jsonify(ActionResponse(success=True, message="Logs cleared").model_dump())
