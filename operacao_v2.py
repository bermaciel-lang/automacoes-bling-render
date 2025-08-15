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

# CONFIGURAÇÕES
EMAIL = "robo@organicodochico.com.br"
SENHA = "Roboodc@2025"
ID_PLANILHA = "1urrqcpkuUJ20cIruKtcysDEtAlbingtA_Pl33rQOOIY"
ABA_DESTINO = "OPERACAO"
ARQUIVO_CREDENCIAL = r"C:\Users\Bernardo\Documents\credenciais_google.json"

# Lista de datas: hoje-31 até hoje-3
hoje = datetime.today()
datas = [(hoje - timedelta(days=i)).strftime("%d/%m/%Y") for i in range(31, 2, -1)]

# Função para converter datetime para serial Google Sheets
def date_to_gs_serial(date_obj):
    gs_epoch = datetime(1899, 12, 30)
    delta = date_obj - gs_epoch
    return float(delta.days)

# Navegador
options = Options()
options.add_argument("--start-maximized")
driver = build_driver()
atexit.register(lambda: driver.quit())

print("🔐 Acessando página de login...")
driver.get("https://www.bling.com.br/b/relatorio.vendas.php")

WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(EMAIL + Keys.TAB)
WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))).send_keys(SENHA + Keys.ENTER)
time.sleep(2)

WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "periodoPesq")))
Select(driver.find_element(By.ID, "periodoPesq")).select_by_visible_text("De um período")
time.sleep(2)
Select(driver.find_element(By.ID, "campo1")).select_by_visible_text("Produto")
time.sleep(2)
Select(driver.find_element(By.ID, "situacao")).select_by_visible_text("Finalizado")
time.sleep(2)

# Planilha
escopo = ["https://www.googleapis.com/auth/spreadsheets"]
credenciais = None  # replaced by gs_auth.open_sheet_by_key
cliente = None  # replaced by gs_auth.open_sheet_by_key
planilha = open_sheet_by_key(ID_PLANILHA)
aba = planilha.worksheet(ABA_DESTINO)

# Limpar colunas C:F
print("🧹 Limpando colunas C:F da aba OPERACAO...")
aba.batch_clear(["C2:F10000"])
time.sleep(2)

# Loop por data
for data in datas:
    print(f"📅 Processando {data}...")

    driver.find_element(By.ID, "dataIni").clear()
    driver.find_element(By.ID, "dataIni").send_keys(data)
    time.sleep(2)

    driver.find_element(By.ID, "dataFim").clear()
    driver.find_element(By.ID, "dataFim").send_keys(data)
    time.sleep(2)

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Visualizar')]"))
    ).click()
    time.sleep(30)  # Aguarda carregamento completo

    # Verificar se há alerta de "sem vendas"
    try:
        alerta = driver.find_element(By.CLASS_NAME, "alert-box-warning")
        if "não retornou nenhum registro" in alerta.text.lower():
            print(f"📭 Sem vendas em {data}, pulando...")
            continue
    except:
        pass

    try:
        tabela = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="resultado"]'))
        )
        html = tabela.get_attribute("outerHTML")
        soup = BeautifulSoup(html, "html.parser")
        df = pd.read_html(str(soup), header=0)[0]

        if not all(col in df.columns for col in ["Produto", "Código", "Qtde"]):
            print(f"⚠️ Colunas faltando para {data}, pulando...")
            continue

        df = df[["Produto", "Código", "Qtde"]]

        # Qtde como inteiro (arredondado)
        df["Qtde"] = (
            df["Qtde"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .astype(float)
            / 100
        ).round().astype(int)

        # Data como número serial do Google Sheets
        date_obj = pd.to_datetime(data, dayfirst=True)
        gs_serial = date_to_gs_serial(date_obj)
        df["Data"] = gs_serial

        df = df.fillna("")
        valores = df[["Produto", "Código", "Qtde", "Data"]].values.tolist()

        # Usar primeira célula vazia da coluna C
        col_C = aba.col_values(3)
        try:
            proxima_linha = col_C.index("") + 1
        except ValueError:
            proxima_linha = len(col_C) + 1

        range_destino = f"C{proxima_linha}:F{proxima_linha + len(valores) - 1}"
        aba.update(values=valores, range_name=range_destino)
        print(f"✅ Exportado {data} com sucesso.")
        time.sleep(2)

    except Exception as e:
        print(f"⚠️ Erro ao processar {data}: {e}")
        continue

# ➕ FORMATAÇÃO DAS COLUNAS E E F AO FINAL
try:
    print("🔄 Formatando coluna E como NÚMERO (inteiro)...")
    aba.format("E2:E10000", {
        "numberFormat": {
            "type": "NUMBER",
            "pattern": "0"
        }
    })
    print("✅ Coluna E formatada com sucesso.")

    print("🔄 Formatando coluna F como DATA (dd/MM/yyyy)...")
    aba.format("F2:F10000", {
        "numberFormat": {
            "type": "DATE",
            "pattern": "dd/MM/yyyy"
        }
    })
    print("✅ Coluna F formatada com sucesso.")

except Exception as e:
    print(f"❌ Erro ao formatar colunas: {e}")

print("🏁 Finalizado.")
