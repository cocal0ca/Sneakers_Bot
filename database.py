import sqlite3
import datetime
from config import DB_NAME, REPOST_DAYS


def init_db():
    """Создает таблицу, если её нет, и мигрирует схему при необходимости"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Основная таблица
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                link TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                old_price TEXT,
                last_seen TIMESTAMP
            )
        """)

        # Миграция: проверяем, есть ли колонка last_seen
        cursor.execute("PRAGMA table_info(deals)")
        columns = [info[1] for info in cursor.fetchall()]

        if "last_seen" not in columns:
            print("База данных: добавляем колонку last_seen...")
            try:
                cursor.execute("ALTER TABLE deals ADD COLUMN last_seen TIMESTAMP")
            except sqlite3.OperationalError:
                # Если вдруг колонка уже есть (иногда бывает рассинхрон)
                pass

            # Заполняем старые записи текущим временем
            now = datetime.datetime.now()
            cursor.execute("UPDATE deals SET last_seen = ?", (now,))

        # Если осталась старая колонка date_added, можно её игнорировать или удалить (в SQLite сложно удалять)

        conn.commit()


def deal_exists(link):
    """
    Проверяет, нужно ли отправлять товар.
    Возвращает True, если товар НЕ нужно отправлять (он актуален и видели недавно).
    Возвращает False, если товар нужно отправить (его нет или он вернулся после долгого отсутствия).
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_seen FROM deals WHERE link = ?", (link,))
        row = cursor.fetchone()

        if row is None:
            return False  # Товара нет, надо слать

        last_seen_str = row[0]

        if not last_seen_str:
            return False  # Дата сломана, шлем на всякий случай

        try:
            last_seen = datetime.datetime.fromisoformat(last_seen_str)
        except ValueError:
            return False

        # Проверяем "дырку" (gap)
        # Если мы видели товар недавно (меньше чем REPOST_DAYS назад), значит он просто висит на сайте
        # Если мы не видели его ДАВНО (> REPOST_DAYS), значит он пропал и вернулся -> шлем
        delta = datetime.datetime.now() - last_seen
        if delta.days >= REPOST_DAYS:
            return False  # Прошло много времени, скидка "вернулась"

        return True  # Скидка актуальна, видели недавно, не спамим


def save_deal(title, price, old_price, link):
    """
    Сохраняет товар или обновляет статус 'last_seen'.
    Эту функцию надо вызывать ДЛЯ ВСЕХ найденных товаров.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # INSERT OR REPLACE обновит запись и поставит свежий last_seen
        cursor.execute(
            """
            INSERT OR REPLACE INTO deals (link, title, price, old_price, last_seen)
            VALUES (?, ?, ?, ?, ?)
        """,
            (link, title, price, old_price, now),
        )
        conn.commit()
