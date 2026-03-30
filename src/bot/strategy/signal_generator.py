"""Signal generation: CROSSOVER, PULLBACK, MOMENTUM, BREAKOUT."""

import logging
from typing import Literal

import pandas as pd

from src.bot.strategy.indicators import sma, rsi
from src.config.presets import StylePreset

logger = logging.getLogger(__name__)

SignalType = Literal["CROSSOVER", "PULLBACK", "MOMENTUM", "BREAKOUT", "NONE"]
Direction = Literal["LONG", "SHORT", "NONE"]
Trend = Literal["UP", "DOWN", "NEUTRAL"]


def get_htf_trend(df_htf: pd.DataFrame, preset: StylePreset) -> Trend:
    """Determine higher-timeframe trend direction."""
    if len(df_htf) < preset.sma_trend:
        return "NEUTRAL"
    close = df_htf["close"]
    trend_val = sma(close, preset.sma_trend).iloc[-1]
    fast_val = sma(close, preset.sma_fast).iloc[-1]
    price = close.iloc[-1]
    if price > trend_val and fast_val > trend_val:
        return "UP"
    if price < trend_val and fast_val < trend_val:
        return "DOWN"
    return "NEUTRAL"


def _crossover(df: pd.DataFrame, preset: StylePreset, trend: Trend) -> Direction:
    """SMA fast/slow crossover in the trend direction."""
    if len(df) < preset.sma_slow + 2:
        return "NONE"
    fast = sma(df["close"], preset.sma_fast)
    slow = sma(df["close"], preset.sma_slow)
    crossed_up = fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]
    crossed_dn = fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]
    if crossed_up and trend == "UP":
        return "LONG"
    if crossed_dn and trend == "DOWN":
        return "SHORT"
    return "NONE"


def _pullback(df: pd.DataFrame, preset: StylePreset, trend: Trend) -> Direction:
    """Price pulls back to fast SMA and bounces with RSI confirmation."""
    if len(df) < preset.sma_slow + 2:
        return "NONE"
    close = df["close"]
    fast = sma(close, preset.sma_fast)
    slow = sma(close, preset.sma_slow)
    price = close.iloc[-1]
    prev = close.iloc[-2]
    fast_val = fast.iloc[-1]
    slow_val = slow.iloc[-1]
    tol = fast_val * 0.003  # Increased from 0.2% to 0.3% to avoid minor wicks
    rsi_val = rsi(close).iloc[-1]

    if trend == "UP" and fast_val > slow_val:
        if rsi_val >= 40 and prev <= fast_val + tol and price > prev:
            return "LONG"
    if trend == "DOWN" and fast_val < slow_val:
        if rsi_val <= 60 and prev >= fast_val - tol and price < prev:
            return "SHORT"
    return "NONE"


def _momentum(df: pd.DataFrame, preset: StylePreset, trend: Trend) -> Direction:
    """Fast SMA rising, price above both MAs, RSI 50-75."""
    if len(df) < preset.sma_slow + 15:
        return "NONE"
    close = df["close"]
    fast = sma(close, preset.sma_fast)
    slow = sma(close, preset.sma_slow)
    rsi_val = rsi(close).iloc[-1]
    price = close.iloc[-1]
    fast_val = fast.iloc[-1]
    slow_val = slow.iloc[-1]

    if trend == "UP":
        fast_rising = fast.iloc[-1] > fast.iloc[-3]
        if fast_rising and price > fast_val > slow_val and 50 <= rsi_val <= 75:
            return "LONG"
    if trend == "DOWN":
        fast_falling = fast.iloc[-1] < fast.iloc[-3]
        if fast_falling and price < fast_val < slow_val and 25 <= rsi_val <= 50:
            return "SHORT"
    return "NONE"


def _breakout(df: pd.DataFrame, trend: Trend) -> Direction:
    """Price exceeds 20-bar high/low with volume and momentum confirmation."""
    if len(df) < 50:
        return "NONE"
    prev_high = df["high"].iloc[-21:-1].max()
    prev_low = df["low"].iloc[-21:-1].min()
    price = df["close"].iloc[-1]
    volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].iloc[-21:-1].mean()

    if volume < avg_volume * 1.5:
        return "NONE"

    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    candle_range = df["high"].iloc[-1] - df["low"].iloc[-1]
    if candle_range == 0 or body / candle_range < 0.6:
        return "NONE"

    if trend == "UP" and price > prev_high:
        return "LONG"
    if trend == "DOWN" and price < prev_low:
        return "SHORT"
    return "NONE"


def get_signal(
    df: pd.DataFrame,
    df_htf: pd.DataFrame,
    preset: StylePreset,
) -> tuple[SignalType, Direction]:
    """Return (signal_type, direction) for the current market state."""
    trend = get_htf_trend(df_htf, preset)
    if trend == "NEUTRAL":
        return "NONE", "NONE"

    checks: list[tuple[Direction, SignalType]] = [
        (_crossover(df, preset, trend), "CROSSOVER"),
        (_pullback(df, preset, trend), "PULLBACK"),
        (_momentum(df, preset, trend), "MOMENTUM"),
        (_breakout(df, trend), "BREAKOUT"),
    ]
    for direction, name in checks:
        if direction != "NONE":
            logger.info("Signal: %s %s (HTF trend=%s)", name, direction, trend)
            return name, direction  # type: ignore[return-value]

    return "NONE", "NONE"
