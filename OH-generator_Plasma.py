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
    page_title="Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Rafraîchissement automatique toutes les 2 secondes pour le temps réel Cloud
st_autorefresh(interval=2000, key="datarefresh")

# Titre officiel du projet
st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Données Mixtes : Capteurs & Modèles)")
st.caption("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.info(f"📅 Date du jour : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. CONNEXION FIREBASE
# =================================================================
@st.cache_resource
def initialiser_firebase():
    """Initialise la connexion Firebase via Secrets ou JSON local"""
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                fb_secrets = dict(st.secrets["firebase"])
                if "private_key" in fb_secrets:
                    fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(fb_secrets)
            else:
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur Firebase : {e}")
        return False

# Initialisation des états
if 'last_temp' not in st.session_state:
    st.session_state.last_temp = 23.0
if 'last_hum' not in st.session_state:
    st.session_state.last_hum = 45.0

# =================================================================
# 3. BARRE LATÉRALE : PARAMÈTRES
# =================================================================
with st.sidebar:
    st.header("🎮 Contrôle du Système")
    mode_experimental = st.toggle("🚀 Activer Mode Expérimental (Wemos D1)", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Réception [MESURÉE]")
        if initialiser_firebase():
            try:
                ref = db.reference('/EDT_SBA')
                data_cloud = ref.get()
                if data_cloud:
                    st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                    st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
                    st.success("✅ Capteurs en ligne")
                else:
                    st.warning("⏳ Attente de données...")
            except Exception as e:
                st.error(f"Erreur flux : {e}")
        
        # Valeurs Capteurs (Mesurées)
        temp = st.session_state.last_temp
        hum = st.session_state.last_hum
        # Valeurs Fixes (Simulées en mode réel)
        v_peak = 23.0
        freq = 15000.0
        
    else:
        st.header("💻 Mode [SIMULATION]")
        v_peak = st.slider("Tension Crête Vp (kV) [SIM]", 10.0, 35.0, 23.0)
        freq = st.slider("Fréquence f (Hz) [SIM]", 1000.0, 25000.0, 15000.0)
        temp = st.slider("Température T (°C) [SIM]", 20.0, 100.0, 25.0)
        hum = st.slider("Humidité H2O (%) [SIM]", 10.0, 95.0, 50.0)
    
    st.divider()
    st.header("📐 Géométrie [SIMULÉE]")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0, step=0.1)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0, step=1.0)

# =================================================================
# 4. CALCULS PHYSIQUES [SIMULÉS]
# =================================================================
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000.0)) / np.log(R_ext / R_int)

if v_peak > v_th:
    p_watt = 4 * freq * C_die * (v_th * 1000.0) * ((v_peak - v_th) * 1000.0) * 2
else:
    p_watt = 0.0

k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/100.0) * np.exp(-(temp - 25.0) / 150.0)

k_o3 = 0.00129 
o3_final = k_o3 * p_watt * (1.0 - hum/100.0) * np.exp(-(temp - 25.0) / 45.0) if v_peak > v_th else 0.0

total = oh_final + o3_final
pct_oh = (oh_final / total * 100.0) if total > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 5. AFFICHAGE : DISTINCTION MESURÉ VS SIMULÉ
# =================================================================
st.subheader(f"Statut : {'🔴 MODE RÉEL (WEMOS D1)' if mode_experimental else '🔵 MODE SIMULATION'}")

# Section Données Environnementales (Capteurs si Experimental, sinon Slider)
st.markdown("#### 🧪 Paramètres Environnementaux " + ("**[MESURÉS]**" if mode_experimental else "**[SIMULÉS]**"))
m_col1, m_col2 = st.columns(2)
m_col1.metric("Température", f"{temp:.1f} °C", delta=f"{temp-25:.1f}°")
m_col2.metric("Humidité relative", f"{hum:.1f} %")

st.write("") # Espacement

# Section Résultats Physico-Chimiques (Toujours Simulés/Calculés)
st.markdown("#### ⚡ Résultats Physico-Chimiques **[SIMULÉS]**")
c_col1, c_col2, c_col3, c_col4 = st.columns(4)
c_col1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
c_col2.metric("Production O3", f"{o3_final:.2f} ppm")
c_col3.metric("Puissance active", f"{p_watt:.1f} W")
c_col4.metric("Efficacité (G-Value)", f"{g_value:.3f} g/kWh")

st.divider()

# =================================================================
# 6. ANALYSE GRAPHIQUE
# =================================================================
graph_left, graph_right = st.columns(2)

with graph_left:
    st.subheader("🌀 Cycle de Charge [SIMULÉ]")
    t_vals = np.linspace(0, 2*np.pi, 500)
    v_axis = v_peak * np.sin(t_vals)
    q_axis = (C_die * 1e6 * v_peak) * np.cos(t_vals) 
    fig_lis = go.Figure(go.Scatter(x=v_axis, y=q_axis, fill="toself", line=dict(color='#ADFF2F')))
    fig_lis.update_layout(template="plotly_dark", xaxis_title="U (kV)", yaxis_title="Q (µC)")
    st.plotly_chart(fig_lis, use_container_width=True)

with graph_right:
    st.subheader("📊 Modèle Cinétique [SIMULÉ]")
    v_range = np.linspace(10, 35, 100)
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000.0) * ((v - v_th) * 1000.0) * 2) if v > v_th else 0 for v in v_range]
    fig_oh = go.Figure(go.Scatter(x=v_range, y=oh_curve, line=dict(color='#00FBFF', width=3)))
    fig_oh.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="·OH (ppm)")
    st.plotly_chart(fig_oh, use_container_width=True)

# =================================================================
# 7. PIED DE PAGE
# =================================================================
st.warning("⚠️ Sécurité : Risque de Haute Tension. Système sous surveillance du Département d'Électrotechnique.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<center><b>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</b></center>", 
    unsafe_allow_html=True
)
