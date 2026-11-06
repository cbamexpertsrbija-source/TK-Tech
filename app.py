import streamlit as st
import pandas as pd
import os
import requests
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_geolocation import streamlit_geolocation
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------
# TELEGRAM I GEOFENCING KONFIGURACIJA
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = "9092555598:AAFwtK5E6sH_yk8DSkKBKvc-1DAvseh5gHM"
TELEGRAM_CHAT_ID = "9167363271"

FIRMA_LAT = 43.3117532
FIRMA_LON = 21.7931703
DOZVOLJENI_RADIJUS_METARA = 150

def posalji_telegram_poruku(tekst):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": tekst, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Greška pri slanju Telegram obaveštenja: {e}")

def izracunaj_udaljenost(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ---------------------------------------------------------
# GOOGLE SHEETS DIREKTNA KONEKCIJA (GSPREAD)
# ---------------------------------------------------------
def otvori_radni_list():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet.worksheet("Sheet1")

def ucitaj_evidenciju():
    try:
        worksheet = otvori_radni_list()
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame(columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])

def dodaj_u_evidenciju(vreme, radnik, akcija, lokacija_ok):
    worksheet = otvori_radni_list()
    worksheet.append_row([str(vreme), str(radnik), str(akcija), str(lokacija_ok)])

# ---------------------------------------------------------
# UPRAVLJANJE RADNICIMA
# ---------------------------------------------------------
WORKERS_FILE = "radnici.csv"

if not os.path.exists(WORKERS_FILE):
    default_korisnici = {
        "Blagojević Vladica": "0000",
        "Nikolić Nenad kr": "1111",
        "Stojanović Jugoslav": "2222",
        "Momčilović Ljubiša": "3333",
        "Timotijević Milosav": "4444",
        "Živadinović Milisav": "5555",
        "Nikolić Zoran": "6666",
        "Rakić Aleksandar": "7777",
        "Mirić Miljan": "8888",
        "Nikolić Nenad Bres": "9999"
    }
    df_w = pd.DataFrame(list(default_korisnici.items()), columns=["Radnik", "PIN"])
    df_w.to_csv(WORKERS_FILE, index=False)

def ucitaj_korisnike():
    if os.path.exists(WORKERS_FILE):
        df_w = pd.read_csv(WORKERS_FILE)
        return dict(zip(df_w['Radnik'], df_w['PIN'].astype(str)))
    return {}

# ---------------------------------------------------------
# APLIKACIJA - EVIDENCIJA RADNOG VREMENA
# ---------------------------------------------------------
st.set_page_config(page_title="Evidencija Radnog Vremena - Top Kraft Tech", page_icon="📍", layout="centered")
st.title("📍 Evidencija Radnog Vremena - Top Kraft Tech")

if 'uspesno_evidentirano' not in st.session_state:
    st.session_state.uspesno_evidentirano = False

korisnici = ucitaj_korisnike()

if st.session_state.uspesno_evidentirano:
    st.success("✅ Evidencija je uspešno zabeležena u Google Sheets!")
    st.info("Za novi unos potrebno je ponovo skenirati kod na ulazu.")
else:
    st.write("Skenirajte kôd na ulazu, izaberite Vaše ime i evidentirajte dolazak ili odlazak.")
    
    opcije_meni = ["Izaberite sa spiska...", "Admin Panel"] + list(korisnici.keys())
    izabrani_radnik = st.selectbox("Izaberite Vaše ime:", opcije_meni)

    if izabrani_radnik == "Admin Panel":
        st.subheader("🔐 Admin Panel - Upravljanje i Izveštaji")
        admin_pass = st.text_input("Unesite Admin lozinku:", type="password")
        
        if admin_pass == "admin123":
            st.success("Uspešan pristup admin panelu!")
            tab1, tab2 = st.tabs(["📊 Izveštaji i Detekcija", "👥 Upravljanje Radnicima"])
            
            with tab1:
                df_admin = ucitaj_evidenciju()
                if not df_admin.empty:
                    df_admin['Vreme_dt'] = pd.to_datetime(df_admin['Vreme'], errors='coerce')
                    df_admin['Mesec'] = df_admin['Vreme_dt'].dt.strftime('%Y-%m')
                    
                    st.subheader("⚠️ Detekcija propuštenih (zaboravljenih) odjava (>12h)")
                    zaboravljene = []
                    trenutno_vreme = datetime.now(ZoneInfo("Europe/Belgrade"))
                    
                    for radnik in korisnici.keys():
                        df_r = df_admin[df_admin['Radnik'] == radnik].sort_values('Vreme_dt')
                        otvorena_prijava = None
                        for _, row in df_r.iterrows():
                            if row['Akcija'] == 'PRIJAVA':
                                otvorena_prijava = row['Vreme_dt']
                            elif row['Akcija'] == 'ODJAVA':
                                otvorena_prijava = None
                        
                        if otvorena_prijava is not None and pd.notnull(otvorena_prijava):
                            razlika_sati = (trenutno_vreme.replace(tzinfo=None) - otvorena_prijava.replace(tzinfo=None)).total_seconds() / 3600
                            if razlika_sati > 12:
                                zaboravljene.append({"Radnik": radnik, "poslednja_prijava": otvorena_prijava, "trajanje_h": razlika_sati})
                    
                    if zaboravljene:
                        st.warning("Pronađeni radnici sa nezavršenim smenama (traju duže od 12 sati):")
                        for z in zaboravljene:
                            st.write(f"- **{z['Radnik']}** (Prijava: `{z['poslednja_prijava']}`, otvoren pre `{z['trajanje_h']:.1f}` h)")
                    else:
                        st.info("Nema zaboravljenih odjava.")

                    st.divider()
                    st.subheader("📊 Filteri i sati")
                    radnici_lista = ["Svi radnici"] + list(korisnici.keys())
                    filter_radnik = st.selectbox("Filtriraj po radniku:", radnici_lista)
                    
                    dostupni_meseci = sorted(df_admin['Mesec'].dropna().unique(), reverse=True)
                    if not dostupni_meseci:
                        dostupni_meseci = [datetime.now(ZoneInfo("Europe/Belgrade")).strftime("%Y-%m")]
                    filter_mesec = st.selectbox("Filtriraj po mesecu:", ["Svi meseci"] + dostupni_meseci)
                    
                    df_filtriran = df_admin.copy()
                    if filter_radnik != "Svi radnici":
                        df_filtriran = df_filtriran[df_filtriran['Radnik'] == filter_radnik]
                    if filter_mesec != "Svi meseci":
                        df_filtriran = df_filtriran[df_filtriran['Mesec'] == filter_mesec]
                    
                    st.dataframe(df_filtriran[["Vreme", "Radnik", "Akcija", "Lokacija_OK"]], use_container_width=True)
                    
                    if filter_radnik != "Svi radnici":
                        ukupni_sati = 0.0
                        prijava_vreme = None
                        for _, row in df_filtriran.sort_values('Vreme_dt').iterrows():
                            if row['Akcija'] == 'PRIJAVA':
                                prijava_vreme = row['Vreme_dt']
                            elif row['Akcija'] == 'ODJAVA' and prijava_vreme is not None:
                                razlika = (row['Vreme_dt'] - prijava_vreme).total_seconds() / 3600
                                if razlika > 0:
                                    ukupni_sati += razlika
                                prijava_vreme = None
                        st.metric(f"Ukupno sati ({filter_radnik})", f"{ukupni_sati:.2f} h")

            with tab2:
                st.subheader("👥 Dodavanje i brisanje radnika")
                df_w_current = pd.read_csv(WORKERS_FILE)
                st.dataframe(df_w_current, use_container_width=True)
                
                novi_ime = st.text_input("Ime i prezime radnika:")
                novi_pin = st.text_input("Četvorocifreni PIN:", type="password", max_chars=4)
                
                if st.button("Sačuvaj novog radnika"):
                    if novi_ime and len(novi_pin) == 4:
                        if novi_ime in df_w_current['Radnik'].values:
                            st.error("Radnik već postoji!")
                        else:
                            novi_red_w = pd.DataFrame([[novi_ime, novi_pin]], columns=["Radnik", "PIN"])
                            df_w_current = pd.concat([df_w_current, novi_red_w], ignore_index=True)
                            df_w_current.to_csv(WORKERS_FILE, index=False)
                            st.success(f"Dodat radnik: {novi_ime}")
                            st.rerun()

    elif izabrani_radnik != "Izaberite sa spiska...":
        pin = st.text_input("Unesite Vaš PIN kod:", type="password")
        pin_ispravan = (pin == korisnici.get(izabrani_radnik))

        if pin and pin_ispravan:
            st.success("PIN uspešno potvrđen!")
            df_all = ucitaj_evidenciju()
            
            if not df_all.empty:
                df_all['Vreme_dt'] = pd.to_datetime(df_all['Vreme'], errors='coerce')
                trenutni_mesec = datetime.now(ZoneInfo("Europe/Belgrade")).strftime("%Y-%m")
                df_radnik = df_all[(df_all['Radnik'] == izabrani_radnik) & (df_all['Vreme_dt'].dt.strftime("%Y-%m") == trenutni_mesec)]
                
                if not df_radnik.empty:
                    st.info(f"📅 Vaša evidencija za mesec ({trenutni_mesec}):")
                    st.dataframe(df_radnik[["Vreme", "Akcija", "Lokacija_OK"]], use_container_width=True)

            st.divider()
            st.subheader("📍 GPS Geofencing - Provera lokacije")
            location = streamlit_geolocation()
            
            dozvoljeno_evidentiranje = False
            lokacija_ok = False
            
            if location and location.get('latitude') and location.get('longitude'):
                lat = location['latitude']
                lon = location['longitude']
                udaljenost = izracunaj_udaljenost(lat, lon, FIRMA_LAT, FIRMA_LON)
                
                if udaljenost <= DOZVOLJENI_RADIJUS_METARA:
                    st.success(f"✅ Lokacija potvrđena! (Udaljenost: {udaljenost:.1f}m)")
                    lokacija_ok = True
                    dozvoljeno_evidentiranje = True
                else:
                    st.error(f"❌ Van kruga firme! (Udaljenost: {udaljenost:.1f}m)")
                    dozvoljeno_evidentiranje = False

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                btn_prijava = st.button("🟢 PRIJAVA (Dolazak)", use_container_width=True, disabled=not dozvoljeno_evidentiranje)
            with col2:
                btn_odjava = st.button("🔴 ODJAVA (Odlazak)", use_container_width=True, disabled=not dozvoljeno_evidentiranje)
                
            if btn_prijava or btn_odjava:
                akcija = "PRIJAVA" if btn_prijava else "ODJAVA"
                vreme_sada = datetime.now(ZoneInfo("Europe/Belgrade")).strftime("%Y-%m-%d %H:%M:%S")
                
                # Upis u Google Sheets
                dodaj_u_evidenciju(vreme_sada, izabrani_radnik, akcija, lokacija_ok)
                
                # Telegram obaveštenje
                emoji_akcija = "🟢 PRIJAVA" if akcija == "PRIJAVA" else "🔴 ODJAVA"
                poruka_telegram = (
                    f"**{emoji_akcija} - Top Kraft Tech**\n\n"
                    f"👤 **Radnik:** {izabrani_radnik}\n"
                    f"🕒 **Vreme:** {vreme_sada}\n"
                    f"📍 **Geofencing:** Potvrđeno"
                )
                posalji_telegram_poruku(poruka_telegram)
                
                st.session_state.uspesno_evidentirano = True
                st.rerun()

        elif pin and not pin_ispravan:
            st.error("Pogrešan PIN kod!")
