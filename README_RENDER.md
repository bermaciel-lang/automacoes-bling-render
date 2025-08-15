# Automação Bling + QIVE no Render

## Estrutura
- Dockerfile → instala Python, Selenium, Chromium e Chromedriver.
- requirements.txt → pacotes Python.
- *_v2.py → scripts de automação.
- selenium_setup.py, gs_auth.py → utilitários.
- runner.py → roda todos scripts em sequência.

## Passos para deploy
1. Subir todos esses arquivos para um repositório no GitHub.
2. No Render:
   - **New → Cron Job**
   - Conectar ao GitHub e selecionar o repositório.
   - Ele detecta o Dockerfile automaticamente.
   - Em **Command**, coloque por exemplo:
     - `python bling_3m_v2.py` para rodar só um.
     - ou `python runner.py` para rodar todos.
   - Em **Schedule**, use o horário em UTC.
3. Configurar variáveis de ambiente (Settings → Environment):
   - `GSHEETS_SA_JSON` → conteúdo do JSON da conta de serviço do Google Sheets.
   - `BLING_USER` e `BLING_PASS` → login do Bling.
   - Se usar NOTASQIVEBLING:
     - `QIVE_USER` e `QIVE_PASS`.
   - `TZ` (opcional) → `America/Sao_Paulo` para logs no horário local.
4. Compartilhar suas planilhas do Google com o `client_email` do JSON.

Pronto! O Render executará seus scripts automaticamente.
