import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==========================
# 1. КОНФИГ
# ==========================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================
# 2. СПИСОК GIFTS (пока вручную)
# ==========================

# Можно добавить свои gifты сюда
GIFTS = [
    {
        "slug": "snow_globe",
        "name": "Snow Globe",
        "price": 3.16,
        "change_24h": 10.1,
        "volume": 72800,
        "image_url": "https://cdn.pixabay.com/photo/2017/01/31/21/23/snow-globe-2021066_1280.png"
    },
    {
        "slug": "cat_mask",
        "name": "Cat Mask",
        "price": 5.99,
        "change_24h": -2.3,
        "volume": 15400,
        "image_url": "https://cdn.pixabay.com/photo/2017/11/11/21/41/cat-2944820_1280.png"
    },
    {
        "slug": "heart_box",
        "name": "Heart Box",
        "price": 2.45,
        "change_24h": 3.7,
        "volume": 9820,
        "image_url": "https://cdn.pixabay.com/photo/2017/02/12/17/15/heart-2069396_1280.png"
    }
]


# ==========================
# 3. МЕНЮ
# ==========================

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Ціна подарунка", callback_data="price")
    kb.button(text="🔥 Топ-дарунки", callback_data="top")
    kb.button(text="📈 Трекінг (soon)", callback_data="tracking")
    kb.button(text="⚡ Сигнали (soon)", callback_data="signals")
    kb.adjust(1)
    return kb.as_markup()


# ==========================
# 4. КОМАНДЫ
# ==========================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎁 *TG Gift Hub Bot*\n\n"
        "Маленьке застосунок всередині Telegram для NFT / gifts.\n\n"
        "Оберіть дію:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📘 *Команди:*\n"
        "/start — головне меню\n"
        "/help — допомога\n\n"
        "Просто напиши частину назви giftʼа (наприклад: `snow`, `cat`, `heart`),\n"
        "і я покажу всі знайдені варіанти.",
        parse_mode="Markdown"
    )


# ==========================
# 5. CALLBACK КНОПКИ
# ==========================

@dp.callback_query(F.data == "price")
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔍 Введи назву або частину назви giftʼа (наприклад: `snow`, `mask`, `cat`)."
    )
    await callback.answer()


@dp.callback_query(F.data == "top")
async def cb_top(callback: types.CallbackQuery):
    await callback.message.answer("🔥 Топ-дарунки буде додано пізніше.")
    await callback.answer()


@dp.callback_query(F.data == "tracking")
async def cb_tracking(callback: types.CallbackQuery):
    await callback.message.answer("📈 Трекінг скоро буде доступний.")
    await callback.answer()


@dp.callback_query(F.data == "signals")
async def cb_signals(callback: types.CallbackQuery):
    await callback.message.answer("⚡ Сигнали ринку у розробці.")
    await callback.answer()


# ==========================
# 6. ПОШУК ПО СПИСКУ GIFTS
# ==========================

def search_gifts(query: str):
    """
    Повертає список gifтов, де query входить в name або slug (без урахування регістру).
    """
    q = query.lower()
    results = []
    for g in GIFTS:
        if q in g["name"].lower() or q in g["slug"].lower():
            results.append(g)
    return results


# ==========================
# 7. ОБРОБКА ТЕКСТУ (ПОШУК)
# ==========================

@dp.message()
async def text_router(message: types.Message):
    text = (message.text or "").strip()
    if not text:
        return

    # Якщо це команда — ігноруємо (їх вже обробляють інші хендлери)
    if text.startswith("/"):
        return

    matches = search_gifts(text)

    if not matches:
        await message.answer("❌ Нічого не знайдено по цьому запиту. Спробуй іншу назву.")
        return

    # Виводимо всі знайдені
    for g in matches:
        slug = g["slug"]
        name = g["name"]
        price = g["price"]
        change = g["change_24h"]
        volume = g["volume"]
        image_url = g["image_url"]

        arrow = "📈" if change >= 0 else "📉"
        change_str = f"{arrow} {change:.2f}%"
        volume_str = f"{volume:.0f}"

        caption = (
            f"🎁 *{name}*\n"
            f"`{slug}`\n\n"
            f"💎 Ціна: `{price}`\n"
            f"📊 24h зміна: {change_str}\n"
            f"📦 Обʼєм: `{volume_str}`"
        )

        if image_url:
            await message.answer_photo(
                photo=image_url,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await message.answer(caption, parse_mode="Markdown")


# ==========================
# 8. ЗАПУСК БОТА
# ==========================

async def main():
    print("🤖 Bot is running (no DB, gifts in code)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
