import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота (лучше брать из переменных окружения, но для старта можно так)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Ссылка для парсинга (Brandshop - Кроссовки со скидками)
# Можно также использовать /muzhskoe/obuv/krossovki/ для всех мужских кроссовок
TARGET_URL = "https://brandshop.ru/sale/obuv/krossovki/"

# Ссылка для Lamoda (мужские кроссовки и кеды со скидками)
LAMODA_URL = "https://www.lamoda.ru/c/2968/shoes-krossovki-kedy/?genders=men&is_sale=1"

# Заголовки, чтобы притворяться обычным браузером
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

# Имя файла базы данных
DB_NAME = "deals.db"

# ID канала для рассылки
CHANNEL_ID = "@Sneaker_Deals"

# Через сколько дней можно присылать товар повторно (если он пропадал из продажи)
REPOST_DAYS = 7

# Настройки партнерских сетей (CPA)
# Замените значения на ваши реальные ссылки/ID
AFFILIATE_NETWORKS = {
    "StreetBeat": {
        "type": "admitad",
        # Пример: https://ad.admitad.com/g/YOUR_KEY/?subid=telegram_bot&ulp=
        "base_url": "",
    },
    "Lamoda": {
        "type": "actionpay",
        # Пример: https://click.actionpay.ru/...?url=
        "base_url": "",
    },
    "Brandshop": {
        "type": "custom",
        # Любой другой формат
        "base_url": "",
    },
}
