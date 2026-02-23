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
st.set_page_config(page_title="Plasma Monitoring - UDL-SBA", layout="wide")

# Titre exact demandé
st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption(f"Département d'Électrotechnique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. BARRE LATÉRALE : SÉLECTION DU MODE ET PARAMÈTRES
# =================================================================
with st.sidebar:
    st.header("🎮 Mode de Fonctionnement")
    mode_experimental = st.toggle("🚀 Passer en Mode Expérimental (TTGO)", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Connexion TTGO")
        port_com = st.text_input("Port COM (ex: COM3)", value="COM3")
        try:
            # Tentative d'ouverture du port série pour la TTGO
            ser = serial.Serial(port_com, 115200, timeout=0.1)
            st.success(f"TTGO connectée sur {port_com}")
            
            # Lecture des données réelles (Format : Vp,Freq,Temp)
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
            st.error("Erreur : TTGO non détectée.")
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
# 3. MOTEUR DE CALCUL PHYSIQUE (MODÈLE HYBRIDE)
# =================================================================

# Constantes et Paramètres Quartz
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 # mm

# 1. Tension de Seuil (Vth)
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# 2. Modélisation Capacitive
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(R_ext / R_int)

# 3. Calcul de la Puissance Active (Loi de Manley)
if v_peak > v_th:
    p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * 2
else:
    p_watt = 0.0

# 4. Production de Radicaux ·OH
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/75) * np.exp(-(temp - 45) / 200)

# 5. Production d'Ozone O3 (Nouveau)
k_o3 = 0.00129 # Constante de production O3
o3_final = k_o3 * p_watt * (1 - hum/100) * np.exp(-(temp - 45) / 45) if v_peak > v_th else 0.0

# 6. Calcul du Mélange Hybride (%)
total_oxydants = oh_final + o3_final
if total_oxydants > 0:
    pct_oh = (oh_final / total_oxydants) * 100
    pct_o3 = (o3_final / total_oxydants) * 100
else:
    pct_oh, pct_o3 = 0.0, 0.0

# 7. G-Value
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 4. AFFICHAGE DES RÉSULTATS (METRICS)
# =================================================================
label_mode = "🔴 EXPÉRIMENTAL (TTGO)" if mode_experimental else "🔵 SIMULATION"
st.subheader(f"État du Système : {label_mode}")

# Première ligne : OH et O3
m1, m2, m3, m4 = st.columns(4)
m1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
m2.metric("Production O3", f"{o3_final:.2f} ppm", f"{pct_o3:.1f} %")
m3.metric("Puissance Active", f"{p_watt:.1f} W")
m4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

# Deuxième ligne : Paramètres de contrôle
m5, m6, m7, m8 = st.columns(4)
m5.metric("Fréquence", f"{freq} Hz")
m6.metric("Température", f"{temp:.1f} °C")
m7.metric("Humidité", f"{hum} %")
m8.metric("V-Seuil (Vth)", f"{v_th:.2f} kV")

st.divider()

# =================================================================
# 5. VISUALISATION GRAPHIQUE
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("🌀 Figure de Lissajous (Loi Tension-Charge)")
    # Courbe de Lissajous en forme de cercle/ellipse (Loi Tension-Charge)
    t = np.linspace(0, 2*np.pi, 500)
    # Tension sinusoïdale
    v_sin = v_peak * np.sin(t)
    # Charge déphasée pour créer le cercle/ellipse
    q_sin = (C_die * 1e6 * v_peak) * np.cos(t) 
    
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=v_sin, y=q_sin, fill="toself", line=dict(color='#ADFF2F', width=2)))
    fig_q.update_layout(template="plotly_dark", xaxis_title="Tension v(t) [kV]", yaxis_title="Charge q(t) [µC]")
    st.plotly_chart(fig_q, use_container_width=True)

with g2:
    st.subheader("📊 Performance vs Tension")
    
    v_range = np.linspace(10, 35, 100)
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000) * ((v - v_th) * 1000) * 2) if v > v_th else 0 for v in v_range]
    o3_curve = [k_o3 * (4 * freq * C_die * (v_th * 1000) * ((v - v_th) * 1000) * 2) * (1 - hum/100) * np.exp(-(temp - 45) / 45) if v > v_th else 0 for v in v_range]
    
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH (ppm)", line=dict(color='#00FBFF')))
    fig_v.add_trace(go.Scatter(x=v_range, y=o3_curve, name="O3 (ppm)", line=dict(color='orange')))
    fig_v.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="Concentration (ppm)")
    st.plotly_chart(fig_v, use_container_width=True)

# =================================================================
# 6. BASES PHYSIQUES ET SÉCURITÉ
# =================================================================
with st.expander("📚 Physique du modèle"):
    st.latex(r"P_{active} = 4 \cdot f \cdot C_{die} \cdot V_{th} \cdot (V_p - V_{th})")
    st.write(f"Vitesse d'acquisition TTGO : 115200 bauds")
    st.info("Le pourcentage (%) sous les métriques OH et O3 représente la part de chaque espèce dans le mélange hybride total.")

st.error("⚠️ Sécurité : Haute Tension. Production d'ozone. Utiliser sous hotte aspirante.")
st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)

