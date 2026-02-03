import time
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from playwright_stealth import Stealth
from config import LAMODA_URL


class LamodaScraperPW:
    """
    Playwright-based scraper for Lamoda.ru.
    """

    def __init__(self):
        # Playwright manages its own browser instance lifecycle in the context manager usually,
        # but here we might want to wrap it in a class.
        pass

    def scrape(self, max_pages: int = 1) -> List[Dict]:
        print(f"[LamodaScraperPW] Starting scrape from: {LAMODA_URL}")
        deals = []

        with sync_playwright() as p:
            # Launch browser
            # headless=False is good for debugging, but for production use True
            # Timeweb might need headless=True
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--start-maximized",
                ],
            )

            # Create context with stealth
            # Note: stealth is applied to page or context
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="ru-RU",
            )

            page = context.new_page()

            # Additional script to hide webdriver
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Apply stealth
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

            try:
                # 1. Collect items from catalog
                catalog_items = []
                for page_num in range(1, max_pages + 1):
                    url = (
                        LAMODA_URL if page_num == 1 else f"{LAMODA_URL}&page={page_num}"
                    )
                    print(f"[LamodaScraperPW] Loading catalog page {page_num}: {url}")

                    try:
                        page.goto(url, timeout=60000, wait_until="domcontentloaded")

                        # Debug: Check webdriver property
                        is_webdriver = page.evaluate("navigator.webdriver")
                        print(f"[LamodaScraperPW] navigator.webdriver = {is_webdriver}")

                        # Wait for cards
                        page.wait_for_selector(
                            "div[class*='x-product-card__card']", timeout=15000
                        )
                    except Exception as e:
                        print(
                            f"[LamodaScraperPW] Timeout or error loading page {page_num}: {e}"
                        )

                        # Debug: Save screenshot and HTML
                        page.screenshot(path=f"debug_lamoda_pw_page_{page_num}.png")
                        with open(
                            f"debug_lamoda_pw_page_{page_num}.html",
                            "w",
                            encoding="utf-8",
                        ) as f:
                            f.write(page.content())

                        if "403" in page.title():
                            print("[LamodaScraperPW] 403 Forbidden detected!")
                            break
                        continue

                    # Scroll to load lazy images? Lamoda uses infinite scroll sometimes but pagination is present.
                    # Just in case, scroll a bit.
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    time.sleep(1)

                    cards = page.query_selector_all(
                        "div[class*='x-product-card__card']"
                    )
                    print(
                        f"[LamodaScraperPW] Found {len(cards)} items on page {page_num}"
                    )

                    for card in cards:
                        item = self._parse_catalog_item(card)
                        if item:
                            catalog_items.append(item)

                    if not cards:
                        break

                print(
                    f"[LamodaScraperPW] Total catalog items collected: {len(catalog_items)}"
                )

                # 2. Enrich with sizes
                enriched_deals = []
                for i, item in enumerate(catalog_items, 1):
                    print(
                        f"[LamodaScraperPW] Processing {i}/{len(catalog_items)}: {item['title'][:30]}..."
                    )
                    try:
                        page.goto(
                            item["link"], timeout=45000, wait_until="domcontentloaded"
                        )

                        # Wait a bit for sizes to initialize
                        try:
                            page.wait_for_selector(
                                "div[class*='ui-product-page-sizes-chooser-item']",
                                timeout=5000,
                            )
                        except PlaywrightTimeoutError:
                            pass

                        sizes = self._extract_sizes(page)
                        item["sizes"] = sizes
                        enriched_deals.append(item)

                        # Polite delay
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"[LamodaScraperPW] Error processing {item['link']}: {e}")
                        enriched_deals.append(item)

                deals = enriched_deals

            except Exception as e:
                print(f"[LamodaScraperPW] Critical error: {e}")
            finally:
                browser.close()

        return deals

    def _parse_catalog_item(self, card_handle) -> Optional[Dict]:
        try:
            # We need to query inside the card handle
            # Brand
            brand_el = card_handle.query_selector(
                "div.x-product-card-description__brand-name"
            )
            brand = brand_el.inner_text().strip() if brand_el else ""

            # Filter (same logic as before)
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
            if brand.lower() not in TARGET_BRANDS:
                return None

            # Name
            name_el = card_handle.query_selector(
                "div.x-product-card-description__product-name"
            )
            model = name_el.inner_text().strip() if name_el else ""
            title = f"{brand} {model}".strip()

            # Link
            link_el = card_handle.query_selector("a.x-product-card__pic")
            link = (
                f"https://www.lamoda.ru{link_el.get_attribute('href')}"
                if link_el
                else ""
            )

            # Price
            price_el = card_handle.query_selector(
                "span.x-product-card-description__price-new"
            )
            if not price_el:
                price_el = card_handle.query_selector(
                    "span.x-product-card-description__price-single"
                )

            price_text = price_el.inner_text().strip() if price_el else ""

            # Old Price
            old_price_el = card_handle.query_selector(
                "span.x-product-card-description__price-old"
            )
            old_price_text = (
                old_price_el.inner_text().strip() if old_price_el else "N/A"
            )

            # Discount
            # Not critical, can skip or try to find badge
            discount_text = ""

            # Image
            img_el = card_handle.query_selector("img[class*='x-product-card__pic-img']")
            image_url = ""
            if img_el:
                src = img_el.get_attribute("src")
                # Fix resolution
                if src:
                    image_url = re.sub(r"img\d+x\d+", "img600x866", src)
                    if src.startswith("//"):
                        image_url = "https:" + image_url

            if not title or not link:
                return None

            return {
                "title": title,
                "price": price_text,
                "old_price": old_price_text,
                "discount": discount_text,
                "link": link,
                "image_url": image_url,
                "sizes": [],
                "source": "Lamoda",
            }

        except Exception:
            return None

    def _extract_sizes(self, page) -> List[str]:
        sizes = []
        try:
            # Select all size elements
            size_elems = page.query_selector_all(
                "div[class*='ui-product-page-sizes-chooser-item']"
            )

            for elem in size_elems:
                class_attr = elem.get_attribute("class") or ""
                if "disabled" in class_attr.lower() or "colspanDisabled" in class_attr:
                    continue

                text = elem.inner_text().strip()

                # Logic from old scraper
                eur_match = re.search(r"(\d+(?:[.,]\d+)?)\s*EUR", text)
                if eur_match:
                    sizes.append(f"EU {eur_match.group(1)}")
                else:
                    rus_match = re.search(
                        r"(\d+(?:[.,]\d+)?)\s*RUS", text, re.IGNORECASE
                    )
                    if rus_match:
                        sizes.append(f"{rus_match.group(1)} RUS")
                    else:
                        sizes.append(text.replace("\n", " "))

            return sizes
        except Exception as e:
            print(f"Size extraction error: {e}")
            return []


def get_lamoda_discounts(max_pages=1):
    scraper = LamodaScraperPW()
    return scraper.scrape(max_pages)


if __name__ == "__main__":
    # Test run
    items = get_lamoda_discounts(max_pages=1)
    print(f"Found {len(items)} items.")
    for item in items[:3]:
        print(item)
