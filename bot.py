import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import ssl

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_MAIN = os.getenv("CHAT_ID")
CHAT_ID_FRIEND = os.getenv("CHAT_ID_FRIEND")
CHAT_ID_FRIEND2 = os.getenv("CHAT_ID_FRIEND2")

if not TELEGRAM_BOT_TOKEN or not CHAT_ID_MAIN or not CHAT_ID_FRIEND:
    raise RuntimeError("В .env немає TELEGRAM_BOT_TOKEN, CHAT_ID або CHAT_ID_FRIEND")

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Монети + лімітки
CONTRACTS = {  # ф’ючерси
    "K_USDT": 0.226       # ф’ючерси
}
SPOT_TOKENS = {
    "SNEK_USDT": 0.0075    # спот
}

# Збереження останніх цін
last_sent_price = {symbol: None for symbol in CONTRACTS | SPOT_TOKENS}

async def send_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chat_ids = [CHAT_ID_MAIN, CHAT_ID_FRIEND, CHAT_ID_FRIEND2]
    async with aiohttp.ClientSession() as session:
        for chat_id in chat_ids:
            if chat_id:  # перевірка, щоб не було None
                await session.post(url, data={"chat_id": chat_id, "text": text}, ssl=ssl_context)



async def get_futures_price(contract: str):
    url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data:
                    if item.get("contract") == contract:
                        return float(item.get("last"))
    return None

async def get_spot_price(symbol: str):
    url = "https://api.gateio.ws/api/v4/spot/tickers"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data:
                    if item.get("currency_pair") == symbol:
                        return float(item.get("last"))
    return None

async def check_prices():
    while True:
        # Ф’ючерси
        for contract, limit_price in CONTRACTS.items():
            price = await get_futures_price(contract)
            if price:
                last_price = last_sent_price[contract]
                if last_price is None:
                    await send_message(f"Стартова ціна {contract}: {price} USDT")
                    last_sent_price[contract] = price
                else:
                    percent_change = ((price - last_price) / last_price) * 100
                    if percent_change >= 10 or price >= limit_price:
                        await send_message(
                            f"{contract}: {price} USDT\n"
                            f"Зростання: {percent_change:.2f}%\n"
                            f"Лімітка: {limit_price} USDT"
                        )
                        last_sent_price[contract] = price
            else:
                await send_message(f"Не вдалося отримати ціну для {contract}")

        # Спот
        for token, limit_price in SPOT_TOKENS.items():
            price = await get_spot_price(token)
            if price:
                last_price = last_sent_price[token]
                if last_price is None:
                    await send_message(f"Стартова ціна {token} (спот): {price} USDT")
                    last_sent_price[token] = price
                else:
                    percent_change = ((price - last_price) / last_price) * 100
                    if percent_change >= 10 or price >= limit_price:
                        await send_message(
                            f"{token} (спот): {price} USDT\n"
                            f"Зростання: {percent_change:.2f}%\n"
                            f"Лімітка: {limit_price} USDT"
                        )
                        last_sent_price[token] = price
            else:
                await send_message(f"Не вдалося отримати ціну для {token} (спот)")

        await asyncio.sleep(60)

async def main():
    await send_message("Бот запущено ✅ Відстежуємо TOWNS, K (ф’ючерси) та SNEK (спот)")
    await check_prices()

if __name__ == "__main__":
    asyncio.run(main())











