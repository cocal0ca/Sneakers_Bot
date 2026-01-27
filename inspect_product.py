"""
Script to inspect a single Lamoda product page for sizes.
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time


def inspect_product():
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = uc.Chrome(options=options, version_main=133)

    # URL of a product (sneakers)
    test_url = "https://www.lamoda.ru/p/mp002xw0oxsc/shoes-sprox-kedy/"
    print(f"Inspecting product: {test_url}")

    try:
        driver.get(test_url)
        time.sleep(5)

        # 1. Try CSS selectors for sizes
        # Usually looking for something like "ui-product-page-sizes-chooser-item" or text matching regex
        try:
            # Common selector for size buttons
            # Inspecting common classes seen in Lamoda before: 'x-product-sizes__count', 'ui-product-page-sizes-chooser-item'
            size_elems = driver.find_elements(
                By.CSS_SELECTOR, "div[class*='ui-product-page-sizes-chooser-item']"
            )
            if not size_elems:
                # Try another common pattern for size blocks
                size_elems = driver.find_elements(
                    By.CSS_SELECTOR, "div.x-product-sizes__item"
                )

            print(f"Found {len(size_elems)} size elements via CSS")
            for i, elem in enumerate(size_elems):
                text = elem.text.strip()

                # Clean text for display
                text_clean = text.replace(" RUS", "").strip()
                inner_text_content = (
                    elem.get_attribute("textContent").strip().replace(" RUS", "")
                )

                print(f"Size {i} Text: '{text_clean}' (Raw: '{text}')")
                print(f"Size {i} Value: '{inner_text_content}'")
                # print(f"Size {i} Inner: {inner[:100]}...")

        except Exception as e:
            print(f"CSS Error: {e}")

        # 2. Try JSON State (Nuxt/Next)
        try:
            # Check for __NUXT__ or generic script tags with JSON
            scripts = driver.find_elements(By.TAG_NAME, "script")
            for script in scripts:
                content = script.get_attribute("innerHTML")
                if "payload" in content and "sizes" in content:
                    print("Found potential JSON payload script!")
                    # It's usually huge, so let's try to extract a snippet
                    idx = content.find("sizes")
                    print(f"Snippet: {content[idx : idx + 200]}")

        except Exception as e:
            print(f"JSON Error: {e}")

        # Save HTML
        with open("product_page_dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved product_page_dump.html")

    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    inspect_product()
