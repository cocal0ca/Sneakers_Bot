from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from config import TARGET_URL
from selenium.webdriver.support.ui import WebDriverWait
from utils import has_valid_size


def get_driver():
    options = Options()
    options.add_argument("--headless=new")  # Раскомментировать для продакшена

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # Инициализация драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def get_discounts(max_pages=3):
    """
    Парсит кроссовки с Brandshop.
    Извлекает данные из Nuxt.js state (window.__NUXT__).

    Args:
        max_pages: Максимальное количество страниц для парсинга (по умолчанию 3)
    """
    print(f"Запускаю браузер для: {TARGET_URL}")
    driver = None
    deals = []

    try:
        driver = get_driver()

        for page_num in range(1, max_pages + 1):
            # Формируем URL с пагинацией
            if page_num == 1:
                url = TARGET_URL
            else:
                url = f"{TARGET_URL}?page={page_num}"

            print(f"Загружаю страницу {page_num}: {url}")
            driver.get(url)

            # Ждем появления данных (умное ожидание вместо sleep)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return window.__NUXT__ !== undefined")
                )
            except Exception:
                print(f"Таймаут ожидания данных на странице {page_num}")

            # Извлекаем данные из Nuxt state
            try:
                items_data = driver.execute_script(
                    "return window.__NUXT__ && window.__NUXT__.data && window.__NUXT__.data[0] ? window.__NUXT__.data[0].catalogProducts : null"
                )
            except Exception as e:
                print(f"Ошибка при извлечении данных со страницы {page_num}: {e}")
                continue

            if not items_data:
                print(f"Страница {page_num}: Товары не найдены, завершаем парсинг")
                break

            print(f"Страница {page_num}: Найдено {len(items_data)} товаров")

            for item in items_data:
                try:
                    # Извлекаем данные о товаре
                    brand = item.get("title", "")

                    # Формируем короткое название: Бренд + Модель
                    # Модель часто находится в subtitles[1]
                    subtitles = item.get("subtitles", [])
                    model = ""
                    if len(subtitles) > 1:
                        # Обычно subtitles[0] это "Кроссовки", а subtitles[1] это модель
                        model = subtitles[1].get("subtitle", "")

                    if model:
                        title = f"{brand} {model}".strip()
                    else:
                        # Fallback на полное имя, если структуру поменяли
                        full_name = item.get("fullName", "")
                        title = f"{brand} {full_name}".strip()

                    # Цены
                    price_info = item.get("price", {})
                    current_price = price_info.get("newAmount") or price_info.get(
                        "amount"
                    )
                    old_price = (
                        price_info.get("amount")
                        if price_info.get("newAmount")
                        else None
                    )

                    # Скидка
                    is_discount = item.get("isDiscount", False)
                    discount = price_info.get("discount", "")

                    # Ссылка на товар
                    url_part = item.get("url", "")

                    # Изображение товара
                    product_img = item.get("productImg", [])
                    image_url = None
                    if product_img and len(product_img) > 0:
                        # Берем первое изображение в высоком качестве (retina popup)
                        image_url = product_img[0].get("retina", {}).get("popup", "")

                    if not title or not current_price or not url_part:
                        continue

                    link = f"https://brandshop.ru{url_part}"

                    # Размеры
                    sizes_data = item.get("sizes", {}).get("size", [])
                    sizes_list = []
                    if sizes_data:
                        for s in sizes_data:
                            s_name = s.get("name", "")
                            # Обычно формат "41 EU", "42 EU" и т.д.
                            if s_name:
                                sizes_list.append(s_name)

                    # Фильтрация по размеру (только если есть 41+)
                    if not has_valid_size(sizes_list):
                        # Debug
                        # print(f"Пропускаем {title} (размеры: {sizes_list})")
                        continue

                    # Форматируем цены
                    price_text = f"{int(current_price):,} ₽".replace(",", " ")
                    old_price_text = (
                        f"{int(old_price):,} ₽".replace(",", " ")
                        if old_price
                        else "N/A"
                    )
                    discount_text = f"-{discount}%" if discount else ""

                    deals.append(
                        {
                            "title": title,
                            "price": price_text,
                            "old_price": old_price_text,
                            "discount": discount_text,
                            "link": link,
                            "is_discount": is_discount,
                            "image_url": image_url,
                            "sizes": sizes_list,
                        }
                    )

                except Exception as e:
                    print(f"Ошибка при обработке товара: {e}")
                    continue

    except Exception as e:
        print(f"Критическая ошибка Selenium: {e}")
    finally:
        if driver:
            driver.quit()

    print(f"Всего найдено товаров: {len(deals)}")
    return deals


if __name__ == "__main__":
    import sys

    # Устанавливаем UTF-8 для вывода в консоль
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 50)
    print("Тестовый запуск парсера Brandshop")
    print("=" * 50)

    items = get_discounts(max_pages=1)  # Для теста парсим только 1 страницу

    print("\nПримеры найденных товаров (первые 5):")
    print("-" * 50)

    for i, item in enumerate(items[:5], 1):
        print(f"\n{i}. {item['title']}")
        print(f"   Цена: {item['price']}", end="")
        if item["old_price"] != "N/A":
            print(f" (было {item['old_price']}) {item['discount']}")
        else:
            print()
        print(f"   Ссылка: {item['link']}")
        if item.get("image_url"):
            print(f"   Фото: {item['image_url']}")
        else:
            print("   Фото: не найдено")

        if item.get("sizes"):
            print(f"   Размеры: {', '.join(item['sizes'])}")
