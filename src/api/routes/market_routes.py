"""Market data endpoints: price, chart, session."""

import logging

import pandas as pd
from flask import Blueprint, current_app, jsonify

from src.api.schemas.models import CandleData, ChartResponse, MarketResponse, SessionResponse
from src.bot.analysis.session_analyzer import (
    calculate_atr_value,
    calculate_volume_ratio,
    get_current_session,
    get_session_recommendation,
)
from src.bot.strategy.indicators import macd as calc_macd
from src.bot.strategy.indicators import sma as calc_sma

logger = logging.getLogger(__name__)
market_bp = Blueprint("market", __name__)


def _s():
    return current_app.config["BOT_STATE"]


@market_bp.get("/api/market")
def get_market():
    s = _s()
    try:
        ticker = s.get_client().get_ticker_24h(s.settings.symbol)
        return jsonify(
            MarketResponse(
                symbol=s.settings.symbol,
                price=float(ticker["lastPrice"]),
                change_24h=float(ticker["priceChangePercent"]),
                volume_24h=float(ticker["volume"]),
                high_24h=float(ticker["highPrice"]),
                low_24h=float(ticker["lowPrice"]),
            ).model_dump()
        )
    except Exception as exc:
        logger.error("Market data error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@market_bp.get("/api/chart/<timeframe>")
def get_chart(timeframe: str):
    s = _s()
    try:
        # Fetch extra candles so the 200-period SMA trend has enough history to compute
        klines = s.get_client().get_klines(s.settings.symbol, timeframe, 500)
    except Exception as exc:
        logger.error("Chart fetch error: %s", exc)
        return jsonify({"error": str(exc)}), 500

    df = pd.DataFrame(klines)
    close = df["close"]
    preset = s.preset
    df["sma_fast"] = calc_sma(close, preset.sma_fast)
    df["sma_slow"] = calc_sma(close, preset.sma_slow)
    df["sma_trend"] = calc_sma(close, preset.sma_trend)
    macd_df = calc_macd(close)
    # Trim to last 200 candles after all indicators are computed with full history
    df = df.tail(200).reset_index(drop=True)
    macd_df = macd_df.tail(200).reset_index(drop=True)

    def _f(v) -> float | None:
        return None if pd.isna(v) else float(v)

    candles = [
        CandleData(
            time=int(row["open_time"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            sma_fast=_f(row["sma_fast"]),
            sma_slow=_f(row["sma_slow"]),
            sma_trend=_f(row["sma_trend"]),
        ).model_dump()
        for _, row in df.iterrows()
    ]

    macd_data = [
        {
            "time": int(df.iloc[i]["open_time"]),
            "macd": _f(macd_df.iloc[i]["macd"]),
            "signal": _f(macd_df.iloc[i]["signal"]),
            "histogram": _f(macd_df.iloc[i]["histogram"]),
        }
        for i in range(len(df))
    ]

    return jsonify(
        ChartResponse(
            symbol=s.settings.symbol,
            timeframe=timeframe,
            candles=candles,
            macd=macd_data,
        ).model_dump()
    )


@market_bp.get("/api/session")
def get_session():
    s = _s()
    try:
        klines = s.get_client().get_klines(s.settings.symbol, "1m", 50)
    except Exception as exc:
        logger.error("Session fetch error: %s", exc)
        return jsonify({"error": str(exc)}), 500

    df = pd.DataFrame(klines)
    session = get_current_session()
    atr_val = calculate_atr_value(df)
    vol_ratio = calculate_volume_ratio(df)
    rec = get_session_recommendation(session, atr_val, vol_ratio)

    return jsonify(
        SessionResponse(
            session=session,
            recommendation=rec,
            atr=atr_val,
            volume_ratio=vol_ratio,
        ).model_dump()
    )
