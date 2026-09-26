"""
Fair Value Gap (FVG) = a 3-candle imbalance where candle 1's range and
candle 3's range don't overlap, leaving a gap that price often revisits.
"""


def find_fvgs(candles, lookback=40):
    """
    Returns a list of FVGs (most recent first):
    {"type": "bullish"|"bearish", "top": float, "bottom": float, "index": int}
    """
    data = candles[-lookback:] if len(candles) > lookback else candles
    fvgs = []

    for i in range(2, len(data)):
        c1, c3 = data[i - 2], data[i]

        # Bullish FVG: candle1 high < candle3 low (gap up)
        if c1["high"] < c3["low"]:
            fvgs.append({
                "type": "bullish",
                "top": c3["low"],
                "bottom": c1["high"],
                "index": i,
            })

        # Bearish FVG: candle1 low > candle3 high (gap down)
        elif c1["low"] > c3["high"]:
            fvgs.append({
                "type": "bearish",
                "top": c1["low"],
                "bottom": c3["high"],
                "index": i,
            })

    fvgs.sort(key=lambda f: f["index"], reverse=True)
    return fvgs


def price_inside_fvg(price, fvg):
    return fvg["bottom"] <= price <= fvg["top"]
