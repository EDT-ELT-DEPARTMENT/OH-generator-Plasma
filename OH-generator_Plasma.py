import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import serial
import time

# =================================================================
# 1. CONFIGURATION ET TITRE
# =================================================================
st.set_page_config(page_title="Plasma Monitoring - UDL-SBA", layout="wide")

st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption(f"Département d'Électrotechnique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. BARRE LATÉRALE : SÉLECTION DU MODE ET CARTES
# =================================================================
with st.sidebar:
    st.header("🎮 Mode de Fonctionnement")
    mode_experimental = st.toggle("🚀 Passer en Mode Expérimental", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Configuration Matérielle")
        # Sélection de la carte
        choix_carte = st.selectbox("Choisir la carte :", ["Wemos D1 Mini (ESP8266)", "TTGO T-Internet-POE (ESP32)"])
        port_com = st.text_input("Port COM (ex: COM3)", value="COM3")
        
        try:
            # Initialisation série
            ser = serial.Serial(port_com, 115200, timeout=1)
            st.success(f"{choix_carte} connectée sur {port_com}")
            
            # Lecture des données (Format attendu du Wemos : Temp,Hum)
            line = ser.readline().decode('utf-8').strip()
            if line:
                data = line.split(',')
                # Adaptation selon les données reçues
                temp = float(data[0])
                hum = float(data[1])
                # Valeurs par défaut pour le reste en attendant les autres capteurs
                v_peak, freq = 23.0, 15000 
            else:
                st.warning("En attente des données du capteur...")
                v_peak, freq, temp, hum = 23.0, 15000, 45.0, 75.0
        except Exception as e:
            st.error(f"Erreur : Carte non détectée. ({e})")
            v_peak, freq, temp, hum = 23.0, 15000, 45.0, 75.0
    else:
        st.header("💻 Mode Simulation")
        v_peak = st.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.slider("Fréquence f (Hz)", 1000, 25000, 15000)
        temp = st.slider("Température T (°C)", 20, 250, 45)
        hum = st.slider("Humidité H2O (%)", 10, 95, 75)
    
    st.divider()
    st.header("📐 Géométrie du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)

# =================================================================
# 3. MOTEUR DE CALCUL (CONSERVÉ)
# =================================================================
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(R_ext / R_int)

if v_peak > v_th:
    p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * 2
else:
    p_watt = 0.0

k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/75) * np.exp(-(temp - 45) / 200)
k_o3 = 0.00129 
o3_final = k_o3 * p_watt * (1 - hum/100) * np.exp(-(temp - 45) / 45) if v_peak > v_th else 0.0

total_oxydants = oh_final + o3_final
pct_oh = (oh_final / total_oxydants * 100) if total_oxydants > 0 else 0.0
pct_o3 = (o3_final / total_oxydants * 100) if total_oxydants > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 4. AFFICHAGE (METRICS & GRAPHIQUES)
# =================================================================
label_mode = f"🔴 EXPÉRIMENTAL ({choix_carte})" if mode_experimental else "🔵 SIMULATION"
st.subheader(f"État du Système : {label_mode}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
col2.metric("Production O3", f"{o3_final:.2f} ppm", f"{pct_o3:.1f} %")
col3.metric("Puissance Active", f"{p_watt:.1f} W")
col4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Fréquence", f"{freq} Hz")
col6.metric("Température", f"{temp:.1f} °C")
col7.metric("Humidité", f"{hum:.1f} %")
col8.metric("V-Seuil (Vth)", f"{v_th:.2f} kV")

st.divider()

# Section Graphiques (Lissajous et Performance)
g1, g2 = st.columns(2)
with g1:
    st.subheader("🌀 Figure de Lissajous")
    t = np.linspace(0, 2*np.pi, 500)
    v_sin = v_peak * np.sin(t)
    q_sin = (C_die * 1e6 * v_peak) * np.cos(t) 
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=v_sin, y=q_sin, fill="toself", line=dict(color='#ADFF2F', width=2)))
    fig_q.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="Charge (µC)")
    st.plotly_chart(fig_q, use_container_width=True)

with g2:
    st.subheader("📊 Performance vs Tension")
    v_range = np.linspace(10, 35, 100)
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000) * ((v - v_th) * 1000) * 2) if v > v_th else 0 for v in v_range]
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH (ppm)", line=dict(color='#00FBFF')))
    fig_v.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="Concentration (ppm)")
    st.plotly_chart(fig_v, use_container_width=True)

st.error("⚠️ Sécurité : Haute Tension. Production d'ozone. Utiliser sous hotte aspirante.")
st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
