"""Flask application factory."""

import logging

from flask import Flask, render_template
from flask_cors import CORS

from src.api.routes.activity_routes import activity_bp
from src.api.routes.bot_routes import bot_bp
from src.api.routes.config_routes import config_bp
from src.api.routes.market_routes import market_bp
from src.api.routes.portfolio_routes import portfolio_bp

logger = logging.getLogger(__name__)


def create_app(bot_state, bot_runner) -> Flask:
    """Create and configure the Flask app with all blueprints registered."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    CORS(app)

    app.config["BOT_STATE"] = bot_state
    app.config["BOT_RUNNER"] = bot_runner
    app.config["SECRET_KEY"] = bot_state.settings.secret_key

    app.register_blueprint(activity_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(config_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
