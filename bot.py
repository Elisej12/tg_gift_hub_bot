import os
import asyncio
import asyncpg
import aiohttp
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

GETGEMS_URL = "https://graphql.getgems.io/graphql"


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
# 4. Команди /start, /help
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
        "📘 *Команди:*\n"
        "/start — головне меню\n"
        "/help — опис команд\n"
        "/price — ціна NFT gift\n"
        "/addgift — додати gift вручну в локальну БД\n\n"
        "Спочатку бот шукає у GETGEMS, потім — у локальній БД.",
        parse_mode="Markdown"
    )


# ==========================
# 5. /addgift (локальна БД)
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
            "`/addgift slug Name_With_Underscores price [change24h] [volume]`\n\n"
            "Приклад:\n"
            "`/addgift snow_globe Snow_Globe 3.16 10.1 72800`",
            parse_mode="Markdown"
        )
        return

    slug = parts[1]
    name = parts[2].replace("_", " ")

    try:
        price = float(parts[3].replace(",", "."))
    except Exception:
        await message.answer("❌ Некоректна ціна!")
        return

    change_24h = float(parts[4]) if len(parts) > 4 else None
    volume = float(parts[5]) if len(parts) > 5 else None

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO gifts (slug, name, last_price, last_change_24h, last_volume, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                last_price = EXCLUDED.last_price,
                last_change_24h = EXCLUDED.last_change_24h,
                last_volume = EXCLUDED.last_volume,
                updated_at = NOW();
        """, slug, name, price, change_24h, volume)

    await message.answer(
        f"✅ Gift `{slug}` → *{name}* збережено!",
        parse_mode="Markdown"
    )


# ==========================
# 6. Кнопка /price
# ==========================

@dp.callback_query(F.data == "price")
async def cb_price(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔍 Введи назву або частину назви NFT giftʼа (наприклад: `snow`, `cat`, `mask`).",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(Command("price"))
async def price_cmd(message: types.Message):
    await message.answer(
        "🔍 Введи назву або частину назви NFT giftʼа.",
        parse_mode="Markdown"
    )


# ==========================
# 7. GETGEMS: пошук NFT (список)
# ==========================

async def search_nfts_gem(query: str, limit: int = 5):
    """
    Пошук NFT у GETGEMS по назві (повертає список до `limit` штук).
    """
    json_query = {
        "query": """
        query SearchNFT($search: String!, $limit: Int!) {
          nftItems(
            filter: { name: { contains: $search } }
            limit: $limit
          ) {
            name
            address
            price
            lastSale { price }
            previews { url }
            collection { name }
          }
        }
        """,
        "variables": {"search": query, "limit": limit}
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GETGEMS_URL, json=json_query) as resp:
            data = await resp.json()
            items = data.get("data", {}).get("nftItems", [])
            return items


async def get_nft_by_address(address: str):
    """
    Отримати один NFT по address (для колбеку з кнопки).
    """
    json_query = {
        "query": """
        query NftByAddress($addr: String!) {
          nftItem(address: $addr) {
            name
            address
            price
            lastSale { price }
            previews { url }
            collection { name }
          }
        }
        """,
        "variables": {"addr": address}
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(GETGEMS_URL, json=json_query) as resp:
            data = await resp.json()
            return data.get("data", {}).get("nftItem")


# ==========================
# 8. Локальний пошук у БД
# ==========================

async def find_gift_local(query: str):
    global db_pool
    q = f"%{query.lower()}%"

    async with db_pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT slug, name, last_price, last_change_24h, last_volume, updated_at
            FROM gifts
            WHERE LOWER(name) LIKE $1 OR LOWER(slug) LIKE $1
            ORDER BY updated_at DESC
            LIMIT 1;
        """, q)


# ==========================
# 9. Обробка ВСЬОГО тексту — головний пошук
# ==========================

@dp.message()
async def text_router(message: types.Message):
    query = message.text.strip()

    # ігноруємо команди
    if query.startswith("/"):
        return

    # 1) шукаємо у GETGEMS
    nfts = await search_nfts_gem(query)

    if nfts:
        # якщо знайдено ОДИН NFT → одразу показуємо картку
        if len(nfts) == 1:
            nft = nfts[0]
            await send_nft_card(message.chat.id, nft)
            return

        # якщо кілька → показуємо вибір
        kb = InlineKeyboardBuilder()
        text_lines = ["🔎 *Знайшов кілька NFT, обери:*", ""]

        for idx, item in enumerate(nfts, start=1):
            name = item.get("name", "Без назви")
            collection = (item.get("collection") or {}).get("name") if item.get("collection") else ""
            short = (name[:18] + "…") if len(name) > 18 else name
            btn_text = f"{idx}. {short}"
            address = item.get("address")
            if not address:
                continue

            kb.button(text=btn_text, callback_data=f"nft_{address}")
            line = f"{idx}) *{name}*"
            if collection:
                line += f" — _{collection}_"
            text_lines.append(line)

        kb.adjust(1)
        await message.answer("\n".join(text_lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        return

    # 2) якщо GETGEMS нічого не знайшов → пробуємо локальну БД
    gift = await find_gift_local(query)
    if gift:
        slug, name, price, change_24h, volume, updated_at = gift

        price_str = f"{float(price):.2f}" if price is not None else "—"
        volume_str = f"{float(volume):.0f}" if volume else "—"
        updated_str = updated_at.strftime("%Y-%m-%d %H:%M") if updated_at else "—"

        if change_24h is None:
            change_str = "—"
        else:
            arrow = "📈" if change_24h >= 0 else "📉"
            change_str = f"{arrow} {change_24h:.2f}%"

        text_reply = (
            f"🎁 *{name}*\n"
            f"`{slug}`\n\n"
            f"💎 *Ціна:* `{price_str}` TON\n"
            f"📉 *24h зміна:* {change_str}\n"
            f"📊 *Обʼєм:* `{volume_str}`\n"
            f"🕒 *Оновлено:* `{updated_str}`"
        )

        await message.answer(text_reply, parse_mode="Markdown")
        return

    # 3) взагалі нічого не знайшли
    await message.answer("❌ Не знайдено NFT за цим запитом ні в GETGEMS, ні в локальній БД.")


# ==========================
# 10. Обробка вибору NFT з кнопок
# ==========================

@dp.callback_query(F.data.startswith("nft_"))
async def nft_choice_callback(callback: types.CallbackQuery):
    address = callback.data.removeprefix("nft_")
    nft = await get_nft_by_address(address)

    if not nft:
        await callback.message.answer("❌ Не вдалося завантажити дані про цей NFT.")
        await callback.answer()
        return

    await send_nft_card(callback.message.chat.id, nft)
    await callback.answer()


# ==========================
# 11. Відправка красивої картки NFT
# ==========================

async def send_nft_card(chat_id: int, nft: dict):
    name = nft.get("name", "Без назви")
    address = nft.get("address", "")
    collection = (nft.get("collection") or {}).get("name") if nft.get("collection") else "Unknown"

    price = nft.get("price")
    last_sale = nft.get("lastSale", {}).get("price") if nft.get("lastSale") else None
    preview = None
    previews = nft.get("previews") or []
    if previews:
        preview = previews[0].get("url")

    price_str = f"{price} TON" if price is not None else "—"
    last_sale_str = f"{last_sale} TON" if last_sale is not None else "—"

    text = (
        f"🎁 *{name}*\n"
        f"📚 Колекція: *{collection}*\n\n"
        f"💎 *Поточна ціна:* `{price_str}`\n"
        f"💼 *Останній продаж:* `{last_sale_str}`\n\n"
        f"🔗 [Відкрити в Getgems](https://getgems.io/asset/{address})"
    )

    if preview:
        await bot.send_photo(chat_id, photo=preview, caption=text, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, text, parse_mode="Markdown")


# ==========================
# 12. Запуск
# ==========================

async def main():
    await init_db()
    print("🤖 Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
