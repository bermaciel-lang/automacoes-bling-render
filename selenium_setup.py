# selenium_setup.py
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def build_driver():
    opts = Options()
    # usa o Chromium instalado via apt
    opts.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    # flags para rodar no container
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    # usa o chromedriver do pacote chromium-driver
    driver_path = os.environ.get("CHROMEDRIVER", "/usr/bin/chromedriver")
    service = Service(driver_path)

    driver = webdriver.Chrome(service=service, options=opts)
    return driver
