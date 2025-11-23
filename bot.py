import asyncio
import os
from typing import Optional, Dict

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# === Налаштування токена ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не заданий у змінних оточення!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# === Наш список "дарунків" (активів) ===
# Ключ — те, що користувач може ввести (/price ton, /price btc)
GIFT_ASSETS: Dict[str, Dict[str, str]] = {
    "ton": {"id": "toncoin", "symbol": "TON", "name": "Toncoin"},
    "btc": {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    "eth": {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    "usdt": {"id": "tether", "symbol": "USDT", "name": "Tether"},
}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


# === Допоміжні функції ===
def resolve_asset(query: str) -> Optional[Dict[str, str]]:
    """
    Знаходимо актив по введеному тексту:
    - ton / TON / Toncoin
    - btc / BTC / Bitcoin
    """
    q = query.strip().lower()
    for key, data in GIFT_ASSETS.items():
        if q == key:
            return data
        if q == data["symbol"].lower():
            return data
        if q == data["name"].lower():
            return data
    return None


async def fetch_price_usd(asset_id: str) -> Optional[float]:
    """
    Отримати ціну активу в USD з CoinGecko.
    asset_id — це, наприклад, "bitcoin", "toncoin".
    """
    params = {
        "ids": asset_id,
        "vs_currencies": "usd",
    }
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(COINGECKO_URL, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

    try:
        price = data[asset_id]["usd"]
        return float(price)
    except Exception:
        return None


# === Обробники команд ===

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Вітаю у *TG Gift Hub Bot*!\n\n"
        "Я допоможу:\n"
        "• дізнатися ціну дарунка (/price)\n"
        "• подивитися топ дарунків (/top)\n"
        "• скоро: трекінг та сигнали (/track, /signals)\n\n"
        "Введи /help, щоб побачити всі команди.",
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    assets_list = "\n".join(
        [f"- {v['name']} ({k.upper()})" for k, v in GIFT_ASSETS.items()]
    )
    await message.answer(
        "📘 *Доступні команди:*\n"
        "/price <дарунок> — дізнатися ціну (наприклад: /price ton, /price btc)\n"
        "/top — топ дарунків по ціні\n"
        "/track — (в розробці) трекінг дарунків\n"
        "/signals — (в розробці) ринкові сигнали\n\n"
        "*Підтримувані дарунки зараз:*\n"
        f"{assets_list}",
        parse_mode="Markdown"
    )


@dp.message(Command("price"))
async def price_handler(message: types.Message):
    """
    /price ton
    /price btc
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        # Користувач не вказав, що саме
        assets_list = ", ".join([k.upper() for k in GIFT_ASSETS.keys()])
        await message.answer(
            "❓ Напиши, для якого дарунка показати ціну.\n\n"
            "Приклад:\n"
            "`/price ton`\n"
            "`/price btc`\n\n"
            f"Зараз доступні: {assets_list}",
            parse_mode="Markdown"
        )
        return

    query = parts[1]
    asset = resolve_asset(query)
    if not asset:
        assets_list = ", ".join([k.upper() for k in GIFT_ASSETS.keys()])
        await message.answer(
            "⚠️ Не знайшов такий дарунок.\n\n"
            f"Спробуй щось із цього списку: {assets_list}"
        )
        return

    price = await fetch_price_usd(asset["id"])
    if price is None:
        await message.answer("😔 Не вдалося отримати ціну. Спробуй пізніше.")
        return

    await message.answer(
        f"🎁 *{asset['name']}* ({asset['symbol']})\n"
        f"Поточна ціна: *{price:.4f} USD*",
        parse_mode="Markdown"
    )


@dp.message(Command("top"))
async def top_handler(message: types.Message):
    """
    ТОП дарунків по поточній ціні (USD).
    Поки без відсотків росту/падіння — це зробимо на наступному етапі.
    """
    results = []
    for key, asset in GIFT_ASSETS.items():
        price = await fetch_price_usd(asset["id"])
        if price is not None:
            results.append((asset, price))

    if not results:
        await message.answer("😔 Не вдалося отримати дані для топу. Спробуй пізніше.")
        return

    # Сортуємо по ціні, спочатку найдорожчі
    results.sort(key=lambda x: x[1], reverse=True)

    lines = []
    for idx, (asset, price) in enumerate(results, start=1):
        lines.append(f"{idx}. *{asset['name']}* ({asset['symbol']}) — {price:.4f} USD")

    text = "🏆 *ТОП дарунків (по ціні, USD):*\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("track"))
async def track_handler(message: types.Message):
    await message.answer(
        "🛠 Функція трекінгу дарунків ще в розробці.\n\n"
        "План: ти зможеш додати дарунок у список, і бот буде "
        "відстежувати зміну його ціни та надсилати сповіщення."
    )


@dp.message(Command("signals"))
async def signals_handler(message: types.Message):
    await message.answer(
        "📡 Сигнали ще в розробці.\n\n"
        "План: бот буде аналізувати ринок і надсилати алерти, "
        "коли буде різкий ріст/падіння або цікаві точки входу."
    )


async def main():
    print("Bot started polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
