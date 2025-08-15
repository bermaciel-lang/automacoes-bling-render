import os

# tentamos usar undetected-chromedriver; se faltar, caímos no Selenium normal
try:
    import undetected_chromedriver as uc
    HAVE_UC = True
except Exception:
    HAVE_UC = False

def build_driver(headless=True, download_dir="/tmp/downloads"):
    os.makedirs(download_dir, exist_ok=True)

    if HAVE_UC:
        opts = uc.ChromeOptions()
    else:
        from selenium.webdriver.chrome.options import Options
        opts = Options()

    # Preferências de download
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    try:
        opts.add_experimental_option("prefs", prefs)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
    except Exception:
        pass

    # Flags para container/headless
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
    if headless or os.getenv("HEADLESS", "1") == "1":
        opts.add_argument("--headless=new")

    # Cria o driver
    if HAVE_UC:
        driver = uc.Chrome(options=opts, use_subprocess=True)
    else:
        from selenium import webdriver
        driver = webdriver.Chrome(options=opts)
        # remove o navigator.webdriver
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
            )
        except Exception:
            pass

    return driver
