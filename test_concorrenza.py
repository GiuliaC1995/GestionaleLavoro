import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =====================================
# CONFIGURAZIONE
# =====================================
SHEET_NAME = "GestionaleLavoro_TEST"  # ⚠️ Usa SEMPRE il foglio duplicato
GOOGLE_CREDS_FILE = "service_account.json"  # metti qui il nome del tuo file di credenziali

# =====================================
# CONNESSIONE AL FOGLIO GOOGLE
# =====================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# =====================================
# TEST 1 – Stato iniziale
# =====================================
print("\n📄 Lettura dati iniziali...")
df_before = pd.DataFrame(sheet.get_all_records())
print(f"Righe iniziali: {len(df_before)}")

# =====================================
# TEST 2 – Simula 2 utenti che salvano contemporaneamente
# =====================================
print("\n👥 Inserimento simulato di due nuove attività...")

new_activities = [
    {
        "ID": int(df_before["ID"].max() + 1) if not df_before.empty else 1,
        "NomeUtente": "GiuliaC",
        "Data": datetime.now().isoformat(sep=" "),
        "MacroAttivita": "LABORATORIO",
        "Tipologia": "Lavoro al bancone",
        "Attivita": "Estrazione DNA",
        "Note": "Test simultaneo",
        "Ore": 1,
        "Minuti": 20,
        "NumCampioni": 5,
        "TipoMalattia": "FSHD",
        "NumReferti": "",
        "TipoMalattiaRef": ""
    },
    {
        "ID": int(df_before["ID"].max() + 2) if not df_before.empty else 2,
        "NomeUtente": "MarioTest",
        "Data": datetime.now().isoformat(sep=" "),
        "MacroAttivita": "REFERTAZIONE",
        "Tipologia": "Compilazione referti",
        "Attivita": "Stesura bozza referto",
        "Note": "Test simultaneo 2",
        "Ore": 2,
        "Minuti": 0,
        "NumCampioni": "",
        "TipoMalattia": "",
        "NumReferti": 3,
        "TipoMalattiaRef": "Cardio"
    }
]

df_add = pd.DataFrame(new_activities)

# Aggiungiamo le nuove righe in coda
sheet.append_rows(df_add.astype(str).values.tolist())

# =====================================
# TEST 3 – Rilettura e verifica
# =====================================
print("\n🔄 Lettura dati dopo inserimento...")
df_after = pd.DataFrame(sheet.get_all_records())
print(f"Righe dopo: {len(df_after)}")

# =====================================
# TEST 4 – Controlli automatici
# =====================================
ok_rows = True
missing_dates = df_after["Data"].isna().sum()

if len(df_after) < len(df_before) + 2:
    ok_rows = False
    print("❌ ERRORE: alcune righe sono state cancellate o non salvate.")
else:
    print("✅ Tutte le righe sono ancora presenti.")

if missing_dates > 0:
    ok_rows = False
    print(f"⚠️ ATTENZIONE: {missing_dates} righe senza data.")
else:
    print("✅ Tutte le righe hanno una data valida.")

if ok_rows:
    print("\n🎉 TEST SUPERATO! Il sistema sembra gestire bene la concorrenza.")
else:
    print("\n❌ TEST NON SUPERATO: controlla la funzione save_data o append_data.")
