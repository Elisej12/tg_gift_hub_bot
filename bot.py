import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================
# 1. Telegram TOKEN
# =========================
TOKEN = os.getenv("BOT_TOKEN")

# =========================
# 2. Database URL
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

# =========================
# Bot + Dispatcher
# =========================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================
# Database connection
# =========================
async def connect_db():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Створюємо таблицю якщо її немає
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS gifts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price FLOAT,
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    await conn.close()
    print("✅ Database connected & table created")


# ===========================================================
# Головне меню
# ===========================================================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Ціна подарунка", callback_data="price")
    kb.button(text="🔥 Топ-дарунки", callback_data="top")
    kb.button(text="📈 Трекінг", callback_data="tracking")
    kb.button(text="⚡ Сигнали", callback_data="signals")
    kb.adjust(1)
    return kb.as_markup()


# ===========================================================
# Команди
# ===========================================================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🎁 *TG Gift Hub Bot — твій асистент подарунків і NFT!*\n\n"
        "Оберіть дію нижче:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📘 *Доступні команди:*\n"
        "/start — меню\n"
        "/help — опис команд\n"
        "/price — ціна NFT\n"
        "/top — топ NFT\n"
        "/track — відстеження\n"
        "/signals — ринкові зміни\n",
        parse_mode="Markdown"
    )


# ===========================================================
# Обробка кнопок
# ===========================================================
@dp.callback_query(lambda c: c.data == "price")
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer("🔍 Введи назву NFT подарунка.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "top")
async def cb_top(callback: types.CallbackQuery):
    await callback.message.answer("🔥 ТОП-дарунків скоро буде доступний!")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "tracking")
async def cb_track(callback: types.CallbackQuery):
    await callback.message.answer("📈 Трекінг подарунків в процесі.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "signals")
async def cb_signals(callback: types.CallbackQuery):
    await callback.message.answer("⚡ Сигнали ринку будуть скоро.")
    await callback.answer()


# ===========================================================
# Запуск
# ===========================================================
async def main():
    # Підключення до БД
    await connect_db()

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
