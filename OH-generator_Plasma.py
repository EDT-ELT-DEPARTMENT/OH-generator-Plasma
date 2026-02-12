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

# --- CONNEXION FIREBASE ---
if not firebase_admin._apps:
    try:
        # Utilisez les secrets Streamlit pour la sécurité en production
        cred = credentials.Certificate('cle_firebase.json') 
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'VOTRE_URL_FIREBASE_ICI' 
        })
        st.sidebar.success("✅ Connecté au Cloud Firebase")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur de connexion Cloud : {e}")

# =================================================================
# 2. RÉCUPÉRATION DES DONNÉES TEMPS RÉEL
# =================================================================
def get_live_metrics():
    try:
        ref = db.reference('/mesures')
        return ref.get()
    except:
        return None

live_data = get_live_metrics()

# =================================================================
# 3. TITRE ET ENTÊTE OFFICIEL
# =================================================================
st.title("⚡ Start-up-OH Generator Plasma")
st.markdown("### OH-generator Plasma - Système Intelligent de Traitement des Fumées")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 4. BARRE LATÉRALE (SIDEBAR) - CONTRÔLE HYBRIDE
# =================================================================
with st.sidebar:
    st.header("🎮 Configuration du Système")
    
    nb_reacteurs = st.number_input(
        "Nombre de réacteurs (en parallèle)", 
        min_value=1, 
        max_value=20, 
        value=2
    )
    
    st.divider()
    
    st.header("⚙️ Paramètres Opérationnels")
    
    if live_data:
        st.info("📡 Mode : Temps Réel (Labo)")
        v_peak = float(live_data.get('tension', 25.0))
        freq = int(live_data.get('frequence', 15000))
        hum = int(live_data.get('humidite', 70))
        temp = int(live_data.get('temperature', 60))
    else:
        st.warning("🔌 Mode : Simulation")
        v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
        freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
        hum = st.slider("Humidité H2O (%)", 10, 95, 70)
        temp = st.slider("Température de l'Air Porteur (°C)", 20, 250, 60)
    
    st.divider()
    
    # Paramètres de transport
    st.header("🚚 Transport des Radicaux")
    dist_cm = st.slider("Distance au polluant (cm)", 0, 50, 5)
    v_flux = st.slider("Vitesse du flux (m/s)", 1, 30, 15)

    st.divider()
    st.subheader("📱 Monitoring Mobile")
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Accès distant")
    
    if st.button("🛑 ARRÊT D'URGENCE", type="primary", use_container_width=True):
        st.error("HAUTE TENSION COUPÉE")

# =================================================================
# 5. MOTEUR DE CALCUL PHYSIQUE (PLASMA & CHIMIE)
# =================================================================
# Constantes fixes
C_UNIT = 150e-12 
V_TH = 12.0
ALPHA = 0.09  
BETA = 85     
D_GAP = 0.005 # 5mm
E_QUARTZ = 0.002
EPS_QUARTZ = 3.8

# A. Calculs Électriques
puissance_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq
v_range = np.linspace(0, v_peak, 100)
i_plasma_unit = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_peak_ma = (i_plasma_unit[-1] * 1000) * nb_reacteurs

# B. Champ Électrique (Air Porteur)
delta = (293 / (273 + temp)) 
E_paschen = 30 * delta * (1 + 0.3 / (np.sqrt(delta * 0.5)))
V_plasma_eff = v_peak * (1 - (E_QUARTZ / (E_QUARTZ + D_GAP * EPS_QUARTZ)))
E_applied = V_plasma_eff / (D_GAP * 100) # kV/cm

# C. Production et Survie des Radicaux
oh_initial = (puissance_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_ppm = (puissance_active * (1 - hum/100) * 0.045) * np.exp(-temp / BETA)

# Temps de vol et Recombinaison
t_transit = (dist_cm / 100) / v_flux
k_decay = 120 * (1 + (temp / 100)) # Coeff de disparition
oh_final = oh_initial * np.exp(-k_decay * t_transit)

# =================================================================
# 6. AFFICHAGE DES INDICATEURS
# =================================================================

c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH (Impact)", f"{oh_final:.2f} ppm", f"{oh_final-oh_initial:.1f} perte")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm")
c3.metric("Puissance Totale", f"{puissance_active:.1f} W")
c4.metric("Champ Appliqué", f"{E_applied:.2f} kV/cm")

st.divider()

# =================================================================
# 7. VISUALISATION GRAPHIQUE
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique Électrique")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_range, y=i_plasma_unit * 1000 * nb_reacteurs, 
                               fill='tozeroy', line=dict(color='#FF00FF', width=3)))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Courant (mA)", template="plotly_dark")
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("📉 Décroissance des Radicaux (Survie)")
    dist_sim = np.linspace(0, 50, 100)
    survie_sim = oh_initial * np.exp(-k_decay * ((dist_sim/100)/v_flux))
    fig_decay = go.Figure()
    fig_decay.add_trace(go.Scatter(x=dist_sim, y=survie_sim, fill='tozeroy', line=dict(color='#00FBFF')))
    fig_decay.add_vline(x=dist_cm, line_dash="dash", line_color="red", annotation_text="Point d'injection")
    fig_decay.update_layout(xaxis_title="Distance (cm)", yaxis_title="·OH (ppm)", template="plotly_dark")
    st.plotly_chart(fig_decay, use_container_width=True)

# =================================================================
# 8. MODULE DE DÉPOLLUTION
# =================================================================
st.subheader("🍃 Simulation du Traitement des Fumées")
cp1, cp2 = st.columns(2)

with cp1:
    polluant = st.selectbox("Polluant à traiter :", ["NOx", "SO2"])
    conc_in = st.number_input("Concentration initiale (ppm)", value=250)

with cp2:
    # Efficacité basée sur le ratio OH/Polluant
    k_eff = 0.9 if polluant == "NOx" else 1.2
    reduction = (1 - np.exp(-k_eff * (oh_final / 150))) * 100
    conc_out = conc_in * (1 - reduction/100)
    st.metric("Réduction estimée", f"{reduction:.1f} %", delta_color="normal")
    st.write(f"**Concentration de sortie :** {conc_out:.1f} ppm")

# =================================================================
# 9. PIED DE PAGE
# =================================================================
st.divider()
st.markdown("<center>© 2026 OH-generator Plasma - Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
