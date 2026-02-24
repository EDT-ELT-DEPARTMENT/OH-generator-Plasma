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
    page_title="Plateforme de gestion-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA",
    layout="wide"
)

# Rafraîchissement automatique toutes les 2 secondes pour le temps réel
st_autorefresh(interval=2000, key="datarefresh")

st.title("⚡ Plateforme de monitoring à distance de la génération des oxcidants hybrides OH-/O3")
st.markdown("### Unité de Contrôle Hybride (Simulation & Expérimental)")
st.caption(f"Département d'Électrotechnique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. CONNEXION FIREBASE (VERSION HYBRIDE PC/CLOUD)
# =================================================================
@st.cache_resource
def initialiser_firebase():
    """Initialise Firebase en local ou sur Streamlit Cloud"""
    try:
        if not firebase_admin._apps:
            # 1. Test si on est sur Streamlit Cloud (utilisation des Secrets)
            if "firebase" in st.secrets:
                fb_secrets = dict(st.secrets["firebase"])
                # Correction pour les sauts de ligne de la clé privée
                if "private_key" in fb_secrets:
                    fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(fb_secrets)
            
            # 2. Sinon, utilisation du fichier local pour tes tests PC
            else:
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur d'initialisation : {e}")
        return False

# Initialisation des variables de session (mémoire de l'interface)
if 'last_temp' not in st.session_state:
    st.session_state.last_temp = 23.0
if 'last_hum' not in st.session_state:
    st.session_state.last_hum = 45.0

# =================================================================
# 3. BARRE LATÉRALE : CONTRÔLE ET MODES
# =================================================================
with st.sidebar:
    st.header("🎮 Mode de Fonctionnement")
    mode_experimental = st.toggle("🚀 Passer en Mode Expérimental (Wemos D1)", value=False)
    
    st.divider()
    
    if mode_experimental:
        st.header("🔌 Données en Direct (Cloud)")
        if initialiser_firebase():
            try:
                # Récupération depuis le chemin défini dans ton code Arduino
                ref = db.reference('/EDT_SBA')
                data_cloud = ref.get()
                
                if data_cloud:
                    st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                    st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
                    st.success("✅ Données Wemos reçues")
                else:
                    st.warning("⏳ En attente de données Firebase...")
            except Exception as e:
                st.error(f"Erreur de lecture : {e}")
        
        # Valeurs fixées par la Wemos en mode expérimental
        temp = st.session_state.last_temp
        hum = st.session_state.last_hum
        v_peak = 23.0  # Valeur de tension par défaut
        freq = 15000.0 # Fréquence par défaut
        
    else:
        st.header("💻 Mode Simulation")
        v_peak = st.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.slider("Fréquence f (Hz)", 1000.0, 25000.0, 15000.0)
        temp = st.slider("Température T (°C)", 20.0, 100.0, 25.0)
        hum = st.slider("Humidité H2O (%)", 10.0, 95.0, 50.0)
    
    st.divider()
    st.header("📐 Géométrie du Réacteur")
    d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0)
    L_act = st.number_input("Longueur Active (L) [mm]", value=150.0)

# =================================================================
# 4. CALCULS PHYSIQUES (MODÈLE DE MANLEY)
# =================================================================
# Constantes physiques
EPS_0 = 8.854e-12
EPS_R_QUARTZ = 3.8
R_ext, R_int = 4.0, 2.5 

# Calcul de la Tension de Seuil (Theory of DBD)
v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 

# Calcul de la Capacité du Diélectrique (Farads)
C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000.0)) / np.log(R_ext / R_int)

# Calcul de la Puissance Active (Loi de Manley)
p_watt = 4 * freq * C_die * (v_th * 1000.0) * ((v_peak - v_th) * 1000.0) * 2 if v_peak > v_th else 0.0

# Modélisation des concentrations d'oxydants (en PPM)
k_oh = 0.03554
oh_final = k_oh * p_watt * (hum/100.0) * np.exp(-(temp - 25.0) / 150.0)

k_o3 = 0.00129 
o3_final = k_o3 * p_watt * (1.0 - hum/100.0) * np.exp(-(temp - 25.0) / 45.0) if v_peak > v_th else 0.0

# Calculs de ratios et efficacité
total_oxidants = oh_final + o3_final
pct_oh = (oh_final / total_oxidants * 100.0) if total_oxidants > 0 else 0.0
g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

# =================================================================
# 5. DASHBOARD PRINCIPAL (MÉTRIQUES)
# =================================================================
label_mode = "🔴 MODE EXPÉRIMENTAL" if mode_experimental else "🔵 MODE SIMULATION"
st.subheader(f"État du Système : {label_mode}")

# Ligne 1 : Résultats de production
col1, col2, col3, col4 = st.columns(4)
col1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} % du flux")
col2.metric("Production O3", f"{o3_final:.2f} ppm")
col3.metric("Puissance Active", f"{p_watt:.1f} W")
col4.metric("Efficacité (G-Value)", f"{g_value:.3f} g/kWh")

# Ligne 2 : Paramètres d'entrée
col5, col6, col7, col8 = st.columns(4)
col5.metric("Fréquence Source", f"{freq:.0f} Hz")
col6.metric("Température Gaz", f"{temp:.1f} °C", delta=f"{temp-25:.1f}° diff")
col7.metric("Humidité Relative", f"{hum:.1f} %")
col8.metric("V-Breakdown (th)", f"{v_th:.2f} kV")

st.divider()

# =================================================================
# 6. VISUALISATION GRAPHIQUE
# =================================================================
graph_col1, graph_col2 = st.columns(2)

with graph_col1:
    st.subheader("🌀 Figure de Lissajous (Q-V)")
    # Simulation de la boucle de charge pour le graphique
    t_plot = np.linspace(0, 2*np.pi, 500)
    v_sin = v_peak * np.sin(t_plot)
    q_sin = (C_die * 1e6 * v_peak) * np.cos(t_plot) 
    
    fig_liss = go.Figure()
    fig_liss.add_trace(go.Scatter(x=v_sin, y=q_sin, fill="toself", line=dict(color='#ADFF2F', width=2)))
    fig_liss.update_layout(
        template="plotly_dark", 
        xaxis_title="Tension (kV)", 
        yaxis_title="Charge (µC)",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_liss, use_container_width=True)

with graph_col2:
    st.subheader("📊 Sensibilité Production vs Tension")
    v_range = np.linspace(10, 35, 100)
    # Courbe théorique de production d'OH
    oh_curve = [k_oh * (4 * freq * C_die * (v_th * 1000.0) * ((v - v_th) * 1000.0) * 2) if v > v_th else 0 for v in v_range]
    
    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(x=v_range, y=oh_curve, name="·OH (ppm)", line=dict(color='#00FBFF', width=3)))
    fig_sens.update_layout(
        template="plotly_dark", 
        xaxis_title="Tension Appliquée (kV)", 
        yaxis_title="Concentration (ppm)",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_sens, use_container_width=True)

# =================================================================
# FOOTER & SÉCURITÉ
# =================================================================
st.error("⚠️ SÉCURITÉ : Présence de Haute Tension et d'Ozone. Manipulation strictement réservée au laboratoire.")
st.markdown("<center>© 2026 Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</center>", unsafe_allow_html=True)
