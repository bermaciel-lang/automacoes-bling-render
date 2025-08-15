import os
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# -------- util de debug (pedida pelos seus scripts) --------
def dump_debug(driver, prefix: str = "DEBUG"):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"/tmp/{prefix}_{ts}"
    png = f"{base}.png"
    html = f"{base}.html"
    try:
        driver.save_screenshot(png)
    except Exception:
        pass
    try:
        with open(html, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception:
        pass
    return png, html

# -------- Cloudflare --------
def wait_cf_challenge(driver, max_wait=90):
    """
    Espera e tenta passar pelo "Just a moment..." do Cloudflare.
    Retorna True se a página deixar de exibir o desafio.
    """
    start = time.time()
    last_url = None

    while time.time() - start < max_wait:
        html = driver.page_source.lower()
        url = driver.current_url

        bloqueado = (
            "just a moment" in html
            or "verify you are human" in html
            or "cloudflare" in html
            or "verifique que você é humano" in html
            or "turnstile" in html
        )

        # saiu do desafio?
        if not bloqueado:
            return True

        # às vezes o CF coloca o botão "Verify"/"Verificar"
        for xp in [
            "//button[contains(., 'Verify') or contains(., 'Verificar') or contains(., 'Sou humano')]",
            "//input[@type='submit' and (contains(@value,'Verify') or contains(@value,'Verificar'))]",
            "//div[@id='challenge-stage']//button",
        ]:
            try:
                el = driver.find_element(By.XPATH, xp)
                el.click()
                time.sleep(2)
                break
            except Exception:
                pass

        # alguns desafios ficam em iframe
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for ifr in iframes:
                title = (ifr.get_attribute("title") or "").lower()
                src = (ifr.get_attribute("src") or "").lower()
                if "challenge" in title or "turnstile" in title or "cf-chl" in src:
                    driver.switch_to.frame(ifr)
                    # tenta clicar qualquer botão dentro
                    try:
                        btns = driver.find_elements(By.TAG_NAME, "button")
                        if btns:
                            btns[0].click()
                            time.sleep(2)
                    except Exception:
                        pass
                    driver.switch_to.default_content()
                    break
        except Exception:
            pass

        # Se a URL mudou, dá uma chance extra
        if last_url != url:
            last_url = url
            time.sleep(2)
            continue

        time.sleep(2)

    return False

# -------- Login “inteligente” no Bling --------
def smart_login(driver, email, senha, wait_seconds=40):
    driver.get("https://www.bling.com.br/login")
    w = WebDriverWait(driver, wait_seconds)

    # 1) Cloudflare
    if not wait_cf_challenge(driver, max_wait=90):
        png, html = dump_debug(driver, "CF_BLOCKED")
        raise TimeoutException(
            f"Bloqueado pelo Cloudflare. Debug salvo: {png} / {html}"
        )

    # 2) alguns logins vêm dentro de iframe
    try:
        ifr = driver.find_element(By.CSS_SELECTOR, "iframe")
        driver.switch_to.frame(ifr)
    except Exception:
        pass

    # 3) usuário
    user_locators = [
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input#login"),
        (By.CSS_SELECTOR, "input[name='username']"),
        (By.CSS_SELECTOR, "input#username"),
        (By.XPATH, "//input[contains(@placeholder,'e-mail') or contains(@placeholder,'email')]"),
    ]
    field_user = None
    for how, sel in user_locators:
        try:
            field_user = w.until(EC.visibility_of_element_located((how, sel)))
            if field_user:
                break
        except TimeoutException:
            continue
    if not field_user:
        png, html = dump_debug(driver, "LOGIN_NO_USER")
        raise TimeoutException("Campo de usuário não encontrado em nenhum seletor")

    field_user.clear()
    field_user.send_keys(email)

    # 4) Avançar / enviar
    for xp in [
        "//button[@type='submit']",
        "//button[contains(., 'Entrar')]",
        "//button[contains(., 'Continuar')]",
        "//button[contains(., 'Acessar')]",
    ]:
        try:
            driver.find_element(By.XPATH, xp).click()
            time.sleep(1)
            break
        except Exception:
            pass

    # 5) senha
    field_pass = None
    for how, sel in [
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.CSS_SELECTOR, "input#password"),
        (By.CSS_SELECTOR, "input[name='password']"),
    ]:
        try:
            field_pass = w.until(EC.visibility_of_element_located((how, sel)))
            if field_pass:
                break
        except TimeoutException:
            continue
    if not field_pass:
        png, html = dump_debug(driver, "LOGIN_NO_PASS")
        raise TimeoutException("Campo de senha não encontrado em nenhum seletor")

    field_pass.clear()
    field_pass.send_keys(senha)

    # 6) enviar
    for xp in [
        "//button[@type='submit']",
        "//button[contains(., 'Entrar')]",
        "//button[contains(., 'Acessar')]",
    ]:
        try:
            driver.find_element(By.XPATH, xp).click()
            break
        except Exception:
            pass

    # 7) pós-login (melhor esforço)
    try:
        w.until(EC.any_of(
            EC.url_contains("/home"),
            EC.url_contains("/dashboard"),
            EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Bem-vindo') or contains(., 'Início')]")),
        ))
    except TimeoutException:
        # deixa o caller decidir se considera ok
        pass
