"""Application settings loaded from environment variables."""

import logging
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """All environment-based configuration for BitbotV7."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=False,
    )

    # Binance API
    testnet_api_key: str = Field(default="")
    testnet_secret_key: str = Field(default="")
    live_api_key: str = Field(default="")
    live_secret_key: str = Field(default="")

    # Flask
    flask_env: str = Field(default="development")
    flask_debug: bool = Field(default=True)
    secret_key: str = Field(default="change-me-in-production")

    # Bot defaults
    default_mode: Literal["paper", "testnet", "live"] = Field(default="paper")
    default_style: Literal["scalping", "day_trading", "swing_trading"] = Field(default="scalping")

    # Trading parameters
    symbol: str = Field(default="BTCUSDT")
    initial_capital: float = Field(default=1000.0)
    max_daily_loss_pct: float = Field(default=5.0)
    max_position_value_pct: float = Field(default=80.0)
    emergency_stop: bool = Field(default=False)
    update_interval: int = Field(default=5)
    # Taker fee rate per side (Binance BTC/USDT spot taker = 0.1%)
    fee_rate: float = Field(default=0.001)


def get_settings() -> Settings:
    """Return a Settings instance loaded from environment / .env file."""
    return Settings()
