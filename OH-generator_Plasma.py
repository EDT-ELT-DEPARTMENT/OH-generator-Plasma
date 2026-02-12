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
    rayon_interne = st.number_input("Rayon Électrode Interne (r_int) [mm]", value=2.5, step=0.1)
    epaisseur_dielectrique = st.number_input("Épaisseur Quartz (e) [mm]", value=1.5, step=0.1)
    gap_gaz = st.number_input("Gap de décharge (d) [mm]", value=3.0, step=0.1)
    longueur_decharge = st.number_input("Longueur Active (L) [mm]", value=150.0, step=10.0)
    
    st.divider()
    st.header("🎮 Configuration Système")
    nb_reacteurs = st.number_input("Nombre de réacteurs (n)", min_value=1, max_value=20, value=2)
    
    st.divider()
    st.header("⚙️ Paramètres Opérationnels")
    
    # Valeur par défaut forcée à 23 kV pour ton test actuel
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 23.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 75)
    temp = st.slider("Température (°C)", 20, 250, 45)
    
    st.divider()
    st.header("🚚 Transport des Radicaux")
    dist_cm = st.slider("Distance d'injection (cm)", 0, 50, 2)
    v_flux = st.slider("Vitesse du flux (m/s)", 1, 30, 20)

# =================================================================
# 4. MOTEUR DE CALCUL PHYSIQUE "HIGH-YIELD"
# =================================================================
EPS_R = 3.8  
EPS_0 = 8.854e-12
V_AMORCAGE = 14.0 # Tension où le plasma commence à consommer du courant

# 1. Capacité du Quartz (Barrière)
C_quartz = (2 * np.pi * EPS_0 * EPS_R * (longueur_decharge/1000)) / np.log((rayon_interne + epaisseur_dielectrique)/rayon_interne)
# 2. Capacité du Gap de Gaz
C_gap = (2 * np.pi * EPS_0 * 1.0 * (longueur_decharge/1000)) / np.log((rayon_interne + epaisseur_dielectrique + gap_gaz)/(rayon_interne + epaisseur_dielectrique))
# Capacité équivalente (série)
C_cell = (C_quartz * C_gap) / (C_quartz + C_gap)

# 3. Simulation Lissajous Réaliste
t = np.linspace(0, 1/freq, 1000)
V_t = v_peak * np.sin(2 * np.pi * freq * t)

# Facteur de transfert de charge (ouvre la boucle de Lissajous)
# Si V > V_AMORCAGE, on simule le courant de décharge
charge_conductrice = 0
if v_peak > V_AMORCAGE:
    # On calcule l'ouverture de la boucle (parallélogramme)
    charge_conductrice = (C_quartz * (v_peak - V_AMORCAGE) * 2.0) # Facteur de gain x2

# Simulation de la boucle Q(V)
# Composante capacitive + Composante dissipative (plasma)
Q_t = (C_cell * nb_reacteurs * 1e6) * V_t + (charge_conductrice * 1e6 * nb_reacteurs) * np.tanh(10 * np.sin(2 * np.pi * freq * t))

# 4. Calcul de la Puissance par Intégration de Surface
if hasattr(np, 'trapezoid'):
    energie_mJ = np.abs(np.trapezoid(Q_t, V_t))
else:
    energie_mJ = np.abs(np.trapz(Q_t, V_t))

puissance_reelle = energie_mJ * (freq / 1000)

# 5. Modèle de Production Chimique Recalibré
# On augmente ALPHA car le plasma est maintenant "chaud" électriquement
ALPHA_VRAI = 1.2 
oh_initial = (puissance_reelle * (hum/100) * ALPHA_VRAI) / (1 + (temp/1000))
o3_ppm = (puissance_reelle * (1 - hum/100) * 0.12) * np.exp(-temp / 60)

# Décroissance temporelle
t_transit = (dist_cm / 100) / v_flux
k_decay = 75 * (1 + (temp / 100))
oh_final = oh_initial * np.exp(-k_decay * t_transit)

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm")
c3.metric("Puissance Réelle", f"{puissance_reelle:.1f} W")
c4.metric("Énergie / Cycle", f"{energie_mJ:.2f} mJ")

st.divider()

# =================================================================
# 6. GRAPHIQUES
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique de Décharge I(V)")
    v_plot = np.linspace(0, v_peak, 100)
    i_plot = np.where(v_plot > V_AMORCAGE, 0.005 * (v_plot - V_AMORCAGE)**2, 1e-6)
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_plot, y=i_plot * 1000 * nb_reacteurs, fill='tozeroy', line=dict(color='#FF00FF')))
    fig_iv.update_layout(xaxis_title="V (kV)", yaxis_title="I (mA)", template="plotly_dark", height=350)
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("🌀 Analyse de Lissajous (Q-V)")
    
    fig_liss = go.Figure()
    fig_liss.add_trace(go.Scatter(x=V_t, y=Q_t, fill="toself", line=dict(color='#ADFF2F', width=4)))
    fig_liss.update_layout(xaxis_title="Tension (kV)", yaxis_title="Charge (µC)", template="plotly_dark", height=350)
    st.plotly_chart(fig_liss, use_container_width=True)

# =================================================================
# 7. PIED DE PAGE
# =================================================================
st.info(f"💡 **Analyse SBA :** À {v_peak} kV, le champ électrique moyen est de {v_peak/gap_gaz:.2f} kV/mm. "
        f"L'air est en régime de décharge filamentaire active.")
st.markdown("<center>© 2026 OH-generator Plasma - UDL-SBA</center>", unsafe_allow_html=True)
