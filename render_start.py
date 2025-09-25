# -*- coding: utf-8 -*-
"""
Minimal Telegram signal bot for Render.
Configure TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in Render environment variables.

Uses:
 - python-telegram-bot v20.x
 - yfinance to fetch prices
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# CONFIG
INTERVAL = int(os.environ.get("CHECK_INTERVAL_SECONDS", "60"))

# Symbols: 3 FX + 3 acciones ejemplo
CURRENCIES = ["EURUSD=X", "EURCAD=X", "EURJPY=X"]
STOCKS = ["AAPL", "TSLA", "AMZN"]
SYMBOLS = CURRENCIES + STOCKS

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def fetch_last_price(symbol: str) -> Optional[float]:
    """Blocking fetch price using yfinance. Return None on failure."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1d", interval="1m", progress=False)
        if hist is not None and not hist.empty:
            return float(hist["Close"].dropna()[-1])
        hist2 = t.history(period="2d", interval="1d", progress=False)
        if hist2 is not None and not hist2.empty:
            return float(hist2["Close"].dropna()[-1])
    except Exception:
        logger.exception("fetch error %s", symbol)
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SniperPro minimal bot running. Commands: /status /symbols")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prev = context.application.bot_data.get("prev_prices", {})
    msg = f"Monitoring {len(SYMBOLS)} symbols. Interval={INTERVAL}s\n"
    for s in SYMBOLS:
        msg += f"{s}: {prev.get(s)}\n"
    await update.message.reply_text(msg)


async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\n".join(SYMBOLS))


async def monitor_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    bot = app.bot
    loop = asyncio.get_event_loop()
    prev: Dict[str, Optional[float]] = app.bot_data.setdefault("prev_prices", {})
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID not set.")
        return

    lines = []
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    for symbol in SYMBOLS:
        price = await loop.run_in_executor(None, fetch_last_price, symbol)
        if price is None:
            lines.append(f"{symbol}: price N/A")
            continue
        prev_price = prev.get(symbol)
        signal = "NO PREV" if prev_price is None else ("BUY" if price > prev_price else ("SELL" if price < prev_price else "HOLD"))
        prev[symbol] = price
        lines.append(f"{symbol}: {price:.6f} => {signal}")

    if lines:
        text = f"SniperPro signals ({ts}):\n" + "\n".join(lines)
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            logger.info("Sent signals")
        except Exception:
            logger.exception("send failed")


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not set. Exiting.")
        raise SystemExit("TELEGRAM_TOKEN missing")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("symbols", symbols_command))

    app.bot_data["prev_prices"] = {}
    # first run after 5s
    app.job_queue.run_repeating(monitor_job, interval=INTERVAL, first=5)

    logger.info("Bot starting polling")
    app.run_polling()


if __name__ == "__main__":
    main()
