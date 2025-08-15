import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def wait_cf_challenge(driver, max_wait=90):
    """Espera e tenta acionar o desafio do Cloudflare.
       Retorna True se a página sair do “Just a moment…”, False se expirar."""
    start = time.time()
    while time.time() - start < max_wait:
        html = driver.page_source.lower()

        bloqueado = (
            "just a moment" in html or
            "verify you are human" in html or
            "cloudflare" in html or
            "verifique que você é humano" in html or
            "verificar" in html
        )
        if not bloqueado:
            return True

        # tenta clicar em botões/inputs de verificação quando existirem
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

        # dá um respiro e tenta de novo
        time.sleep(2)

    return False

def smart_login(driver, email, senha, wait_seconds=40):
    driver.get("https://www.bling.com.br/login")
    w = WebDriverWait(driver, wait_seconds)

    # 1) Cloudflare
    if not wait_cf_challenge(driver, max_wait=90):
        raise TimeoutException("Bloqueado pelo Cloudflare (não consegui passar o desafio).")

    # 2) alguns logins vêm dentro de iframe
    try:
        ifr = driver.find_element(By.CSS_SELECTOR, "iframe")
        driver.switch_to.frame(ifr)
    except Exception:
        pass

    # 3) usuário
    locators_user = [
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input#login"),
        (By.CSS_SELECTOR, "input[name='username']"),
        (By.CSS_SELECTOR, "input#username"),
        (By.XPATH, "//input[contains(@placeholder,'e-mail') or contains(@placeholder,'email')]"),
    ]
    field_user = None
    for how, sel in locators_user:
        try:
            field_user = w.until(EC.visibility_of_element_located((how, sel)))
            if field_user:
                break
        except TimeoutException:
            continue
    if not field_user:
        raise TimeoutException("Campo de usuário não encontrado em nenhum seletor")
    field_user.clear(); field_user.send_keys(email)

    # 4) Avançar/enviar
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
        raise TimeoutException("Campo de senha não encontrado em nenhum seletor")
    field_pass.clear(); field_pass.send_keys(senha)

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
