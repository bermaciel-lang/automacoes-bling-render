
import os, time, zipfile, io, glob, atexit
from datetime import datetime, timedelta
import pytz

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium_setup import build_driver

# Secrets esperados no Replit:
# QIVE_USER, QIVE_PASS
# BLING_USER, BLING_PASS
#
# Fluxo:
# 1) Loga no QIVE (Arquivei), filtra por data (ontem por padrão), seleciona tudo e baixa ZIP de XMLs
# 2) Extrai XMLs para /tmp/xmls
# 3) Loga no Bling e abre a tela de importação de XML (compras) e faz upload dos XMLs um a um
#
# Observação: seletores podem precisar pequenos ajustes por mudanças visuais do site.

TZ = pytz.timezone("America/Sao_Paulo")

def log(msg):
    print(f"[{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def qive_login_and_download(driver, user, passwd, date_from, date_to):
    driver.get("https://app.arquivei.com.br/nfe/list")
    wait = WebDriverWait(driver, 30)

    # Login
    # Campos podem mudar; tente localizar por name/id comuns
    # (ajuste se necessário)
    email_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email'], input#email")))
    email_input.clear(); email_input.send_keys(user)
    next_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button[data-testid='login-button']")
    next_btn.click()

    passwd_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    passwd_input.clear(); passwd_input.send_keys(passwd)
    login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_btn.click()

    # Abrir filtros
    # Primeiro botão "Filtrar" (abre o painel)
    filtrar1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Filtrar')]")))
    filtrar1.click()

    # Preencher datas - campos por 'data de criação'
    # Tente localizar inputs de data no painel aberto
    # Ajuste os seletores conforme necessário
    time.sleep(1)
    inputs_date = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
    if len(inputs_date) >= 2:
        inputs_date[0].clear(); inputs_date[0].send_keys(date_from.strftime("%Y-%m-%d"))
        inputs_date[1].clear(); inputs_date[1].send_keys(date_to.strftime("%Y-%m-%d"))

    # Segundo "Filtrar" (aplica)
    filtrar2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Filtrar')]")))
    filtrar2.click()

    # Aguardar resultados
    wait.until(EC.any_of(
        EC.presence_of_element_located((By.XPATH, "//*[contains(., 'resultados') or contains(., 'itens')]")),
        EC.presence_of_element_located((By.CSS_SELECTOR, "table, [role='table']"))
    ))
    time.sleep(2)

    # Selecionar todos
    # Geralmente há um checkbox geral no header de tabela
    try:
        select_all = driver.find_element(By.CSS_SELECTOR, "thead input[type='checkbox']")
        driver.execute_script("arguments[0].click();", select_all)
    except Exception:
        # fallback: tentar um botão "Selecionar todos"
        try:
            btn_all = driver.find_element(By.XPATH, "//button[contains(., 'Selecionar todos')]")
            btn_all.click()
        except Exception:
            log("Aviso: não localizei seletor 'Selecionar todos'. Prossigo com o que estiver visível.")

    # Envio e Download > Baixar XMLs em ZIP
    menu_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Envio e Download')]")))
    menu_btn.click()
    zip_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Baixar XMLs em ZIP')]")))
    zip_btn.click()

    # Aguardar download (o Replit não mostra prompt; o browser tende a baixar para memória).
    # Estratégia: interceptamos via DevTools? Simplesmente aguarde e verifique <a download>?
    # Para simplificar aqui, vamos tentar capturar um link gerado e baixá-lo via requests autenticadas seria ideal.
    # Como atalho, muitos sistemas disparam um download automático; vamos aguardar alguns segundos
    time.sleep(10)

    # Como workaround, se o app abrir um link de download, ele costuma aparecer como <a href="...zip">.
    # Tentamos encontrar links na página (melhor ajustar manualmente se necessário).
    links = driver.find_elements(By.CSS_SELECTOR, "a[href$='.zip']")
    if not links:
        log("Não encontrei link de ZIP na página. Se o download for automático, você precisará adaptar este trecho.")
        return None

    zip_url = links[0].get_attribute("href")
    log(f"Link ZIP detectado: {zip_url}")
    # Baixar via Selenium não é o ideal; mas podemos abrir em nova aba e tentar obter via requests com cookies.
    # Por simplicidade, vamos abrir o link e aguardar o navegador baixar.
    driver.get(zip_url)
    time.sleep(10)
    # Em headless padrão, o download vai para um local temporário invisível.
    # Para produção, recomendo mudar preferências do Chrome para um diretório (exige usar Selenium Service e setExperimentalOption).
    # Aqui, como fallback, retornamos a própria URL para que você baixe via requests com cookies de sessão.
    return zip_url

def bling_login(driver, user, passwd):
    driver.get("https://www.bling.com.br/login")
    wait = WebDriverWait(driver, 30)
    email = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email'], input#login")))
    email.clear(); email.send_keys(user)
    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    btn.click()
    pwd = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    pwd.clear(); pwd.send_keys(passwd)
    btn2 = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    btn2.click()
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Bem-vindo') or contains(., 'Início')]")))

def bling_import_xmls_ui(driver, xml_dir):
    wait = WebDriverWait(driver, 30)
    # Tentar abrir a página de importação de XML de compra
    # URL de importação pode mudar; tentar navegar pelos menus
    driver.get("https://www.bling.com.br/")
    time.sleep(2)
    # Tentar acessar via busca de menu:
    # Como fallback, vamos tentar acessar um endpoint comum de importação (ajustar conforme necessário)
    # driver.get("https://www.bling.com.br/notasfiscais/importar")
    # Se essa URL não existir, será preciso mapear o menu em sua conta.
    time.sleep(2)

    # Upload de cada XML (genérico; ajustar seletor do input[type=file])
    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    if not xml_files:
        log("Nenhum XML encontrado para importar.")
        return

    for fp in xml_files:
        log(f"Importando {os.path.basename(fp)}")
        try:
            file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
            file_input.send_keys(fp)
            # Clique no botão de importação/confirmar
            try:
                import_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Importar') or contains(., 'Enviar')]")))
                import_btn.click()
            except Exception:
                pass
            # esperar confirmação
            time.sleep(4)
        except Exception as e:
            log(f"Falha ao importar {fp}: {e}")

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
    # Observação: este exemplo não faz o download do ZIP para disco por causa de limitações do headless padrão.
    # Em produção, recomendo configurar o Chrome para baixar em /tmp e depois extrair.
    # Abaixo, criamos uma pasta para XMLs caso você traga os arquivos manualmente ou ajuste o download.
    xml_dir = "/tmp/xmls"
    os.makedirs(xml_dir, exist_ok=True)

    log("Login no Bling...")
    bling_login(driver, BLING_USER, BLING_PASS)

    log("Importando XMLs no Bling...")
    bling_import_xmls_ui(driver, xml_dir)

    log("Concluído.")

if __name__ == "__main__":
    main()
