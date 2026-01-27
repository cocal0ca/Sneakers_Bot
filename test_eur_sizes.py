from lamoda_scraper import LamodaScraper
import sys

# Win32 UTF-8 fix
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def test_eur_parsing():
    scraper = LamodaScraper()
    # URL из дампа, где точно есть таблица размеров с EUR
    url = "https://www.lamoda.ru/p/mp002xw0oxsc/shoes-sprox-kedy/"

    print(f"Testing URL: {url}")

    try:
        scraper.driver.get(url)
        sizes = scraper._extract_sizes()
        print("Extracted sizes:", sizes)

        # Check if we have EU sizes
        has_eu = any("EU" in s for s in sizes)
        if has_eu:
            print("SUCCESS: Found EU sizes!")
        else:
            print(
                "WARNING: No EU sizes found (maybe only RUS available or parsing failed)."
            )

    except Exception as e:
        print(f"Error: {e}")
    finally:
        scraper.close()


if __name__ == "__main__":
    test_eur_parsing()
