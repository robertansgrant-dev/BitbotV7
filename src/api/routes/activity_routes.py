"""Activity feed endpoints — SSE stream and polling fallback."""

import json
import logging
import time
from typing import Generator

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

logger = logging.getLogger(__name__)
activity_bp = Blueprint("activity", __name__)


def _s():
    return current_app.config["BOT_STATE"]


def _sse_generator(last_id: int) -> Generator[str, None, None]:
    """Yield SSE-formatted events for all activity events newer than last_id."""
    state = _s()
    try:
        while True:
            with state._lock:
                new_events = [e for e in state.activity_events if e["id"] > last_id]

            for event in new_events:
                last_id = event["id"]
                payload = json.dumps(event)
                yield f"id: {event['id']}\ndata: {payload}\n\n"

            # heartbeat every 15 s to keep connection alive through proxies
            yield ": keepalive\n\n"
            time.sleep(15)
    except GeneratorExit:
        logger.debug("SSE client disconnected")


@activity_bp.get("/api/stream/activity")
def stream_activity() -> Response:
    """Server-Sent Events endpoint — streams live bot activity to the browser."""
    try:
        last_id = int(request.args.get("since", 0))
    except (ValueError, TypeError):
        last_id = 0

    return Response(
        stream_with_context(_sse_generator(last_id)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@activity_bp.get("/api/activity")
def get_activity() -> Response:
    """Polling fallback — returns all activity events newer than ?since=<id>."""
    try:
        last_id = int(request.args.get("since", 0))
    except (ValueError, TypeError):
        last_id = 0

    state = _s()
    with state._lock:
        events = [e for e in state.activity_events if e["id"] > last_id]

    return jsonify({"events": events})
