import os, json, gspread
from google.oauth2.service_account import Credentials

def open_sheet_by_key(sheet_key: str):
    sa_json = os.getenv("GSHEETS_SA_JSON")
    if not sa_json:
        raise RuntimeError("GSHEETS_SA_JSON ausente nos Secrets do Replit.")
    info = json.loads(sa_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_key)
