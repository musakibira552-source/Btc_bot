"""
Displacement = a strong, momentum candle that breaks structure,
signalling institutional participation rather than a slow grind.
"""


def _avg_body_size(candles):
    bodies = [abs(c["close"] - c["open"]) for c in candles]
    return sum(bodies) / len(bodies) if bodies else 0


def detect_displacement(candles, lookback=30, multiplier=1.8):
    """
    Returns the displacement candle (dict) plus its direction if the most
    recent candle's body is significantly larger than the recent average,
    otherwise returns None.
    """
    if len(candles) < lookback + 1:
        return None

    recent = candles[-(lookback + 1):-1]
    last = candles[-1]

    avg_body = _avg_body_size(recent)
    last_body = abs(last["close"] - last["open"])

    if avg_body == 0 or last_body < avg_body * multiplier:
        return None

    direction = "bullish" if last["close"] > last["open"] else "bearish"
    return {
        "candle": last,
        "direction": direction,
        "body_size": last_body,
        "avg_body": avg_body,
    }
