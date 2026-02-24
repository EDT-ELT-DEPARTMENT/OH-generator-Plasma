import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from streamlit_autorefresh import st_autorefresh

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Plateforme de gestion-S2-2026-Département d'Électrotechnique-UDL-SBA",
    layout="wide"
)

# Rafraîchissement automatique toutes les 2 secondes (pour le temps réel Cloud)
st_autorefresh(interval=2000, key="datarefresh")

st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.info(f"📅 Date du jour : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. CONNEXION FIREBASE (COMPATIBLE LOCAL ET CLOUD)
# =================================================================
@st.cache_resource
def initialiser_firebase():
    """Initialise la connexion Firebase via Secrets (Cloud) ou JSON (Local)"""
    try:
        if not firebase_admin._apps:
            # Priorité 1 : Streamlit Cloud Secrets
            if "firebase" in st.secrets:
                fb_secrets = dict(st.secrets["firebase"])
                # Nettoyage de la clé privée pour les sauts de ligne
                if "private_key" in fb_secrets:
                    fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(fb_secrets)
            
            # Priorité 2 : Fichier local JSON
            else:
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion Firebase : {e}")
        return False

# Initialisation de la mémoire de l'interface
if 'last_temp' not in st.session_state:
    st.session_state.last_temp = 23.0
if 'last_hum' not in st.session_state:
    st.session_state.last_hum = 45.0

# =================================================================
# 3. BARRE LATÉRALE : PARAMÈTRES ET MODES
# =================================================================
with st.sidebar:
    st.header("🎮 Contrôle du Système")
    mode_experimental = st.toggle("🚀 Activer Mode Expérimental (Wemos D1)", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Réception Cloud")
        if initialiser_firebase():
            try:
                # Récupération du chemin /EDT_SBA défini dans ton Arduino
                ref = db.reference('/EDT_SBA')
                data_cloud = ref.get()
                
                if data_cloud:
                    st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                    st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
                    st.success("✅ Wemos connectée")
                else:
                    st.warning("⏳ En attente de données...")
            except Exception as e:
                st.error(f"Erreur de flux : {e}")
        
        temp = st.session_state.last_temp
        hum = st.session_state.last_hum
        v_peak = 23.0  # Valeur nominale pour le réacteur
        freq = 15000.0 # Fréquence standard
        
    else:
        st.header("💻 Mode Simulation")
        v_peak = st.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.slider("Fréquence f (Hz)", 1000.0, 25000.0, 15000.0)
        temp = st.slider("Température T (°C)", 20.0, 100.0, 25.0)
        hum = st.slider("Humidité H2O (%)", 10.0, 95.0, 50.0)
    
    st.divider()
    st.header("📐 Paramètres du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)

# =================================================================
# 4. MODÉLISATION PHYSIQUE DU PLASMA (DBD)
# =================================================================
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

# Tension de seuil (Breakdown)
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# Capacité diélectrique
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000.0)) / np.log(R_ext / R_int)

# Puissance dissipée (Formule de Manley)
p_watt = 4 * freq * C_die * (v_th * 1000.0) * ((v_peak - v_th) * 1000.0) * 2 if v_peak > v_th else 0.0

# Cinétique chimique simplifiée
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/100.0) * np.exp(-(temp - 25.0) / 150.0)

k_o3 = 0.00129 
o3_final = k_o3 * p_watt * (1.0 - hum/100.0) * np.exp(-(temp - 25.0) / 45.0) if v_peak > v_th else 0.0

total = oh_final + o3_final
pct_oh = (oh_final / total * 100.0) if total > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (MÉTRIQUES)
# =================================================================
label_display = "🔴 RÉEL (WEMOS)" if mode_experimental else "🔵 SIMULATION"
st.subheader(f"Statut : {label_display}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
m2.metric("Production O3", f"{o3_final:.2f} ppm")
m3.metric("Puissance Active", f"{p_watt:.1f} W")
m4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

m5, m6, m7, m8 = st.columns(4)
m5.metric("Fréquence", f"{freq:.0f} Hz")
m6.metric("Température", f"{temp:.1f} °C", delta=f"{temp-25:.1f}°")
m7.metric("Humidité", f"{hum:.1f} %")
m8.metric("V-Théorique", f"{v_th:.2f} kV")

st.divider()

# =================================================================
# 6. ANALYSE GRAPHIQUE (LISSajous & RENDEMENT)
# =================================================================
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("🌀 Cycle de Charge (Lissajous)")
    t = np.linspace(0, 2*np.pi, 500)
    v_axis = v_peak * np.sin(t)
    q_axis = (C_die * 1e6 * v_peak) * np.cos(t) 
    
    fig_lis = go.Figure(go.Scatter(x=v_axis, y=q_axis, fill="toself", line=dict(color='#ADFF2F')))
    fig_lis.update_layout(template="plotly_dark", xaxis_title="U (kV)", yaxis_title="Q (µC)")
    st.plotly_chart(fig_lis, use_container_width=True)

with right_col:
    st.subheader("📊 Courbe de Production ·OH")
    v_vec = np.linspace(10, 35, 100)
    oh_vec = [k_oh * (4 * freq * C_die * (v_th * 1000.0) * ((v - v_th) * 1000.0) * 2) if v > v_th else 0 for v in v_vec]
    
    fig_oh = go.Figure(go.Scatter(x=v_vec, y=oh_vec, name="·OH", line=dict(color='#00FBFF')))
    fig_oh.update_layout(template="plotly_dark", xaxis_title="V_peak (kV)", yaxis_title="·OH (ppm)")
    st.plotly_chart(fig_oh, use_container_width=True)

# =================================================================
# PIED DE PAGE ET SÉCURITÉ
# =================================================================
st.error("⚠️ Attention : Risque de Haute Tension et d'émanations d'Ozone (O3).")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<center><b>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</b></center>", unsafe_allow_html=True)
