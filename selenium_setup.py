import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def build_driver():
    chrome_path = shutil.which("chromium") or "/usr/bin/chromium"
    driver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    # Opcional: idioma
    opts.add_argument("--lang=pt-BR")
    if chrome_path:
        opts.binary_location = chrome_path

    # Selenium 4: use Service() in ideal world, but keep compatibility by passing executable_path
    driver = webdriver.Chrome(executable_path=driver_path, options=opts)
    return driver
