import config
from data import fetcher
from strategy import supply_demand, liquidity, displacement, fvg, confirmation, retracement
from risk import risk_manager


def determine_bias(daily_candles):
    """
    Simple structure-based bias from the daily timeframe:
    compares the two most recent swing highs and swing lows.
    Falls back to a plain momentum check if not enough swings found.
    """
    zones = supply_demand.find_zones(daily_candles, lookback=len(daily_candles))
    highs = [z for z in zones if z["type"] == "supply"]
    lows = [z for z in zones if z["type"] == "demand"]

    if len(highs) >= 2 and len(lows) >= 2:
        higher_high = highs[0]["top"] > highs[1]["top"]
        higher_low = lows[0]["bottom"] > lows[1]["bottom"]
        lower_high = highs[0]["top"] < highs[1]["top"]
        lower_low = lows[0]["bottom"] < lows[1]["bottom"]

        if higher_high and higher_low:
            return "bullish"
        if lower_high and lower_low:
            return "bearish"

    # Fallback: simple momentum over the lookback window
    start_close = daily_candles[0]["close"]
    end_close = daily_candles[-1]["close"]
    return "bullish" if end_close > start_close else "bearish"


def analyze_pair(symbol):
    """
    Runs the full 1D -> 4H -> 15M pipeline for one pair.
    Returns a signal dict if a valid setup is found, else None.
    """
    daily = fetcher.get_candles(symbol, config.TF_DIRECTION, config.CANDLES_DIRECTION)
    h4 = fetcher.get_candles(symbol, config.TF_ZONE, config.CANDLES_ZONE)
    m15 = fetcher.get_candles(symbol, config.TF_ENTRY, config.CANDLES_ENTRY)

    if not daily or not h4 or not m15:
        return None

    # 1. Bias (1D)
    bias = determine_bias(daily)

    # 2. Zone (4H)
    zones_4h = supply_demand.find_zones(h4, lookback=len(h4))
    current_price = m15[-1]["close"]
    zone = supply_demand.nearest_untapped_zone(zones_4h, current_price, bias)
    if zone is None:
        return None

    # Liquidity check: was there a sweep near this zone recently on 4H?
    liq = liquidity.find_equal_highs_lows(h4, lookback=len(h4))
    liq_side = "low" if bias == "bullish" else "high"
    liq_levels = liq["equal_lows"] if bias == "bullish" else liq["equal_highs"]
    swept = any(liquidity.swept_recently(h4, lvl, liq_side) for lvl in liq_levels) if liq_levels else False

    # 3. Entry (15M): price must have retraced into the 4H zone
    if not retracement.has_retraced_into(current_price, zone):
        return None

    disp = displacement.detect_displacement(m15)
    if disp is None or disp["direction"] != bias:
        return None

    fvgs_15m = fvg.find_fvgs(m15)
    matching_fvg = next((f for f in fvgs_15m if f["type"] == bias), None)

    confirmed = confirmation.confirm_entry(m15, bias)
    if not confirmed:
        return None

    # Build suggested trade levels
    stop_price = zone["bottom"] if bias == "bullish" else zone["top"]
    targets = risk_manager.calculate_targets(current_price, stop_price, bias)

    return {
        "symbol": symbol,
        "bias": bias,
        "zone": zone,
        "liquidity_swept": swept,
        "fvg_present": matching_fvg is not None,
        "entry": targets["entry"],
        "stop": targets["stop"],
        "take_profit": targets["take_profit"],
        "risk_usd": targets["risk_usd"],
        "rr_ratio": targets["rr_ratio"],
    }
