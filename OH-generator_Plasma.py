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

# Rafraîchissement automatique toutes les 2 secondes pour le temps réel
st_autorefresh(interval=2000, key="datarefresh")

# Titre imposé par la charte du département
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
                # Nettoyage de la clé privée pour gérer les sauts de ligne du format RSA
                if "private_key" in fb_secrets:
                    fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(fb_secrets)
            
            # Priorité 2 : Fichier local JSON (votre-cle.json)
            else:
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion Firebase : {e}")
        return False

# Initialisation des variables d'état pour éviter les erreurs de rafraîchissement
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
                # Récupération de la référence EDT_SBA (Chemin Firebase)
                ref = db.reference('/EDT_SBA')
                data_cloud = ref.get()
                
                if data_cloud:
                    # Extraction sécurisée des données avec valeurs par défaut
                    st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                    st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
                    st.success("✅ Wemos connectée (Données Cloud)")
                else:
                    st.warning("⏳ En attente de données Cloud...")
            except Exception as e:
                st.error(f"Erreur de flux : {e}")
        
        # En mode réel, les variables sont imposées par le capteur
        temp = st.session_state.last_temp
        hum = st.session_state.last_hum
        v_peak = 23.0  # Valeur fixe pour le réacteur en test réel
        freq = 15000.0 # Fréquence de résonance nominale
        
    else:
        st.header("💻 Mode Simulation")
        v_peak = st.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.slider("Fréquence f (Hz)", 1000.0, 25000.0, 15000.0)
        temp = st.slider("Température T (°C)", 20.0, 100.0, 25.0)
        hum = st.slider("Humidité H2O (%)", 10.0, 95.0, 50.0)
    
    st.divider()
    st.header("📐 Paramètres du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0, step=0.1)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0, step=1.0)

# =================================================================
# 4. MODÉLISATION PHYSIQUE DU PLASMA (DBD)
# =================================================================
# Constantes physiques
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

# Calcul de la tension de seuil (Breakdown Voltage)
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# Calcul de la capacité du diélectrique (Quartz)
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000.0)) / np.log(R_ext / R_int)

# Calcul de la puissance selon Manley (en Watts)
if v_peak > v_th:
    p_watt = 4 * freq * C_die * (v_th * 1000.0) * ((v_peak - v_th) * 1000.0) * 2
else:
    p_watt = 0.0

# Cinétique chimique approximative
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/100.0) * np.exp(-(temp - 25.0) / 150.0)

k_o3 = 0.00129 
if v_peak > v_th:
    o3_final = k_o3 * p_watt * (1.0 - hum/100.0) * np.exp(-(temp - 25.0) / 45.0)
else:
    o3_final = 0.0

# Métriques de rendement
total = oh_final + o3_final
pct_oh = (oh_final / total * 100.0) if total > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (MÉTRIQUES)
# =================================================================
label_display = "🔴 MODE EXPÉRIMENTAL (WEMOS D1)" if mode_experimental else "🔵 MODE SIMULATION"
st.subheader(f"Statut actuel : {label_display}")

# Première ligne de métriques
col1, col2, col3, col4 = st.columns(4)
col1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
col2.metric("Production O3", f"{o3_final:.2f} ppm")
col3.metric("Puissance Active", f"{p_watt:.1f} W")
col4.metric("G-Value (OH)", f"{g_value:.3f} g/kWh")

# Deuxième ligne de métriques
col5, col6, col7, col8 = st.columns(4)
col5.metric("Fréquence", f"{freq:.0f} Hz")
col6.metric("Température", f"{temp:.1f} °C", delta=f"{temp-25:.1f}°")
col7.metric("Humidité", f"{hum:.1f} %")
col8.metric("V-Threshold", f"{v_th:.2f} kV")

st.divider()

# =================================================================
# 6. ANALYSE GRAPHIQUE (LISSAJOUS & CINETIQUE)
# =================================================================
graph_left, graph_right = st.columns(2)

with graph_left:
    st.subheader("🌀 Cycle de Charge (Lissajous)")
    t_vals = np.linspace(0, 2*np.pi, 500)
    v_axis = v_peak * np.sin(t_vals)
    q_axis = (C_die * 1e6 * v_peak) * np.cos(t_vals) 
    
    fig_lis = go.Figure(go.Scatter(x=v_axis, y=q_axis, fill="toself", line=dict(color='#ADFF2F'), name="Lissajous"))
    fig_lis.update_layout(
        template="plotly_dark", 
        xaxis_title="U (kV)", 
        yaxis_title="Q (µC)",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_lis, use_container_width=True)

with graph_right:
    st.subheader("📊 Courbe de Production ·OH")
    v_range = np.linspace(10, 35, 100)
    # Calcul dynamique de la courbe
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000.0) * ((v - v_th) * 1000.0) * 2) if v > v_th else 0 for v in v_range]
    
    fig_oh = go.Figure(go.Scatter(x=v_range, y=oh_curve, name="Concentration ·OH", line=dict(color='#00FBFF', width=3)))
    fig_oh.update_layout(
        template="plotly_dark", 
        xaxis_title="V_peak (kV)", 
        yaxis_title="·OH (ppm)",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_oh, use_container_width=True)

# =================================================================
# 7. PIED DE PAGE ET SÉCURITÉ
# =================================================================
st.warning("⚠️ Attention : Risque de Haute Tension et d'émanations d'Ozone (O3). Manipulation réservée au personnel du laboratoire.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<center><b>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</b></center>", 
    unsafe_allow_html=True
)
