import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# Config Google Sheets
# =========================
SHEET_NAME = "GestionaleLavoro"   # <-- nome del tuo Google Sheet

def connect_gsheet(sheet_name, worksheet=0):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    # 🔑 Legge le credenziali dai secrets di Streamlit
    creds_dict = st.secrets["google"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).get_worksheet(worksheet)

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

def sync_now():
    try:
        save_data(st.session_state.sheet, st.session_state.df_att)
        st.success("✅ Dati sincronizzati su Google Sheets.")
    except Exception as e:
        st.error(f"❌ Errore sincronizzazione: {e}")

# =========================
# Dati utenti (login)
# =========================
utenti_data = {
    "NomeUtente": ["giulia","marco","anna","prof"],
    "Password": ["123","123","123","prof123"],
    "Ruolo": ["utente","utente","utente","capo"]
}
df_utenti = pd.DataFrame(utenti_data)

# =========================
# Dizionario Macro/Tipologia/Attività
# =========================
macro_tipologia_attivita = {
    "AGENDA": {
        "Gestione agenda appuntamenti e telefono": [
            "Informazioni analisi",
            "Telefonate in entrata",
            "Telefonate in uscita",
            "Comunicazione con pazienti (mail o telefono)",
            "Organizzazione appuntamenti con medici",
            "Supporto amministrativo (se pertinente)",
            "Prenotazioni"
        ],
        "Controllo e-mail e risposta": [
            "Prenotazioni",
            "Informazioni analisi",
            "Richieste varie"
        ]
    },
    "CONSULENZA GENETICA": {
        "Ambulatorio": [
            "Consulenza",
            "Controllo Impegnative",
            "Relazioni consulenza"
        ],
        "Teleconsulenza": [
            "Consulenza Telefonica",
            "Relazione Post-test"
        ]
    },
    "ACCETTAZIONE": {
        "Accettazione campioni e impegnative": [
            "Accettazione campioni interni",
            "Accettazione campioni esterni",
            "Registrazione impegnative access",
            "Conteggio impegnative (mensile)"
        ]
    },
    "ORDINI E MAGAZZINO": {
        "Gestione Ordini Reagenti e varie": [
            "Richiesta preventivo",
            "Ordine SAP",
            "Verifica arrivi DDT",
            "Controllo Giacenza"
        ]
    },
    "LABORATORIO": {
        "Lavoro al bancone": [
            "Estrazione DNA",
            "Preparazione reagenti",
            "Analisi molecolare",
            "Digestioni",
            "Blot",
            "Ibridazioni"
        ],
        "Manutenzione strumenti": [
            "Pulizia ABI e/o cambio capillari",
            "Pulizia NextSeq",
            "Pulizia MiSeq"
        ]
    },
    "INFORMATICA": {
        "Backup Dati": ["Scarico Dati"],
        "Programmazione": ["Programmazione"],
        "Interpretazione dati grezzi": [
            "Analisi dati NGS",
            "Match OA",
            "Interpretazione analisi Sanger",
            "Interpretazione analisi MLPA",
            "Interpretazione analisi Microsatelliti",
            "Interpretazione analisi Metilazione",
            "Lettura e interpretazione Lastre"
        ]
    },
    "REFERTAZIONE": {
        "Compilazione referti": [
            "Calcolo coverage e OMIM",
            "Stesura bozza referto"
        ],
        "Rilettura e validazione referti": [
            "NGS",
            "Analisi di sequenza (Trombofilia, Segregazioni mut)",
            "MLPA",
            "Analisi di frammenti (FC, Trombofilia, ecc.)",
            "FSHD"
        ]
    },
    "ATTIVITA' DIDATTICA": {
        "Lezioni": ["Lezioni"],
        "Esami": ["Esami"],
        "Correzione tesi": ["Correzione tesi"],
        "Slide": ["Slide"]
    },
    "RICERCA": {
        "Articolo scientifico": ["Scrittura", "Revisione", "Sottomissione"]
    }
}

# =========================
# Stato sessione & Login utils
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""

def login(username, password):
    user = df_utenti[(df_utenti["NomeUtente"]==username) & (df_utenti["Password"]==password)]
    if not user.empty:
        return user.iloc[0]["Ruolo"]
    return None

# =========================
# Connessione e Cache iniziale (una sola volta)
# =========================
if "sheet" not in st.session_state:
    try:
        st.session_state.sheet = connect_gsheet(SHEET_NAME)
    except Exception as e:
        st.error(f"Impossibile connettersi a Google Sheets: {e}")
        st.stop()

if "df_att" not in st.session_state:
    st.session_state.df_att = load_data(st.session_state.sheet)

# =========================
# UI
# =========================
st.title("📊 Gestionale Lavoro")

# --- LOGIN ---
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
        else:
            st.error("Nome utente o password errati")
    st.stop()

# --- Contenuto principale ---
st.sidebar.write(f"Benvenuto, {st.session_state.username} ({st.session_state.ruolo})")
if st.sidebar.button("Sincronizza adesso"):
    sync_now()
if st.sidebar.button("Logout"):
    try:
        sync_now()
    except:
        pass
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""
    st.experimental_rerun()

# =========================
# Area UTENTE
# =========================
if st.session_state.ruolo == "utente":
    st.subheader("Le mie attività")

    # --- INSERIMENTO NUOVA ATTIVITÀ ---
    # (resta uguale, non lo riscrivo per spazio)

    # --- MODIFICA ATTIVITÀ ESISTENTI ---
    # (resta uguale)

    # --- ELENCO ATTIVITÀ CON FILTRO & PAGINAZIONE ---
    st.markdown("---")
    st.subheader("Le mie attività - elenco")

    df_mio = st.session_state.df_att[
        st.session_state.df_att["NomeUtente"] == st.session_state.username
    ].copy()

    if df_mio.empty:
        st.info("Nessuna attività registrata.")
    else:
        if not pd.api.types.is_datetime64_any_dtype(df_mio["Data"]):
            df_mio["Data"] = pd.to_datetime(df_mio["Data"], errors="coerce")

        data_min = df_mio["Data"].dropna().min().date()
        data_max = df_mio["Data"].dropna().max().date()

        colA, colB, colC = st.columns([1, 1, 1])
        with colA:
            start_date = st.date_input("Da", data_min, key="tbl_start")
        with colB:
            end_date = st.date_input("A", data_max, key="tbl_end")
        with colC:
            page_size = st.selectbox("Righe per pagina", [10, 20, 50, 100], index=1, key="tbl_pagesize")

        df_filtered = df_mio[
            df_mio["Data"].notna()
            & (df_mio["Data"].dt.date >= start_date)
            & (df_mio["Data"].dt.date <= end_date)
        ].sort_values("Data", ascending=False)

        # --- Ricerca rapida ---
        search_term = st.text_input("🔍 Cerca nelle attività (note, attività, tipologia)...", "")
        if search_term:
            df_filtered = df_filtered[
                df_filtered.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            ]

        total = len(df_filtered)
        if total == 0:
            st.info("Nessuna attività nel periodo selezionato.")
        else:
            total_pages = (total + page_size - 1) // page_size
            page = st.number_input("Pagina", min_value=1, max_value=total_pages, value=1, step=1, key="tbl_page")
            start = (page - 1) * page_size
            end = min(start + page_size, total)

            st.caption(f"Mostrando {start + 1}–{end} di {total} record")
            st.dataframe(df_filtered.iloc[start:end])

            st.download_button(
                "Scarica risultato (CSV)",
                df_filtered.to_csv(index=False).encode("utf-8"),
                "attivita_filtrate.csv",
                "text/csv",
                key="tbl_download"
            )

    # --- GRAFICI RIASSUNTIVI PERSONALI ---
    st.markdown("---")
    st.subheader("Riepilogo attività personali")

    df_mio = st.session_state.df_att[st.session_state.df_att["NomeUtente"] == st.session_state.username]

    if not df_mio.empty:
        if not pd.api.types.is_datetime64_any_dtype(df_mio["Data"]):
            df_mio["Data"] = pd.to_datetime(df_mio["Data"], errors="coerce")

        data_min = df_mio["Data"].dropna().min().date() if df_mio["Data"].notna().any() else datetime.today().date()
        data_max = df_mio["Data"].dropna().max().date() if df_mio["Data"].notna().any() else datetime.today().date()

        start_date = st.date_input("Data inizio", data_min)
        end_date = st.date_input("Data fine", data_max)

        df_periodo = df_mio[
            df_mio["Data"].notna()
            & (df_mio["Data"].dt.date >= start_date)
            & (df_mio["Data"].dt.date <= end_date)
        ]

        # --- 📊 KPI ---
        st.markdown("### 📊 Indicatori chiave (KPI)")

        tot_ore = df_periodo["Ore"].fillna(0).sum()
        tot_minuti = df_periodo["Minuti"].fillna(0).sum()
        tot_ore_equivalenti = tot_ore + (tot_minuti / 60)

        tot_campioni = df_periodo["NumCampioni"].fillna(0).sum()
        tot_referti = df_periodo["NumReferti"].fillna(0).sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("⏱️ Ore totali", f"{tot_ore_equivalenti:.1f}")
        col2.metric("🧪 Campioni", int(tot_campioni))
        col3.metric("📄 Referti", int(tot_referti))

        # --- Grafici ---
        # 1) Ore totali per MacroAttività
        st.markdown("**Ore totali per MacroAttività**")
        ore_macro = df_periodo.copy()
        ore_macro["Ore"] = pd.to_numeric(ore_macro["Ore"], errors="coerce").fillna(0)
        ore_macro = ore_macro.groupby("MacroAttivita")["Ore"].sum()
        if not ore_macro.empty:
            st.bar_chart(ore_macro)
        else:
            st.info("Nessuna ora registrata nel periodo selezionato.")

        # 2) Referti: compilati vs validati
        df_ref = df_periodo[df_periodo["MacroAttivita"] == "REFERTAZIONE"].copy()
        if not df_ref.empty:
            st.markdown("**Referti: compilati vs validati**")
            referti_counts = df_ref["Tipologia"].value_counts().reindex(
                ["Compilazione referti", "Rilettura e validazione referti"]
            ).fillna(0)
            st.bar_chart(referti_counts)
        else:
            st.info("Nessun referto registrato nel periodo selezionato.")

        # 3) Accettazione: campioni interni vs esterni
        df_acc = df_periodo[df_periodo["MacroAttivita"] == "ACCETTAZIONE"].copy()
        if not df_acc.empty:
            st.markdown("**Accettazione: campioni interni vs esterni**")
            df_acc["NumCampioni"] = pd.to_numeric(df_acc["NumCampioni"], errors="coerce").fillna(0)
            att_lower = df_acc["Attivita"].str.lower().fillna("")
            df_acc["TipoAcc"] = att_lower.apply(
                lambda s: "Interni" if "intern" in s else ("Esterni" if "estern" in s else "Altro")
            )
            serie_accettazione = (
                df_acc.groupby("TipoAcc")["NumCampioni"]
                      .sum()
                      .reindex(["Interni", "Esterni", "Altro"])
                      .fillna(0)
            )
            serie_plot = serie_accettazione[["Interni", "Esterni"]].fillna(0)
            if serie_plot.sum() > 0:
                st.bar_chart(serie_plot)
            else:
                st.info("Nessun campione registrato nel periodo selezionato.")
        else:
            st.info("Nessuna attività di accettazione nel periodo selezionato.")

# =========================
# Area CAPO
# =========================
elif st.session_state.ruolo == "capo":
    st.subheader("📊 Resoconto completo (Admin)")

    df_all = st.session_state.df_att.copy()

    if df_all.empty:
        st.info("Nessuna attività registrata dagli utenti.")
    else:
        # Converto la colonna Data
        if not pd.api.types.is_datetime64_any_dtype(df_all["Data"]):
            df_all["Data"] = pd.to_datetime(df_all["Data"], errors="coerce")

        # --- Filtri dinamici ---
        st.markdown("### 🔍 Filtri")
        col1, col2, col3 = st.columns(3)
        with col1:
            utenti_sel = st.multiselect("Utenti", sorted(df_all["NomeUtente"].unique()), default=list(df_all["NomeUtente"].unique()))
        with col2:
            macro_sel = st.multiselect("MacroAttività", sorted(df_all["MacroAttivita"].dropna().unique()), default=list(df_all["MacroAttivita"].dropna().unique()))
        with col3:
            data_min = df_all["Data"].dropna().min().date()
            data_max = df_all["Data"].dropna().max().date()
            start_date = st.date_input("Da", data_min)
            end_date = st.date_input("A", data_max)

        df_filtrato = df_all[
            (df_all["NomeUtente"].isin(utenti_sel))
            & (df_all["MacroAttivita"].isin(macro_sel))
            & (df_all["Data"].dt.date >= start_date)
            & (df_all["Data"].dt.date <= end_date)
        ]

        if df_filtrato.empty:
            st.warning("⚠️ Nessun dato corrispondente ai filtri selezionati.")
        else:
            # --- KPI globali ---
            st.markdown("### 📌 Indicatori globali")
            tot_ore = df_filtrato["Ore"].fillna(0).sum()
            tot_min = df_filtrato["Minuti"].fillna(0).sum()
            tot_ore_eq = tot_ore + (tot_min/60)
            tot_campioni = df_filtrato["NumCampioni"].fillna(0).sum()
            tot_referti = df_filtrato["NumReferti"].fillna(0).sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("⏱️ Ore totali", f"{tot_ore_eq:.1f}")
            c2.metric("🧪 Campioni", int(tot_campioni))
            c3.metric("📄 Referti", int(tot_referti))

            # --- Tabella dati filtrati ---
            st.markdown("### 📑 Tabella dati filtrati")
            st.dataframe(df_filtrato.sort_values("Data", ascending=False))

            # --- Grafici ---
            st.markdown("### 📈 Grafici")

            colA, colB = st.columns(2)

            with colA:
                st.markdown("**Ore totali per utente**")
                ore_user = df_filtrato.groupby("NomeUtente")["Ore"].sum().sort_values(ascending=False)
                if not ore_user.empty:
                    st.bar_chart(ore_user)

            with colB:
                st.markdown("**Ore per MacroAttività**")
                ore_macro = df_filtrato.groupby("MacroAttivita")["Ore"].sum().sort_values(ascending=False)
                if not ore_macro.empty:
                    st.bar_chart(ore_macro)

            st.markdown("**Campioni e Referti per utente**")
            stats = df_filtrato.groupby("NomeUtente")[["NumCampioni","NumReferti"]].sum().fillna(0)
            st.bar_chart(stats)


