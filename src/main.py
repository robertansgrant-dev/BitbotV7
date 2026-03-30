"""Entry point — starts the Flask web server with the bot runner."""

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path when running as `python src/main.py`
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.bot.bot_runner import BotRunner, BotState
from src.config.settings import get_settings
from src.ui.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Initialise state, create the Flask app, and serve on localhost:5000."""
    settings = get_settings()
    state = BotState(settings)
    runner = BotRunner(state)
    app = create_app(state, runner)

    logger.info("Starting BitbotV7 — http://localhost:8000")
    logger.info("Mode: %s  Style: %s  Symbol: %s", state.mode, state.style, settings.symbol)

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=settings.flask_debug,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
