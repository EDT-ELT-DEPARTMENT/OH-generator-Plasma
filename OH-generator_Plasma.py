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

# Rafraîchissement automatique toutes les 2 secondes
st_autorefresh(interval=2000, key="datarefresh")

st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption(f"Département d'Électrotechnique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# Initialisation des variables de session
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
        port_com = st.text_input("Port COM", value="COM5")
        
        if st.button("🔌 Initialiser la connexion"):
            try:
                if st.session_state.ser is not None:
                    st.session_state.ser.close()
                st.session_state.ser = serial.Serial(port_com, 115200, timeout=1)
                time.sleep(2)
                st.success(f"✅ Liaison {port_com} établie !")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
                st.session_state.ser = None

        if st.session_state.ser and st.session_state.ser.is_open:
            try:
                st.session_state.ser.reset_input_buffer()
                line = st.session_state.ser.readline().decode('utf-8', errors='ignore').strip()
                if line and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        st.session_state.last_temp = float(parts[0])
                        st.session_state.last_hum = float(parts[1])
                temp, hum = st.session_state.last_temp, st.session_state.last_hum
                v_peak, freq = 23.0, 15000 
            except Exception:
                temp, hum = st.session_state.last_temp, st.session_state.last_hum
                v_peak, freq = 23.0, 15000
        else:
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
# 3. MOTEUR DE CALCUL
# =================================================================
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(R_ext / R_int)

p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * 2 if v_peak > v_th else 0.0

k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/75) * np.exp(-(temp - 45) / 200)
k_o3 = 0.00129 
o3_final = k_o3 * p_watt * (1 - hum/100) * np.exp(-(temp - 45) / 45) if v_peak > v_th else 0.0

total = oh_final + o3_final
pct_oh = (oh_final / total * 100) if total > 0 else 0.0
pct_o3 = (o3_final / total * 100) if total > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 4. AFFICHAGE (METRICS & GRAPHIQUES)
# =================================================================
label_mode = f"🔴 EXPÉRIMENTAL ({choix_carte})" if mode_experimental else "🔵 SIMULATION"
st.subheader(f"État du Système : {label_mode}")

# Metrics corrigées (toutes les parenthèses sont fermées)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
c2.metric("Production O3", f"{o3_final:.2f} ppm", f"{pct_o3:.1f} %")
c3.metric("Puissance Active", f"{p_watt:.1f} W")
c4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Fréquence", f"{freq} Hz")
c6.metric("Température", f"{temp:.1f} °C")
c7.metric("Humidité", f"{hum:.1f} %")
c8.metric("V-Seuil (Vth)", f"{v_th:.2f} kV")

st.divider()

g1, g2 = st.columns(2)
with g1:
    st.subheader("🌀 Figure de Lissajous")
    t_plot = np.linspace(0, 2*np.pi, 500)
    v_sin = v_peak * np.sin(t_plot)
    q_sin = (C_die * 1e6 * v_peak) * np.cos(t_plot) 
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
