import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Plasma Control - Électrotechnique UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# --- CONNEXION FIREBASE SÉCURISÉE ---
if not firebase_admin._apps:
    try:
        fb_secrets = dict(st.secrets["firebase"])
        fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n").strip()
        
        cred = credentials.Certificate(fb_secrets)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.firebaseio.com/' 
        })
    except Exception as e:
        st.sidebar.error(f"⚠️ Mode Local (Firebase non connecté)")

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

    # QR Code
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Scanner pour Monitoring Mobile")

# =================================================================
# 4. MOTEUR DE CALCUL PHYSIQUE (MODÈLE DE MANLEY AMÉLIORÉ)
# =================================================================
EPS_0 = 8.854e-12
EPS_R = 3.8
V_TH = 13.5 # Seuil d'amorçage réaliste en kV

# Capacités
C_d = (2 * np.pi * EPS_0 * EPS_R * (L_act/1000)) / np.log((r_int + e_q)/r_int)
C_g = (2 * np.pi * EPS_0 * 1.0 * (L_act/1000)) / np.log((r_int + e_q + d_gap)/(r_int + e_q))
C_eq = (C_d * C_g) / (C_d + C_g)

# Signaux temporels
t = np.linspace(0, 1/freq, 1000)
V_t = v_peak * np.sin(2 * np.pi * freq * t)

# Génération de la boucle de charge Q(V)
Q_t = []
for v in V_t:
    if v > V_TH:
        q = C_d * (v - V_TH) + C_eq * V_TH
    elif v < -V_TH:
        q = C_d * (v + V_TH) - C_eq * V_TH
    else:
        q = C_eq * v
    Q_t.append(q * 1e6 * n_react) # Conversion en µC

Q_t = np.array(Q_t)

# Calcul de l'aire de Lissajous (Puissance)
def shoelace_area(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

energie_mJ = shoelace_area(V_t, Q_t)
puissance_w = energie_mJ * (freq / 1000)

# =================================================================
# 5. MODÈLES CHIMIQUES (OH ET O3)
# =================================================================

# --- MODÈLE OH ---
# Production favorisée par l'humidité et la puissance
ALPHA_OH = 1.45
oh_init = (puissance_w * (hum/100) * ALPHA_OH) / (1 + (temp/1000))
k_decay_oh = 85 * (1 + (temp / 100))
t_transit = (dist_cm / 100) / v_flux
oh_final = oh_init * np.exp(-k_decay_oh * t_transit)

# --- MODÈLE OZONE (O3) ---
# 1. L'ozone est produit par l'oxygène (inverse de l'humidité)
# 2. Sa décomposition thermique est exponentielle avec T (Loi d'Arrhenius simplifiée)
BETA_O3 = 0.25 # Coefficient de production
# Facteur de destruction thermique : k = A * exp(-Ea / RT)
# Ici simplifié : l'ozone chute de moitié tous les 50°C après 60°C
thermal_destruction = np.exp(-(temp - 20) / 60) 
o3_init = (puissance_w * (1 - hum/100) * BETA_O3) * thermal_destruction
o3_final = max(0.0, o3_init)

# =================================================================
# 6. INDICATEURS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_final:.2f} ppm")
c3.metric("Puissance Réelle", f"{puissance_w:.1f} W")
c4.metric("Énergie / Cycle", f"{energie_mJ:.2f} mJ")

st.divider()

# =================================================================
# 7. VISUALISATION
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique I(V) du Plasma")
    v_range = np.linspace(0, v_peak, 100)
    # Courant de conduction (filamentaire)
    i_cond = np.where(v_range > V_TH, 0.01 * (v_range - V_TH)**1.5, 0)
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_range, y=i_cond * 1000, fill='tozeroy', line=dict(color='#FF00FF', width=3)))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Courant (mA)", template="plotly_dark")
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("🌀 Figure de Lissajous (Diagnostic Q-V)")
    
    fig_liss = go.Figure()
    fig_liss.add_trace(go.Scatter(x=V_t, y=Q_t, fill="toself", line=dict(color='#ADFF2F', width=4)))
    fig_liss.update_layout(xaxis_title="Tension (kV)", yaxis_title="Charge (µC)", template="plotly_dark")
    st.plotly_chart(fig_liss, use_container_width=True)

# =================================================================
# 8. ANALYSE ET PIED DE PAGE
# =================================================================
st.info(f"💡 **Analyse du modèle :** À {temp}°C, le taux d'ozone est réduit par un facteur thermique de {thermal_destruction:.2f}. "
        "Pour augmenter l'ozone, baissez la température ou réduisez l'humidité.")

st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
