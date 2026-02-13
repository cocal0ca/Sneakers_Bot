from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait

from config import TARGET_URL
from utils import has_valid_size


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    Handles browser initialization and common cleanup.
    """

    def __init__(self):
        self.driver = self._get_driver()

    def _get_driver(self):
        options = Options()
        options.add_argument("--headless=new")  # Recommended for production
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def close(self):
        if self.driver:
            self.driver.quit()

    @abstractmethod
    def scrape(self, max_pages: int = 3) -> list:
        """
        Main scrapping method.
        Must return a list of dictionaries with standardized keys:
        - title, price, old_price, discount, link, image_url, sizes, source
        """
        pass


class BrandshopScraper(BaseScraper):
    """
    Scraper implementation for Brandshop.ru using Nuxt.js state extraction.
    """

    def scrape(self, max_pages: int = 3) -> list:
        print(f"[{self.__class__.__name__}] Starting scrape for {TARGET_URL}")
        deals = []

        try:
            for page_num in range(1, max_pages + 1):
                # Construct URL
                url = TARGET_URL if page_num == 1 else f"{TARGET_URL}?page={page_num}"
                print(f"[{self.__class__.__name__}] Loading page {page_num}: {url}")

                self.driver.get(url)

                # Wait for Nuxt state
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda d: d.execute_script(
                            "return window.__NUXT__ !== undefined"
                        )
                    )
                except Exception:
                    print(
                        f"[{self.__class__.__name__}] Timeout waiting for data on page {page_num}"
                    )
                    continue

                # Extract data
                try:
                    items_data = self.driver.execute_script(
                        "return window.__NUXT__ && window.__NUXT__.data && window.__NUXT__.data[0] ? window.__NUXT__.data[0].catalogProducts : null"
                    )
                except Exception as e:
                    print(
                        f"[{self.__class__.__name__}] Error extracting data on page {page_num}: {e}"
                    )
                    continue

                if not items_data:
                    print(
                        f"[{self.__class__.__name__}] No items found on page {page_num}, stopping."
                    )
                    break

                print(
                    f"[{self.__class__.__name__}] Found {len(items_data)} raw items on page {page_num}"
                )

                for item in items_data:
                    try:
                        parsed_item = self._parse_item(item)
                        if parsed_item:
                            deals.append(parsed_item)
                    except Exception as e:
                        print(f"[{self.__class__.__name__}] Error parsing item: {e}")
                        continue

        except Exception as e:
            print(f"[{self.__class__.__name__}] Critical Selenium Error: {e}")

        return deals

    def _parse_item(self, item: dict) -> dict:
        """Helper to parse a single raw item dictionary."""
        brand = item.get("title", "")

        # Determine model name
        subtitles = item.get("subtitles", [])
        model = ""
        if len(subtitles) > 1:
            model = subtitles[1].get("subtitle", "")

        if model:
            title = f"{brand} {model}".strip()
        else:
            full_name = item.get("fullName", "")
            title = f"{brand} {full_name}".strip()

        # Prices
        price_info = item.get("price", {})
        current_price = price_info.get("newAmount") or price_info.get("amount")
        old_price = price_info.get("amount") if price_info.get("newAmount") else None

        discount = price_info.get("discount", "")
        url_part = item.get("url", "")

        # Image
        product_img = item.get("productImg", [])
        image_url = None
        if product_img and len(product_img) > 0:
            image_url = product_img[0].get("retina", {}).get("popup", "")

        # Validation
        if not title or not current_price or not url_part:
            return None

        link = f"https://brandshop.ru{url_part}"

        # Sizes
        sizes_data = item.get("sizes", {}).get("size", [])
        sizes_list = [s.get("name", "") for s in sizes_data if s.get("name")]

        # Filter sizes
        if not has_valid_size(sizes_list):
            return None

        # Formatting
        price_text = f"{int(current_price):,} ₽".replace(",", " ")
        old_price_text = (
            f"{int(old_price):,} ₽".replace(",", " ") if old_price else "N/A"
        )
        discount_text = f"-{discount}%" if discount else ""

        return {
            "title": title,
            "price": price_text,
            "old_price": old_price_text,
            "discount": discount_text,
            "link": link,
            "is_discount": item.get("isDiscount", False),
            "image_url": image_url,
            "sizes": sizes_list,
            "source": "Brandshop",
        }


def get_discounts(max_pages=3):
    """
    Wrapper function to maintain backward compatibility with main.py.
    Instantiates the scraper, runs it, and ensures cleanup.
    """
    scraper = None
    try:
        scraper = BrandshopScraper()
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
    print("Testing BrandshopScraper Class")
    print("=" * 50)

    # Use the wrapper to test everything end-to-end
    items = get_discounts(max_pages=1)

    print("\nResult Sample (First 3 items):")
    print("-" * 50)
    for i, item in enumerate(items[:3], 1):
        print(
            f"{i}. [{item['source']}] {item['title']} | {item['price']} (Old: {item['old_price']})"
        )
        print(f"   Link: {item['link']}")
        print(f"   Sizes: {item['sizes']}")
