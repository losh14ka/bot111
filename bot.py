import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Збираємо всіх отримувачів: CHAT_ID, CHAT_ID_FRIEND, CHAT_ID_FRIEND2, ...
CHAT_IDS = [v for k, v in os.environ.items() if k.startswith("CHAT_ID") and v]

if not TELEGRAM_BOT_TOKEN or not CHAT_IDS:
    raise RuntimeError("Немає TELEGRAM_BOT_TOKEN або жодного CHAT_ID у Variables")

# Лімітки беруться з Variables (або дефолти)
CONTRACTS = {
    "TOWNS_USDT": float(os.getenv("TOWNS_LIMIT", "0.33")),
    "K_USDT": float(os.getenv("K_LIMIT", "0.25")),
}

# Поріг відсоткового зростання (наприклад, 10 означає +10% від останнього надісланого)
PERCENT_UP = float(os.getenv("PERCENT_UP", "10"))

last_sent_price = {symbol: None for symbol in CONTRACTS}

async def send_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        for chat_id in CHAT_IDS:
            try:
                await session.post(url, data={"chat_id": chat_id, "text": text})
            except Exception as e:
                print(f"[send_message] error for {chat_id}: {e}")

async def get_futures_price(contract: str):
    # Точковий запит за одним контрактом
    url = f"https://api.gateio.ws/api/v4/futures/usdt/tickers?contract={contract}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return float(data[0]["last"])
        except Exception as e:
            print(f"[get_futures_price] {contract} error: {e}")
    return None

async def check_prices():
    while True:
        for contract, limit_price in CONTRACTS.items():
            price = await get_futures_price(contract)
            if price is None:
                await send_message(f"⚠️ Не вдалося отримати ціну для {contract}")
                continue

            prev = last_sent_price[contract]
            if prev is None:
                # перший запуск — фіксуємо базову ціну, без спаму
                last_sent_price[contract] = price
                continue

            change_pct = ((price - prev) / prev) * 100 if prev > 0 else 0.0

            if change_pct >= PERCENT_UP or price >= limit_price:
                await send_message(
                    f"🚀 {contract}: {price} USDT\n"
                    f"Зміна від останнього алерту: {change_pct:.2f}%\n"
                    f"Лімітка: {limit_price} USDT"
                )
                # оновлюємо базову точку, щоб наступний +P% рахувався від цієї ціни
                last_sent_price[contract] = price

        await asyncio.sleep(60)  # перевірка щохвилини

async def main():
    await send_message(
        "✅ Бот запущено. Відстежуємо: "
        + ", ".join(CONTRACTS.keys())
        + f"\nУмови: +{PERCENT_UP}% або досягнення лімітки."
    )
    await check_prices()

if __name__ == "__main__":
    asyncio.run(main())
