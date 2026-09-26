import json
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from analyzer import analyze_pair

TOKEN = config.TELEGRAM_BOT_TOKEN


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


# ---------- Commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    subs.add(chat_id)
    save_subscribers(subs)

    await update.message.reply_text(
        "🤖 Forex Signal Bot is online!\n\n"
        f"Watching {len(config.PAIRS)} pairs across 1D / 4H / 15M.\n"
        "You're subscribed to auto-push alerts.\n\n"
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
    await update.message.reply_text(
        f"🟢 Bot is running.\nScanning every {config.SCAN_INTERVAL_SECONDS // 60} min."
    )


async def pairs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Watching:\n" + "\n".join(config.PAIRS))


def format_signal(sig):
    arrow = "🟢⬆️" if sig["bias"] == "bullish" else "🔴⬇️"
    return (
        f"{arrow} *{sig['symbol']}* — {sig['bias'].upper()} setup\n"
        f"Zone: {sig['zone']['type']} ({sig['zone']['bottom']:.5f} - {sig['zone']['top']:.5f})\n"
        f"Liquidity swept: {'Yes' if sig['liquidity_swept'] else 'No'}\n"
        f"FVG present: {'Yes' if sig['fvg_present'] else 'No'}\n\n"
        f"Entry: {sig['entry']:.5f}\n"
        f"Stop: {sig['stop']:.5f}\n"
        f"Target: {sig['take_profit']:.5f} (RR {sig['rr_ratio']}:1)\n"
        f"Suggested risk: ${sig['risk_usd']}"
    )


async def signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning all pairs, one moment...")
    found = []
    for symbol in config.PAIRS:
        try:
            sig = analyze_pair(symbol)
        except Exception as e:
            print(f"[signals_cmd] error scanning {symbol}: {e}")
            sig = None
        if sig:
            found.append(sig)

    if not found:
        await update.message.reply_text("📊 No confirmed setups right now.")
        return

    for sig in found:
        await update.message.reply_text(format_signal(sig), parse_mode="Markdown")


# ---------- Background auto-scan job ----------

async def scan_job(context: ContextTypes.DEFAULT_TYPE):
    subs = load_subscribers()
    if not subs:
        return

    for symbol in config.PAIRS:
        try:
            sig = analyze_pair(symbol)
        except Exception as e:
            print(f"[scan_job] error scanning {symbol}: {e}")
            sig = None

        if sig:
            message = format_signal(sig)
            for chat_id in subs:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id, text=message, parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"[scan_job] failed to message {chat_id}: {e}")


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
