import os, time, zipfile, io, glob, atexit
from datetime import datetime, timedelta
import pytz

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from selenium_setup import build_driver  # usa o selenium 4 (Service/Selenium Manager)

# Secrets esperados no ambiente:
# QIVE_USER, QIVE_PASS
# BLING_USER, BLING_PASS
#
# Fluxo:
# 1) Loga no QIVE (Arquivei), filtra por data (ontem por padrão), seleciona tudo e baixa ZIP de XMLs
# 2) Extrai XMLs para /tmp/xmls
# 3) Loga no Bling e abre a tela de importação de XML (compras) e faz upload dos XMLs um a um

TZ = pytz.timezone("America/Sao_Paulo")

def log(msg):
    print(f"[{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def dump_debug(driver, label="DEBUG"):
    """Salva screenshot e HTML da página atual em /tmp para ajudar na análise via logs."""
    try:
        ts = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
        ss_path = f"/tmp/{label.replace(' ', '_')}_{ts}.png"
        html_path = f"/tmp/{label.replace(' ', '_')}_{ts}.html"
        driver.save_screenshot(ss_path)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        log(f"🖼️ Screenshot salvo: {ss_path}")
        log(f"📄 HTML salvo: {html_path}")
    except Exception as e:
        log(f"⚠️ dump_debug falhou: {e}")

def _first_present(wait, candidates, by="xpath", clickable=False, visible=False, timeout_msg=None):
    """Tenta múltiplos seletores e retorna o primeiro que aparecer."""
    for sel in candidates:
        try:
            if by == "xpath":
                locator = (By.XPATH, sel)
            elif by == "css":
                locator = (By.CSS_SELECTOR, sel)
            elif by == "id":
                locator = (By.ID, sel)
            elif by == "name":
                locator = (By.NAME, sel)
            else:
                locator = (By.XPATH, sel)

            if clickable:
                return wait.until(EC.element_to_be_clickable(locator))
            if visible:
                return wait.until(EC.visibility_of_element_located(locator))
            return wait.until(EC.presence_of_element_located(locator))
        except Exception:
            pass
    if timeout_msg:
        raise TimeoutException(timeout_msg)
    return None

def qive_login_and_download(driver, user, passwd, date_from, date_to):
    """
    Faz login no Arquivei (QIVE), abre o painel de filtros, preenche período e aplica.
    Depois tenta localizar a ação de download (ZIP). Retorna a URL do ZIP (se detectada),
    caso contrário retorna None (quando o download é automático).
    """
    driver.get("https://app.arquivei.com.br/nfe/list")
    wait = WebDriverWait(driver, 40)

    # ===== LOGIN (tolerante a variações) =====
    try:
        # Alguns fluxos podem já estar autenticados -> procurar rapidamente algo de "lista" ou perfil
        time.sleep(1)

        email_input = _first_present(
            wait,
            candidates=[
                "//*[@type='email']",
                "//*[@id='email']",
                "//input[@name='email' or @name='username']",
            ],
            clickable=False,
            visible=True,
            timeout_msg=None,
        )
        if email_input:
            email_input.clear()
            email_input.send_keys(user)
            # botão continuar/entrar
            btn = _first_present(
                wait,
                candidates=[
                    "//button[@type='submit']",
                    "//button[contains(@data-testid,'login')]",
                    "//button[contains(., 'Entrar')]",
                    "//button[contains(., 'Acessar')]",
                    "//input[@type='submit']",
                ],
                clickable=True,
            )
            if btn:
                btn.click()

            passwd_input = _first_present(
                wait,
                candidates=["//*[@type='password']", "//input[@name='password']"],
                visible=True,
                timeout_msg="Campo de senha não apareceu."
            )
            passwd_input.clear()
            passwd_input.send_keys(passwd)

            btn2 = _first_present(
                wait,
                candidates=[
                    "//button[@type='submit']",
                    "//button[contains(., 'Entrar') or contains(., 'Acessar') or contains(., 'Login')]",
                    "//input[@type='submit']",
                ],
                clickable=True,
                timeout_msg="Botão de login não apareceu."
            )
            btn2.click()
        # Se não achou email_input, assumimos que já está logado
    except Exception as e:
        log(f"⚠️ Login do QIVE: prosseguindo (pode já estar logado). Detalhe: {e}")

    # ===== ABRIR FILTROS (o botão 'Filtrar' pode abrir o painel OU aplicar) =====
    try:
        # Se os inputs de data ainda NÃO estão visíveis, clique para abrir o painel
        date_inputs_present = False
        try:
            _ = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
            if _:
                date_inputs_present = True
        except Exception:
            pass

        if not date_inputs_present:
            filtrar_abrir = _first_present(
                wait,
                candidates=[
                    "//button[normalize-space()='Filtrar']",
                    "//button[contains(., 'Filtrar')]",
                    "//a[normalize-space()='Filtrar']",
                    "//a[contains(., 'Filtrar')]",
                ],
                clickable=True,
                timeout_msg="Botão 'Filtrar' (abrir) não apareceu."
            )
            # scroll até o botão (evita overlays)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", filtrar_abrir)
            filtrar_abrir.click()
            time.sleep(1)

    except Exception as e:
        dump_debug(driver, "QIVE_FILTRAR_ABRIR_FALHOU")
        raise

    # ===== PREENCHER DATAS =====
    try:
        # maioria dos input[type=date] espera YYYY-MM-DD
        yyyy_mm_dd_from = date_from.strftime("%Y-%m-%d")
        yyyy_mm_dd_to   = date_to.strftime("%Y-%m-%d")

        # tente encontrar 2 inputs de data
        inputs_date = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
        if len(inputs_date) >= 2:
            inputs_date[0].clear(); inputs_date[0].send_keys(yyyy_mm_dd_from)
            inputs_date[1].clear(); inputs_date[1].send_keys(yyyy_mm_dd_to)
        else:
            # fallback por name/id comuns
            dt_ini = _first_present(
                wait,
                by="css",
                candidates=[
                    "input[name='dataInicio']",
                    "input[name='date_from']",
                    "#dataInicio",
                ],
                visible=True
            )
            if dt_ini:
                dt_ini.clear(); dt_ini.send_keys(yyyy_mm_dd_from)

            dt_fim = _first_present(
                wait,
                by="css",
                candidates=[
                    "input[name='dataFim']",
                    "input[name='date_to']",
                    "#dataFim",
                ],
                visible=True
            )
            if dt_fim:
                dt_fim.clear(); dt_fim.send_keys(yyyy_mm_dd_to)

    except Exception as e:
        log(f"⚠️ Erro ao preencher datas: {e}")
        dump_debug(driver, "QIVE_PREENCHER_DATAS")

    # ===== APLICAR FILTRO (segundo 'Filtrar') =====
    try:
        filtrar_aplicar = _first_present(
            wait,
            candidates=[
                # muitas vezes o botão de aplicar é visualmente igual:
                "//button[normalize-space()='Filtrar']",
                "//button[contains(., 'Filtrar')]",
                # variações dentro de drawer/modal
                "//div[contains(@class,'drawer') or contains(@class,'modal')]//button[contains(.,'Filtrar')]",
            ],
            clickable=True,
            timeout_msg="Botão 'Filtrar' (aplicar) não apareceu."
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", filtrar_aplicar)
        filtrar_aplicar.click()
    except Exception as e:
        log(f"❌ Falhou ao localizar/clicar em 'Filtrar' (aplicar): {e}")
        dump_debug(driver, "QIVE_FILTRAR_APLICAR_FALHOU")
        raise

    # ===== AGUARDAR RESULTADOS (tabela/lista) =====
    try:
        wait.until(EC.any_of(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, [role='table']")),
            EC.presence_of_element_located((By.XPATH, "//*[contains(., 'resultados') or contains(., 'itens')]"))
        ))
        time.sleep(2)
    except TimeoutException:
        log("⚠️ Resultados não visíveis após aplicar filtro.")
        dump_debug(driver, "QIVE_RESULTADOS_TIMEOUT")

    # ===== SELECIONAR TODOS =====
    try:
        # checkbox no header
        select_all = driver.find_element(By.CSS_SELECTOR, "thead input[type='checkbox']")
        driver.execute_script("arguments[0].click();", select_all)
    except Exception:
        try:
            btn_all = driver.find_element(By.XPATH, "//button[contains(., 'Selecionar todos') or contains(., 'Selecionar Tudo')]")
            driver.execute_script("arguments[0].click();", btn_all)
        except Exception:
            log("Aviso: não localizei 'Selecionar todos'. Prosseguindo com o que estiver visível.")

    # ===== DOWNLOAD ZIP (varia por layout) =====
    zip_url = None
    try:
        # caminho 1: menu "Envio e Download" -> "Baixar XMLs em ZIP"
        try:
            menu_btn = _first_present(
                wait,
                candidates=["//button[contains(., 'Envio e Download')]"],
                clickable=True
            )
            menu_btn.click()
            zip_btn = _first_present(
                wait,
                candidates=["//button[contains(., 'Baixar XMLs em ZIP')]"],
                clickable=True
            )
            zip_btn.click()
        except Exception:
            # caminho 2: botão direto de exportação/zip
            try:
                zip_btn2 = _first_present(
                    wait,
                    candidates=[
                        "//button[contains(., 'ZIP')]",
                        "//button[contains(., 'Exportar')]",
                        "//a[contains(., 'ZIP') or contains(., 'Exportar')]",
                    ],
                    clickable=True
                )
                zip_btn2.click()
            except Exception:
                log("⚠️ Não encontrei botões de download/ZIP imediatamente.")
                dump_debug(driver, "QIVE_BOTAO_ZIP_NAO_ENCONTRADO")

        # aguarda um pouco por links de zip na página
        time.sleep(6)
        links = driver.find_elements(By.CSS_SELECTOR, "a[href$='.zip']")
        if links:
            zip_url = links[0].get_attribute("href")
            log(f"Link ZIP detectado: {zip_url}")
            # abrir link (opcional) — muitos ambientes headless precisam de preferências p/ salvar arquivo
            try:
                driver.get(zip_url)
                time.sleep(8)
            except Exception:
                pass
        else:
            log("Nenhum link .zip visível; pode ser que o download seja disparado automaticamente.")
    except Exception as e:
        log(f"⚠️ Falha no fluxo de download ZIP: {e}")
        dump_debug(driver, "QIVE_DOWNLOAD_ZIP_FALHA")

    return zip_url  # pode ser None se o download for automático

def bling_login(driver, user, passwd):
    driver.get("https://www.bling.com.br/login")
    wait = WebDriverWait(driver, 40)

    email = _first_present(
        wait,
        by="css",
        candidates=["input[type='email']", "input#login", "input[name='email']"],
        visible=True,
        timeout_msg="Campo de email do Bling não apareceu."
    )
    email.clear(); email.send_keys(user)

    btn = _first_present(
        wait,
        candidates=["//button[@type='submit']"],
        clickable=True,
        timeout_msg="Botão de continuar (email) do Bling não apareceu."
    )
    btn.click()

    pwd = _first_present(
        wait,
        by="css",
        candidates=["input[type='password']", "input[name='password']"],
        visible=True,
        timeout_msg="Campo de senha do Bling não apareceu."
    )
    pwd.clear(); pwd.send_keys(passwd)

    btn2 = _first_present(
        wait,
        candidates=["//button[@type='submit']"],
        clickable=True,
        timeout_msg="Botão de login (senha) do Bling não apareceu."
    )
    btn2.click()

    # algum elemento de área logada
    _first_present(
        wait,
        candidates=[
            "//*[contains(., 'Bem-vindo') or contains(., 'Início') or contains(., 'Dashboard')]",
        ],
        visible=True,
        timeout_msg=None
    )

def bling_import_xmls_ui(driver, xml_dir):
    wait = WebDriverWait(driver, 40)

    # Abra a home; dependendo do plano/conta, a URL de importação muda
    driver.get("https://www.bling.com.br/")
    time.sleep(2)

    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    if not xml_files:
        log("Nenhum XML encontrado para importar (pasta vazia).")
        return

    for fp in xml_files:
        log(f"Importando {os.path.basename(fp)}")
        try:
            # Tente encontrar um input[type=file] visível na página atual
            file_input = _first_present(
                wait,
                by="css",
                candidates=["input[type='file']"],
                visible=True,
                timeout_msg=None
            )
            if file_input:
                file_input.send_keys(fp)
                # tentar clicar em importar/enviar se existir
                try:
                    import_btn = _first_present(
                        wait,
                        candidates=[
                            "//button[contains(., 'Importar') or contains(., 'Enviar') or contains(., 'Upload')]"
                        ],
                        clickable=True,
                        timeout_msg=None
                    )
                    if import_btn:
                        import_btn.click()
                except Exception:
                    pass
                time.sleep(4)
            else:
                log("Não encontrei input de upload. Talvez seja necessário navegar até a tela de importação específica.")
                break
        except Exception as e:
            log(f"Falha ao importar {fp}: {e}")
            dump_debug(driver, f"BLING_IMPORT_{os.path.basename(fp)}")

def main():
    QIVE_USER = os.getenv("QIVE_USER")
    QIVE_PASS = os.getenv("QIVE_PASS")
    BLING_USER = os.getenv("BLING_USER")
    BLING_PASS = os.getenv("BLING_PASS")
    if not all([QIVE_USER, QIVE_PASS, BLING_USER, BLING_PASS]):
        raise RuntimeError("Faltam Secrets: QIVE_USER, QIVE_PASS, BLING_USER, BLING_PASS.")

    # Datas: ontem por padrão
    today = datetime.now(TZ).date()
    date_from = today - timedelta(days=1)
    date_to   = today - timedelta(days=1)

    driver = build_driver()
    atexit.register(lambda: driver.quit())

    log("Baixando XMLs do QIVE...")
    zip_url = qive_login_and_download(driver, QIVE_USER, QIVE_PASS, date_from, date_to)
    if zip_url:
        log(f"URL do ZIP (caso precise baixar via requests com cookies): {zip_url}")

    # Observação: este exemplo NÃO força o download físico em headless.
    # Para baixar para disco, configure preferências do Chrome no build_driver()
    # (p.ex.: download.default_directory=/tmp/downloads) e então manipule o arquivo.
    xml_dir = "/tmp/xmls"
    os.makedirs(xml_dir, exist_ok=True)

    # Se você já tiver os XMLs (ou ajustar o build_driver para baixar automaticamente),
    # descompacte aqui. Exemplo, caso você tenha o conteúdo do ZIP em memória:
    # with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
    #     zf.extractall(xml_dir)

    log("Login no Bling...")
    bling_login(driver, BLING_USER, BLING_PASS)

    log("Importando XMLs no Bling...")
    bling_import_xmls_ui(driver, xml_dir)

    log("Concluído.")

if __name__ == "__main__":
    main()
