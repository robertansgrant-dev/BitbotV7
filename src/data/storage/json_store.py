"""Thread-safe JSON persistence for portfolio and session data."""

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Write data to a JSON file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.debug("Saved JSON to %s", path)


def load_json(path: Path) -> dict[str, Any]:
    """Load data from a JSON file. Returns empty dict if missing or corrupt."""
    if not path.exists():
        return {}
    with _lock:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load %s: %s", path, exc)
            return {}


def delete_json(path: Path) -> None:
    """Delete a JSON file if it exists."""
    with _lock:
        if path.exists():
            path.unlink()
            logger.info("Deleted %s", path)
