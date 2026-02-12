import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Plasma Control - UDL-SBA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation du Session State pour l'IA
if 'v_p' not in st.session_state: st.session_state.v_p = 23.0
if 'f_q' not in st.session_state: st.session_state.f_q = 15000

# =================================================================
# 2. TITRE OFFICIEL ET IDENTITÉ
# =================================================================
st.title("⚡ Start-up-OH Generator Plasma")
st.subheader("Système Intelligent de Traitement des Fumées")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 3. BARRE LATÉRALE (SIDEBAR) - GÉOMÉTRIE ET ÉLECTRIQUE
# =================================================================
with st.sidebar:
    st.header("🤖 Commande IA Adaptive")
    if st.button("🚀 Appliquer l'Optimisation"):
        st.session_state.v_p = 32.0
        st.session_state.f_q = 18000
        st.rerun()
    
    st.divider()
    st.header("⚙️ Paramètres Électriques")
    v_peak = st.slider("Tension Crête $V_p$ (kV)", 10.0, 35.0, st.session_state.v_p)
    freq = st.slider("Fréquence $f$ (Hz)", 1000, 25000, st.session_state.f_q)
    hum = st.slider("Humidité $H_2O$ (%)", 10, 95, 75)
    temp = st.slider("Température $T$ (°C)", 20, 250, 45)
    
    st.divider()
    st.header("📐 Géométrie du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)
    R_ext = st.number_input("Rayon externe Quartz (mm)", value=4.0)
    R_int = st.number_input("Rayon interne Quartz (mm)", value=2.5)
    n_r = st.number_input("Nombre de réacteurs (n)", value=2)

# =================================================================
# 4. MOTEUR DE CALCUL PHYSIQUE (MODÈLE DBD RIGOUREUX)
# =================================================================

# --- A. Constantes diélectriques ---
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8

# --- B. Tension de Seuil d'ionisation ---
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# --- C. Modélisation Capacitive ---
# Capacité de la barrière (Quartz)
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(R_ext / R_int)
# Capacité du Gap (Air)
C_gap = (2 * np.pi * EPS_0 * 1.0 * (L_act/1000)) / np.log((R_int) / (R_int - d_gap/1000))
# Capacité totale (avant décharge)
C_cell = (C_die * C_gap) / (C_die + C_gap)

# --- D. Puissance Active (Loi de Manley Calibrée) ---
if v_peak > v_th:
    # Puissance P = 4 * f * C_die * Vth * (Vp - Vth)
    p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * n_r
else:
    p_watt = 0.0

# --- E. Cinétique Chimique (Cibles : 72.89 ppm / 1.422 g/kWh) ---
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/75) * np.exp(-(temp - 45) / 200)

o3_ref = 2.64
o3_final = o3_ref * (p_watt / 2050.4) * (1 - hum/100) * np.exp(-(temp - 45) / 45)

if p_watt > 0.1:
    g_value = (oh_final * 40.0) / p_watt
else:
    g_value = 0.0

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (METRICS)
# =================================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Production ·OH", f"{oh_final:.2f} ppm")
col2.metric("Résiduel O3", f"{o3_final:.2f} ppm")
col3.metric("Puissance Active", f"{p_watt:.1f} W")
col4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

st.divider()

# =================================================================
# 6. ANALYSE GRAPHIQUE DYNAMIQUE
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("📊 Influence de la Tension sur les Espèces")
    
    v_range = np.linspace(10, 35, 100)
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000) * ((v - v_th) * 1000) * n_r) if v > v_th else 0 for v in v_range]
    
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH (ppm)", line=dict(color='#00FBFF', width=3)))
    fig_v.update_layout(template="plotly_dark", xaxis_title="Tension Crête (kV)", yaxis_title="Concentration (ppm)")
    st.plotly_chart(fig_v, use_container_width=True)

with g2:
    st.subheader("🌀 Figure de Lissajous (Cycle Q-V)")
    
    # Simulation du cycle de décharge réel
    t = np.linspace(0, 2*np.pi, 1000)
    v_t = v_peak * np.sin(t)
    v_dot = v_peak * freq * np.cos(t) # Dérivée pour l'orientation
    
    q_t = []
    for i in range(len(v_t)):
        v = v_t[i]
        # Phase de décharge (V > Vth ou V < -Vth)
        if abs(v) > v_th:
            # Pente = C_die (Capacité de la barrière seule)
            q = C_die * 1e6 * (v - np.sign(v)*v_th) + np.sign(v) * (C_cell * 1e6 * v_th)
        else:
            # Phase capacitive (V < Vth) - Pente = C_cell
            q = C_cell * 1e6 * v
        q_t.append(q)
    
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=v_t, y=q_t, fill="toself", line=dict(color='#ADFF2F', width=2)))
    fig_q.update_layout(template="plotly_dark", xaxis_title="Tension v(t) [kV]", yaxis_title="Charge q(t) [µC]")
    st.plotly_chart(fig_q, use_container_width=True)

# =================================================================
# 7. RÉCAPITULATIF TECHNIQUE (VALEURS CALCULÉES)
# =================================================================
with st.expander("📝 Détails de la Configuration du Réacteur"):
    st.write(f"**Tension de seuil calculée :** {v_th:.2f} kV")
    st.write(f"**Capacité Diélectrique ($C_{{die}}$) :** {C_die*1e12:.2f} pF")
    st.write(f"**Capacité du Gap ($C_{{gap}}$) :** {C_gap*1e12:.2f} pF")
    st.write(f"**Capacité Totale Cellule ($C_{{cell}}$) :** {C_cell*1e12:.2f} pF")

# =================================================================
# 8. BASES PHYSIQUES ET SÉCURITÉ
# =================================================================
with st.expander("📚 Équations Physiques du Modèle"):
    st.latex(r"P_{active} = 4 \cdot f \cdot C_{die} \cdot V_{th} \cdot (V_{peak} - V_{th})")
    st.latex(r"C_{die} = \frac{2\pi\epsilon_0\epsilon_{quartz} L}{\ln(R_{ext}/R_{int})}")
    st.write("Le modèle de Lissajous simule la transition entre la capacité géométrique du gaz et la capacité de la barrière quartz lors de l'amorçage.")

st.error("⚠️ **Sécurité :** Haute Tension (35kV). Production de radicaux oxydants. Ventilation requise.")
st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
