import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# =====================================
# Config Google Sheets
# =====================================
SHEET_NAME = "GestionaleLavoro"

def connect_gsheet(sheet_name, worksheet=0):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).get_worksheet(worksheet)

def load_utenti(sheet_name="GestionaleLavoro", worksheet_name="Utenti"):
    client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["google"], 
        ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
    ))
    ws = client.open(sheet_name).worksheet(worksheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=["NomeUtente","Password","Ruolo"])
    return ws, df

def save_utenti(ws, df):
    ws.clear()
    ws.update([df.columns.tolist()] + df.astype(str).values.tolist())

def load_data(sheet):
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID","NomeUtente","Data","MacroAttivita","Tipologia","Attivita",
            "Note","Ore","Minuti","NumCampioni","TipoMalattia","NumReferti","TipoMalattiaRef"
        ])
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    for col in ["Ore","Minuti","NumCampioni","NumReferti"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def save_data(sheet, df):
    df_to_save = df.copy()
    if "Data" in df_to_save.columns:
        df_to_save["Data"] = df_to_save["Data"].apply(
            lambda x: x.isoformat(sep=" ") if pd.notna(x) else ""
        )
    sheet.clear()
    sheet.update([df_to_save.columns.tolist()] + df_to_save.astype(str).values.tolist())

# =====================================
# Carico utenti
# =====================================
if "df_utenti" not in st.session_state:
    try:
        st.session_state.ws_utenti, st.session_state.df_utenti = load_utenti()
    except Exception as e:
        st.error(f"Errore caricamento utenti da Google Sheets: {e}")
        st.stop()

# =====================================
# Stato sessione & Login utils
# =====================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""

def login(username, password):
    dfu = st.session_state.df_utenti
    user = dfu[(dfu["NomeUtente"] == username) & (dfu["Password"] == password)]
    if not user.empty:
        return user.iloc[0]["Ruolo"]
    return None

# =====================================
# Connessione e Cache iniziale (una sola volta)
# =====================================
if "sheet" not in st.session_state:
    try:
        st.session_state.sheet = connect_gsheet(SHEET_NAME)
    except Exception as e:
        st.error(f"Impossibile connettersi a Google Sheets: {e}")
        st.stop()

if "df_att" not in st.session_state:
    st.session_state.df_att = load_data(st.session_state.sheet)

# =====================================
# UI - Titolo e Login
# =====================================
st.image("https://img.icons8.com/fluency/96/laboratory.png", width=80)
st.title("🧬 SmartLab - Gestionale Moderno")
st.caption("Dashboard per monitoraggio attività di laboratorio")

if not st.session_state.logged_in:
    st.subheader("Login")
    username = st.text_input("Nome utente")
    password = st.text_input("Password", type="password")
    if st.button("Accedi"):
        ruolo = login(username, password)
        if ruolo:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.ruolo = ruolo
            st.rerun()
        else:
            st.error("Nome utente o password errati")
    st.stop()

# =====================================
# Sidebar: info utente e azioni
# =====================================
st.sidebar.image("https://img.icons8.com/color/96/microscope.png", width=60)
st.sidebar.markdown(f"👋 Benvenuto **{st.session_state.username}** ({st.session_state.ruolo})")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""
    st.rerun()

# Cambio password
st.sidebar.markdown("---")
if st.sidebar.button("🔑 Cambia password"):
    st.session_state.show_pw_change = True

if st.session_state.get("show_pw_change", False):
    st.subheader("🔑 Cambia la tua password")
    old_pw = st.text_input("Password attuale", type="password", key="old_pw")
    new_pw = st.text_input("Nuova password", type="password", key="new_pw")
    confirm_pw = st.text_input("Conferma nuova password", type="password", key="confirm_pw")
    if st.button("Salva nuova password"):
        dfu = st.session_state.df_utenti
        user_row = dfu[dfu["NomeUtente"] == st.session_state.username]
        if user_row.empty:
            st.error("Utente non trovato.")
        elif old_pw != user_row.iloc[0]["Password"]:
            st.error("❌ La password attuale non è corretta.")
        elif new_pw != confirm_pw:
            st.error("❌ Le nuove password non coincidono.")
        elif len(new_pw) < 6:
            st.error("❌ La password deve avere almeno 6 caratteri.")
        else:
            st.session_state.df_utenti.loc[
                st.session_state.df_utenti["NomeUtente"] == st.session_state.username, "Password"
            ] = new_pw
            try:
                save_utenti(st.session_state.ws_utenti, st.session_state.df_utenti)
                st.success("✅ Password cambiata e salvata su Google Sheets!")
            except Exception as e:
                st.warning(f"Password aggiornata localmente ma non su Google Sheets: {e}")
            st.session_state.show_pw_change = False

# =====================================
# NAVIGAZIONE UTENTE
# =====================================
if st.session_state.ruolo == "utente":
    scelta = st.sidebar.radio("📌 Menu", ["➕ Inserisci", "✏️ Modifica", "📑 Elenco", "📊 Grafici"])
    df = st.session_state.df_att

    if scelta == "➕ Inserisci":
        st.subheader("➕ Inserisci nuova attività")
        macro = st.selectbox("MacroAttività", ["--"] + df["MacroAttivita"].dropna().unique().tolist())
        tipologia = st.text_input("Tipologia")
        att = st.text_input("Attività")
        note = st.text_area("Note")
        ore = st.number_input("Ore", 0, 24)
        minuti = st.number_input("Minuti", 0, 59)
        if st.button("💾 Salva"):
            new_id = 1 if df.empty else df["ID"].max() + 1
            new_row = pd.DataFrame([{
                "ID": new_id,
                "NomeUtente": st.session_state.username,
                "Data": datetime.now(),
                "MacroAttivita": macro,
                "Tipologia": tipologia,
                "Attivita": att,
                "Note": note,
                "Ore": ore,
                "Minuti": minuti
            }])
            st.session_state.df_att = pd.concat([df, new_row], ignore_index=True)
            save_data(st.session_state.sheet, st.session_state.df_att)
            st.success("✅ Attività salvata!")

    if scelta == "📊 Grafici":
        st.subheader("📊 Analisi attività")
        df_user = df[df["NomeUtente"] == st.session_state.username]
        if df_user.empty:
            st.info("Nessuna attività")
        else:
            ore_tot = df_user["Ore"].sum() + df_user["Minuti"].sum()/60
            ref = df_user["NumReferti"].fillna(0).sum()
            camp = df_user["NumCampioni"].fillna(0).sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("⏱️ Ore", f"{ore_tot:.1f}")
            col2.metric("📄 Referti", int(ref))
            col3.metric("🧪 Campioni", int(camp))

            fig = px.bar(df_user, x="MacroAttivita", y="Ore", color="MacroAttivita")
            st.plotly_chart(fig)

# =====================================
# NAVIGAZIONE CAPO
# =====================================
elif st.session_state.ruolo == "capo":
    st.subheader("📊 Dashboard Admin")
    df = st.session_state.df_att
    if df.empty:
        st.info("Nessuna attività registrata")
    else:
        ore_tot = df["Ore"].sum() + df["Minuti"].sum()/60
        ref = df["NumReferti"].fillna(0).sum()
        camp = df["NumCampioni"].fillna(0).sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("⏱️ Ore totali", f"{ore_tot:.1f}")
        col2.metric("📄 Referti", int(ref))
        col3.metric("🧪 Campioni", int(camp))

        fig = px.bar(df, x="NomeUtente", y="Ore", color="MacroAttivita")
        st.plotly_chart(fig)
