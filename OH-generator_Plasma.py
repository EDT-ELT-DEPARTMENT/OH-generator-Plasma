import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import serial # Pour la communication avec la TTGO
import time

# =================================================================
# 1. CONFIGURATION ET TITRE OFFICIEL
# =================================================================
st.set_page_config(page_title="TTGO Plasma System - UDL-SBA", layout="wide")

# Rappel du titre mémorisé exigé
st.title("⚡ Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption(f"Département d'Électrotechnique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. BARRE LATÉRALE : SÉLECTION DU MODE
# =================================================================
with st.sidebar:
    st.header("🎮 Mode de Fonctionnement")
    mode_experimental = st.toggle("🚀 Passer en Mode Expérimental (TTGO)", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Connexion TTGO")
        port_com = st.text_input("Port COM (ex: COM3)", value="COM3")
        try:
            # Tentative d'ouverture du port série
            ser = serial.Serial(port_com, 115200, timeout=0.1)
            st.success(f"TTGO connectée sur {port_com}")
            
            # Lecture d'une ligne de données (Format attendu : Vp,Freq,Temp)
            line = ser.readline().decode('utf-8').strip()
            if line:
                data = line.split(',')
                v_peak = float(data[0])
                freq = float(data[1])
                temp = float(data[2])
            else:
                st.warning("Attente de données série...")
                v_peak, freq, temp = 23.0, 15000, 45.0
        except Exception as e:
            st.error("Erreur : TTGO non détectée. Vérifiez le branchement.")
            v_peak, freq, temp = 23.0, 15000, 45.0
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
# 3. MOTEUR DE CALCUL PHYSIQUE (COMMUN AUX DEUX MODES)
# =================================================================

# Constantes et Paramètres Quartz
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 # mm

# 1. Tension de Seuil (Loi de Paschen adaptée)
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# 2. Modélisation Capacitive
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(R_ext / R_int)
C_gap = (2 * np.pi * EPS_0 * 1.0 * (L_act/1000)) / np.log((R_int) / (R_int - d_gap/1000))
C_cell = (C_die * C_gap) / (C_die + C_gap)

# 3. Calcul de la Puissance Réelle
if v_peak > v_th:
    p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * 2
else:
    p_watt = 0.0

# 4. Cinétique OH (Calibration M2RE)
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/75) * np.exp(-(temp - 45) / 200)
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 4. AFFICHAGE DES RÉSULTATS (DYNAMIQUE)
# =================================================================
label_mode = "🔴 EXPÉRIMENTAL (TTGO)" if mode_experimental else "🔵 SIMULATION"
st.subheader(f"État du Système : {label_mode}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Puissance Active", f"{p_watt:.1f} W")
c3.metric("Fréquence", f"{freq} Hz")
c4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

st.divider()

# =================================================================
# 5. ANALYSE GRAPHIQUE (LISSAJOUS ET TENSION)
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("🌀 Figure de Lissajous (Q-V)")
    
    t = np.linspace(0, 2*np.pi, 1000)
    v_t = v_peak * np.sin(t)
    q_t = [ (C_die * 1e6 * (v - np.sign(v)*v_th) + np.sign(v)*(C_cell*1e6*v_th)) if abs(v) > v_th else (C_cell*1e6*v) for v in v_t]
    
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=v_t, y=q_t, fill="toself", line=dict(color='#ADFF2F', width=2)))
    fig_q.update_layout(template="plotly_dark", xaxis_title="V (kV)", yaxis_title="Charge (µC)")
    st.plotly_chart(fig_q, use_container_width=True)

with g2:
    st.subheader("📊 Performance vs Tension")
    
    v_range = np.linspace(10, 35, 100)
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000) * ((v - v_th) * 1000) * 2) if v > v_th else 0 for v in v_range]
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH", line=dict(color='#00FBFF', width=3)))
    fig_v.add_vline(x=v_peak, line_dash="dash", line_color="yellow", annotation_text="Point de fonctionnement")
    fig_v.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="OH (ppm)")
    st.plotly_chart(fig_v, use_container_width=True)

# =================================================================
# 6. ÉQUATIONS UTILISÉES
# =================================================================
with st.expander("📚 Physique du modèle"):
    st.latex(r"P_{active} = 4 \cdot f \cdot C_{die} \cdot V_{th} \cdot (V_p - V_{th})")
    st.write(f"Vitesse d'acquisition TTGO : 115200 bauds")

st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
