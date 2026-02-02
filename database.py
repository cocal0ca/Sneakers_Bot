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
                pass
            now = datetime.datetime.now()
            cursor.execute("UPDATE deals SET last_seen = ?", (now,))

        if "sent" not in columns:
            print("База данных: добавляем колонку sent...")
            try:
                cursor.execute("ALTER TABLE deals ADD COLUMN sent INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

        # Миграция для дополнительных полей (для очереди)
        if "sizes" not in columns:
            try:
                cursor.execute("ALTER TABLE deals ADD COLUMN sizes TEXT")
            except:
                pass
        if "image_url" not in columns:
            try:
                cursor.execute("ALTER TABLE deals ADD COLUMN image_url TEXT")
            except:
                pass
        if "source" not in columns:
            try:
                cursor.execute("ALTER TABLE deals ADD COLUMN source TEXT")
            except:
                pass
        if "image_bytes_b64" not in columns:
            try:
                cursor.execute("ALTER TABLE deals ADD COLUMN image_bytes_b64 TEXT")
            except:
                pass

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
        delta = datetime.datetime.now() - last_seen
        if delta.days >= REPOST_DAYS:
            return False  # Прошло много времени, скидка "вернулась"

        return True  # Скидка актуальна, видели недавно, не спамим


def save_deal(
    title,
    price,
    old_price,
    link,
    sizes=None,
    image_url=None,
    source=None,
    image_bytes_b64=None,
    sent=False,
):
    """
    Сохраняет товар со всеми данными для отложенной публикации.
    sizes - ожидается список строк, мы его склеим в строку через запятую.
    """
    now = datetime.datetime.now()
    sent_int = 1 if sent else 0

    # Конвертируем список размеров в строку для БД
    sizes_str = ""
    if sizes:
        if isinstance(sizes, list):
            sizes_str = ",".join(sizes)
        else:
            sizes_str = str(sizes)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT sent FROM deals WHERE link = ?", (link,))
        row = cursor.fetchone()

        if row is None:
            # Новая запись со всеми полями
            cursor.execute(
                """
                INSERT INTO deals (link, title, price, old_price, last_seen, sent, sizes, image_url, source, image_bytes_b64)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link,
                    title,
                    price,
                    old_price,
                    now,
                    sent_int,
                    sizes_str,
                    image_url,
                    source,
                    image_bytes_b64,
                ),
            )
        else:
            # Обновляем, включая новые поля (вдруг размеры обновились)
            cursor.execute(
                """
                UPDATE deals 
                SET title=?, price=?, old_price=?, last_seen=?, sizes=?, image_url=?, source=?, image_bytes_b64=?
                WHERE link=?
                """,
                (
                    title,
                    price,
                    old_price,
                    now,
                    sizes_str,
                    image_url,
                    source,
                    image_bytes_b64,
                    link,
                ),
            )

            if sent:
                cursor.execute("UPDATE deals SET sent=1 WHERE link=?", (link,))

        conn.commit()


def get_next_pending_deal():
    """Возвращает одну неотправленную скидку (самую старую по дате обнаружения)."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Берем неотправленные (sent=0), сортируем по last_seen (чтобы старые первыми ушли)
        cursor.execute(
            "SELECT * FROM deals WHERE sent = 0 ORDER BY last_seen ASC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def mark_deal_as_sent(link):
    """Помечает скидку как отправленную."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE deals SET sent = 1 WHERE link = ?", (link,))
        conn.commit()
