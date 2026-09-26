"""
Detects liquidity pools (equal highs/lows) and sweeps of those pools —
used to confirm that stops were hunted before a reversal into a zone.
"""


def find_equal_highs_lows(candles, lookback=100, tolerance_pct=0.0008):
    """
    Finds clusters of roughly-equal highs (resistance liquidity) and
    roughly-equal lows (support liquidity).
    Returns {"equal_highs": [levels], "equal_lows": [levels]}
    """
    data = candles[-lookback:] if len(candles) > lookback else candles
    highs = [c["high"] for c in data]
    lows = [c["low"] for c in data]

    def cluster(values):
        clusters = []
        used = [False] * len(values)
        for i, v in enumerate(values):
            if used[i]:
                continue
            group = [v]
            used[i] = True
            for j in range(i + 1, len(values)):
                if used[j]:
                    continue
                if abs(values[j] - v) / v <= tolerance_pct:
                    group.append(values[j])
                    used[j] = True
            if len(group) >= 2:
                clusters.append(sum(group) / len(group))
        return clusters

    return {
        "equal_highs": cluster(highs),
        "equal_lows": cluster(lows),
    }


def swept_recently(candles, level, side, within=5):
    """
    Checks whether the last `within` candles wicked through `level`
    and closed back on the other side (a liquidity sweep).
    side: "high" -> swept up through resistance then closed back below
          "low"  -> swept down through support then closed back above
    """
    recent = candles[-within:]
    for c in recent:
        if side == "high" and c["high"] > level and c["close"] < level:
            return True
        if side == "low" and c["low"] < level and c["close"] > level:
            return True
    return False
