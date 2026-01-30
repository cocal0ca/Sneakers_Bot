import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from typing import List, Dict, Optional
from database import deal_exists

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
        driver = uc.Chrome(options=options, version_main=144)
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

            # Прокрутка для ленивой загрузки (чтобы DOM с размерами отрендерился)
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)

            # 1. Извлекаем данные из JSON (надежно для Title, Image, Price)
            try:
                json_items = self.driver.execute_script(
                    "return window.digitalData && window.digitalData.listing ? window.digitalData.listing.items : [];"
                )
                print(
                    f"[StreetBeatScraper] Найдено элементов в JSON: {len(json_items)}"
                )
            except Exception as e:
                print(f"[StreetBeatScraper] Ошибка извлечения JSON: {e}")
                json_items = []

            # 2. Извлекаем размеры из DOM (они есть в HTML, но нет в листинге JSON)
            # Создаем карту url -> sizes
            dom_sizes_map = {}
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, "div.product-card")
                print(f"[StreetBeatScraper] Найдено карточек в DOM: {len(cards)}")

                for card in cards:
                    try:
                        # Ссылка для связывания
                        info_el = card.find_element(
                            By.CSS_SELECTOR, ".product-card__info"
                        )
                        link_href = info_el.get_attribute("href")

                        # Размеры
                        sizes = []
                        size_labels = card.find_elements(
                            By.CSS_SELECTOR, ".block-hover__product-size .radio__label"
                        )
                        sizes = [
                            lbl.get_attribute("textContent").strip()
                            for lbl in size_labels
                        ]
                        sizes = [s for s in sizes if s]

                        if link_href:
                            # Нормализуем ссылку для ключа (убираем домен если есть)
                            # href обычно абсолютный или относительный, приведем к относительному
                            rel_link = link_href.replace("https://street-beat.ru", "")
                            dom_sizes_map[rel_link] = sizes

                    except Exception:
                        continue
            except Exception as e:
                print(f"[StreetBeatScraper] Ошибка парсинга DOM размеров: {e}")

            # 3. Объединяем данные
            if not json_items:
                print(
                    "[StreetBeatScraper] JSON пуст, переходим к DOM-only парсингу (резервный механизм)"
                )
                # Тут можно оставить старую логику или просто вернуть то что удалось собрать из DOM если бы мы собирали все
                # Но лучше полагаться на JSON. Если его нет - сайт вероятно сильно изменился.
                pass

            for item in json_items:
                try:
                    product_url = item.get("url", "")
                    # Нормализация для поиска в map
                    rel_url = product_url.replace("https://street-beat.ru", "")

                    sizes = dom_sizes_map.get(rel_url, [])

                    # Если размеров нет в мапе, возможно DOM не прогрузился или структура другая.
                    # Но пробуем добавить товар, если есть размеры?
                    # Требование: "приходят сообщения ... без размеров".
                    # Если размеров нет - скипаем, как и раньше.
                    if not sizes:
                        continue

                    title = item.get("name", "")
                    price_num = item.get("unitSalePrice")
                    old_price_num = item.get("unitPrice")

                    price_text = (
                        f"{int(price_num)}".replace(",", " ") + " ₽"
                        if price_num
                        else ""
                    )

                    # Show old price only if it's strictly greater than current price
                    if old_price_num and old_price_num > price_num:
                        old_price_text = (
                            f"{int(old_price_num)}".replace(",", " ") + " ₽"
                        )
                    else:
                        old_price_text = ""

                    # Скидка
                    discount = ""
                    if price_num and old_price_num and old_price_num > price_num:
                        disc_percent = int(100 - (price_num / old_price_num * 100))
                        discount = f"-{disc_percent}%"

                    image_url = item.get("imageUrl", "")

                    deal = {
                        "title": title,
                        "price": price_text,
                        "old_price": old_price_text,
                        "discount": discount,
                        "link": product_url,
                        "image_url": image_url,
                        "sizes": sizes,
                        "source": "StreetBeat",
                    }

                    # Проверяем, новый ли это товар, и если да — скачиваем фото браузером
                    # Это нужно, так как обычные requests (process_image) блокируются (403 Forbidden)
                    if not deal_exists(product_url):
                        if image_url:
                            try:
                                script = """
                                var url = arguments[0];
                                var callback = arguments[1];
                                fetch(url)
                                    .then(response => response.blob())
                                    .then(blob => {
                                        var reader = new FileReader();
                                        reader.onload = function() {
                                            callback(reader.result);
                                        };
                                        reader.readAsDataURL(blob);
                                    })
                                    .catch(err => callback(null));
                                """
                                # execute_async_script allows passing a callback
                                b64_data = self.driver.execute_async_script(
                                    script, image_url
                                )
                                if b64_data:
                                    # Remove header if present
                                    if "," in b64_data:
                                        _, b64_data = b64_data.split(",", 1)
                                    deal["image_bytes_b64"] = b64_data
                                    print(
                                        f"[StreetBeatScraper] Скачано фото для {title}"
                                    )
                            except Exception as e:
                                print(
                                    f"[StreetBeatScraper] Ошибка скачивания фото JS: {e}"
                                )

                    deals.append(deal)

                except Exception as e:
                    # print(f"Error processing item: {e}")
                    continue

        except Exception as e:
            print(f"[StreetBeatScraper] Критическая ошибка: {e}")
        finally:
            self.close()

        return deals

    def _parse_card(self, card) -> Optional[Dict]:
        """Устаревший метод, оставлен для совместимости или если понадобится вернуть DOM парсинг."""
        pass


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
