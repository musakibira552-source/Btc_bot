import json
import os
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from analyzer import analyze_pair

TOKEN = config.TELEGRAM_BOT_TOKEN


# ---------- Weekend market-hours check ----------

def is_market_closed_for_weekend():
    """
    Forex closes Friday evening (UTC) and reopens Sunday evening (UTC).
    weekday(): Monday=0 ... Sunday=6
    """
    if not config.WEEKEND_PAUSE_ENABLED:
        return False

    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    hour = now.hour

    if weekday == 4 and hour >= config.FRIDAY_CLOSE_HOUR_UTC:  # Friday, after close
        return True
    if weekday == 5:  # Saturday, all day
        return True
    if weekday == 6 and hour < config.SUNDAY_OPEN_HOUR_UTC:  # Sunday, before reopen
        return True
    return False


def load_market_state():
    if not os.path.exists(config.MARKET_STATE_FILE):
        return {"paused": False}
    try:
        with open(config.MARKET_STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"paused": False}


def save_market_state(state):
    with open(config.MARKET_STATE_FILE, "w") as f:
        json.dump(state, f)


# ---------- Subscriber storage (chat IDs that get auto-push alerts) ----------

def load_subscribers():
    if not os.path.exists(config.SUBSCRIBERS_FILE):
        return set()
    try:
        with open(config.SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def save_subscribers(chat_ids):
    with open(config.SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(chat_ids), f)


# ---------- Zone state storage (avoids re-alerting on the same zone) ----------

def load_zone_state():
    if not os.path.exists(config.ZONE_STATE_FILE):
        return {}
    try:
        with open(config.ZONE_STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_zone_state(state):
    with open(config.ZONE_STATE_FILE, "w") as f:
        json.dump(state, f)


# ---------- Commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    subs.add(chat_id)
    save_subscribers(subs)

    await update.message.reply_text(
        "🤖 Forex Signal Bot is online!\n\n"
        f"Watching {len(config.PAIRS)} pairs across 1D / 4H / 15M.\n"
        "You're subscribed to auto-push alerts (watching + confirmed).\n\n"
        "Commands:\n"
        "/status - Check bot status\n"
        "/signals - Scan all pairs right now\n"
        "/pairs - List watched pairs\n"
        "/stop - Unsubscribe from auto alerts"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    subs.discard(chat_id)
    save_subscribers(subs)
    await update.message.reply_text("🔕 Unsubscribed from auto-push alerts.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_market_closed_for_weekend():
        market_note = "🌙 Market closed for the weekend (resumes Monday)."
    else:
        market_note = "🟢 Market open — scanning active."
    await update.message.reply_text(
        f"{market_note}\nScanning every {config.SCAN_INTERVAL_SECONDS // 60} min."
    )


async def pairs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Watching:\n" + "\n".join(config.PAIRS))


# ---------- Message formatting ----------

def format_watching(sig):
    arrow = "🟡⬆️" if sig["bias"] == "bullish" else "🟡⬇️"
    return (
        f"{arrow} *{sig['symbol']}* — WATCHING ({sig['bias'].upper()})\n"
        f"4H {sig['zone']['type']} zone tapped (BOS + FVG confirmed): "
        f"{sig['zone']['bottom']:.5f} - {sig['zone']['top']:.5f}\n"
        f"Current price: {sig['current_price']:.5f}\n\n"
        f"Waiting for 15M MSS + liquidity sweep to confirm entry."
    )


def format_signal(sig):
    arrow = "🟢⬆️" if sig["bias"] == "bullish" else "🔴⬇️"
    candle_note = "✅ candle confirmed" if sig["candle_confirmation"] else "⚠️ no extra candle confirmation"
    return (
        f"{arrow} *{sig['symbol']}* — A+ {sig['bias'].upper()} setup CONFIRMED\n"
        f"4H {sig['zone']['type']} zone (BOS + FVG confirmed): "
        f"{sig['zone']['bottom']:.5f} - {sig['zone']['top']:.5f}\n"
        f"15M MSS confirmed | Liquidity swept: Yes | {candle_note}\n\n"
        f"📍 Set a {'buy' if sig['bias'] == 'bullish' else 'sell'} LIMIT at: {sig['entry']:.5f}\n"
        f"🛑 Stop loss: {sig['stop']:.5f} (≤{config.MAX_STOP_PIPS} pips)\n"
        f"🎯 Take profit: {sig['take_profit']:.5f} (RR {sig['rr_ratio']}:1)\n"
        f"💵 Suggested risk: ${sig['risk_usd']}\n\n"
        f"_Reminder: move to break-even and take partial at 1:1._"
    )


async def signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning all pairs, one moment...")
    watching_found = []
    confirmed_found = []

    for symbol in config.PAIRS:
        try:
            sig = analyze_pair(symbol)
        except Exception as e:
            print(f"[signals_cmd] error scanning {symbol}: {e}")
            sig = None

        if sig is None:
            continue
        if sig["stage"] == "watching":
            watching_found.append(sig)
        elif sig["stage"] == "confirmed":
            confirmed_found.append(sig)

    if not watching_found and not confirmed_found:
        await update.message.reply_text("📊 No zones tapped and no confirmed setups right now.")
        return

    for sig in confirmed_found:
        await update.message.reply_text(format_signal(sig), parse_mode="Markdown")
    for sig in watching_found:
        await update.message.reply_text(format_watching(sig), parse_mode="Markdown")


# ---------- Background auto-scan job ----------

async def scan_job(context: ContextTypes.DEFAULT_TYPE):
    subs = load_subscribers()
    if not subs:
        return

    market_state = load_market_state()
    was_paused = market_state.get("paused", False)
    closed_now = is_market_closed_for_weekend()

    if closed_now:
        if not was_paused:
            for chat_id in subs:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🌙 Forex market closed for the weekend. Pausing scans until Monday.",
                    )
                except Exception as e:
                    print(f"[scan_job] failed to message {chat_id}: {e}")
            market_state["paused"] = True
            save_market_state(market_state)
        return  # skip scanning entirely while closed

    if was_paused:
        for chat_id in subs:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="☀️ Forex market reopened. Resuming scans.",
                )
            except Exception as e:
                print(f"[scan_job] failed to message {chat_id}: {e}")
        market_state["paused"] = False
        save_market_state(market_state)

    state = load_zone_state()

    for symbol in config.PAIRS:
        try:
            sig = analyze_pair(symbol)
        except Exception as e:
            print(f"[scan_job] error scanning {symbol}: {e}")
            sig = None

        if sig is None:
            # No active zone for this pair anymore -> clear its state
            state.pop(symbol, None)
            continue

        key = sig["zone_key"]
        prev = state.get(symbol)
        message = None

        if sig["stage"] == "watching":
            if prev is None or prev.get("zone_key") != key or not prev.get("watching_sent"):
                message = format_watching(sig)
                state[symbol] = {"zone_key": key, "watching_sent": True, "confirmed_sent": False}

        elif sig["stage"] == "confirmed":
            if prev is None or prev.get("zone_key") != key or not prev.get("confirmed_sent"):
                message = format_signal(sig)
                state[symbol] = {"zone_key": key, "watching_sent": True, "confirmed_sent": True}

        if message:
            for chat_id in subs:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id, text=message, parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"[scan_job] failed to message {chat_id}: {e}")

    save_zone_state(state)


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    if not config.TWELVEDATA_API_KEY:
        raise RuntimeError("TWELVEDATA_API_KEY is not configured.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pairs", pairs_cmd))
    app.add_handler(CommandHandler("signals", signals_cmd))

    app.job_queue.run_repeating(scan_job, interval=config.SCAN_INTERVAL_SECONDS, first=10)

    print("Forex signal bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
