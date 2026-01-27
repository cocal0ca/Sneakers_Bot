import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time


def inspect_streetbeat():
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = uc.Chrome(options=options, version_main=133)

    # URL for Men's Sneakers Sale
    # Based on common patterns and search: /cat/man/krossovki/sale/ or similar
    # Let's try the likely one: https://street-beat.ru/cat/man/krossovki/sale/
    url = "https://street-beat.ru/cat/man/krossovki/sale/"

    print(f"Inspecting URL: {url}")

    try:
        driver.get(url)
        time.sleep(10)  # Wait for potential JS load and respect delay lightly

        print(f"Page Title: {driver.title}")

        # Save HTML for review
        with open("streetbeat_dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved streetbeat_dump.html")

        # Try to find product cards
        # Typical classes might be 'catalog-item', 'product-card', etc.
        # Let's look for common tags
        cards = driver.find_elements(By.CSS_SELECTOR, "div.catalog-item")
        if not cards:
            cards = driver.find_elements(By.CSS_SELECTOR, "div[data-product-id]")

        print(f"Found {len(cards)} potential product cards")

        if cards:
            card = cards[0]
            print("\n--- First Card Analysis ---")
            print(f"Outer HTML (truncated): {card.get_attribute('outerHTML')[:500]}")
            print(f"Text: {card.text}")

            # Try to find specific elements within the card
            try:
                # Link
                link_el = card.find_element(By.TAG_NAME, "a")
                print(f"Link: {link_el.get_attribute('href')}")
            except:
                print("Link not found")

            try:
                # Image
                img_el = card.find_element(By.TAG_NAME, "img")
                print(f"Image Src: {img_el.get_attribute('src')}")
            except:
                print("Image not found")

            try:
                # Price
                # Usually has a class like 'catalog-item__price' or similar
                price_el = card.find_element(By.CSS_SELECTOR, "[class*='price']")
                print(f"Price Text: {price_el.text}")
            except:
                print("Price not found")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    inspect_streetbeat()
