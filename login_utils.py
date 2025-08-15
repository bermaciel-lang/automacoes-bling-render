# login_utils.py
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import base64, sys

def _try_click_overlays(driver):
    # banners comuns de cookies / modais
    candidatos = [
        "//button[contains(translate(., 'ACEITAR', 'aceitar'), 'aceitar')]",
        "//button[contains(translate(., 'OK', 'ok'), 'ok')]",
        "//button[contains(., 'Entendi')]",
        "//button[contains(., 'Prosseguir')]",
        "//div[@role='dialog']//button[1]"
    ]
    for xp in candidatos:
        try:
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xp))).click()
            break
        except Exception:
            pass

def _switch_to_iframe_if_needed(driver):
    # tenta achar o campo dentro de iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for i, f in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(f)
            # se achar um input, fica nesse frame
            if driver.find_elements(By.TAG_NAME, "input"):
                return True
        except Exception:
            continue
    driver.switch_to.default_content()
    return False

def smart_login(driver, email, password, wait_seconds=30):
    _try_click_overlays(driver)
    _switch_to_iframe_if_needed(driver)

    wait = WebDriverWait(driver, wait_seconds)

    # vários seletores possíveis para usuário e senha
    user_selectors = [
        (By.ID, "username"),
        (By.NAME, "username"),
        (By.NAME, "email"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[autocomplete='username']")
    ]
    pass_selectors = [
        (By.ID, "password"),
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.CSS_SELECTOR, "input[autocomplete='current-password']")
    ]

    user_el = None
    for sel in user_selectors:
        try:
            user_el = wait.until(EC.presence_of_element_located(sel))
            break
        except TimeoutException:
            continue

    if not user_el:
        raise TimeoutException("Campo de usuário não encontrado em nenhum seletor")

    user_el.clear()
    user_el.send_keys(email + Keys.TAB)

    pass_el = None
    for sel in pass_selectors:
        try:
            pass_el = wait.until(EC.presence_of_element_located(sel))
            break
        except TimeoutException:
            continue

    if not pass_el:
        raise TimeoutException("Campo de senha não encontrado em nenhum seletor")

    pass_el.clear()
    pass_el.send_keys(password + Keys.ENTER)

def dump_debug(driver, label="DEBUG"):
    try:
        url = driver.current_url
        title = driver.title
        body_text = driver.find_element(By.TAG_NAME, "body").text[:800]
        png_b64 = driver.get_screenshot_as_base64()
        print(f"===== {label} =====")
        print(f"URL atual: {url}")
        print(f"Título: {title}")
        print(f"Trecho do body: {body_text}")
        print(f"(Screenshot base64 iniciado) data:image/png;base64,{png_b64[:200]}... (cortado)")
        print("====================")
        sys.stdout.flush()
    except Exception as e:
        print(f"[dump_debug] falhou: {e}")
