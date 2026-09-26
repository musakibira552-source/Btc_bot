"""
Checks whether current price has retraced back into a given zone
(supply/demand or FVG) — the pullback we wait for before an entry.
"""


def has_retraced_into(price, zone, buffer_pct=0.0005):
    """
    zone: dict with "top" and "bottom" keys (works for both
    supply/demand zones and FVGs).
    Adds a small buffer so we don't require a pixel-perfect touch.
    """
    span = zone["top"] - zone["bottom"]
    buffer = span * buffer_pct if span > 0 else 0
    return (zone["bottom"] - buffer) <= price <= (zone["top"] + buffer)


def retracement_depth_pct(price, swing_start, swing_end):
    """
    Returns how far price has retraced as a % of the prior swing
    (0 = no retrace, 1 = fully retraced to swing start).
    """
    full_range = swing_end - swing_start
    if full_range == 0:
        return 0
    return abs((price - swing_end) / full_range)
