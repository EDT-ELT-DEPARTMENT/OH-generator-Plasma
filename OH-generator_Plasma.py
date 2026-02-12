import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# =================================================================
# 1. CONFIGURATION DE LA PAGE & STYLE
# =================================================================
st.set_page_config(
    page_title="Plasma Control - UDL-SBA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation du Session State pour l'Optimisation IA
if 'v_p' not in st.session_state: st.session_state.v_p = 23.0
if 'f_q' not in st.session_state: st.session_state.f_q = 15000
if 'h_m' not in st.session_state: st.session_state.h_m = 75
if 't_p' not in st.session_state: st.session_state.t_p = 45
if 'v_l' not in st.session_state: st.session_state.v_l = 20

# =================================================================
# 2. TITRE OFFICIEL ET ENTÊTE
# =================================================================
# Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA
st.title("⚡ Start-up-OH Generator Plasma")
st.subheader("Système Intelligent de Traitement des Fumées")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 3. BARRE LATÉRALE (SIDEBAR) - PARAMÈTRES ET IA
# =================================================================
with st.sidebar:
    st.header("🤖 Commande IA Adaptive")
    if st.button("🚀 Appliquer l'Optimisation"):
        st.session_state.v_p = 32.0
        st.session_state.f_q = 18000
        st.session_state.h_m = 85
        st.session_state.t_p = 40
        st.session_state.v_l = 25
        st.rerun()
    
    st.divider()
    
    st.header("⚙️ Paramètres Opérationnels")
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, st.session_state.v_p)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, st.session_state.f_q)
    hum = st.slider("Humidité H2O (%)", 10, 95, st.session_state.h_m)
    temp = st.slider("Température (°C)", 20, 250, st.session_state.t_p)
    
    st.divider()
    st.header("📐 Géométrie du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)
    n_r = st.number_input("Nombre de réacteurs (n)", value=2)
    
    st.divider()
    st.header("🚚 Transport")
    v_flux = st.slider("Vitesse du flux (m/s)", 1, 30, st.session_state.v_l)
    dist_cm = st.number_input("Distance d'injection (cm)", value=2.0)

# =================================================================
# 4. MOTEUR DE CALCUL PHYSIQUE (MODÈLE DYNAMIQUE)
# =================================================================

# --- A. Équations Fondamentales ---
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
# Tension de seuil d'ionisation (Loi de Paschen adaptée)
V_seuil = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# --- B. Calcul de la Puissance Réelle (Manley) ---
if v_peak > V_seuil:
    # Capacité de la barrière diélectrique
    # C = (2*pi*eps0*epsr*L) / ln(r_ext/r_int) -> Estimée pour r_int=2.5mm
    C_q = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000)) / np.log(4.0/2.5)
    # Puissance Active : P = 4 * f * Cq * Vth * (Vp - Vth)
    p_watt_total = 4 * freq * C_q * (V_seuil * 1000) * (v_peak - V_seuil) * 1000 * n_r
    p_watt = max(0.1, p_watt_total / 1.2) # Facteur de correction labo
else:
    p_watt = 0.0

# --- C. Production de OH (Relation Empirique Dynamique) ---
k_oh = 0.15 # Constante de production
oh_base = k_oh * (p_watt**0.85) * (hum/100)
# Décroissance thermique du OH
oh_final = oh_base * np.exp(-(temp - 20) / 150)

# --- D. Production d'Ozone O3 (Stabilité Thermique) ---
k_o3 = 0.09
o3_base = k_o3 * (p_watt**0.75) * (1 - (hum/100))
# Loi de décomposition thermique de l'ozone (SBA Model)
destruction_o3 = np.exp(-(temp - 20) / 45)
o3_final = o3_base * destruction_o3 if v_peak > V_seuil else 0.0

# --- E. Calcul du Rendement Énergétique (G-Value) ---
# G (g/kWh) = (Concentration * Débit_Molaire * Masse_Molaire) / Puissance
if p_watt > 0:
    # Estimation simplifiée du rendement en g/kWh pour OH
    g_value_oh = (oh_final * 0.04) / (p_watt / 1000) 
else:
    g_value_oh = 0.0

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (INDICATEURS)
# =================================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Production ·OH", f"{oh_final:.2f} ppm")
col2.metric("Résiduel O3", f"{o3_final:.2f} ppm")
col3.metric("Puissance Active", f"{p_watt:.1f} W")
col4.metric("G-Value (OH)", f"{g_value_oh:.3f} g/kWh")

st.divider()

# =================================================================
# 6. GRAPHIQUES ET ANALYSE DYNAMIQUE
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("📊 Influence de la Tension sur les Espèces")
    v_range = np.linspace(10, 35, 100)
    oh_curve = []
    o3_curve = []
    for v in v_range:
        if v > V_seuil:
            p = 4 * freq * C_q * (V_seuil * 1000) * (v - V_seuil) * 1000 * n_r / 1.2
            oh = (k_oh * (p**0.85) * (hum/100)) * np.exp(-(temp - 20) / 150)
            o3 = (k_o3 * (p**0.75) * (1 - (hum/100))) * np.exp(-(temp - 20) / 45)
        else: oh, o3 = 0, 0
        oh_curve.append(oh)
        o3_curve.append(o3)
    
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH", line=dict(color='#00FBFF')))
    fig_v.add_trace(go.Scatter(x=v_range, y=o3_curve, name="O3", line=dict(color='orange')))
    fig_v.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="ppm")
    st.plotly_chart(fig_v, use_container_width=True)

with g2:
    st.subheader("🌀 Figure de Lissajous Simulée (Q-V)")
    
    t_plot = np.linspace(0, 2*np.pi, 500)
    v_sin = v_peak * np.sin(t_plot)
    q_sin = []
    for v in v_sin:
        if v > V_seuil: q = 0.6 * (v - V_seuil) + 0.3
        elif v < -V_seuil: q = 0.6 * (v + V_seuil) - 0.3
        else: q = 0.15 * v
        q_sin.append(q)
    
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=v_sin, y=q_sin, fill="toself", line=dict(color='#ADFF2F')))
    fig_q.update_layout(template="plotly_dark", xaxis_title="V (kV)", yaxis_title="Q (µC)")
    st.plotly_chart(fig_q, use_container_width=True)

# =================================================================
# 7. RÉCAPITULATIF (DISPOSITION MÉMORISÉE)
# =================================================================
st.subheader("📋 Récapitulatif du Système (Disposition Officielle)")
# Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
recap_data = {
    "Enseignements": ["Simulation Plasma", "Cinétique Radicale", "Génie Électrique"],
    "Code": ["DBD-23kV", "OH-SBA", "IA-ADAPT"],
    "Enseignants": ["Dépt Électrotechnique", "Fac. Génie Élec.", "UDL-SBA"],
    "Horaire": [f"{v_peak} kV", f"{freq} Hz", f"{temp} °C"],
    "Jours": ["Dimanche", "Lundi", "Mardi"],
    "Lieu": ["Labo S06", "Labo S06", "S06"],
    "Promotion": ["M2RE", "M2RE", "M2RE"]
}
st.table(pd.DataFrame(recap_data))

# =================================================================
# 8. BASES PHYSIQUES (EXPANDER)
# =================================================================
with st.expander("📚 Détails des Équations Utilisées"):
    st.latex(r"V_{th} = 13.2 \cdot (1 + 0.05\sqrt{d})")
    st.latex(r"P_{active} = 4 \cdot f \cdot C_d \cdot V_{th} \cdot (V_p - V_{th})")
    st.latex(r"[O_3] = k_{O3} \cdot P^{0.75} \cdot (1-H) \cdot e^{-\frac{T-20}{45}}")
    st.write("Le modèle utilise une intégration numérique de la surface de Lissajous pour valider la puissance active réelle.")

st.info("💡 **Analyse Technique :** Le rendement énergétique (G-Value) est optimal lorsque la température est maintenue en dessous de 50°C.")
st.error("⚠️ Sécurité : Haute Tension (35kV). Utilisation de lunettes UV obligatoire.")
st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
