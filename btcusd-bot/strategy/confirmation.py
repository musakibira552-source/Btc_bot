"""
Confirms an entry trigger at a zone using simple candle patterns:
bullish/bearish engulfing, or a strong rejection wick.
"""


def is_bullish_engulfing(candles):
    if len(candles) < 2:
        return False
    prev, last = candles[-2], candles[-1]
    return (
        prev["close"] < prev["open"] and
        last["close"] > last["open"] and
        last["close"] >= prev["open"] and
        last["open"] <= prev["close"]
    )


def is_bearish_engulfing(candles):
    if len(candles) < 2:
        return False
    prev, last = candles[-2], candles[-1]
    return (
        prev["close"] > prev["open"] and
        last["close"] < last["open"] and
        last["close"] <= prev["open"] and
        last["open"] >= prev["close"]
    )


def is_rejection_wick(candles, direction, min_wick_ratio=0.6):
    """
    direction: "bullish" -> long lower wick (rejection of lower prices)
               "bearish" -> long upper wick (rejection of higher prices)
    """
    last = candles[-1]
    full_range = last["high"] - last["low"]
    if full_range == 0:
        return False

    body_top = max(last["open"], last["close"])
    body_bottom = min(last["open"], last["close"])

    if direction == "bullish":
        lower_wick = body_bottom - last["low"]
        return (lower_wick / full_range) >= min_wick_ratio
    else:
        upper_wick = last["high"] - body_top
        return (upper_wick / full_range) >= min_wick_ratio


def confirm_entry(candles, direction):
    """
    Returns True if any confirmation pattern supports the given direction
    on the most recent candle.
    """
    if direction == "bullish":
        return is_bullish_engulfing(candles) or is_rejection_wick(candles, "bullish")
    else:
        return is_bearish_engulfing(candles) or is_rejection_wick(candles, "bearish")
