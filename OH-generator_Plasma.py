import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(page_title="Plasma Dynamics - UDL-SBA", layout="wide")

# TITRE OFFICIEL
st.title("⚡ Start-up-OH Generator Plasma")
st.markdown("### Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.caption(f"Optimisation IA - Département d'Électrotechnique - SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. PARAMÈTRES (SIDEBAR)
# =================================================================
with st.sidebar:
    st.header("⚙️ Paramètres Opérationnels")
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 23.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 75)
    temp = st.slider("Température (°C)", 20, 250, 45)
    
    st.divider()
    st.header("📐 Géométrie du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)
    n_r = st.number_input("Nombre de réacteurs (n)", value=2)

# =================================================================
# 3. MODÈLE MATHÉMATIQUE DYNAMIQUE (RELATIONS FONDAMENTALES)
# =================================================================

# --- A. Seuil d'ionisation ---
V_seuil = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# --- B. Calcul de la Puissance (Loi de Manley) ---
if v_peak > V_seuil:
    # Capacité estimée du Quartz
    C_q = 80e-12 * (L_act / 150) 
    # Relation fondamentale : P = 4 * f * Cq * Vth * (Vp - Vth)
    p_watt = 4 * freq * C_q * (V_seuil * 1000) * (v_peak - V_seuil) * 1000 * n_r
    p_watt = p_watt / 1.5 # Facteur de perte réelle
else:
    p_watt = 0.0

# --- C. Production OH (Dynamique Empirique) ---
# OH est sensible à la densité d'énergie et à l'humidité
k_oh = 0.12 
oh_base = k_oh * (max(0, p_watt)**0.85) * (hum/100)
# Décroissance naturelle légère avec T
oh_final = oh_base * np.exp(-(temp - 20) / 180)

# --- D. Production O3 (Décomposition Thermique) ---
k_o3 = 0.08
o3_base = k_o3 * (max(0, p_watt)**0.75) * (1 - hum/100)
# Relation fondamentale de décomposition thermique de l'ozone
destruction_o3 = np.exp(-(temp - 20) / 45) 
o3_final = o3_base * destruction_o3 if v_peak > V_seuil else 0.0

# =================================================================
# 4. AFFICHAGE DES RÉSULTATS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_final:.2f} ppm")
c3.metric("Puissance active", f"{p_watt:.1f} W")
c4.metric("E/V (Champ moy.)", f"{v_peak/d_gap:.2f} kV/mm")

st.divider()

# =================================================================
# 5. GRAPHIQUE D'INFLUENCE DYNAMIQUE
# =================================================================
st.subheader("📊 Dynamique de Production vs Tension")


v_range = np.linspace(10, 35, 100)
oh_curve = []
o3_curve = []

for v in v_range:
    if v > V_seuil:
        p = 4 * freq * C_q * (V_seuil * 1000) * (v - V_seuil) * 1000 * n_r / 1.5
        oh = (k_oh * (max(0, p)**0.85) * (hum/100)) * np.exp(-(temp - 20) / 180)
        o3 = (k_o3 * (max(0, p)**0.75) * (1 - hum/100)) * np.exp(-(temp - 20) / 45)
    else:
        oh, o3 = 0, 0
    oh_curve.append(oh)
    o3_curve.append(o3)

fig = go.Figure()
fig.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH (ppm)", line=dict(color='#00FBFF', width=3)))
fig.add_trace(go.Scatter(x=v_range, y=o3_curve, name="O3 (ppm)", line=dict(color='orange', width=3)))
fig.add_vline(x=v_peak, line_dash="dash", line_color="white", annotation_text=f"Point actuel: {v_peak}kV")
fig.update_layout(xaxis_title="Tension Crête (kV)", yaxis_title="Concentration (ppm)", template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# =================================================================
# 6. RÉCAPITULATIF (Disposition mémorisée)
# =================================================================
st.subheader("📋 État du Système")
# Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
data_table = {
    "Enseignements": ["Analyse Radicaux", "Stabilité Ozone"],
    "Code": ["OH-DYN", "O3-THERM"],
    "Enseignants": ["Labo SBA", "Électrotechnique"],
    "Horaire": [f"{v_peak} kV", f"{temp} °C"],
    "Jours": ["S2-2026", "S2-2026"],
    "Lieu": ["S06", "S06"],
    "Promotion": ["M2RE", "M2RE"]
}
st.table(pd.DataFrame(data_table))

st.info("💡 **Expertise SBA :** Notez que la courbe d'Ozone (orange) s'aplatit très vite si vous augmentez la température, tandis que les OH restent plus stables.")
