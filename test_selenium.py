from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

try:
    print("Initializing standard Chrome driver...")
    options = Options()
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    print("Driver initialized. Navigating...")

    driver.get("https://www.google.com")
    print(f"Title: {driver.title}")

    time.sleep(5)
    driver.quit()
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
