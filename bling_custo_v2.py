from gs_auth import open_sheet_by_key
import atexit
from selenium_setup import build_driver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
import gspread
import time
import pandas as pd

# --- CONFIGURAÇÕES ---
EMAIL = "robo@organicodochico.com.br"
SENHA = "Roboodc@2025"
ID_PLANILHA = "1urrqcpkuUJ20cIruKtcysDEtAlbingtA_Pl33rQOOIY"
ABA_DESTINO = "CUSTO"
ARQUIVO_CREDENCIAL = r"C:\Users\Bernardo\Documents\credenciais_google.json"

# --- INICIA NAVEGADOR ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = build_driver()
atexit.register(lambda: driver.quit())

# --- ACESSA A PÁGINA DO RELATÓRIO ---
driver.get("https://www.bling.com.br/relatorio.estoque.visao.financeira.php")

# --- LOGIN ---
WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(EMAIL)
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.XPATH, '//input[@type="password" and contains(@class, "InputText-input")]'))
).send_keys(SENHA + "\ue007")  # Pressiona Enter

# --- PAUSA APÓS LOGIN ---
time.sleep(5)

# --- ESPERA CAMPO DE VALORIZAÇÃO ---
WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "valorizacao")))
time.sleep(2)

# --- SELECIONA "Preço de custo" ---
Select(driver.find_element(By.ID, "valorizacao")).select_by_visible_text("Preço de custo")
time.sleep(2)

# --- CLICA EM "Visualizar" ---
WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Visualizar')]"))
).click()

# --- AGUARDA RELATÓRIO CARREGAR ---
time.sleep(90)

# --- EXTRAI A TABELA ---
tabela = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, '//*[@id="resultado"]')))
html = tabela.get_attribute("outerHTML")
soup = BeautifulSoup(html, "html.parser")
df = pd.read_html(str(soup), header=0)[0]

# --- AJUSTES DE FORMATAÇÃO ---
def formatar_valor(v, dividir_por=1):
    try:
        v = float(v) / dividir_por
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "" if pd.isna(v) else str(v)

for col in df.columns:
    if "Quantidade" in col:
        df[col] = df[col].apply(lambda x: formatar_valor(x, 10**10))
    elif "Valor unitário" in col or "Valor total" in col:
        df[col] = df[col].apply(lambda x: formatar_valor(x, 100))
    else:
        df[col] = df[col].fillna("").astype(str)

# --- ENVIA PARA GOOGLE SHEETS ---
escopo = ["https://www.googleapis.com/auth/spreadsheets"]
credenciais = None  # replaced by gs_auth.open_sheet_by_key
cliente = None  # replaced by gs_auth.open_sheet_by_key
planilha = open_sheet_by_key(ID_PLANILHA)
aba = planilha.worksheet(ABA_DESTINO)

# Limpa intervalo alvo (mantém colunas A e B intactas)
aba.batch_clear(["C2:Z999"])

# Envia dados
aba.update("C2", df.values.tolist())

print("✅ Relatório CUSTO atualizado com sucesso.")
driver.quit()

