import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import BOT_TOKEN, CHANNEL_ID
from database import init_db, deal_exists, save_deal
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


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    SUBSCRIBERS.add(message.chat.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔍 Поиск скидок")]], resize_keyboard=True
    )
    await message.answer(
        "Привет! 👟 Я буду присылать тебе скидки на кроссовки с Brandshop и Lamoda.\n"
        "Я автоматически проверяю сайты каждые 30 минут.\n"
        "Нажми кнопку ниже или /latest чтобы запустить проверку прямо сейчас.",
        reply_markup=kb,
    )


@dp.message(F.text == "🔍 Поиск скидок")
async def handle_search_button(message: types.Message):
    await cmd_latest(message)


@dp.message(Command("latest"))
async def cmd_latest(message: types.Message):
    await message.answer("🔍 Ищу скидки на Brandshop и Lamoda, подождите...")
    count = await check_and_send_discounts(chat_id=message.chat.id)
    if count == 0:
        await message.answer("Пока новых скидок не найдено.")


async def check_and_send_discounts(chat_id=None):
    """
    Запускает парсеры и рассылает новые скидки.
    Если передан chat_id, отправляет только ему (ручной запуск).
    Иначе отправляет всем подписчикам.
    """
    loop = asyncio.get_running_loop()

    # Запускаем оба парсера параллельно в отдельных потоках
    brandshop_deals = await loop.run_in_executor(None, get_discounts)
    lamoda_deals = await loop.run_in_executor(None, get_lamoda_discounts)
    streetbeat_deals = await loop.run_in_executor(None, get_streetbeat_discounts)

    # Объединяем результаты
    deals = brandshop_deals + lamoda_deals + streetbeat_deals
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

            # Очищаем название
            cleaned_title = clean_title(deal["title"])

            # Формируем сообщение (caption для фото)
            source_name = deal.get("source", "Brandshop")
            caption = (
                f"👀 <b>Смотри, что нашел на {source_name}</b>\n\n"
                f"{cleaned_title}\n\n"
                f"💰 <b>{deal['price']}</b> (было {deal['old_price']})\n"
                f"🏷 Скидка: {deal['discount']}\n\n"
                f"📏 {size_label}: EU {sizes_str}"
            )

            # Создаем кнопку с партнерской ссылкой
            aff_manager = AffiliateManager()
            aff_link = aff_manager.convert_link(
                deal["link"], deal.get("source", "Unknown")
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Посмотреть 🛒", url=aff_link)]
                ]
            )

            # --- ОПТИМИЗАЦИЯ ФОТО ---
            # Загружаем фото один раз перед отправкой всем получателям
            photo_bytes = None
            if deal.get("image_url"):
                try:
                    photo_bytes = await loop.run_in_executor(
                        None, process_image, deal["image_url"]
                    )
                except Exception as e:
                    print(f"Error processing image for {deal['title']}: {e}")
                    photo_bytes = None

            # Вспомогательная функция отправки
            async def send_deal_photo(target_id, photo_data=None):
                # Если смогли скачать фото
                if photo_data:
                    try:
                        # Важно: сбрасываем указатель в начало, так как буфер мог быть прочитан
                        photo_data.seek(0)

                        # Создаем новый InputFile для каждой отправки
                        photo_file = BufferedInputFile(
                            photo_data.read(), filename="sneaker.jpg"
                        )

                        await bot.send_photo(
                            target_id,
                            photo=photo_file,
                            caption=caption,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                        return  # Успех
                    except Exception as e:
                        print(f"Photo bytes send error to {target_id}: {e}")
                        # Если не вышло байтами, пробуем URL ниже

                # Если байтов нет или отправка байтами упала - пробуем URL
                if deal.get("image_url"):
                    try:
                        await bot.send_photo(
                            target_id,
                            photo=deal["image_url"],
                            caption=caption,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                    except Exception as e:
                        print(f"Photo URL send error to {target_id}: {e}")
                        # Если и URL не прошел - шлем текст
                        await bot.send_message(
                            target_id,
                            caption,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                else:
                    # Если фото совсем нет
                    await bot.send_message(
                        target_id,
                        caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )

            # Отправляем в канал
            if CHANNEL_ID:
                try:
                    await send_deal_photo(CHANNEL_ID, photo_bytes)
                except Exception as e:
                    print(f"Error sending to channel: {e}")

            # Отправляем подписчикам (тест)
            if chat_id:
                try:
                    await send_deal_photo(chat_id, photo_bytes)
                except Exception:
                    pass

            new_deals_count += 1
            await asyncio.sleep(1)  # Пауза чтобы не спамить в API телеграма

        # ВАЖНО: Мы ВСЕГДА обновляем запись в базе (last_seen = now)
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
