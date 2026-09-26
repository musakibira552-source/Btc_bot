"""
Break of Structure (BOS) and Market Structure Shift (MSS) detection.

Per the strategy: a valid demand/supply zone must be the one that CAUSED
a BOS (not just any swing point). After price retraces into that zone,
we then wait for an MSS on the lower timeframe — a break of a minor
swing point in the direction of the original bias — before entering.
"""


def find_swing_points(candles, span=2):
    """
    Returns swing points as a list of dicts:
    {"type": "high"|"low", "price": float, "index": int}
    """
    points = []
    for i in range(len(candles)):
        if i - span < 0 or i + span >= len(candles):
            continue
        high = candles[i]["high"]
        low = candles[i]["low"]

        is_high = all(candles[j]["high"] <= high for j in range(i - span, i + span + 1) if j != i)
        is_low = all(candles[j]["low"] >= low for j in range(i - span, i + span + 1) if j != i)

        if is_high:
            points.append({"type": "high", "price": high, "index": i})
        elif is_low:
            points.append({"type": "low", "price": low, "index": i})

    return points


def detect_bos(candles, direction, span=2):
    """
    Checks whether price has broken (closed beyond) the most recent
    relevant swing point in `direction`:
      "bullish" -> close above the last swing high (uptrend continuation)
      "bearish" -> close below the last swing low (downtrend continuation)
    Returns {"broken_level": float, "break_index": int} or None.
    """
    swings = find_swing_points(candles, span)
    wanted_type = "high" if direction == "bullish" else "low"
    candidates = [s for s in swings if s["type"] == wanted_type]
    if not candidates:
        return None

    target = candidates[-1]
    for i in range(target["index"] + 1, len(candles)):
        c = candles[i]
        if direction == "bullish" and c["close"] > target["price"]:
            return {"broken_level": target["price"], "break_index": i}
        if direction == "bearish" and c["close"] < target["price"]:
            return {"broken_level": target["price"], "break_index": i}

    return None


def detect_mss(candles, bias_direction, span=1):
    """
    MSS is the same mechanic as BOS but checked with a tighter span on
    the entry timeframe, after a retracement — it signals structure
    shifting back in favor of the higher-timeframe bias.
    """
    return detect_bos(candles, bias_direction, span=span)


def nearest_swing_extreme(candles, direction, span=1, lookback=40):
    """
    Finds the most recent swing low (for a bullish setup, to use as SL)
    or swing high (for a bearish setup) within the lookback window.
    Returns the price, or None if none found.
    """
    data = candles[-lookback:] if len(candles) > lookback else candles
    swings = find_swing_points(data, span)
    wanted_type = "low" if direction == "bullish" else "high"
    candidates = [s for s in swings if s["type"] == wanted_type]
    if not candidates:
        return None
    return candidates[-1]["price"]
