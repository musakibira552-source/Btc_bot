"""
Pulls OHLC candle data from Twelve Data for a given pair/timeframe.
Docs: https://twelvedata.com/docs#time-series
"""

import requests
import config

BASE_URL = "https://api.twelvedata.com/time_series"


def get_candles(symbol: str, interval: str, outputsize: int = 100):
    """
    Returns a list of candle dicts, OLDEST first:
    [{"datetime": ..., "open": float, "high": float, "low": float, "close": float}, ...]
    Returns None on failure (bad symbol, rate limit, no API key, etc).
    """
    if not config.TWELVEDATA_API_KEY:
        raise RuntimeError("TWELVEDATA_API_KEY is not configured.")

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": config.TWELVEDATA_API_KEY,
        "order": "ASC",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        payload = resp.json()
    except Exception as e:
        print(f"[fetcher] request failed for {symbol}/{interval}: {e}")
        return None

    if payload.get("status") == "error" or "values" not in payload:
        print(f"[fetcher] API error for {symbol}/{interval}: {payload.get('message')}")
        return None

    candles = []
    for row in payload["values"]:
        try:
            candles.append({
                "datetime": row["datetime"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            })
        except (KeyError, ValueError):
            continue

    return candles if candles else None
