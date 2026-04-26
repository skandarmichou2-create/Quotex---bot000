import asyncio
import random
import time
from datetime import datetime, timedelta
from pyquotex.stable_api import Quotex
from telethon import TelegramClient

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
            if ups >= 3: call_score += 3
            if downs >= 3: put_score += 3
            last_close = candles[-1]["close"]
        else:
            last_close = 0

        rsi = await client.calculate_indicator(asset, "RSI", {"period":14}, history_size=3600, timeframe=60)
        if rsi and "current" in rsi and rsi["current"] is not None:
            rsi_val = float(rsi["current"])
            if rsi_val < 35: call_score += 2
            elif rsi_val > 65: put_score += 2

        ema = await client.calculate_indicator(asset, "EMA", {"period":20}, history_size=3600, timeframe=60)
        if ema and "current" in ema and ema["current"] is not None:
            ema_val = float(ema["current"])
            if last_close > ema_val: call_score += 2
            elif last_close < ema_val: put_score += 2

        sma = await client.calculate_indicator(asset, "SMA", {"period":20}, history_size=3600, timeframe=60)
        if sma and "current" in sma and sma["current"] is not None:
            sma_val = float(sma["current"])
            if last_close > sma_val: call_score += 1
            elif last_close < sma_val: put_score += 1

        if call_score > put_score: return "call"
        elif put_score > call_score: return "put"
        else: return random.choice(["call", "put"])
    except Exception as e:
        print("DECIDE ERROR:", e)
        return random.choice(["call", "put"])

# =========================
# EXECUTE + RESULT ENGINE
# =========================
async def trade_once(client, asset, amount, direction, duration, target_time):
    # ندخل قبل بداية الشمعة بـ 1.5 ثانية
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds() - 1.5
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

    print(f"🟡 BUY ATTEMPT: {asset} | {direction}")
    success, order_info = await client.buy(amount, asset, direction, duration, time_mode="TIME")
    if not success or not order_info or "id" not in order_info:
        return None, None, None, "none"

    order_id = order_info["id"]
    print("✅ ORDER ID:", order_id)

    # ننتظر مدة الصفقة + هامش صغير
    await asyncio.sleep(duration + 2)

    # نجيب النتيجة من سجل التداول
    result = "none"
    history = await client.get_history()
    if history and "data" in history:
        for trade in history["data"]:
            if trade.get("id") == order_id:
                profit = trade.get("profit", 0)
                result = "win" if profit > 0 else "loss"
                break

    return order_id, asset, direction, result

# =========================
# SAFE TELEGRAM SEND
# =========================
async def safe_tg_send(tg, text):
    for attempt in range(3):
        try:
            if not tg.is_connected():
                await tg.connect()
            await tg.send_message(CHANNEL, text)
            return True
        except Exception as e:
            print("TG SEND FAILED:", e)
            try: await tg.disconnect()
            except Exception: pass
            await asyncio.sleep(1.5)
    return False

# =========================
# MAIN BOT
# =========================
async def main():
    client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
    client.set_account_mode("PRACTICE")
    connected, reason = await client.connect()
    if not connected:
        print("❌ فشل الاتصال:", reason)
        return
    await client.change_account("PRACTICE")

    tg = TelegramClient("session_pc", API_ID, API_HASH)
    await tg.start()
    await safe_tg_send(tg, "🚀 LATCHI DZ BOT STARTED")

    while True:
        try:
            asset = random.choice(ASSETS)
            direction = await decide_direction(client, asset)

            now = datetime.now()
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            if (next_minute - now).total_seconds() < 4:
                next_minute += timedelta(minutes=1)
            target_time = next_minute

            preview_msg = f"""📊 صفقة جديدة LATCHI DZ VIP 🌟:

{asset.upper()} | M1 | {target_time.strftime('%H:%M')} | {"CALL 🔼" if direction=="call" else "PUT ⬇️"}

#QUOTEX"""
            await safe_tg_send(tg, preview_msg)

            order_id, asset_used, dir_used, result = await trade_once(client, asset, BASE_AMOUNT, direction, 60, target_time)

            if dir_used is None:
                await safe_tg_send(tg, f"⚠️ الصفقة لم تنفذ | {asset.upper()}")
                await asyncio.sleep(3)
                continue

            if result == "win":
                await safe_tg_send(tg, f"🟢 ربح ✅ | {asset_used.upper()} | {dir_used.upper()}")
            elif result == "loss":
                await safe_tg_send(tg, f"🔴 خسارة ❌ | {asset_used.upper()} | {dir_used.upper()}")
            else:
                await safe_tg_send(tg, f"⚪ لم يتم تحديد النتيجة | {asset_used.upper()} | {dir_used.upper()}")

            await asyncio.sleep(10)

        except Exception as e:
            print("MAIN LOOP ERROR:", e)
            await asyncio.sleep(5)

asyncio.run(main())