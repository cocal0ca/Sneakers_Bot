import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, CHANNEL_ID
from database import init_db, deal_exists, save_deal
from scraper import get_discounts

from utils import format_sizes

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список ID пользователей для рассылки (в идеале хранить в БД)
SUBSCRIBERS = set()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    SUBSCRIBERS.add(message.chat.id)
    await message.answer(
        "Привет! 👟 Я буду присылать тебе скидки на кроссовки с Brandshop.\n"
        "Я автоматически проверяю сайт каждые 30 минут.\n"
        "Нажми /latest чтобы запустить проверку прямо сейчас."
    )


@dp.message(Command("latest"))
async def cmd_latest(message: types.Message):
    await message.answer("🔍 Ищу скидки, подождите...")
    count = await check_and_send_discounts(chat_id=message.chat.id)
    if count == 0:
        await message.answer("Пока новых скидок не найдено.")


async def check_and_send_discounts(chat_id=None):
    """
    Запускает парсер и рассылает новые скидки.
    Если передан chat_id, отправляет только ему (ручной запуск).
    Иначе отправляет всем подписчикам.
    """
    # Запускаем блокирующую функцию парсинга в отдельном потоке
    loop = asyncio.get_running_loop()
    # Первым аргументом None означает использование дефолтного executor-а (ThreadPoolExecutor)
    deals = await loop.run_in_executor(None, get_discounts)
    new_deals_count = 0

    for deal in deals:
        # Проверяем, нужно ли отправлять (возвращает False, если нужно отправить)
        # ВНИМАНИЕ: deal_exists теперь возвращает True если "существует и актуально" (не слать)
        # и False если "новое или вернулось" (слать)
        should_post = not deal_exists(deal["link"])

        if should_post:
            # Формируем строку с размерами
            sizes_list = deal.get("sizes", [])
            sizes_str = format_sizes(sizes_list)

            # Выбираем заголовок в зависимости от количества размеров
            size_label = "Размер" if len(sizes_list) == 1 else "Размеры"

            # Формируем сообщение (caption для фото)
            caption = (
                f"👀 <b>Смотри, что нашел</b>\n"
                f"👟 {deal['title']}\n"
                f"💰 <b>{deal['price']}</b> (было {deal['old_price']})\n"
                f"🏷 Скидка: {deal['discount']}\n"
                f"📏 {size_label}: EU {sizes_str}"
            )

            # Создаем кнопку
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Посмотреть 🛒", url=deal["link"])]
                ]
            )

            # Отправляем в канал
            if CHANNEL_ID:
                try:
                    if deal.get("image_url"):
                        await bot.send_photo(
                            CHANNEL_ID,
                            photo=deal["image_url"],
                            caption=caption,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                    else:
                        # Если нет фото, отправляем текстом
                        await bot.send_message(
                            CHANNEL_ID,
                            caption,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                except Exception as e:
                    print(f"Ошибка отправки в канал: {e}")

            # Отправляем подписчикам (если это ручной запуск)
            if chat_id:
                try:
                    if deal.get("image_url"):
                        await bot.send_photo(
                            chat_id,
                            photo=deal["image_url"],
                            caption=caption,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                    else:
                        # Если нет фото, отправляем текстом
                        await bot.send_message(
                            chat_id, caption, parse_mode="HTML", reply_markup=keyboard
                        )
                except Exception:
                    pass

            new_deals_count += 1
            await asyncio.sleep(1)  # Пауза чтобы не спамить в API телеграма

        # ВАЖНО: Мы ВСЕГДА обновляем запись в базе (last_seen = now)
        # Если отправили - запишется как новая.
        # Если не отправили - обновится last_seen, чтобы "дырка" не росла.
        save_deal(deal["title"], deal["price"], deal["old_price"], deal["link"])

    return new_deals_count


async def scheduler():
    """Фоновая задача, которая запускается раз в 30 минут"""
    while True:
        await asyncio.sleep(60 * 30)  # 30 минут
        if SUBSCRIBERS:
            print("Запуск плановой проверки...")
            await check_and_send_discounts()


async def main():
    init_db()

    # Запускаем планировщик в фоне
    asyncio.create_task(scheduler())

    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
