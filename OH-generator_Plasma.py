import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import serial
import time
from streamlit_autorefresh import st_autorefresh

# =================================================================
# 1. CONFIGURATION ET TITRE
# =================================================================
st.set_page_config(page_title="Plasma Monitoring - UDL-SBA", layout="wide")

# Rafraîchissement automatique toutes les 2 secondes pour capter le flux Wemos
st_autorefresh(interval=2000, key="datarefresh")

st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption(f"Département d'Électrotechnique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# Initialisation des variables de session pour la persistance des données réelles
if 'last_temp' not in st.session_state:
    st.session_state.last_temp = 45.0
if 'last_hum' not in st.session_state:
    st.session_state.last_hum = 75.0
if 'ser' not in st.session_state:
    st.session_state.ser = None

# =================================================================
# 2. BARRE LATÉRALE : SÉLECTION DU MODE ET CARTES
# =================================================================
with st.sidebar:
    st.header("🎮 Mode de Fonctionnement")
    mode_experimental = st.toggle("🚀 Passer en Mode Expérimental", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Configuration Matérielle")
        choix_carte = st.selectbox("Choisir la carte :", ["Wemos D1 Mini (ESP8266)", "TTGO T-Internet-POE (ESP32)"])
        
        # Port COM5 par défaut pour le département d'électrotechnique
        port_com = st.text_input("Port COM", value="COM5")
        
        # Bouton d'initialisation
        if st.button("🔌 Initialiser la connexion"):
            try:
                if st.session_state.ser is not None:
                    st.session_state.ser.close()
                
                st.session_state.ser = serial.Serial(port_com, 115200, timeout=1)
                time.sleep(2) # Temps de stabilisation pour le DHT22
                st.success(f"✅ Liaison COM5 établie !")
            except Exception as e:
                st.error(f"❌ Erreur de connexion : {e}")
                st.session_state.ser = None

        # LECTURE DES DONNÉES RÉELLES
        if st.session_state.ser and st.session_state.ser.is_open:
            try:
                st.session_state.ser.reset_input_buffer()
                line = st.session_state.ser.readline().decode('utf-8', errors='ignore').strip()
                
                if line and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        # Mise à jour des valeurs avec les données du capteur
                        st.session_state.last_temp = float(parts[0])
                        st.session_state.last_hum = float(parts[1])
                
                # Affectation des valeurs captées
                temp = st.session_state.last_temp
                hum = st.session_state.last_hum
                v_peak, freq = 23.0, 15000 
            except Exception:
                temp, hum = st.session_state.last_temp, st.session_state.last_hum
                v_peak, freq = 23.0, 15000
        else:
            # En attente de connexion, on utilise les dernières valeurs ou défaut
            temp, hum = st.session_state.last_temp, st.session_state.last_hum
            v_peak, freq = 23.0, 15000
            
    else:
        st.header("💻 Mode Simulation")
        choix_carte = "Simulateur"
        v_peak = st.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.slider("Fréquence f (Hz)", 1000, 25000, 15000)
        temp = st.slider("Température T (°C)", 20, 250, 45.0)
        hum = st.slider("Humidité H2O (%)", 10, 95, 75.0)
    
    st.divider()
    st.header("📐 Géométrie du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)

# =================================================================
# 3. MOTEUR DE CALCUL (PHYSIQUE DU PLASMA)
# =================================================================
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

# Calcul de la tension de seuil et capacité diélectrique
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(R_ext / R_int)

# Calcul de la puissance dissipée (Formule de Manley adaptée)
if v_peak > v_th:
    p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * 2
else:
    p_watt = 0.0

# Modélisation chimique simplifiée des oxydants
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/75) * np.exp(-(temp - 45) / 200)

k_o3 = 0.00129 
o3_final = k_o3 * p_watt * (1 - hum/100) * np.exp(-(temp - 45) / 45) if v_peak > v_th else 0.0

total_oxydants = oh_final + o3_final
pct_oh = (oh_final / total_oxydants * 100) if total_oxydants > 0 else 0.0
pct_o3 = (o3_final / total_oxydants * 100) if total_oxydants > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 4. AFFICHAGE DES RÉSULTATS
# =================================================================
label_mode = f"🔴 EXPÉRIMENTAL ({choix_carte})" if mode_experimental else "🔵 SIMULATION"
st.subheader(f"État du Système : {label_mode}")

# Première ligne de métriques
col1, col2, col3, col4 = st.columns(4)
col1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
col2.metric("Production O3",
