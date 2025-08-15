# selenium_setup.py
import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def _detect_chrome_binary() -> str | None:
    """Tenta detectar o binário do Chrome/Chromium no container."""
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _detect_chromedriver() -> str | None:
    """Tenta detectar o chromedriver instalado via apt ou disponível no PATH."""
    candidates = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Se não achar, o Selenium Manager tentará baixar/gerenciar automaticamente
    return None


def build_driver(download_dir: str | None = None) -> webdriver.Chrome:
    """
    Cria um driver Chrome headless com:
      - downloads permitidos e direcionados para /tmp/downloads (padrão)
      - flags recomendadas para containers (no-sandbox, disable-dev-shm-usage)
      - compatível com Selenium 4 (Service + Options)
    """
    # Diretório de download (padrão em /tmp/downloads; pode sobrescrever via env BROWSER_DOWNLOAD_DIR)
    download_dir = (
        download_dir
        or os.getenv("BROWSER_DOWNLOAD_DIR")
        or "/tmp/downloads"
    )
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    opts = Options()

    # Headless moderno (suporta download em headless)
    # Se tiver algum problema no seu ambiente, troque por "--headless"
    opts.add_argument("--headless=new")

    # Flags úteis em container
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--start-maximized")

    # Menos ruído de logs + evitar 'automation' banner
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Preferências de download
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        # permite múltiplos downloads sem prompt
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    opts.add_experimental_option("prefs", prefs)

    # Detecta binários (útil quando o Chrome/Chromium vem do apt)
    chrome_binary = _detect_chrome_binary()
    if chrome_binary:
        opts.binary_location = chrome_binary

    # Service: usa o chromedriver do sistema se existir; senão Selenium Manager
    chromedriver_path = _detect_chromedriver()
    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
    else:
        service = Service()  # Selenium Manager resolve automaticamente

    driver = webdriver.Chrome(service=service, options=opts)

    # Fallback extra: em alguns ambientes, ainda é necessário habilitar via CDP
    # (no headless antigo isso era obrigatório; aqui mantemos por segurança)
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )
    except Exception:
        # Em headless=new geralmente não precisa; ignore se não suportar
        pass

    return driver
