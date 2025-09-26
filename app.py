import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =====================================
# Config Google Sheets
# =====================================
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

def sync_now():
    try:
        save_data(st.session_state.sheet, st.session_state.df_att)
        st.success("✅ Dati sincronizzati su Google Sheets.")
    except Exception as e:
        st.error(f"❌ Errore sincronizzazione: {e}")

# =====================================
# Dati utenti (login demo)
# =====================================

# Carico gli utenti dal foglio "Utenti"
if "df_utenti" not in st.session_state:
    try:
        st.session_state.ws_utenti, st.session_state.df_utenti = load_utenti()
    except Exception as e:
        st.error(f"Errore caricamento utenti da Google Sheets: {e}")
        st.stop()
   
# =====================================
# Dizionario Macro/Tipologia/Attività
# =====================================
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
st.title("🧬SmartLab")

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
st.sidebar.write(f"Benvenuto, **{st.session_state.username}** ({st.session_state.ruolo})")
if st.sidebar.button("🔄 Sincronizza adesso"):
    sync_now()
if st.sidebar.button("🚪 Logout"):
    try:
        sync_now()
    except:
        pass
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.ruolo = ""
    st.rerun()
    
# =====================================
# Cambio password
# =====================================
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

            # Salvo subito su Google Sheets
            try:
                save_utenti(st.session_state.ws_utenti, st.session_state.df_utenti)
                st.success("✅ Password cambiata e salvata su Google Sheets!")
            except Exception as e:
                st.warning(f"Password aggiornata localmente ma non su Google Sheets: {e}")

            st.session_state.show_pw_change = False
            
# =====================================
# Navigazione per ruolo
# =====================================
if st.session_state.ruolo == "utente":
    # Menu utente
    scelta_pagina = st.sidebar.radio(
        "📌 Menu utente",
        ["➕ Inserisci attività", "✏️ Modifica attività", "📑 Elenco attività", "📊 Riepilogo e Grafici"]
    )

    # ---------- INSERISCI ----------
    if scelta_pagina == "➕ Inserisci attività":
        st.subheader("➕ Inserisci nuova attività")

        # Macro → Tipologia → Attività
        macro_tmp = st.selectbox("MacroAttività", ["-- Seleziona --"] + list(macro_tipologia_attivita.keys()), key="macro_form_tmp")
        if macro_tmp == "-- Seleziona --":
            macro_tmp = None

        tipologie_tmp = list(macro_tipologia_attivita.get(macro_tmp, {}).keys()) if macro_tmp else []
        tipologia_tmp = st.selectbox("Tipologia", ["-- Seleziona --"] + tipologie_tmp if tipologie_tmp else ["-- Seleziona --"], key="tipologia_form_tmp")
        if tipologia_tmp == "-- Seleziona --":
            tipologia_tmp = None

        attivita_list_tmp = macro_tipologia_attivita.get(macro_tmp, {}).get(tipologia_tmp, []) if tipologia_tmp else []
        attivita_tmp = st.selectbox("Attività", ["-- Seleziona --"] + attivita_list_tmp if attivita_list_tmp else ["-- Seleziona --"], key="attivita_form_tmp")
        if attivita_tmp == "-- Seleziona --":
            attivita_tmp = None

        # Note e tempi
        note_tmp = st.text_area("Note", key="note_tmp")
        ore_tmp = st.number_input("Ore impiegate", min_value=0, max_value=24, step=1, key="ore_tmp")
        minuti_tmp = st.number_input("Minuti impiegati", min_value=0, max_value=59, step=1, key="min_tmp")

        # Campi aggiuntivi
        num_campioni, tipo_malattia, num_referti, tipo_malattia_ref = None, None, None, None
        if macro_tmp == "ACCETTAZIONE":
            with st.expander("Dettagli campioni"):
                num_campioni = st.number_input("Numero di campioni", min_value=0, step=1, key="num_campioni")
                tipo_malattia = st.selectbox("Tipo di malattia", ["-- Seleziona --", "Parkinson", "Alzheimer", "Altro"], key="tipo_malattia")
                if tipo_malattia == "-- Seleziona --":
                    tipo_malattia = None
        elif macro_tmp == "REFERTAZIONE":
            with st.expander("Dettagli referti"):
                num_referti = st.number_input("Numero di referti", min_value=0, step=1, key="num_referti")
                tipo_malattia_ref = st.selectbox("Tipo di malattia", ["-- Seleziona --", "Parkinson", "Alzheimer", "Altro"], key="tipo_malattia_ref")
                if tipo_malattia_ref == "-- Seleziona --":
                    tipo_malattia_ref = None

        # Salvataggio
        with st.form("salva_attivita_form"):
            submitted = st.form_submit_button("💾 Salva attività")
            if submitted:
                if not (macro_tmp and tipologia_tmp and attivita_tmp):
                    st.error("Seleziona MacroAttività, Tipologia e Attività prima di salvare!")
                else:
                    new_id = 1 if st.session_state.df_att.empty else int(pd.to_numeric(st.session_state.df_att["ID"], errors="coerce").fillna(0).max()) + 1
                    new_row = pd.DataFrame([{
                        "ID": new_id,
                        "NomeUtente": st.session_state.username,
                        "Data": datetime.now(),
                        "MacroAttivita": macro_tmp,
                        "Tipologia": tipologia_tmp,
                        "Attivita": attivita_tmp,
                        "Note": note_tmp,
                        "Ore": ore_tmp,
                        "Minuti": minuti_tmp,
                        "NumCampioni": num_campioni,
                        "TipoMalattia": tipo_malattia,
                        "NumReferti": num_referti,
                        "TipoMalattiaRef": tipo_malattia_ref
                    }])
                    st.session_state.df_att = pd.concat([st.session_state.df_att, new_row], ignore_index=True)
                    try:
                        save_data(st.session_state.sheet, st.session_state.df_att)
                    except Exception as e:
                        st.warning(f"Attività salvata localmente ma non su Google Sheets: {e}")
                    st.success("✅ Attività salvata!")

    # ---------- MODIFICA ----------
    elif scelta_pagina == "✏️ Modifica attività":
        st.subheader("✏️ Modifica attività esistente")
        df_mio = st.session_state.df_att[st.session_state.df_att["NomeUtente"] == st.session_state.username]
        if df_mio.empty:
            st.info("Nessuna attività registrata.")
        else:
            scelta_id = st.selectbox("Seleziona attività", df_mio["ID"], key="scelta_id_mod")
            attivita_da_modificare = df_mio[df_mio["ID"] == scelta_id].iloc[0]

            current_dt = pd.to_datetime(attivita_da_modificare["Data"], errors="coerce")
            default_date = (current_dt.date() if pd.notna(current_dt) else datetime.today().date())
            default_time = (current_dt.time() if pd.notna(current_dt) else datetime.now().replace(second=0, microsecond=0).time())

            data_mod = st.date_input("Data", value=default_date, key=f"data_mod_{scelta_id}")
            ora_mod = st.time_input("Ora", value=default_time, key=f"ora_mod_{scelta_id}")

            macro_mod_list = list(macro_tipologia_attivita.keys())
            idx_macro = macro_mod_list.index(attivita_da_modificare["MacroAttivita"]) if attivita_da_modificare["MacroAttivita"] in macro_mod_list else 0
            macro_mod = st.selectbox("MacroAttività", macro_mod_list, index=idx_macro, key=f"macro_mod_{scelta_id}")

            tipologie_mod = list(macro_tipologia_attivita.get(macro_mod, {}).keys())
            idx_tipologia = tipologie_mod.index(attivita_da_modificare["Tipologia"]) if attivita_da_modificare["Tipologia"] in tipologie_mod else 0
            tipologia_mod = st.selectbox("Tipologia", tipologie_mod, index=idx_tipologia, key=f"tipologia_mod_{scelta_id}")

            attivita_list_mod = macro_tipologia_attivita.get(macro_mod, {}).get(tipologia_mod, [])
            idx_att = attivita_list_mod.index(attivita_da_modificare["Attivita"]) if attivita_da_modificare["Attivita"] in attivita_list_mod else 0
            attivita_mod = st.selectbox("Attività", attivita_list_mod, index=idx_att, key=f"attivita_mod_{scelta_id}")

            note_val = attivita_da_modificare.get("Note")
            note_mod = st.text_area("Note", note_val if (isinstance(note_val, str) and note_val != "nan") else "", key=f"note_mod_{scelta_id}")
            ore_mod = st.number_input("Ore impiegate", min_value=0, max_value=24, step=1,
                                    value=int(attivita_da_modificare.get("Ore", 0) or 0), key=f"ore_mod_{scelta_id}")
            minuti_mod = st.number_input("Minuti impiegati", min_value=0, max_value=59, step=1,
                                        value=int(attivita_da_modificare.get("Minuti", 0) or 0), key=f"min_mod_{scelta_id}")

            # --- Campi extra per ACCETTAZIONE / REFERTAZIONE ---
            num_campioni_mod, tipo_malattia_mod, num_referti_mod, tipo_malattia_ref_mod = None, None, None, None
            mal_opts = ["-- Seleziona --", "Parkinson", "Alzheimer", "Altro"]

            if macro_mod == "ACCETTAZIONE":
                with st.expander("Dettagli campioni"):
                    num_campioni_mod = st.number_input(
                        "Numero di campioni",
                        min_value=0, step=1,
                        value=int(attivita_da_modificare.get("NumCampioni") or 0),
                        key=f"numcamp_mod_{scelta_id}"
                    )
                    mal_def = attivita_da_modificare.get("TipoMalattia")
                    idx_mal = mal_opts.index(mal_def) if mal_def in mal_opts else 0
                    tipo_malattia_mod = st.selectbox(
                        "Tipo di malattia",
                        mal_opts, index=idx_mal,
                        key=f"tipomal_mod_{scelta_id}"
                    )
                    if tipo_malattia_mod == "-- Seleziona --":
                        tipo_malattia_mod = None

            elif macro_mod == "REFERTAZIONE":
                with st.expander("Dettagli referti"):
                    num_referti_mod = st.number_input(
                        "Numero di referti",
                        min_value=0, step=1,
                        value=int(attivita_da_modificare.get("NumReferti") or 0),
                        key=f"numref_mod_{scelta_id}"
                    )
                    mal_ref_def = attivita_da_modificare.get("TipoMalattiaRef")
                    idx_mal_ref = mal_opts.index(mal_ref_def) if mal_ref_def in mal_opts else 0
                    tipo_malattia_ref_mod = st.selectbox(
                        "Tipo di malattia",
                        mal_opts, index=idx_mal_ref,
                        key=f"tipomalref_mod_{scelta_id}"
                    )
                    if tipo_malattia_ref_mod == "-- Seleziona --":
                        tipo_malattia_ref_mod = None

            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("💾 Salva modifiche", key=f"btn_modifica_{scelta_id}"):
                    nuovo_dt = datetime.combine(data_mod, ora_mod)
                    st.session_state.df_att.loc[
                        st.session_state.df_att["ID"] == scelta_id,
                        ["Data","MacroAttivita","Tipologia","Attivita","Note","Ore","Minuti",
                         "NumCampioni","TipoMalattia","NumReferti","TipoMalattiaRef"]
                    ] = [nuovo_dt, macro_mod, tipologia_mod, attivita_mod, note_mod, ore_mod, minuti_mod,
                         num_campioni_mod, tipo_malattia_mod, num_referti_mod, tipo_malattia_ref_mod]
                    try:
                        save_data(st.session_state.sheet, st.session_state.df_att)
                    except Exception as e:
                        st.warning(f"Modifica salvata localmente ma non su Google Sheets: {e}")
                    st.success("✅ Attività modificata!")

            with col_del:
                if st.button("🗑️ Elimina attività", key=f"btn_elimina_{scelta_id}"):
                    st.session_state.df_att = st.session_state.df_att[st.session_state.df_att["ID"] != scelta_id]
                    try:
                        save_data(st.session_state.sheet, st.session_state.df_att)
                    except Exception as e:
                        st.warning(f"Eliminazione salvata localmente ma non su Google Sheets: {e}")
                    st.success("🗑️ Attività eliminata!")
                    st.rerun()
    # ---------- ELENCO ----------
    elif scelta_pagina == "📑 Elenco attività":
        st.subheader("📑 Le mie attività - elenco")
        df_mio = st.session_state.df_att[st.session_state.df_att["NomeUtente"] == st.session_state.username].copy()
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

            search_term = st.text_input("🔍 Cerca nelle attività (note, attività, tipologia)...", "")
            if search_term:
                df_filtered = df_filtered[
                    df_filtered.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
                ]

            total = len(df_filtered)
            if total == 0:
                st.info("Nessuna attività nel periodo o filtro selezionato.")
            else:
                total_pages = (total + page_size - 1) // page_size
                page = st.number_input("Pagina", min_value=1, max_value=total_pages, value=1, step=1, key="tbl_page")
                start = (page - 1) * page_size
                end = min(start + page_size, total)

                st.caption(f"Mostrando {start + 1}–{end} di {total} record")
                st.dataframe(df_filtered.iloc[start:end])

                st.download_button(
                    "⬇️ Scarica risultato (CSV)",
                    df_filtered.to_csv(index=False).encode("utf-8"),
                    "attivita_filtrate.csv",
                    "text/csv",
                    key="tbl_download"
                )

    # ---------- GRAFICI ----------
    elif scelta_pagina == "📊 Riepilogo e Grafici":
        st.subheader("📊 Riepilogo attività personali")

        df_mio = st.session_state.df_att[st.session_state.df_att["NomeUtente"] == st.session_state.username]

        if df_mio.empty:
            st.info("Nessuna attività registrata.")
        else:
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

            # KPI
            tot_ore = df_periodo["Ore"].fillna(0).sum()
            tot_minuti = df_periodo["Minuti"].fillna(0).sum()
            tot_ore_equivalenti = tot_ore + (tot_minuti / 60)
            tot_campioni = df_periodo["NumCampioni"].fillna(0).sum()
            tot_referti = df_periodo["NumReferti"].fillna(0).sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("⏱️ Ore totali", f"{tot_ore_equivalenti:.1f}")
            col2.metric("🧪 Campioni", int(tot_campioni))
            col3.metric("📄 Referti", int(tot_referti))

            # Grafici
            st.markdown("**Ore totali per MacroAttività**")
            ore_macro = df_periodo.copy()
            ore_macro["Ore"] = pd.to_numeric(ore_macro["Ore"], errors="coerce").fillna(0)
            ore_macro = ore_macro.groupby("MacroAttivita")["Ore"].sum()
            if not ore_macro.empty:
                st.bar_chart(ore_macro)
            else:
                st.info("Nessuna ora registrata nel periodo selezionato.")

            df_ref = df_periodo[df_periodo["MacroAttivita"] == "REFERTAZIONE"].copy()
            if not df_ref.empty:
                st.markdown("**Referti: compilati vs validati**")
                referti_counts = df_ref["Tipologia"].value_counts().reindex(
                    ["Compilazione referti", "Rilettura e validazione referti"]
                ).fillna(0)
                st.bar_chart(referti_counts)
            else:
                st.info("Nessun referto registrato nel periodo selezionato.")

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

# =====================================
# Area CAPO (Admin)
# =====================================
elif st.session_state.ruolo == "capo":
    st.subheader("📊 Dashboard Amministratore")

    df_all = st.session_state.df_att.copy()

    if df_all.empty:
        st.info("Nessuna attività registrata dagli utenti.")
    else:
        if not pd.api.types.is_datetime64_any_dtype(df_all["Data"]):
            df_all["Data"] = pd.to_datetime(df_all["Data"], errors="coerce")

        # --- FILTRO PERIODO ---
        data_min = df_all["Data"].dropna().min().date()
        data_max = df_all["Data"].dropna().max().date()
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Da", data_min, key="admin_start")
        with col2:
            end_date = st.date_input("A", data_max, key="admin_end")

        df_periodo = df_all[
            df_all["Data"].notna()
            & (df_all["Data"].dt.date >= start_date)
            & (df_all["Data"].dt.date <= end_date)
        ]

        # =========================
        # 1) Panoramica Campioni e Referti
        # =========================
        st.markdown("### 📦 Panoramica Campioni e Referti")

        tot_campioni = df_periodo["NumCampioni"].fillna(0).sum()
        tot_referti = df_periodo["NumReferti"].fillna(0).sum()

        c1, c2 = st.columns(2)
        c1.metric("🧪 Campioni totali", int(tot_campioni))
        c2.metric("📄 Referti totali", int(tot_referti))

        # Suddivisione referti per tipo
        df_ref = df_periodo[df_periodo["MacroAttivita"] == "REFERTAZIONE"].copy()
        if not df_ref.empty:
            st.markdown("**Referti per tipologia**")
            ref_counts = df_ref["Tipologia"].value_counts()
            st.bar_chart(ref_counts)

            st.markdown("**Referti per malattia**")
            ref_mal = df_ref["TipoMalattiaRef"].value_counts()
            st.bar_chart(ref_mal)

        # Suddivisione campioni per malattia
        df_acc = df_periodo[df_periodo["MacroAttivita"] == "ACCETTAZIONE"].copy()
        if not df_acc.empty:
            st.markdown("**Campioni per malattia**")
            camp_mal = df_acc["TipoMalattia"].value_counts()
            st.bar_chart(camp_mal)

        st.markdown("---")

        # =========================
        # 2) Monitoraggio per utente
        # =========================
        st.markdown("### 👩‍🔬 Monitoraggio per Utente")

        utente_sel = st.selectbox("Seleziona utente", sorted(df_all["NomeUtente"].dropna().unique()))
        df_user = df_periodo[df_periodo["NomeUtente"] == utente_sel]

        if df_user.empty:
            st.info(f"Nessuna attività per {utente_sel} nel periodo selezionato.")
        else:
            tot_ore = df_user["Ore"].fillna(0).sum() + df_user["Minuti"].fillna(0).sum() / 60
            st.metric(f"⏱️ Ore totali di {utente_sel}", f"{tot_ore:.1f}")

            st.markdown("**Ore per MacroAttività**")
            ore_macro = df_user.groupby("MacroAttivita")["Ore"].sum()
            st.bar_chart(ore_macro)

            st.markdown("**Numero referti per tipologia**")
            ref_user = df_user[df_user["MacroAttivita"] == "REFERTAZIONE"]
            if not ref_user.empty:
                st.bar_chart(ref_user["Tipologia"].value_counts())

            st.markdown("**Campioni per malattia**")
            camp_user = df_user[df_user["MacroAttivita"] == "ACCETTAZIONE"]
            if not camp_user.empty:
                st.bar_chart(camp_user["TipoMalattia"].value_counts())

        st.markdown("---")

        # =========================
        # 3) Monitoraggio per Attività/Malattia
        # =========================
        st.markdown("### 🧬 Monitoraggio per Attività / Malattia")

        filtro_att = st.selectbox(
            "Seleziona una malattia/attività da monitorare",
            sorted(set(df_all["TipoMalattia"].dropna().unique()) | set(df_all["TipoMalattiaRef"].dropna().unique()))
        )

        df_filtro = df_periodo[
            (df_periodo["TipoMalattia"] == filtro_att) | (df_periodo["TipoMalattiaRef"] == filtro_att)
        ]

        if df_filtro.empty:
            st.info(f"Nessun dato trovato per '{filtro_att}' nel periodo selezionato.")
        else:
            st.markdown(f"**Dettaglio attività relative a '{filtro_att}'**")
            st.dataframe(df_filtro.sort_values("Data", ascending=False))

            st.markdown("**Referti per utente**")
            st.bar_chart(df_filtro.groupby("NomeUtente")["NumReferti"].sum())

            st.markdown("**Campioni per utente**")
            st.bar_chart(df_filtro.groupby("NomeUtente")["NumCampioni"].sum())

