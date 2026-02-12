import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
import os
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# =================================================================
# 1. CONFIGURATION DE LA PAGE (DOIT ÊTRE LA PREMIÈRE COMMANDE)
# =================================================================
st.set_page_config(
    page_title="OH-generator Plasma | UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# --- CONNEXION FIREBASE ---
if not firebase_admin._apps:
    try:
        chemin_actuel = os.path.dirname(os.path.abspath(__file__))
        chemin_cle = os.path.join(chemin_actuel, 'cle_firebase.json')
        
        if os.path.exists(chemin_cle):
            cred = credentials.Certificate(chemin_cle)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.firebaseio.com/' 
            })
            st.sidebar.success("✅ Connecté au Cloud Firebase")
        else:
            st.sidebar.error("❌ Fichier 'cle_firebase.json' introuvable.")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur Firebase : {e}")

# =================================================================
# 2. RÉCUPÉRATION DES DONNÉES
# =================================================================
def get_live_metrics():
    try:
        ref = db.reference('/mesures')
        return ref.get()
    except:
        return None

live_data = get_live_metrics()

# =================================================================
# 3. TITRE OFFICIEL ET ENTÊTE (UDL-SBA)
# =================================================================
st.title("⚡ Start-up-OH Generator Plasma")
st.markdown("### Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Système Intelligent de Traitement des Fumées | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 4. BARRE LATÉRALE - PARAMÈTRES
# =================================================================
with st.sidebar:
    st.header("🎮 Configuration du Système")
    nb_reacteurs = st.number_input("Nombre de réacteurs", min_value=1, max_value=20, value=2)
    
    st.divider()
    st.header("⚙️ Paramètres Opérationnels")
    
    if live_data and isinstance(live_data, dict):
        st.info("📡 Mode : Temps Réel")
        v_peak = float(live_data.get('tension', 25.0))
        freq = int(live_data.get('frequence', 15000))
        hum = int(live_data.get('humidite', 70))
        temp = int(live_data.get('temperature', 60))
    else:
        st.warning("🔌 Mode : Simulation")
        v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
        freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
        hum = st.slider("Humidité H2O (%)", 10, 95, 70)
        temp = st.slider("Température (°C)", 20, 250, 60)

    # QR Code
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Accès distant")

# =================================================================
# 5. MODÉLISATION PHYSIQUE
# =================================================================
# Constantes UDL-SBA
C_UNIT, V_TH, ALPHA, BETA = 150e-12, 12.0, 0.09, 85

# Calculs
P_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq
oh_ppm = (P_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_ppm = (P_active * (1 - hum/100) * 0.045) * np.exp(-temp / BETA)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_ppm:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm", delta="-Temp", delta_color="inverse")
c3.metric("Puissance Active", f"{P_active:.1f} W")
c4.metric("Courant Crête", f"{((0.00065*(v_peak-12)**1.55)*1000*nb_reacteurs) if v_peak > 12 else 0:.2f} mA")

st.divider()

# =================================================================
# 6. GRAPHIQUES
# =================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("⚡ Caractéristique I(V)")
    v_range = np.linspace(0, v_peak, 100)
    i_vals = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 0) * 1000 * nb_reacteurs
    fig1 = go.Figure(go.Scatter(x=v_range, y=i_vals, fill='tozeroy', line=dict(color='#FF00FF', width=3)))
    fig1.update_layout(xaxis_title="Tension (kV)", yaxis_title="Intensité (mA)", template="plotly_dark")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("📈 Concentrations")
    t_sim = np.linspace(0, 60, 50)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t_sim, y=oh_ppm + np.random.normal(0, 1, 50), name="·OH", line=dict(color='#00FBFF')))
    fig2.add_trace(go.Scatter(x=t_sim, y=o3_ppm + np.random.normal(0, 0.5, 50), name="O3", line=dict(color='orange')))
    fig2.update_layout(xaxis_title="Temps (s)", yaxis_title="ppm", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

# =================================================================
# 7. PIED DE PAGE
# =================================================================
st.divider()
st.markdown("<center>© 2026 OH-generator Plasma - Électrotechnique UDL-SBA | Laboratoire de Génie Électrique</center>", unsafe_allow_html=True)
