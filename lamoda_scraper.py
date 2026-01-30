"""
Lamoda Scraper using undetected-chromedriver to bypass Cloudflare protection.
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from config import LAMODA_URL


class LamodaScraper:
    """
    Scraper for Lamoda.ru using undetected-chromedriver.
    """

    def __init__(self):
        self.driver = self._get_driver()

    def _get_driver(self):
        options = uc.ChromeOptions()
        # Headless может быть заблокирован, пробуем без него
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # undetected-chromedriver автоматически скачивает подходящую версию
        # Указываем версию Chrome явно (133) для избежания несоответствия
        driver = uc.Chrome(options=options, version_main=144)
        return driver

    def close(self):
        if self.driver:
            self.driver.quit()

    def scrape(self, max_pages: int = 1) -> list:
        """
        Скрапинг страниц Lamoda.
        Возвращает список словарей с данными о товарах.
        """
        print(f"[LamodaScraper] Starting scrape from: {LAMODA_URL}")
        catalog_items = []

        try:
            # 1. Сбор ссылок и превью с каталога
            for page_num in range(1, max_pages + 1):
                url = LAMODA_URL if page_num == 1 else f"{LAMODA_URL}&page={page_num}"
                print(f"[LamodaScraper] Loading catalog page {page_num}: {url}")
                self.driver.get(url)

                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div[class*='x-product-card']")
                        )
                    )
                except Exception:
                    print(f"[LamodaScraper] Timeout on page {page_num}")
                    if "403" in self.driver.title:
                        print("[LamodaScraper] Blocked!")
                        break
                    continue

                time.sleep(2)

                product_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='x-product-card__card']"
                )
                print(
                    f"[LamodaScraper] Found {len(product_cards)} items on page {page_num}"
                )

                for card in product_cards:
                    item = self._parse_catalog_item(card)
                    if item:
                        catalog_items.append(item)

                if not product_cards:
                    break

            print(
                f"[LamodaScraper] Total catalog items collected: {len(catalog_items)}"
            )

            # 2. Обогащение данными (Размеры) - заход на страницы
            # Ограничим количество, чтобы не ждать вечность при тесте
            # Но в реальном режиме сканируем все.
            # Если это cron (max_pages=1 или 2), то нормально пройтись по 60-120 товарам.

            enriched_deals = []
            for i, item in enumerate(catalog_items, 1):
                print(
                    f"[LamodaScraper] Processing {i}/{len(catalog_items)}: {item['title'][:30]}..."
                )
                try:
                    self.driver.get(item["link"])
                    time.sleep(1.5)  # Пауза чтобы не заблокировали

                    sizes = self._extract_sizes()
                    item["sizes"] = sizes

                    enriched_deals.append(item)

                except Exception as e:
                    print(
                        f"[LamodaScraper] Error processing product {item['link']}: {e}"
                    )
                    # Если ошибка соединения (драйвер упал), пробуем перезапустить
                    if (
                        "Connection refused" in str(e)
                        or "10061" in str(e)
                        or "disconnected" in str(e)
                    ):
                        print("[LamodaScraper] Driver died! Restarting...")
                        try:
                            self.close()
                            self.driver = self._get_driver()
                            print("[LamodaScraper] Driver restarted successfully.")
                        except Exception as restart_error:
                            print(
                                f"[LamodaScraper] Failed to restart driver: {restart_error}"
                            )
                            break  # Если не смогли перезапустить, выходим

                    # Добавляем как есть, хотя бы с пустыми размерами
                    enriched_deals.append(item)

            return enriched_deals

        except Exception as e:
            print(f"[LamodaScraper] Critical error: {e}")
            return catalog_items

    # Список брендов для фильтрации
    TARGET_BRANDS = {
        "reebok",
        "nike",
        "puma",
        "diadora",
        "new balance",
        "converse",
        "adidas",
        "adidas originals",
        "adidas y-3",
        "adidas yeezy",
        "asics",
        "dc shoes",
        "element",
        "jordan",
        "karhu",
        "lacoste",
        "saucony",
        "vans",
    }

    def _parse_catalog_item(self, card) -> dict:
        """Парсинг превью карточки (без размеров)."""
        try:
            title_elem = card.find_element(
                By.CSS_SELECTOR, "div.x-product-card-description__product-name"
            )
            brand_elem = card.find_element(
                By.CSS_SELECTOR, "div.x-product-card-description__brand-name"
            )
            brand = brand_elem.text.strip() if brand_elem else ""

            # Фильтрация по бренду
            if brand.lower() not in self.TARGET_BRANDS:
                return None

            model = title_elem.text.strip() if title_elem else ""
            title = f"{brand} {model}".strip()

            link_elem = card.find_element(By.CSS_SELECTOR, "a.x-product-card__pic")
            link = link_elem.get_attribute("href") if link_elem else None

            # Цены
            try:
                price_elem = card.find_element(
                    By.CSS_SELECTOR, "span.x-product-card-description__price-new"
                )
                price_text = price_elem.text.strip()
            except Exception:
                try:
                    price_elem = card.find_element(
                        By.CSS_SELECTOR, "span.x-product-card-description__price-single"
                    )
                    price_text = price_elem.text.strip()
                except Exception:
                    return None

            try:
                old_price_elem = card.find_element(
                    By.CSS_SELECTOR, "span.x-product-card-description__price-old"
                )
                old_price_text = old_price_elem.text.strip()
            except Exception:
                old_price_text = "N/A"

            try:
                discount_elem = card.find_element(
                    By.CSS_SELECTOR, "span.ui-product-custom-badge-title"
                )
                discount_text = discount_elem.text.strip()
            except Exception:
                discount_text = ""

            # Изображение
            try:
                img_elem = card.find_element(
                    By.CSS_SELECTOR, "img[class*='x-product-card__pic-img']"
                )
                image_done = img_elem.get_attribute("src")
                if image_done:
                    # Replace any resolution (e.g. img236x341) with img600x866
                    image_url = re.sub(r"img\d+x\d+", "img600x866", image_done)
                else:
                    image_url = None
            except Exception:
                image_url = None

            if not title or not link:
                return None

            return {
                "title": title,
                "price": price_text,
                "old_price": old_price_text,
                "discount": discount_text,
                "link": link,
                "image_url": image_url,
                "sizes": [],  # Пока пусто
                "source": "Lamoda",
            }
        except Exception:
            return None

    def _extract_sizes(self) -> list:
        """Извлечение размеров со страницы товара."""
        sizes = []
        try:
            # Селектор контейнера размера
            # <div class="ui-product-page-sizes-chooser-item ...">
            #   <div class="...">35 RUS</div>
            #   <div class="...">36 EUR</div>
            # </div>

            # Wait for sizes to load
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div[class*='ui-product-page-sizes-chooser-item']",
                        )
                    )
                )
            except Exception:
                print("DEBUG: Timeout waiting for size elements.")

            size_elems = self.driver.find_elements(
                By.CSS_SELECTOR, "div[class*='ui-product-page-sizes-chooser-item']"
            )

            for elem in size_elems:
                class_attr = elem.get_attribute("class")
                if "disabled" in class_attr.lower() or "colspanDisabled" in class_attr:
                    continue

                text_content = elem.get_attribute("textContent").strip()

                # Regex for "38 EUR", "38.5 EUR", "38,5 EUR"
                # Looking for digits, maybe comma/dot, then space EUR
                eur_match = re.search(r"(\d+(?:[.,]\d+)?)\s*EUR", text_content)
                if eur_match:
                    # Found EUR size
                    eur_size = eur_match.group(1)
                    sizes.append(f"EU {eur_size}")
                else:
                    # Fallback to RUS
                    rus_match = re.search(
                        r"(\d+(?:[.,]\d+)?)\s*RUS", text_content, re.IGNORECASE
                    )
                    if rus_match:
                        rus_size = rus_match.group(1)
                        sizes.append(f"{rus_size} RUS")
                    elif text_content:
                        # Just take whatever text if no pattern matches, but clean it
                        sizes.append(text_content.replace("\n", " ").strip())

            return sizes
        except Exception as e:
            print(f"Size extraction error: {e}")
            return []


def get_lamoda_discounts(max_pages=1):
    """
    Обертка для обратной совместимости с main.py.
    """
    scraper = None
    try:
        scraper = LamodaScraper()
        return scraper.scrape(max_pages=max_pages)
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    import sys

    # Win32 UTF-8 fix
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 50)
    print("Testing LamodaScraper")
    print("=" * 50)

    items = get_lamoda_discounts(max_pages=1)

    print(f"\nTotal items found: {len(items)}")
    print("\nResult Sample (First 3 items):")
    print("-" * 50)
    for i, item in enumerate(items[:3], 1):
        print(f"{i}. [{item['source']}] {item['title']}")
        print(
            f"   Price: {item['price']} (Old: {item['old_price']}) {item['discount']}"
        )
        print(f"   Link: {item['link']}")
