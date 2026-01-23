import os

# Токен бота (лучше брать из переменных окружения, но для старта можно так)
BOT_TOKEN = "8583683842:AAGULmRc4SU4wG_OIlWAvFLFqCR8EdsyT08"

# Ссылка для парсинга (Brandshop - Кроссовки со скидками)
# Можно также использовать /muzhskoe/obuv/krossovki/ для всех мужских кроссовок
TARGET_URL = "https://brandshop.ru/sale/obuv/krossovki/"

# Заголовки, чтобы притворяться обычным браузером
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

# Имя файла базы данных
DB_NAME = "deals.db"

# ID канала для рассылки
CHANNEL_ID = "@krosi_na_skidochkax"
