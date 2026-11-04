import streamlit as st
import pandas as pd
from datetime import datetime
import os
import math
from streamlit_geolocation import streamlit_geolocation

# --- KONFIGURACIJA LOKACIJE FIRME ---
# Unesite tačnu geografsku širinu i dužinu vaše firme
FIRMA_LAT = 43.3117417  # Primer (Zamenite vašim koordinatama)
FIRMA_LON = 21.7936907  # Primer (Zamenite vašim koordinatama)
DOZVOLJENA_DISTANCA_METARA = 150  # Radnik mora biti unutar ovog kruga (u metrima)

DATA_FILE = "evidencija.csv"

# Inicijalizacija CSV baze ako ne postoji
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
    df.to_csv(DATA_FILE, index=False)

st.set_page_config(page_title="Evidencija Radnog Vremena", page_icon="⏱️", layout="centered")

st.title("⏱️ Evidencija Radnog Vremena")
st.write("Skenirajte kôd na ulazu, izaberite Vaše ime i evidentirajte dolazak ili odlazak.")

# Lista radnika (možete je kasnije proširiti)
radnici = ["Marko Marković", "Petar Petrović", "Jovana Jovanić"]
izabrani_radnik = st.selectbox("Izaberite Vaše ime:", radnici)

# Unos PIN-a radi sigurnosti
pin = st.text_input("Unesite Vaš PIN kod:", type="password")

st.divider()
st.subheader("📍 Provera lokacije")
st.write("Kliknite na dugme ispod da očitate GPS lokaciju sa vašeg telefona:")

# Dobijanje GPS lokacije uređaja preko Streamlit komponente
location = streamlit_geolocation()

# Funkcija za računanje razdaljine u metrima (Haversine formula)
def izracunaj_rastojanje(lat1, lon1, lat2, lon2):
    R = 6371000  # Radijus Zemlje u metrima
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

lokacija_validna = False

if location.get('latitude') and location.get('longitude'):
    korisnik_lat = location['latitude']
    korisnik_lon = location['longitude']
    
    rastojanje = izracunaj_rastojanje(korisnik_lat, korisnik_lon, FIRMA_LAT, FIRMA_LON)
    
    if rastojanje <= DOZVOLJENA_DISTANCA_METARA:
        st.success(f"✅ Nalazite se na lokaciji firme (Udaljenost: {round(rastojanje)}m).")
        lokacija_validna = True
    else:
        st.error(f"❌ Nalazite se van lokacije firme! (Udaljenost: {round(rastojanje)}m). Prijava nije dozvoljena.")
else:
    st.info("Molimo sačekajte ili osvežite stranicu da bi GPS očitao vašu lokaciju.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("🟢 PRIJAVA (Dolazak)", use_container_width=True, disabled=not lokacija_validna):
        if pin == "1234":  # Primer PIN-a (možete promeniti po želji)
            vreme = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            novi_unos = pd.DataFrame([[vreme, izabrani_radnik, "Dolazak", "Da"]], 
                                     columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
            novi_unos.to_csv(DATA_FILE, mode='a', header=False, index=False)
            st.success(f"Uspešno evidentiran DOLAZAK u {vreme}")
        else:
            st.error("Pogrešan PIN kod!")

with col2:
    if st.button("🔴 ODJAVA (Odlazak)", use_container_width=True, disabled=not lokacija_validna):
        if pin == "1234":
            vreme = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            novi_unos = pd.DataFrame([[vreme, izabrani_radnik, "Odlazak", "Da"]], 
                                     columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
            novi_unos.to_csv(DATA_FILE, mode='a', header=False, index=False)
            st.warning(f"Uspešno evidentiran ODLAZAK u {vreme}")
        else:
            st.error("Pogrešan PIN kod!")

# --- ADMIN PANEL ---
st.divider()
with st.expander("📊 Pregled evidencije (Samo za administratora)"):
    admin_pass = st.text_input("Admin lozinka:", type="password", key="admin_pwd")
    if admin_pass == "admin123":
        if os.path.exists(DATA_FILE):
            df_log = pd.read_csv(DATA_FILE)
            st.dataframe(df_log, use_container_width=True)
            st.download_button("Preuzmi izveštaj (CSV)", df_log.to_csv(index=False), "evidencija.csv", "text/csv")