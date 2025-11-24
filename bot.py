import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==========================
# 1. Конфігурація
# ==========================

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment!")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

db_pool: asyncpg.Pool | None = None


# ==========================
# 2. Ініціалізація БД
# ==========================

async def init_db():
    """
    Створюємо pool підключень та таблицю gifts, якщо її ще немає.
    """
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                id SERIAL PRIMARY KEY,
                slug TEXT UNIQUE,              -- технічне ім'я: snow_globe
                name TEXT NOT NULL,            -- красиве ім'я: Snow Globe
                last_price NUMERIC,            -- остання ціна (наприклад, в TON)
                last_change_24h NUMERIC,       -- зміна за 24 години (%)
                last_volume NUMERIC,           -- об'єм торгів
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    print("✅ DB initialized (gifts table ready)")


# ==========================
# 3. Клавіатура головного меню
# ==========================

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Ціна подарунка", callback_data="price")
    kb.button(text="🔥 Топ-дарунки", callback_data="top")
    kb.button(text="📈 Трекінг", callback_data="tracking")
    kb.button(text="⚡ Сигнали", callback_data="signals")
    kb.adjust(1)
    return kb.as_markup()


# ==========================
# 4. Команди /start, /help
# ==========================

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
        "/start — головне меню\n"
        "/help — опис команд\n"
        "/price — ціна подарунка (з нашої бази)\n"
        "/addgift — додати/оновити gift в базі\n\n"
        "Надалі буде:\n"
        "• /top — топ дарунків\n"
        "• /track — відстеження\n"
        "• /signals — ринкові сигнали\n",
        parse_mode="Markdown"
    )


# ==========================
# 5. Додавання gift в БД  (/addgift)
# ==========================

@dp.message(Command("addgift"))
async def addgift_handler(message: types.Message):
    """
    Формат:
    /addgift slug Назва_з_пробілами_через_нижнє_підкреслення 3.16 10.1 72800

    де:
      slug           — технічна назва (snow_globe)
      Назва_...      — відображуване ім'я (Snow Globe)
      3.16           — ціна (наприклад, в TON)
      10.1           — зміна за 24h (%)
      72800          — об'єм торгів

    Мінімальний формат:
    /addgift slug Назва_з_підкресленнями 3.16
    (інші поля можна не вказувати)
    """
    global db_pool
    if db_pool is None:
        await message.answer("❌ База даних ще не готова. Спробуйте пізніше.")
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(
            "❗ Формат команди:\n"
            "`/addgift slug Назва_з_підкресленнями ціна [зміна24h] [обʼєм]`\n\n"
            "Приклад:\n"
            "`/addgift snow_globe Snow_Globe 3.16 10.1 72800`",
            parse_mode="Markdown"
        )
        return

    slug = parts[1]
    name_raw = parts[2]
    name = name_raw.replace("_", " ")

    try:
        price = float(parts[3].replace(",", "."))
    except ValueError:
        await message.answer("❌ Некоректна ціна. Приклад: 3.16")
        return

    change_24h = None
    volume = None

    if len(parts) >= 5:
        try:
            change_24h = float(parts[4].replace(",", "."))
        except ValueError:
            change_24h = None

    if len(parts) >= 6:
        try:
            volume = float(parts[5].replace(",", "."))
        except ValueError:
            volume = None

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO gifts (slug, name, last_price, last_change_24h, last_volume, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (slug) DO UPDATE
              SET name = EXCLUDED.name,
                  last_price = EXCLUDED.last_price,
                  last_change_24h = EXCLUDED.last_change_24h,
                  last_volume = EXCLUDED.last_volume,
                  updated_at = NOW();
        """, slug, name, price, change_24h, volume)

    await message.answer(
        f"✅ Gift збережено:\n"
        f"`{slug}` → *{name}* — {price}",
        parse_mode="Markdown"
    )


# ==========================
# 6. Кнопка "Ціна подарунка" + /price
# ==========================

@dp.callback_query(F.data == "price")
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer("🔍 Введи назву або slug giftʼа (наприклад: `snow_globe` або `Snow Globe`).",
                                  parse_mode="Markdown")
    await callback.answer()


@dp.message(Command("price"))
async def price_command(message: types.Message):
    await message.answer(
        "🔍 Введи назву або slug giftʼа (наприклад: `snow_globe` або `Snow Globe`).",
        parse_mode="Markdown"
    )


# ==========================
# 7. Пошук gift в БД за текстом користувача
# ==========================

async def find_gift(query: str):
    """
    Шукаємо gift по name або slug (частковий збіг).
    """
    global db_pool
    if db_pool is None:
        return None

    q = f"%{query.lower()}%"
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT slug, name, last_price, last_change_24h, last_volume, updated_at
            FROM gifts
            WHERE LOWER(name) LIKE $1
               OR LOWER(slug) LIKE $1
            ORDER BY updated_at DESC
            LIMIT 1;
        """, q)
    return row


# ==========================
# 8. Обробка тексту (як запит до /price)
# ==========================

@dp.message()
async def text_router(message: types.Message):
    """
    Все, що не команда — вважаємо спробою пошуку gift.
    (поки що так, потім можна зробити FSM/стани)
    """
    text = message.text.strip()

    # Ігноруємо інші команди типу /start, /help
    if text.startswith("/"):
        return

    gift = await find_gift(text)
    if not gift:
        await message.answer("❌ Не знайшов gift з такою назвою. Спробуй інший запит або додай через /addgift.")
        return

    slug, name, price, change_24h, volume, updated_at = gift

    # Форматуємо гарну картку
    change_str = "—"
    if change_24h is not None:
        arrow = "📈" if change_24h >= 0 else "📉"
        change_str = f"{arrow} {change_24h:.2f}%"

    volume_str = f"{volume:.2f}" if volume is not None else "—"

   price_str = f"{float(price):.2f}"
volume_str = f"{float(volume):.0f}" if volume else "—"
updated_str = updated_at.strftime("%Y-%m-%d %H:%M")

text_reply = (
    f"🎁 *{name}*\n"
    f"`{slug}`\n\n"
    f"💎 *Ціна:* `{price_str}` TON\n"
    f"📉 *24h зміна:* {change_str}\n"
    f"📊 *Обʼєм:* `{volume_str}`\n"
    f"🕒 *Оновлено:* `{updated_str}`"
)


    await message.answer(text_reply, parse_mode="Markdown")


# ==========================
# 9. Запуск бота
# ==========================

async def main():
    await init_db()
    print("🤖 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

