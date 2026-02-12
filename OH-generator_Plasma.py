import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO
from datetime import datetime

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Plasma Control - Électrotechnique UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# =================================================================
# 2. TITRE OFFICIEL
# =================================================================
# Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA
st.title("⚡ Start-up-OH Generator Plasma")
st.markdown("### Système Intelligent de Traitement des Fumées")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 3. BARRE LATÉRALE (SIDEBAR)
# =================================================================
with st.sidebar:
    st.header("📐 Dimensions du Réacteur (mm)")
    r_int = st.number_input("Rayon Électrode Interne (r_int) [mm]", value=2.5, step=0.1)
    e_q = st.number_input("Épaisseur Quartz (e) [mm]", value=1.5, step=0.1)
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0, step=0.1)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0, step=10.0)
    
    st.divider()
    st.header("🎮 Configuration Système")
    n_react = st.number_input("Nombre de réacteurs (n)", min_value=1, max_value=20, value=2)
    
    st.divider()
    st.header("⚙️ Paramètres Opérationnels")
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 23.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 75)
    temp = st.slider("Température (°C)", 20, 250, 45)
    
    st.divider()
    st.header("🚚 Transport des Radicaux")
    dist_cm = st.slider("Distance d'injection (cm)", 0, 50, 2)
    v_flux = st.slider("Vitesse du flux (m/s)", 1, 30, 20)

# =================================================================
# 4. MOTEUR PHYSIQUE (MODÈLE DE MANLEY & CHIMIE)
# =================================================================
EPS_0 = 8.854e-12
EPS_R = 3.8
V_TH = 13.5 # Tension de claquage du gaz (kV)

# Capacités du modèle (Loi de Gauss en cylindrique)
C_d = (2 * np.pi * EPS_0 * EPS_R * (L_act/1000)) / np.log((r_int + e_q)/r_int)
C_g = (2 * np.pi * EPS_0 * 1.0 * (L_act/1000)) / np.log((r_int + e_q + d_gap)/(r_int + e_q))
C_eq = (C_d * C_g) / (C_d + C_g)

# Signaux temporels
t = np.linspace(0, 1/freq, 1000)
V_t = v_peak * np.sin(2 * np.pi * freq * t)

# Modélisation de la Charge Q(t) - Cycle de décharge
Q_t = []
for v in V_t:
    if v > V_TH:
        # Gaz conducteur : la pente suit la capacité du diélectrique
        q = C_d * (v - V_TH) + C_eq * V_TH
    elif v < -V_TH:
        q = C_d * (v + V_TH) - C_eq * V_TH
    else:
        # Gaz isolant : la pente suit la capacité équivalente série
        q = C_eq * v
    Q_t.append(q * 1e6 * n_react)

Q_t = np.array(Q_t)

# Calcul de l'aire par la méthode Shoelace (Surface de Lissajous)
def get_lissajous_area(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

energie_mJ = get_lissajous_area(V_t, Q_t)
puissance_w = energie_mJ * (freq / 1000)

# --- CALCUL OH ---
ALPHA_OH = 1.6 # Coefficient de conversion
oh_init = (puissance_w * (hum/100) * ALPHA_OH) / (1 + (temp/800))
k_decay_oh = 80 * (1 + (temp / 100))
t_transit = (dist_cm / 100) / v_flux
oh_final = oh_init * np.exp(-k_decay_oh * t_transit)

# --- CALCUL OZONE (O3) ---
BETA_O3 = 0.35 # Coefficient de production O3
# Décomposition thermique : O3 chute radicalement quand T augmente
# Modèle exponentiel : décroissance rapide après 50°C
thermal_decay_o3 = np.exp(-(temp - 20) / 55) 
o3_init = (puissance_w * (1 - hum/100) * BETA_O3) * thermal_decay_o3
o3_final = max(0.0, o3_init)

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_final:.2f} ppm")
c3.metric("Puissance Réelle", f"{puissance_w:.1f} W")
c4.metric("Énergie / Cycle", f"{energie_mJ:.2f} mJ")

st.divider()

# =================================================================
# 6. VISUALISATION
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique I(V) du Plasma")
    
    v_plot = np.linspace(0, v_peak, 100)
    i_cond = np.where(v_plot > V_TH, 0.012 * (v_plot - V_TH)**1.6, 1e-6)
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_plot, y=i_cond * 1000 * n_react, fill='tozeroy', line=dict(color='#FF00FF', width=3)))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Courant (mA)", template="plotly_dark")
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("🌀 Figure de Lissajous (Diagnostic Q-V)")
    
    fig_liss = go.Figure()
    fig_liss.add_trace(go.Scatter(x=V_t, y=Q_t, fill="toself", line=dict(color='#ADFF2F', width=4)))
    fig_liss.update_layout(xaxis_title="Tension v(t) [kV]", yaxis_title="Charge q(t) [µC]", template="plotly_dark")
    st.plotly_chart(fig_liss, use_container_width=True)

# =================================================================
# 7. PIED DE PAGE ET ANALYSE
# =================================================================
st.info(f"💡 **Rappel Électrotechnique :** La surface de Lissajous représente l'énergie dissipée par claquage des micro-décharges. "
        f"À {temp}°C, l'Ozone est instable. Pour augmenter sa concentration, le refroidissement du réacteur est nécessaire.")

st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
