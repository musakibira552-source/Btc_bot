"""
Identifies supply and demand zones from swing highs/lows (fractal-based).
A zone is the candle range where price turned, before making a strong move away.
"""


def _is_swing_high(candles, i, span=2):
    if i - span < 0 or i + span >= len(candles):
        return False
    high = candles[i]["high"]
    for j in range(i - span, i + span + 1):
        if j != i and candles[j]["high"] >= high:
            return False
    return True


def _is_swing_low(candles, i, span=2):
    if i - span < 0 or i + span >= len(candles):
        return False
    low = candles[i]["low"]
    for j in range(i - span, i + span + 1):
        if j != i and candles[j]["low"] <= low:
            return False
    return True


def find_zones(candles, lookback=150, span=2):
    """
    Returns a list of zones (most recent first):
    {"type": "supply"|"demand", "top": float, "bottom": float, "index": int}
    """
    zones = []
    data = candles[-lookback:] if len(candles) > lookback else candles

    for i in range(len(data)):
        if _is_swing_high(data, i, span):
            zones.append({
                "type": "supply",
                "top": data[i]["high"],
                "bottom": min(data[i]["open"], data[i]["close"]),
                "index": i,
            })
        elif _is_swing_low(data, i, span):
            zones.append({
                "type": "demand",
                "top": max(data[i]["open"], data[i]["close"]),
                "bottom": data[i]["low"],
                "index": i,
            })

    zones.sort(key=lambda z: z["index"], reverse=True)
    return zones


def nearest_untapped_zone(zones, current_price, direction):
    """
    direction: "bullish" -> looking for a demand zone below price
               "bearish" -> looking for a supply zone above price
    Returns the closest matching zone that price hasn't already closed through, or None.
    """
    wanted_type = "demand" if direction == "bullish" else "supply"
    candidates = [z for z in zones if z["type"] == wanted_type]

    if wanted_type == "demand":
        candidates = [z for z in candidates if z["top"] <= current_price]
        candidates.sort(key=lambda z: current_price - z["top"])
    else:
        candidates = [z for z in candidates if z["bottom"] >= current_price]
        candidates.sort(key=lambda z: z["bottom"] - current_price)

    return candidates[0] if candidates else None
