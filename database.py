import sqlite3
from config import DB_NAME

def init_db():
    """Создает таблицу, если её нет"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                link TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                old_price TEXT
            )
        """)
        conn.commit()

def deal_exists(link):
    """Проверяет, присылали ли мы уже этот товар"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM deals WHERE link = ?", (link,))
        return cursor.fetchone() is not None

def save_deal(title, price, old_price, link):
    """Сохраняет новый товар в базу"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO deals (link, title, price, old_price)
            VALUES (?, ?, ?, ?)
        """, (link, title, price, old_price))
        conn.commit()
