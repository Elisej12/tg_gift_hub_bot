import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = "8145174717:AAHxbgUhkH-us5l6l0JpMvTVayOKC1SVcNY"

bot = Bot(token=TOKEN)
dp = Dispatcher()


# /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Вітаю у TG Gift Hub Bot!\n\n"
        "Я допоможу:\n"
        "• дізнатися ціну дарунка\n"
        "• відстежувати ріст/падіння\n"
        "• аналізувати портфель\n\n"
        "Введи /help щоб побачити всі можливості."
    )

# /help
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📘 Доступні команди:\n"
        "/price — дізнатися ціну подарунка\n"
        "/top — топ дарунків\n"
        "/track — відстежувати Gift\n"
        "/portfolio — аналіз портфелю\n"
        "/signals — ринкові сигнали\n"
    )

# /price (поки заглушка)
@dp.message(Command("price"))
async def price_handler(message: types.Message):
    await message.answer("🔍 Ціни скоро будуть доступні. Ми над цим працюємо!")

# /top
@dp.message(Command("top"))
async def top_handler(message: types.Message):
    await message.answer("📊 ТОП дарунків сьогодні з'явиться пізніше.")

# /track
@dp.message(Command("track"))
async def track_handler(message: types.Message):
    await message.answer("📈 Відстеження дарунків буде додано.")

# /portfolio
@dp.message(Command("portfolio"))
async def portfolio_handler(message: types.Message):
    await message.answer("💼 Аналіз портфелю в процесі розробки.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
