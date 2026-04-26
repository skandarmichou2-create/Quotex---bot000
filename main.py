import asyncio
import random
from datetime import datetime, timedelta
from pyquotex.stable_api import Quotex
from telethon import TelegramClient

EMAIL = "wagife9306@mugstock.com"
PASSWORD = "latchi23@@"

API_ID = 21508855
API_HASH = "290e3791a95daa5fffcd1847a1b5da17"
CHANNEL = "@latchidz1"

ASSETS = ["NZDCHF_otc", "USDINR_otc", "USDBDT_otc", "USDARS_otc", "USDPKR_otc"]
BASE_AMOUNT = 1.0

async def connect_telegram():
    tg = TelegramClient("session", API_ID, API_HASH)
    await tg.start()
    return tg

async def connect_quotex():
    while True:
        try:
            client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
            client.set_account_mode("PRACTICE")

            connected, reason = await client.connect()
            if connected:
                await client.change_account("PRACTICE")
                print("✅ Quotex Connected")
                return client
            else:
                print("❌ Quotex Failed:", reason)

        except Exception as e:
            print("QUOTEX ERROR:", e)

        await asyncio.sleep(10)

async def execute_trade_at_time(client, asset, direction):
    try:
        now = datetime.now()
        target = now.replace(second=58, microsecond=0) + timedelta(minutes=1)

        wait_seconds = (target - now).total_seconds()
        print("⌛ WAIT:", wait_seconds)
        await asyncio.sleep(wait_seconds)

        success, order_info = await client.buy(BASE_AMOUNT, asset, direction, 60)

        print("BUY RESPONSE:", success, order_info)

        if not success or not order_info:
            return None

        after_buy_balance = float(order_info.get("accountBalance", 0))
        print("💰 AFTER BUY BALANCE:", after_buy_balance)

        return after_buy_balance

    except Exception as e:
        print("EXECUTE ERROR:", e)
        return None

async def detect_result(client, after_buy_balance):
    try:
        await asyncio.sleep(70)

        final_balance = await client.get_balance()
        print("💰 FINAL BALANCE:", final_balance)

        if final_balance > after_buy_balance:
            return "win"
        else:
            return "loss"

    except Exception as e:
        print("DETECT ERROR:", e)
        return "none"

async def main():
    tg = await connect_telegram()
    await tg.send_message(CHANNEL, "🚀 LATCHI DZ FINAL BOT STARTED")

    client = await connect_quotex()
    await tg.send_message(CHANNEL, "✅ تم الاتصال بـ Quotex بنجاح")

    while True:
        try:
            if not await client.check_connect():
                client = await connect_quotex()

            asset = random.choice(ASSETS)
            direction = random.choice(["call", "put"])

            entry_time = (
                datetime.now().replace(second=0, microsecond=0)
                + timedelta(minutes=2)
            ).strftime("%H:%M")

            await tg.send_message(CHANNEL, f"""📊 صفقة جديدة LATCHI DZ VIP 🌟:

{asset.upper()} | M1 | {entry_time} | {"CALL 🔼" if direction=="call" else "PUT ⬇️"}

#QUOTEX""")

            after_buy_balance = await execute_trade_at_time(client, asset, direction)

            if after_buy_balance is None:
                await tg.send_message(CHANNEL, f"❌ فشل تنفيذ الصفقة | {asset.upper()}")
                await asyncio.sleep(10)
                continue

            await tg.send_message(CHANNEL, "⌛ الصفقة دخلت السوق... انتظار النتيجة")

            result = await detect_result(client, after_buy_balance)

            if result == "win":
                await tg.send_message(CHANNEL, f"🟢 ربح ✅ | {asset.upper()} | {direction.upper()}")
            elif result == "loss":
                await tg.send_message(CHANNEL, f"🔴 خسارة ❌ | {asset.upper()} | {direction.upper()}")
            else:
                await tg.send_message(CHANNEL, f"⚪ تعذر تحديد النتيجة | {asset.upper()} | {direction.upper()}")

            await asyncio.sleep(120)

        except Exception as e:
            print("MAIN LOOP ERROR:", e)
            await asyncio.sleep(10)

asyncio.run(main())