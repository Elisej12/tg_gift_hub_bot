import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder


# === 1. Берём токен из переменной окружения ===
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set! Add it in Railway variables.")


bot = Bot(token=TOKEN)
dp = Dispatcher()


# === 2. Головне меню (інлайн-кнопки) ===
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Ціна подарунка", callback_data="price")
    kb.button(text="🔥 Топ-дарунки", callback_data="top")
    kb.button(text="📈 Трекінг", callback_data="tracking")
    kb.button(text="⚡ Сигнали", callback_data="signals")
    kb.adjust(1)  # по 1 кнопці в ряд
    return kb.as_markup()


# === 3. Команда /start ===
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🎁 *TG Gift Hub Bot — твій асистент подарунків і NFT!*\n\n"
        "Оберіть дію нижче:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


# === 4. Команда /help ===
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📘 *Доступні команди:*\n"
        "/start — головне меню\n"
        "/help — опис команд\n"
        "/price — ціна подарунка\n"
        "/top — топ-дарунків\n"
        "/track — відстеження подарунків\n"
        "/signals — сповіщення про ринок\n\n"
        "Працюємо лише з NFT-дарунками.\n"
        "_API: CoinGecko_",
        parse_mode="Markdown"
    )


# === 5. Обробка натискань на кнопки ===
@dp.callback_query(Text("price"))
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔍 Введи назву NFT подарунка, щоб дізнатися актуальну ціну."
    )
    await callback.answer()


@dp.callback_query(Text("top"))
async def cb_top(callback: types.CallbackQuery):
    await callback.message.answer("🔥 ТОП-дарунків скоро буде доступний!")
    await callback.answer()


@dp.callback_query(Text("tracking"))
async def cb_tracking(callback: types.CallbackQuery):
    await callback.message.answer("📈 Трекінг подарунків в процесі розробки.")
    await callback.answer()


@dp.callback_query(Text("signals"))
async def cb_signals(callback: types.CallbackQuery):
    await callback.message.answer("⚡ Сигнали ринку незабаром будуть доступні.")
    await callback.answer()


# === 6. Запуск бота ===
async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
