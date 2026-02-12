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
    page_title="OH-generator Plasma | UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# --- CONNEXION FIREBASE SÉCURISÉE ---
if not firebase_admin._apps:
    try:
        fb_secrets = dict(st.secrets["firebase"])
        # Nettoyage automatique de la clé pour éviter l'erreur PEM
        fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n").strip()
        
        cred = credentials.Certificate(fb_secrets)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://votre-projet-id-default-rtdb.firebaseio.com/' 
        })
        st.sidebar.success("✅ Cloud Firebase Connecté")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur de configuration Cloud : {e}")
        st.sidebar.info("Vérifiez le format de la private_key dans les Secrets.")

# =================================================================
# 2. TITRE ET ENTÊTE
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
    st.header("🎮 Configuration du Système")
    nb_reacteurs = st.number_input("Nombre de réacteurs", min_value=1, max_value=20, value=2)
    
    st.divider()
    st.header("⚙️ Paramètres Opérationnels")
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 70)
    temp = st.slider("Température (°C)", 20, 250, 60)
    
    st.divider()
    st.header("🚚 Transport")
    dist_cm = st.slider("Distance d'injection (cm)", 0, 50, 10)
    v_flux = st.slider("Vitesse du flux (m/s)", 1, 30, 10)

    # QR Code pour accès mobile
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Scanner pour Monitoring Mobile")

# =================================================================
# 4. AFFICHAGE DES ÉQUATIONS PHYSIQUES
# =================================================================
with st.expander("📚 Bases Physico-Chimiques et Équations du Modèle", expanded=True):
    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        st.markdown("**Modélisation Électrique**")
        st.latex(r"P_{active} = n \times \left( \frac{1}{2} C_{unit} V_{peak}^2 f \right)")
        st.latex(r"I_{total} = n \times k \times (V - V_{th})^{1.55}")
    with col_eq2:
        st.markdown("**Cinétique Chimique**")
        st.latex(r"[\cdot OH]_{ppm} = \frac{P_{active} \times \text{Humidité} \times \alpha}{1 + \frac{T}{1000}}")
        st.latex(r"[\cdot OH](t) = [\cdot OH]_0 \times e^{-k_{decay} \times t}")

# =================================================================
# 5. MOTEUR DE CALCUL (SIMULATION)
# =================================================================
C_UNIT = 150e-12 
V_TH = 12.0
ALPHA = 0.09  
BETA = 85     

# Calculs électriques
puissance_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq
v_range = np.linspace(0, v_peak, 100)
i_plasma_unit = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_peak_ma = (i_plasma_unit[-1] * 1000) * nb_reacteurs

# Calculs chimiques
oh_initial = (puissance_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_ppm = (puissance_active * (1 - hum/100) * 0.045) * np.exp(-temp / BETA)

# Transport et Décroissance
t_transit = (dist_cm / 100) / v_flux
k_decay = 120 * (1 + (temp / 100))
oh_final = oh_initial * np.exp(-k_decay * t_transit)

# =================================================================
# 6. INDICATEURS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm")
c3.metric("Puissance Active", f"{puissance_active:.1f} W")
c4.metric("Courant Crête", f"{i_peak_ma:.2f} mA")

st.divider()

# =================================================================
# 7. VISUALISATION GRAPHIQUE
# =================================================================
col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    st.subheader("⚡ Caractéristique I(V)")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=v_range, 
        y=i_plasma_unit * 1000 * nb_reacteurs, 
        line=dict(color='#FF00FF', width=3),
        fill='tozeroy',
        name="Courant Décharge"
    ))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Intensité (mA)", template="plotly_dark", height=350)
    st.plotly_chart(fig_iv, use_container_width=True)

with col_graph2:
    st.subheader("📈 Profil de Décroissance ·OH")
    distances = np.linspace(0, 50, 100)
    survie_courbe = oh_initial * np.exp(-k_decay * ((distances/100)/v_flux))
    fig_decay = go.Figure()
    fig_decay.add_trace(go.Scatter(
        x=distances, y=survie_courbe,
        line=dict(color='#00FBFF', width=3),
        fill='tozeroy',
        name="Concentration ·OH"
    ))
    fig_decay.add_vline(x=dist_cm, line_dash="dash", line_color="red", annotation_text="Point d'injection")
    fig_decay.update_layout(xaxis_title="Distance (cm)", yaxis_title="·OH (ppm)", template="plotly_dark", height=350)
    st.plotly_chart(fig_decay, use_container_width=True)

# =================================================================
# 8. SÉCURITÉ ET PIED DE PAGE
# =================================================================
st.divider()
s1, s2 = st.columns(2)
with s1:
    st.error("⚠️ Sécurité : Haute Tension (35kV). Ventilation obligatoire.")
with s2:
    st.info(f"🚀 État : {nb_reacteurs} réacteurs en ligne. Temps de transit : {t_transit*1000:.2f} ms")

st.markdown("<center>© 2026 OH-generator Plasma - Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
