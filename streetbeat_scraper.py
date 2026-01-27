import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from typing import List, Dict, Optional

# Constants
STREETBEAT_URL = "https://street-beat.ru/cat/man/krossovki/sale/"


class StreetBeatScraper:
    """
    Парсер для сайта street-beat.ru.
    Использует undetected_chromedriver для обхода защиты.
    """

    def __init__(self):
        self.driver = self._get_driver()

    def _get_driver(self):
        options = uc.ChromeOptions()
        # Headless режим может быть определен Cloudflare, но попробуем с ним или без
        # options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Важно: версия должна совпадать или быть близкой к установленной
        driver = uc.Chrome(options=options, version_main=133)
        return driver

    def close(self):
        if self.driver:
            self.driver.quit()

    def scrape(self, max_pages: int = 1) -> List[Dict]:
        """
        Основной метод парсинга.
        :param max_pages: Количество страниц для (пока скролл, но оставим параметр)
        :return: Список словарей с данными о товарах
        """
        print(f"[StreetBeatScraper] Запуск парсинга: {STREETBEAT_URL}")
        deals = []

        try:
            self.driver.get(STREETBEAT_URL)

            # Ждем загрузки первых карточек
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.product-card")
                    )
                )
            except Exception:
                print("[StreetBeatScraper] Тайм-аут ожидания карточек товаров.")
                return []

            # Прокрутка для ленивой загрузки (прокрутим пару раз)
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)

            # Получаем карточки товаров
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.product-card")
            print(f"[StreetBeatScraper] Найдено карточек: {len(cards)}")

            for card in cards:
                try:
                    item = self._parse_card(card)
                    if item:
                        deals.append(item)
                except Exception as e:
                    # Ошибки парсинга конкретной карты не должны ломать весь процесс
                    continue

        except Exception as e:
            print(f"[StreetBeatScraper] Критическая ошибка: {e}")
        finally:
            self.close()

        return deals

    def _parse_card(self, card) -> Optional[Dict]:
        """Парсит одну карточку товара из DOM."""
        try:
            # Название и Ссылка
            info_el = card.find_element(By.CSS_SELECTOR, ".product-card__info")
            title = info_el.text.strip()
            link = info_el.get_attribute("href")

            # Цена (новая)
            try:
                price_el = card.find_element(
                    By.CSS_SELECTOR, ".product-card__price-new"
                )
                price_text = (
                    price_el.text.strip()
                    .replace("rub.", "")
                    .replace("руб.", "")
                    .strip()
                )
            except Exception:
                # Если нет новой цены, возможно нет скидки, или другая структура
                return None

            # Старая цена
            old_price_text = None
            try:
                old_price_el = card.find_element(
                    By.CSS_SELECTOR, ".product-card__price-old"
                )
                old_price_text = (
                    old_price_el.text.strip()
                    .replace("rub.", "")
                    .replace("руб.", "")
                    .strip()
                )
            except Exception:
                pass

            # Скидка (вычисляем или ищем бейдж)
            discount = ""
            if old_price_text:
                try:
                    # Можно попробовать найти бейдж скидки
                    badge_el = card.find_element(
                        By.CSS_SELECTOR, ".product-new-badge__title"
                    )
                    discount = badge_el.text.strip()
                except Exception:
                    # Если бейджа нет, можно посчитать
                    pass

            # Размеры
            # Они находятся в скрытом блоке hover, но в DOM они есть
            sizes = []
            try:
                size_labels = card.find_elements(
                    By.CSS_SELECTOR, ".block-hover__product-size .radio__label"
                )
                # textContent allows getting text even if element is hidden (display: none)
                sizes = [
                    lbl.get_attribute("textContent").strip() for lbl in size_labels
                ]
                sizes = [s for s in sizes if s]
            except Exception:
                pass

            # Фильтрация по наличию размеров
            # Импортируем валидатор здесь или дублируем логику, чтобы не зависеть циклически
            # В данном случае просто проверим что список не пуст
            if not sizes:
                return None

            # Изображение
            image_url = None
            try:
                # Пробуем найти активное изображение
                img_el = card.find_element(
                    By.CSS_SELECTOR, ".product-card__image-active img"
                )
                image_url = img_el.get_attribute("src")

                # Если src пустой (lazy load), попробуем digitalDataCache через JS
                # Это сложно сделать для конкретного WebElement без ID
                # Поэтому пока оставим как есть, или проверим data-src
                if not image_url or "data:image" in image_url:
                    image_url = img_el.get_attribute("data-src")
            except Exception:
                pass

            return {
                "title": title,
                "price": price_text,
                "old_price": old_price_text,
                "discount": discount,
                "link": link,
                "image_url": image_url,
                "sizes": sizes,
                "source": "StreetBeat",  # Используем короткое имя для Source
            }

        except Exception:
            # print(f"Error parsing card: {e}")
            return None


def get_streetbeat_discounts(max_pages=1):
    """Обертка для вызова парсера."""
    scraper = StreetBeatScraper()
    return scraper.scrape(max_pages)


if __name__ == "__main__":
    import sys

    # Win32 UTF-8 fix
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 50)
    print("Testing StreetBeatScraper")
    print("=" * 50)

    items = get_streetbeat_discounts(max_pages=1)

    print(f"\nFound {len(items)} items:")
    for i, item in enumerate(items[:5], 1):
        print(f"{i}. [{item['source']}] {item['title']}")
        print(
            f"   Price: {item['price']} (Old: {item['old_price']}) {item['discount']}"
        )
        print(f"   Sizes: {item['sizes']}")
        print(f"   Link: {item['link']}")
        print(f"   Image: {item['image_url']}")
