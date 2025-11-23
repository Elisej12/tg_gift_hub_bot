import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# ============================================================
# БЕРЕМО ТОКЕН ІЗ Railway
# ============================================================
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ============================================================
# КНОПКИ — Головне меню
# ============================================================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Ціна подарунка", callback_data="price")
    kb.button(text="🔥 Топ-дарунки", callback_data="top")
    kb.button(text="📈 Трекінг", callback_data="tracking")
    kb.button(text="⚡ Сигнали", callback_data="signals")
    kb.adjust(1)
    return kb.as_markup()



# ============================================================
# /start
# ============================================================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🎁 *TG Gift Hub Bot — твій асистент подарунків і NFT!*\n\n"
        "Оберіть дію нижче:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


# ============================================================
# /help
# ============================================================
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📘 *Доступні команди:*\n"
        "/start — головне меню\n"
        "/help — опис команд\n"
        "/price — ціна подарунка / токена\n"
        "/top — топ-дарунків\n"
        "/track — відстеження подарунків\n"
        "/signals — ринкові сповіщення\n\n"
        "_Працюємо з CoinGecko API_",
        parse_mode="Markdown"
    )


# ============================================================
# CoinGecko API — пошук токена/NFT
# ============================================================
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

async def get_nft_price(name: str):
    """Пошук NFT/токена по назві."""
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": False
    }

    try:
        response = requests.get(COINGECKO_URL, params=params, timeout=5)
        data = response.json()
    except Exception:
        return None

    # Пошук збігів
    for item in data:
        if name.lower() in item["name"].lower():
            return {
                "name": item["name"],
                "symbol": item["symbol"],
                "price": item["current_price"],
                "change": item["price_change_percentage_24h"],
                "volume": item["total_volume"],
                "image": item["image"]
            }

    return None



# ============================================================
# Обробка кнопки "Ціна подарунка"
# ============================================================
@dp.callback_query(F.data == "price")
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer("🔍 Введи назву NFT/токена:")
    await callback.answer()



# ============================================================
# Основний обробник тексту — пошук NFT / токена
# ============================================================
@dp.message()
async def search_nft(message: types.Message):
    name = message.text.strip()

    result = await get_nft_price(name)

    if not result:
        await message.answer("❌ Нічого не знайдено. Спробуй іншу назву.")
        return

    text = (
        f"🎁 *{result['name']}* (`{result['symbol']}`)\n\n"
        f"💲 *Ціна:* `${result['price']}`\n"
        f"📉 *24h зміна:* `{result['change']}%`\n"
        f"📊 *Обсяг:* `${result['volume']}`\n"
    )

    await message.answer_photo(
        result["image"],
        caption=text,
        parse_mode="Markdown"
    )



# ============================================================
# ЗАПУСК БОТА
# ============================================================
async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
