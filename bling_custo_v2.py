# bling_custo_v2.py
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium_setup import build_driver
from login_utils import smart_login, dump_debug

EMAIL = os.getenv("EMAIL", "")
SENHA = os.getenv("SENHA", "")
BLING_LOGIN_URL = os.getenv("BLING_LOGIN_URL", "https://www.bling.com.br/login")  # ajuste se for outro

def main():
    driver = build_driver()
    try:
        driver.get(BLING_LOGIN_URL)

        # ===== LOGIN ROBUSTO =====
        try:
            smart_login(driver, EMAIL, SENHA, wait_seconds=40)
        except Exception as e:
            print(f"❌ ERRO DETECTADO no login: {e}")
            dump_debug(driver, "LOGIN FALHOU - bling_custo_v2")
            raise

        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # ===== SEU FLUXO ORIGINAL A PARTIR DAQUI =====
        # ... resto do seu fluxo ...

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    print("🚀 Executando bling_custo_v2.py...")
    main()
