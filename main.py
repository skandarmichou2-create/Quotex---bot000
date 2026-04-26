import asyncio
import random
import time
import threading
from datetime import datetime, timedelta
from flask import Flask
from pyquotex.stable_api import Quotex
from telethon import TelegramClient

# =========================
# KEEP ALIVE SERVER FOR REPLIT
# =========================
app = Flask('')

@app.route('/')
def home():
    return "LATCHI DZ BOT IS RUNNING"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()

# =========================
# CONFIG
# =========================
EMAIL = "wagife9306@mugstock.com"
PASSWORD = "latchi23@@"

API_ID = 33567199
API_HASH = "3fdd30ef25043c39d8cc897d6251b8f1"
CHANNEL = "@latchidz0"

ASSETS = ["NZDCHF_otc", "USDINR_otc", "USDBDT_otc", "USDARS_otc", "USDPKR_otc"]
BASE_AMOUNT = 1.0

# =========================
# SMART ANALYSIS STRATEGY
# =========================
async def decide_direction(client, asset):
    call_score = 0
    put_score = 0

    try:
        candles = await client.get_candles(asset, int(time.time()), 5, 60)

        if candles:
            ups = sum(1 for c in candles if c["close"] > c["open"])
            downs = sum(1 for c in candles if c["close"] < c["open"])

            if ups >= 3:
                call_score += 3
            if downs >= 3:
                put_score += 3

            last_close = candles[-1]["close"]
        else:
            last_close = 0

        rsi = await client.calculate_indicator(asset, "RSI", {"period":14}, history_size=3600, timeframe=60)
        if rsi and "current" in rsi and rsi["current"] is not None:
            rsi_val = float(rsi["current"])
            if rsi_val < 35:
                call_score += 2
            elif rsi_val > 65:
                put_score += 2

        ema = await client.calculate_indicator(asset, "EMA", {"period":20}, history_size=3600, timeframe=60)
        if ema and "current" in ema and ema["current"] is not None:
            ema_val = float(ema["current"])
            if last_close > ema_val:
                call_score += 2
            elif last_close < ema_val:
                put_score += 2

        sma = await client.calculate_indicator(asset, "SMA", {"period":20}, history_size=3600, timeframe=60)
        if sma and "current" in sma and sma["current"] is not None:
            sma_val = float(sma["current"])
            if last_close > sma_val:
                call_score += 1
            elif last_close < sma_val:
                put_score += 1

        print("CALL SCORE =", call_score, "| PUT SCORE =", put_score)

        if call_score > put_score:
            return "call"
        elif put_score > call_score:
            return "put"
        else:
            return random.choice(["call", "put"])

    except Exception as e:
        print("DECIDE ERROR:", e)
        return random.choice(["call", "put"])

# =========================
# EXECUTE + RESULT ENGINE
# =========================
async def trade_once(client, asset, amount, direction, duration, target_time):
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds() - 1

    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

    success, order_info = await client.buy(amount, asset, direction, duration)

    if not success or not order_info or "id" not in order_info:
        return None, None, None, "none"

    order_id = order_info["id"]
    after_buy_balance = float(order_info.get("accountBalance", 0))

    print("BUY RESPONSE:", success, order_info)
    print("AFTER BUY BALANCE:", after_buy_balance)

    await asyncio.sleep(duration + 15)

    final_balance = after_buy_balance

    for i in range(10):
        try:
            bal = await client.get_balance()
            print("CHECK BALANCE:", bal)

            if float(bal) != float(after_buy_balance):
                final_balance = float(bal)
                break
        except:
            pass

        await asyncio.sleep(2)

    print("FINAL BALANCE:", final_balance)

    if final_balance > after_buy_balance:
        result = "win"
    else:
        result = "loss"

    return order_id, asset, direction, result

# =========================
# MAIN BOT LOOP
# =========================
async def bot_runner():
    client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
    client.set_account_mode("PRACTICE")

    connected, reason = await client.connect()
    if not connected:
        print("❌ فشل الاتصال:", reason)
        return

    await client.change_account("PRACTICE")

    tg = TelegramClient("session_replit", API_ID, API_HASH)
    await tg.start()

    await tg.send_message(CHANNEL, "🚀 LATCHI DZ BOT REPLIT SMART STARTED")

    while True:
        try:
            asset = random.choice(ASSETS)
            direction = await decide_direction(client, asset)

            now = datetime.now()
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=2)
            target_time = next_minute.replace(second=0)

            preview_msg = f"""📊 صفقة جديدة LATCHI DZ VIP 🌟:

{asset.upper()} | M1 | {target_time.strftime("%H:%M")} | {"CALL 🔼" if direction=="call" else "PUT ⬇️"}

#QUOTEX"""
            await tg.send_message(CHANNEL, preview_msg)

            order_id, asset_used, dir_used, result = await trade_once(
                client, asset, BASE_AMOUNT, direction, 60, target_time
            )

            if dir_used is None:
                await tg.send_message(CHANNEL, f"⚠️ الصفقة لم تنفذ | {asset.upper()}")
                await asyncio.sleep(5)
                continue

            if result == "win":
                await tg.send_message(CHANNEL, f"🟢 ربح ✅ | {asset_used.upper()} | {dir_used.upper()}")
            else:
                await tg.send_message(CHANNEL, f"🔴 خسارة ❌ | {asset_used.upper()} | {dir_used.upper()}")

            await asyncio.sleep(10)

        except Exception as e:
            print("MAIN LOOP ERROR:", e)
            await asyncio.sleep(5)

# =========================
# START
# =========================
keep_alive()
asyncio.run(bot_runner())