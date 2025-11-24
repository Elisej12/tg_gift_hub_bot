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
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                id SERIAL PRIMARY KEY,
                slug TEXT UNIQUE,
                name TEXT NOT NULL,
                last_price NUMERIC,
                last_change_24h NUMERIC,
                last_volume NUMERIC,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

    print("✅ DB initialized (gifts table ready)")


# ==========================
# 3. Меню
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
# 4. Команди
# ==========================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🎁 *TG Gift Hub Bot — твій асистент подарунків та NFT!*\n\n"
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
        "/price — ціна подарунка\n"
        "/addgift — додати/оновити gift у базі\n\n",
        parse_mode="Markdown"
    )


# ==========================
# 5. Додавання gift
# ==========================

@dp.message(Command("addgift"))
async def addgift_handler(message: types.Message):
    global db_pool
    if db_pool is None:
        await message.answer("❌ База даних ще не готова.")
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(
            "❗ Формат:\n"
            "`/addgift slug Назва_з_підкресленнями ціна [зміна24h] [обʼєм]`\n"
            "Приклад:\n"
            "`/addgift snow_globe Snow_Globe 3.16 10.1 72800`",
            parse_mode="Markdown"
        )
        return

    slug = parts[1]
    name = parts[2].replace("_", " ")
    price = float(parts[3])

    change_24h = float(parts[4]) if len(parts) > 4 else None
    volume = float(parts[5]) if len(parts) > 5 else None

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
        f"✅ Gift збережено:\n`{slug}` → *{name}* — {price}",
        parse_mode="Markdown"
    )


# ==========================
# 6. Кнопка “📊 Ціна подарунка”
# ==========================

@dp.callback_query(F.data == "price")
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔍 Введи назву або частину назви NFT gift’a (наприклад: `snow`, `cat`, `mask`).",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(Command("price"))
async def price_command(message: types.Message):
    await message.answer(
        "🔍 Введи назву або частину назви gift’a.",
        parse_mode="Markdown"
    )


# ==========================
# 7. Пошук у базі
# ==========================

async def find_gift(query: str):
    global db_pool
    if db_pool is None:
        return None

    q = f"%{query.lower()}%"

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT slug, name, last_price, last_change_24h, last_volume, updated_at
            FROM gifts
            WHERE LOWER(name) LIKE $1 OR LOWER(slug) LIKE $1
            ORDER BY updated_at DESC
            LIMIT 1;
        """, q)

    return row


# ==========================
# 8. Обробка ВЕСЬ текст → пошук
# ==========================

@dp.message()
async def text_router(message: types.Message):

    if message.text.startswith("/"):
        return

    gift = await find_gift(message.text)
    if not gift:
        await message.answer("❌ Нічого не знайдено. Спробуй іншу назву або додай через /addgift")
        return

    slug, name, price, change_24h, volume, updated_at = gift

    arrow = "📈" if (change_24h or 0) >= 0 else "📉"
    change_str = f"{arrow} {change_24h:.2f}%" if change_24h is not None else "—"
    volume_str = f"{volume:.2f}" if volume is not None else "—"

    text_reply = (
        f"🎁 *{name}*\n"
        f"`{slug}`\n\n"
        f"💎 *Ціна:* `{price}`\n"
        f"📊 *24h зміна:* {change_str}\n"
        f"📦 *Обʼєм:* `{volume_str}`\n"
        f"🕒 *Оновлено:* `{updated_at}`"
    )

    await message.answer(text_reply, parse_mode="Markdown")


# ==========================
# 9. Запуск
# ==========================

async def main():
    await init_db()
    print("🤖 Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
