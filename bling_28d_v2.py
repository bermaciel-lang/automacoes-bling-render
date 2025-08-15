from gs_auth import open_sheet_by_key
import atexit
from selenium_setup import build_driver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES ---
EMAIL = "robo@organicodochico.com.br"
SENHA = "Roboodc@2025"
hoje = datetime.today()
data_inicio = (hoje - timedelta(days=31)).strftime("%d/%m/%Y")
data_fim = (hoje - timedelta(days=3)).strftime("%d/%m/%Y")

ID_PLANILHA = "1urrqcpkuUJ20cIruKtcysDEtAlbingtA_Pl33rQOOIY"
ABA_DESTINO = "Bling 1m"
ARQUIVO_CREDENCIAL = r"C:\Users\Bernardo\Documents\credenciais_google.json"

# --- INICIA NAVEGADOR ---
options = Options()
options.add_argument("--start-maximized")
driver = build_driver()
atexit.register(lambda: driver.quit())

try:
    print("🔐 Acessando página de login...")
    driver.get("https://www.bling.com.br/b/relatorio.vendas.php")

    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(EMAIL + Keys.TAB)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))).send_keys(SENHA + Keys.ENTER)

    print("📅 Inserindo período...")
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "periodoPesq")))
    time.sleep(2)

    Select(driver.find_element(By.ID, "periodoPesq")).select_by_visible_text("De um período")
    time.sleep(2)
    driver.find_element(By.ID, "dataIni").clear()
    driver.find_element(By.ID, "dataIni").send_keys(data_inicio)
    driver.find_element(By.ID, "dataFim").clear()
    driver.find_element(By.ID, "dataFim").send_keys(data_fim)

    Select(driver.find_element(By.ID, "campo1")).select_by_visible_text("Produto")
    Select(driver.find_element(By.ID, "situacao")).select_by_visible_text("Finalizado")

    print("📊 Selecionando opções avançadas...")
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "label-mais-opcoes"))).click()
    driver.execute_script("document.getElementById('lucratividade').checked = true;")
    driver.execute_script("mostrarPrecosBase();")

    print("🖱️ Clicando em visualizar...")
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Visualizar')]"))).click()
    time.sleep(90)

    print("📥 Extraindo dados...")
    tabela = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, '//*[@id="resultado"]')))
    html = tabela.get_attribute("outerHTML")
    soup = BeautifulSoup(html, "html.parser")
    df = pd.read_html(str(soup), header=0)[0]

    # --- FORMATAR CAMPOS NUMÉRICOS ---
    def formatar_valor(v, dividir=True):
        try:
            v = float(v)
            if dividir:
                v = v / 100
            return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "" if pd.isna(v) else str(v)

    col_dividir = ['Qtde', 'Qtde faturada', 'Preço Médio', 'Valor', 'Valor faturado',
                   'Frete', 'Desconto', 'Outras despesas', 'Total Venda', 'Custo']
    col_nao_dividir = ['Lucro']

    for col in col_dividir:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: formatar_valor(x, True))

    for col in col_nao_dividir:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: formatar_valor(x, False))

    df = df.fillna("")  # TRATAMENTO FINAL DE NaN

    print("📤 Enviando para Google Sheets...")
    escopo = ["https://www.googleapis.com/auth/spreadsheets"]
    credenciais = None  # replaced by gs_auth.open_sheet_by_key
    cliente = None  # replaced by gs_auth.open_sheet_by_key
    planilha = open_sheet_by_key(ID_PLANILHA)
    aba = planilha.worksheet(ABA_DESTINO)

    num_linhas = len(df)

    # Limpa apenas C2:P...
    aba.batch_clear([f"C2:P{num_linhas+1}"])

    # Envia cabeçalho + dados
    dados = [df.columns.tolist()] + df.values.tolist()
    aba.update(values=dados, range_name="C1")

    print("✅ Pronto! Dados enviados com sucesso.")

except Exception as erro:
    print("❌ ERRO DETECTADO:", erro)
    print("⚠️ Veja onde o navegador parou.")
finally:
    pass  # NÃO fecha o navegador para você verificar
