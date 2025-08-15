import os

# tentamos usar undetected-chromedriver, mas caímos no Selenium "normal" se não houver
try:
    import undetected_chromedriver as uc
    HAVE_UC = True
except Exception:
    HAVE_UC = False

def _str2bool(v: str) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def build_driver(headless: bool = True, download_dir: str = "/tmp/downloads"):
    """
    Cria um Chrome configurado para rodar em container e baixar arquivos.
    - Usa undetected-chromedriver quando disponível.
    - Resolve o bug do UC com 'options.headless' usando ChromeOptions do Selenium.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options  # <— Options do Selenium (tem .headless)

    os.makedirs(download_dir, exist_ok=True)

    # HEADLESS efetivo: env > parâmetro
    env_headless = os.getenv("HEADLESS")
    use_headless = _str2bool(env_headless) if env_headless is not None else bool(headless)

    opts = Options()  # importante: não usar uc.ChromeOptions() para evitar o AttributeError

    # Preferências de download
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    try:
        opts.add_experimental_option("prefs", prefs)
        # “des-automatiza” alguns sinais
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
    except Exception:
        pass

    # Flags usuais de container/headless
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=pt-BR,pt")
    ua = os.getenv(
        "CHROME_UA",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    opts.add_argument(f"--user-agent={ua}")

    # O atributo .headless existe em Options do Selenium; além disso, adicionamos a flag
    if use_headless:
        # define o atributo e também a flag moderna
        try:
            opts.add_argument("--headless=new")
        except Exception:
            opts.add_argument("--headless")
        try:
            # alguns códigos do Selenium leem .headless
            opts.headless = True
        except Exception:
            pass

    if HAVE_UC:
        # Passar headless=True evita que o UC tente acessar options.headless (short-circuit)
        driver = uc.Chrome(options=opts, headless=use_headless, use_subprocess=True)
    else:
        driver = webdriver.Chrome(options=opts)
        # remove o navigator.webdriver (menos “cara de bot”)
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
            )
        except Exception:
            pass

    return driver
