import asyncio
import random
import time
from datetime import datetime, timedelta
import pytz
from pyquotex.stable_api import Quotex
from telethon import TelegramClient

# معلومات الحساب Quotex
EMAIL = "wagife9306@mugstock.com"
PASSWORD = "latchi23@@"

# معلومات تيليجرام
API_ID = 21508855
API_HASH = "290e3791a95daa5fffcd1847a1b5da17"
CHANNEL = "@latchidz1"

# الأزواج المستعملة
ASSETS = ["NZDCHF_otc", "USDINR_otc", "USDBDT_otc", "USDARS_otc", "USDPKR_otc"]

BASE_AMOUNT = 1.0

# المنطقة الزمنية الجزائر
tz = pytz.timezone("Africa/Algiers")

async def decide_direction(client, asset):
    signals = []
    candles = await client.get_candles(asset, int(time.time()), 3, 60)
    if candles:
        ups = sum(1 for c in candles if c["close"] > c["open"])
        downs = sum(1 for c in candles if c["close"] < c["open"])
        signals.append("call" if ups > downs else "put")

    rsi = await client.calculate_indicator(asset, "RSI", {"period":14}, history_size=3600, timeframe=60)
    if rsi and "current" in rsi and rsi["current"] is not None:
        if rsi["current"] < 30:
            signals.append("call")
        elif rsi["current"] > 70:
            signals.append("put")

    if not signals:
        return random.choice(["call","put"])
    return max(set(signals), key=signals.count)

async def trade_once(client, asset, amount, direction, duration):
    success, order_info = await client.buy(amount, asset, direction, duration)
    if not (success or order_info):
        return None, None, None, None

    # ننتظر دقيقة باش الصفقة تغلق
    await asyncio.sleep(70)

    # نجيب آخر صفقة من سجل التداول
    history = await client.get_history()
    result = "none"
    if history and "data" in history and len(history["data"]) > 0:
        last_trade = history["data"][0]
        profit = last_trade.get("profit", 0)
        if profit > 0:
            result = "win"
        elif profit <= 0:
            result = "loss"

    return None, None, direction, result

async def connect_quotex(tg):
    client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
    client.set_account_mode("PRACTICE")
    while True:
        connected, reason = await client.connect()
        if connected:
            print("✅ تم الاتصال بـ Quotex")
            await tg.send_message(CHANNEL, "✅ نجاح الاتصال بـ Quotex")
            await client.change_account("PRACTICE")
            return client
        else:
            print("❌ فشل الاتصال:", reason, "نعيد المحاولة بعد 10 ثواني...")
            await asyncio.sleep(10)

async def main():
    tg = TelegramClient("session", API_ID, API_HASH)
    await tg.start()

    # رسالة بداية التشغيل
    await tg.send_message(CHANNEL, "🚀 البوت بدأ التشغيل (توقيت الجزائر)")

    client = await connect_quotex(tg)

    while True:
        asset = random.choice(ASSETS)
        direction = await decide_direction(client, asset)

        # وقت بداية الشمعة بعد دقيقتين بالتوقيت المحلي
        next_minute = (datetime.now(tz).replace(second=0, microsecond=0) + timedelta(minutes=2))
        entry_time = next_minute.strftime("%H:%M")

        # نرسل الصفقة في تيليجرام
        preview_msg = f"""📊 صفقة جديدة LATCHI DZ VIP 🌟:

{asset.upper()} | M1 | {entry_time} | {"CALL 🔼" if direction=="call" else "PUT ⬇️"}

#QUOTEX"""
        msg = await tg.send_message(CHANNEL, preview_msg)

        # نحجز الصفقة
        _, _, dir_used, result = await trade_once(client, asset, BASE_AMOUNT, direction, 60)

        if dir_used is None:
            await msg.delete()
            continue

        # إرسال النتيجة بالنص فقط
        if result == "win":
            await tg.send_message(CHANNEL, f"🟢 ربح ✅ | {asset.upper()} | {dir_used.upper()}")
        elif result == "loss":
            await tg.send_message(CHANNEL, f"🔴 خسارة ❌ | {asset.upper()} | {dir_used.upper()}")
        else:
            await tg.send_message(CHANNEL, f"⚪ لم تنفذ | {asset.upper()} | {dir_used.upper()}")

        # ينام دقيقتين قبل الصفقة الجديدة
        await asyncio.sleep(120)

asyncio.run(main())