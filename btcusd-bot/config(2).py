import os

# --- Pairs to scan ---
PAIRS = [
    "EUR/CAD",
    "GBP/CAD",
    "EUR/CHF",
    "AUD/JPY",
    "AUD/CHF",
    "AUD/NZD",
    "USD/CAD",
    "USD/JPY",
    "USD/CHF",
    "GBP/USD",
]

# --- Timeframes (Twelve Data interval format) ---
TF_DIRECTION = "1day"   # Bias / trend direction
TF_ZONE = "4h"          # Supply/demand & liquidity zones
TF_ENTRY = "15min"      # Entry trigger (displacement, FVG, confirmation)

# --- How many candles to pull per timeframe ---
CANDLES_DIRECTION = 100
CANDLES_ZONE = 150
CANDLES_ENTRY = 100

# --- Scan loop ---
SCAN_INTERVAL_SECONDS = 15 * 60  # 15 minutes, aligned with entry timeframe

# --- API keys / secrets (set these in Railway Variables) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

# --- Risk settings (for suggested position sizing in the alert message) ---
ACCOUNT_BALANCE_USD = float(os.getenv("ACCOUNT_BALANCE_USD", "5"))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "1"))  # 1% of balance per idea
MAX_STOP_PIPS = float(os.getenv("MAX_STOP_PIPS", "15"))  # per strategy guide
MIN_RR = float(os.getenv("MIN_RR", "2"))  # minimum 1:2 risk:reward

# --- Where chat IDs that should receive auto-push alerts are stored ---
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")

# --- Tracks which zone (per pair) has already triggered a watching/confirmed alert ---
ZONE_STATE_FILE = os.path.join(os.path.dirname(__file__), "zone_state.json")
