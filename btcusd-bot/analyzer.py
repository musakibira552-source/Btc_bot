"""
Multi-timeframe analysis pipeline, following the JAYBE FX demand/supply
methodology:

  1D  -> confirm a trending market (skip ranges) and overall bias
  4H  -> find the zone that CAUSED a BOS, confirmed by an impulsive move + FVG
  4H  -> wait for price to retrace ("mitigate") into that zone
  15M -> wait for an MSS (structure shift) back in the bias direction
  15M -> require a fresh FVG + a liquidity sweep near the entry
  Entry = limit order at the 15M FVG
  Stop  = 15M swing low/high, capped at MAX_STOP_PIPS
  Target = minimum MIN_RR risk:reward
"""

import config
from data import fetcher
from strategy import supply_demand, liquidity, displacement, fvg, confirmation, retracement, structure
from risk import risk_manager


def determine_bias(daily_candles):
    """
    Structure-based bias: requires a clear HH+HL (bullish) or LH+LL (bearish)
    pattern from the two most recent swings. Returns None for a ranging /
    inconclusive market — per the strategy, we only trade trending markets.
    """
    zones = supply_demand.find_zones(daily_candles, lookback=len(daily_candles))
    highs = [z for z in zones if z["type"] == "supply"]
    lows = [z for z in zones if z["type"] == "demand"]

    if len(highs) < 2 or len(lows) < 2:
        return None

    higher_high = highs[0]["top"] > highs[1]["top"]
    higher_low = lows[0]["bottom"] > lows[1]["bottom"]
    lower_high = highs[0]["top"] < highs[1]["top"]
    lower_low = lows[0]["bottom"] < lows[1]["bottom"]

    if higher_high and higher_low:
        return "bullish"
    if lower_high and lower_low:
        return "bearish"

    return None  # ranging / no clear trend -> no trade


def find_valid_zone(h4_candles, bias, current_price):
    """
    Finds the 4H zone that actually caused a BOS in the bias direction,
    and confirms it has an adjacent FVG (imbalance) -> the "A+ setup"
    requirement from the strategy guide.
    Returns the zone dict, or None if no valid zone is found.
    """
    bos = structure.detect_bos(h4_candles, bias, span=2)
    if bos is None:
        return None  # no confirmed break of structure on 4H -> skip

    zones = supply_demand.find_zones(h4_candles, lookback=len(h4_candles))
    zone = supply_demand.nearest_untapped_zone(zones, current_price, bias)
    if zone is None:
        return None

    # Require an FVG near the zone (within a few candles) to confirm imbalance
    h4_fvgs = fvg.find_fvgs(h4_candles, lookback=len(h4_candles))
    wanted_fvg_type = "bullish" if bias == "bullish" else "bearish"
    has_nearby_fvg = any(
        f["type"] == wanted_fvg_type and abs(f["index"] - zone["index"]) <= 5
        for f in h4_fvgs
    )
    if not has_nearby_fvg:
        return None

    return zone


def analyze_pair(symbol):
    """
    Runs the full 1D -> 4H -> 15M pipeline for one pair.
    Returns a signal dict if a valid A+ setup is found, else None.
    """
    daily = fetcher.get_candles(symbol, config.TF_DIRECTION, config.CANDLES_DIRECTION)
    h4 = fetcher.get_candles(symbol, config.TF_ZONE, config.CANDLES_ZONE)
    m15 = fetcher.get_candles(symbol, config.TF_ENTRY, config.CANDLES_ENTRY)

    if not daily or not h4 or not m15:
        return None

    # 1. Bias (1D) — must be a clear trend, not a range
    bias = determine_bias(daily)
    if bias is None:
        return None

    # 2. Zone (4H) — must be the zone that caused a BOS, with a nearby FVG
    current_price = m15[-1]["close"]
    zone = find_valid_zone(h4, bias, current_price)
    if zone is None:
        return None

    # 3. Price must have retraced ("mitigated") into the 4H zone
    if not retracement.has_retraced_into(current_price, zone):
        return None

    # 4. MSS (15M) — structure must shift back in favor of the bias
    mss = structure.detect_mss(m15, bias, span=1)
    if mss is None:
        return None

    # 5. Fresh FVG on 15M near/after the MSS (imbalance requirement)
    fvgs_15m = fvg.find_fvgs(m15, lookback=len(m15))
    matching_fvg = next(
        (f for f in fvgs_15m if f["type"] == bias and f["index"] >= mss["break_index"]),
        None,
    )
    if matching_fvg is None:
        return None

    # 6. Liquidity sweep required near the 15M entry (hard gate)
    liq = liquidity.find_equal_highs_lows(m15, lookback=len(m15))
    liq_side = "low" if bias == "bullish" else "high"
    liq_levels = liq["equal_lows"] if bias == "bullish" else liq["equal_highs"]
    swept = any(liquidity.swept_recently(m15, lvl, liq_side, within=10) for lvl in liq_levels) if liq_levels else False
    if not swept:
        return None

    # 7. Optional extra confirmation candle (engulfing/rejection) — supportive, not required
    confirmed_candle = confirmation.confirm_entry(m15, bias)

    # --- Build trade levels ---
    # Entry = limit order at the FVG (use the edge closer to current price)
    entry_price = matching_fvg["bottom"] if bias == "bullish" else matching_fvg["top"]

    # Stop = 15M swing low/high, capped at MAX_STOP_PIPS
    swing_extreme = structure.nearest_swing_extreme(m15, bias, span=1, lookback=40)
    raw_stop = swing_extreme if swing_extreme is not None else zone["bottom"] if bias == "bullish" else zone["top"]
    stop_price = risk_manager.cap_stop_by_pips(entry_price, raw_stop, bias, symbol)

    targets = risk_manager.calculate_targets(entry_price, stop_price, bias)

    return {
        "symbol": symbol,
        "bias": bias,
        "zone": zone,
        "liquidity_swept": swept,
        "fvg_present": True,
        "candle_confirmation": confirmed_candle,
        "entry": round(entry_price, 5),
        "stop": round(stop_price, 5),
        "take_profit": targets["take_profit"],
        "risk_usd": targets["risk_usd"],
        "rr_ratio": targets["rr_ratio"],
    }
