import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_geolocation import streamlit_geolocation

DATA_FILE = "evidencija.csv"

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
    df.to_csv(DATA_FILE, index=False)

st.set_page_config(page_title="Evidencija Radnog Vremena - Top Kraft Tech", page_icon="📍", layout="centered")

st.title("📍 Evidencija Radnog Vremena - Top Kraft Tech")

if 'uspesno_evidentirano' not in st.session_state:
    st.session_state.uspesno_evidentirano = False

korisnici = {
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

if st.session_state.uspesno_evidentirano:
    st.success("✅ Evidencija je uspešno zabeležena za ovu sesiju!")
    st.info("Za novi unos potrebno je ponovo skenirati QR kod na ulazu.")
else:
    st.write("Skenirajte kôd na ulazu, izaberite Vaše ime i evidentirajte dolazak ili odlazak.")
    
    opcije_meni = ["Izaberite sa spiska...", "Admin Panel"] + list(korisnici.keys())
    izabrani_radnik = st.selectbox("Izaberite Vaše ime:", opcije_meni)

    if izabrani_radnik == "Admin Panel":
        st.subheader("🔐 Admin Panel")
        admin_pass = st.text_input("Unesite Admin lozinku:", type="password")
        
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

    elif izabrani_radnik != "Izaberite sa spiska...":
        pin = st.text_input("Unesite Vaš PIN kod:", type="password")
        
        if os.path.exists(DATA_FILE):
            df_all = pd.read_csv(DATA_FILE)
            if not df_all.empty:
                df_all['Vreme_dt'] = pd.to_datetime(df_all['Vreme'], errors='coerce')
                trenutni_mesec = datetime.now(ZoneInfo("Europe/Belgrade")).strftime("%Y-%m")
                
                df_radnik = df_all[(df_all['Radnik'] == izabrani_radnik) & (df_all['Vreme_dt'].dt.strftime("%Y-%m") == trenutni_mesec)]
                
                if not df_radnik.empty:
                    st.info(f"📅 Vaša evidencija i sati za tekući mesec ({trenutni_mesec}):")
                    st.dataframe(df_radnik[["Vreme", "Akcija", "Lokacija_OK"]], use_container_width=True)
                    
                    ukupni_sati = 0.0
                    prijava_vreme = None
                    for _, row in df_radnik.sort_values('Vreme_dt').iterrows():
                        if row['Akcija'] == 'PRIJAVA':
                            prijava_vreme = row['Vreme_dt']
                        elif row['Akcija'] == 'ODJAVA' and prijava_vreme is not None:
                            razlika = (row['Vreme_dt'] - prijava_vreme).total_seconds() / 3600
                            if razlika > 0:
                                ukupni_sati += razlika
                            prijava_vreme = None
                    st.metric("Ukupno sati ovog meseca", f"{ukupni_sati:.2f} h")

        st.divider()
        st.subheader("📍 Provera lokacije")
        st.write("Kliknite na dugme ispod da očitate GPS lokaciju sa vašeg uređaja:")
        
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
                vreme_sada = datetime.now(ZoneInfo("Europe/Belgrade")).strftime("%Y-%m-%d %H:%M:%S")
                
                nov_red = pd.DataFrame([[vreme_sada, izabrani_radnik, akcija, lokacija_ok]], 
                                       columns=["Vreme", "Radnik", "Akcija", "Lokacija_OK"])
                
                df_postojece = pd.read_csv(DATA_FILE)
                df_novo = pd.concat([df_postojece, nov_red], ignore_index=True)
                df_novo.to_csv(DATA_FILE, index=False)
                
                st.session_state.uspesno_evidentirano = True
                st.rerun()
