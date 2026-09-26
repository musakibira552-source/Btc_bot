"""
Since this is a signal-only bot (trades are placed manually in MT5),
this module computes a suggested entry/stop/target and risk amount to
include in the alert message — it does not place or manage any live orders.

Rules applied here (from the strategy guide):
- Max 15 pip stop loss
- Minimum 1:2 risk:reward
- Break-even and partial-profit reminders included at 1:1 (informational)
"""

import config


def pip_size(symbol):
    """Returns the pip size for a symbol (0.01 for JPY pairs, 0.0001 otherwise)."""
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def suggested_risk_usd():
    return round(config.ACCOUNT_BALANCE_USD * (config.RISK_PERCENT / 100), 4)


def cap_stop_by_pips(entry_price, stop_price, direction, symbol, max_pips=None):
    """
    Caps the stop distance at max_pips (default from config.MAX_STOP_PIPS).
    If the raw stop (e.g. from a swing low/high) is farther than that,
    tightens it to the max allowed distance instead.
    """
    max_pips = max_pips or config.MAX_STOP_PIPS
    pip = pip_size(symbol)
    max_distance = max_pips * pip
    distance = abs(entry_price - stop_price)

    if distance <= max_distance:
        return stop_price

    if direction == "bullish":
        return entry_price - max_distance
    else:
        return entry_price + max_distance


def calculate_targets(entry_price, stop_price, direction, rr_ratio=None):
    """
    Given an entry and a (already pip-capped) stop, returns a suggested
    take-profit at the minimum risk:reward ratio from config.
    """
    rr_ratio = rr_ratio or config.MIN_RR
    risk_distance = abs(entry_price - stop_price)

    if direction == "bullish":
        take_profit = entry_price + risk_distance * rr_ratio
    else:
        take_profit = entry_price - risk_distance * rr_ratio

    return {
        "entry": entry_price,
        "stop": stop_price,
        "take_profit": round(take_profit, 5),
        "risk_usd": suggested_risk_usd(),
        "rr_ratio": rr_ratio,
    }
