import asyncio
import logging
import base64
import time
from functools import partial
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from config import BOT_TOKEN, CHANNEL_ID
from database import (
    init_db,
    deal_exists,
    save_deal,
    get_next_pending_deal,
    mark_deal_as_sent,
)
from scraper import get_discounts
from lamoda_scraper import get_lamoda_discounts
from streetbeat_scraper import get_streetbeat_discounts
from image_processing import process_image
from affiliate_manager import AffiliateManager
from aiogram.types import BufferedInputFile
from utils import format_sizes, clean_title

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список ID пользователей для рассылки (в идеале хранить в БД)
SUBSCRIBERS = set()

# Интервал публикации (в секундах)
PUBLISH_INTERVAL = 20 * 60  # 20 минут
LAST_PUBLISH_TIME = 0.0


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    SUBSCRIBERS.add(message.chat.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Погнали!"), KeyboardButton(text="🔍 Поиск скидок")]
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "Привет! 👟 Я буду мониторить скидки на кроссовки в популярных магазинах.\n"
        "Скидки публикуются в канал @Sneaker_Deals плавно в течение дня.\n\n"
        "Я автоматически ищу новые скидки каждые 30 минут.",
        reply_markup=kb,
        parse_mode="HTML",
    )


@dp.message(F.text == "🚀 Погнали!")
async def handle_home_button(message: types.Message):
    await cmd_start(message)


@dp.message(F.text == "🔍 Поиск скидок")
async def handle_search_button(message: types.Message):
    await cmd_latest(message)


@dp.message(Command("latest"))
async def cmd_latest(message: types.Message):
    await message.answer("🔍 Запускаю внеплановый скан магазинов...")
    # Запускаем скан
    await run_scrapers()

    # Пробуем отправить одну скидку сразу (вне очереди) для проверки
    await message.answer(
        "✅ Скан завершен. Новые скидки добавлены в очередь и будут опубликованы по графику."
    )


async def run_scrapers():
    """
    Запускает парсеры, находит товары и сохраняет их в БД с флагом sent=0.
    Ничего не отправляет в Телеграм.
    """
    print("[Scraper] Starting periodic scan...")
    loop = asyncio.get_running_loop()

    try:
        brandshop_deals = await loop.run_in_executor(None, get_discounts)
    except Exception as e:
        print(f"[Scraper] Brandshop error: {e}")
        brandshop_deals = []

    try:
        lamoda_deals = await loop.run_in_executor(None, get_lamoda_discounts)
    except Exception as e:
        print(f"[Scraper] Lamoda error: {e}")
        lamoda_deals = []

    try:
        streetbeat_deals = await loop.run_in_executor(None, get_streetbeat_discounts)
    except Exception as e:
        print(f"[Scraper] StreetBeat error: {e}")
        streetbeat_deals = []

    all_deals = brandshop_deals + lamoda_deals + streetbeat_deals
    print(f"[Scraper] Found {len(all_deals)} total items. Saving to DB...")

    new_count = 0
    for deal in all_deals:
        # Проверяем наличие.
        is_known = deal_exists(deal["link"])

        # Сохраняем всегда, чтобы обновить last_seen.
        # Если is_known=False (новый), то sent=False (по умолчанию в save_deal, если не передать)
        # Если мы передадим sent=False для СТАРОГО товара, save_deal НЕ перезапишет sent=1 на 0.

        save_deal(
            deal["title"],
            deal["price"],
            deal["old_price"],
            deal["link"],
            sizes=deal.get("sizes"),
            image_url=deal.get("image_url"),
            source=deal.get("source"),
            image_bytes_b64=deal.get("image_bytes_b64"),
            sent=False,  # Это ни на что не повлияет для старых записей, но для новых поставит 0
        )

        if not is_known:
            new_count += 1

    print(f"[Scraper] Scan finished. New/Resurfaced deals queued: {new_count}")


async def send_single_deal(deal_data, target_id=None):
    """
    Отправляет одну конкретную скидку (словарь deal_data из БД) в target_id (или в канал).
    """
    loop = asyncio.get_running_loop()

    # Восстанавливаем данные из БД
    link = deal_data["link"]
    title = deal_data["title"]
    price = deal_data["price"]
    old_price = deal_data["old_price"]
    source_name = deal_data.get("source", "Unknown")
    image_url = deal_data.get("image_url")
    image_bytes_b64 = deal_data.get("image_bytes_b64")

    sizes_str_db = deal_data.get("sizes", "")
    # В БД хранится строка "36,37,...". Нам нужно отформатировать красиво.
    if sizes_str_db:
        sizes_list = sizes_str_db.split(",")
    else:
        sizes_list = []

    formatted_sizes = format_sizes(sizes_list)
    size_label = "Размер" if len(sizes_list) == 1 else "Размеры"
    cleaned_title = clean_title(title)

    # Партнерская ссылка
    aff_manager = AffiliateManager()
    aff_link = aff_manager.convert_link(link, source_name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Посмотреть", url=aff_link)]]
    )

    price_line = f"💰 <b>{price}</b>"
    if old_price:
        price_line += f" (было {old_price})"

    caption = (
        f"👀 <b>Смотри, что нашел на {source_name}</b>\n\n"
        f"{cleaned_title}\n\n"
        f"{price_line}\n"
        f"📏 {size_label}: EU {formatted_sizes}\n\n"
    )

    # --- Подготовка фото ---
    photo_bytes = None

    # 1. Из base64 (если есть в БД)
    if image_bytes_b64:
        try:
            img_data = base64.b64decode(image_bytes_b64)
            func = partial(process_image, image_url, image_data=img_data)
            photo_bytes = await loop.run_in_executor(None, func)
        except Exception:
            pass

    # 2. По URL
    if not photo_bytes and image_url:
        try:
            photo_bytes = await loop.run_in_executor(None, process_image, image_url)
        except Exception:
            pass

    # Функция отправки (копия старой логики)
    async def do_send(chat_id):
        if photo_bytes:
            try:
                photo_bytes.seek(0)
                photo_file = BufferedInputFile(
                    photo_bytes.read(), filename="sneaker.jpg"
                )
                await bot.send_photo(
                    chat_id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                return
            except Exception:
                pass

        if image_url:
            try:
                await bot.send_photo(
                    chat_id,
                    photo=image_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                return
            except Exception:
                pass

        # Текст
        await bot.send_message(
            chat_id, caption, parse_mode="HTML", reply_markup=keyboard
        )

    # Отправка
    if target_id:
        try:
            await do_send(target_id)
        except Exception as e:
            print(f"Error sending to {target_id}: {e}")
    elif CHANNEL_ID:
        try:
            await do_send(CHANNEL_ID)
        except Exception as e:
            print(f"Error sending to channel: {e}")


async def publisher_task():
    """
    Фоновая задача, которая проверяет очередь и отправляет посты раз в PUBLISH_INTERVAL.
    """
    global LAST_PUBLISH_TIME
    print("Publisher task started.")

    # Даем фору при старте, чтобы не постить сразу, если только что запустили
    # Или наоборот, хотим сразу? Пусть первый раз будет через интервал
    LAST_PUBLISH_TIME = time.time() - (PUBLISH_INTERVAL - 60)  # Старт через минуту

    while True:
        now = time.time()
        time_since = now - LAST_PUBLISH_TIME

        if time_since >= PUBLISH_INTERVAL:
            deal_data = get_next_pending_deal()

            if deal_data:
                print(f"[Publisher] Publishing deal: {deal_data['title']}")
                await send_single_deal(deal_data)
                mark_deal_as_sent(deal_data["link"])
                LAST_PUBLISH_TIME = time.time()
            else:
                # Очередь пуста
                pass

        await asyncio.sleep(60)


async def scheduler():
    """Фоновая задача скрапинга запускается раз в 30 минут"""
    while True:
        await run_scrapers()
        await asyncio.sleep(60 * 30)


async def main():
    init_db()

    # Запускаем планировщик скрапинга
    asyncio.create_task(scheduler())
    # Запускаем планировщик рассылки
    asyncio.create_task(publisher_task())

    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
