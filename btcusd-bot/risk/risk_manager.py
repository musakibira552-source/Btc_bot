"""
Since this is a signal-only bot (trades are placed manually in MT5),
this module just computes a suggested risk amount and R:R to include
in the alert message — it does not place or manage any live orders.
"""

import config


def suggested_risk_usd():
    return round(config.ACCOUNT_BALANCE_USD * (config.RISK_PERCENT / 100), 4)


def calculate_targets(entry_price, stop_price, direction, rr_ratio=2.0):
    """
    Given an entry and a stop (placed beyond the zone/liquidity sweep),
    returns a suggested take-profit at the given risk:reward ratio.
    """
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
