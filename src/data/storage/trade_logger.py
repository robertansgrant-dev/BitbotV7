"""Append-only CSV trade logging."""

import csv
import logging
import threading
from dataclasses import asdict
from pathlib import Path

from src.data.models.trade import Trade

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_HEADERS = [
    "trade_id", "symbol", "side", "entry_price", "exit_price",
    "quantity", "timestamp", "pnl", "mode", "style", "signal_type",
]


def log_trade(path: Path, trade: Trade) -> None:
    """Append a completed trade to the CSV log (thread-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with _lock:
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_HEADERS)
            if write_header:
                writer.writeheader()
            row = asdict(trade)
            writer.writerow({k: row.get(k, "") for k in _HEADERS})
    logger.debug("Logged trade %s", trade.trade_id)


def load_trades(path: Path) -> list[dict]:
    """Load all trades from the CSV log. Returns empty list if missing."""
    if not path.exists():
        return []
    with _lock:
        try:
            with path.open("r", newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except OSError as exc:
            logger.warning("Failed to load trades from %s: %s", path, exc)
            return []


def delete_log(path: Path) -> None:
    """Delete the trade log file."""
    with _lock:
        if path.exists():
            path.unlink()
            logger.info("Deleted trade log %s", path)
