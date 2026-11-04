import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

DATA_FILE = "evidencija.csv"

# Inicijalizacija CSV baze ako ne postoji
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
    df.to_csv(DATA_FILE, index=False)

st.set_page_config(page_title="Evidencija Radnog Vremena", page_icon="📍", layout="centered")

st.title("📍 Evidencija Radnog Vremena")
st.write("Skenirajte kôd na ulazu, izaberite Vaše ime i evidentirajte dolazak ili odlazak.")

# Spisak radnika i njihovih jedinstvenih PIN kodova
korisnici = {
    "Nikolić Nenad kr": "1111",
    "Stojanović Jugoslav": "2222",
    "Momčilović Ljubiša": "3344",
    "Timotijević Milosav": "4444",
    "Živadinović Milisav": "5555",
    "Nikolić Zoran": "6666",
    "Rakić Aleksandar": "7777",
    "Mirić Miljan": "8888",
    "Nikolić Nenad Bres": "9999"
}

# Opcije za padajući meni (dodat Admin Panel na početku)
opcije_meni = ["Izaberite sa spiska...", "Admin Panel"] + list(korisnici.keys())
izabrani_radnik = st.selectbox("Izaberite Vaše ime:", opcije_meni)

# Provera da li je izabran Admin Panel
if izabrani_radnik == "Admin Panel":
    st.subheader("🔐 Admin Panel")
    admin_pass = st.text_input("Unesite Admin lozinku:", type="password")
    
    # Možete promeniti admin lozinku ovde po želji (trenutno je "admin123")
    if admin_pass == "admin123":
        st.success("Uspešan pristup admin panelu!")
        if os.path.exists(DATA_FILE):
            df_admin = pd.read_csv(DATA_FILE)
            st.dataframe(df_admin, use_container_width=True)
            st.download_button(
                "Preuzmi kompletan izveštaj (CSV)", 
                df_admin.to_csv(index=False).encode('utf-8'), 
                "evidencija_radnog_vremena.csv", 
                "text/csv"
            )
    elif admin_pass:
        st.error("Pogrešna admin lozinka!")

# Standardna prijava za radnike
elif izabrani_radnik != "Izaberite sa spiska...":
    pin = st.text_input("Unesite Vaš PIN kod:", type="password")
    
    st.divider()
    st.subheader("📍 Provera lokacije")
    st.write("Kliknite na dugme ispod da očitate GPS lokaciju sa vašeg uređaja:")
    
    # Poziv geolokacije
    location = streamlit_geolocation()
    
    lokacija_ok = False
    if location and location.get('latitude') and location.get('longitude'):
        lat = location['latitude']
        lon = location['longitude']
        st.success(f"Lokacija uspešno učitana (Lat: {lat:.4f}, Lon: {lon:.4f})")
        lokacija_ok = True
    else:
        st.info("Molimo sačekajte da se GPS lokacija očitava ili osvežite stranicu ako je potrebno.")

    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        btn_prijava = st.button("🟢 PRIJAVA (Dolazak)", use_container_width=True)
    with col2:
        btn_odjava = st.button("🔴 ODJAVA (Odlazak)", use_container_width=True)
        
    if btn_prijava or btn_odjava:
        if not pin:
            st.error("Molimo unesite Vaš PIN kod!")
        elif pin != korisnici.get(izabrani_radnik):
            st.error("Pogrešan PIN kod! Unesite ispravan PIN za izabranog radnika.")
        else:
            akcija = "PRIJAVA" if btn_prijava else "ODJAVA"
            vreme_sada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Upis u CSV bazu
            nov_red = pd.DataFrame([[vreme_sada, izabrani_radnik, akcija, lokacija_ok]], 
                                   columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
            
            df_postojece = pd.read_csv(DATA_FILE)
            df_novo = pd.concat([df_postojece, nov_red], ignore_index=True)
            df_novo.to_csv(DATA_FILE, index=False)
            
            st.success(f"Uspešno zabeleženo: {akcija} za radnika {izabrani_radnik} u {vreme_sada}!")
