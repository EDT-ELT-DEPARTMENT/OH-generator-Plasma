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
        st.sidebar.success("✅ Cloud Firebase Connecté")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur de configuration : {e}")

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
    rayon_interne = st.number_input("Rayon Électrode Interne (r_int) [mm]", value=2.5, step=0.1)
    epaisseur_dielectrique = st.number_input("Épaisseur Quartz (e) [mm]", value=1.5, step=0.1)
    gap_gaz = st.number_input("Gap de décharge (d) [mm]", value=3.0, step=0.1)
    longueur_decharge = st.number_input("Longueur Active (L) [mm]", value=150.0, step=10.0)
    
    st.divider()
    
    st.header("🎮 Configuration Système")
    nb_reacteurs = st.number_input("Nombre de réacteurs (n)", min_value=1, max_value=20, value=2)
    
    st.divider()
    st.header("⚙️ Paramètres Opérationnels")
    
    # Bouton d'optimisation automatique
    if st.button("🚀 Appliquer les Paramètres Optimaux"):
        st.session_state.v_p = 30.0
        st.session_state.f_q = 15000
        st.session_state.h_m = 75
        st.session_state.t_p = 45
        st.session_state.d_s = 2
        st.session_state.v_l = 22
        st.rerun()

    # Initialisation des variables de session pour l'optimisation
    if 'v_p' not in st.session_state: st.session_state.v_p = 23.0 # Mis à jour à ta valeur actuelle
    if 'f_q' not in st.session_state: st.session_state.f_q = 15000
    if 'h_m' not in st.session_state: st.session_state.h_m = 70
    if 't_p' not in st.session_state: st.session_state.t_p = 60
    if 'd_s' not in st.session_state: st.session_state.d_s = 10
    if 'v_l' not in st.session_state: st.session_state.v_l = 10

    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, st.session_state.v_p)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, st.session_state.f_q)
    hum = st.slider("Humidité H2O (%)", 10, 95, st.session_state.h_m)
    temp = st.slider("Température (°C)", 20, 250, st.session_state.t_p)
    
    st.divider()
    st.header("🚚 Transport des Radicaux")
    dist_cm = st.slider("Distance d'injection (cm)", 0, 50, st.session_state.d_s)
    v_flux = st.slider("Vitesse du flux (m/s)", 1, 30, st.session_state.v_l)

    # QR Code
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Scanner pour Monitoring Mobile")

# =================================================================
# 4. BASES PHYSIQUES ET ÉQUATIONS
# =================================================================
with st.expander("📚 Bases Physico-Chimiques et Équations du Modèle", expanded=True):
    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        st.markdown("**1. Modélisation Électrique**")
        st.latex(r"C_{unit} = \frac{2\pi\epsilon_0\epsilon_r L}{\ln(r_{ext}/r_{int})}")
        st.latex(r"P_{active} = f \cdot \oint Q \, dV")
    with col_eq2:
        st.markdown("**2. Génération & Transport**")
        st.latex(r"[\cdot OH]_{ppm} = \frac{P_{active} \cdot \text{Hum} \cdot \alpha}{1 + T/1000}")
        st.latex(r"[\cdot OH](t) = [\cdot OH]_0 \cdot e^{-k_{decay} \cdot t}")

# =================================================================
# 5. MOTEUR DE CALCUL PHYSIQUE (CORRIGÉ POUR 23kV)
# =================================================================
EPSILON_R = 3.8  
EPSILON_0 = 8.854e-12
V_TH = 12.0 # Tension d'allumage

# Calcul Capacité Géométrique
r_ext = (rayon_interne + epaisseur_dielectrique + gap_gaz) / 1000
r_int = rayon_interne / 1000
L_m = longueur_decharge / 1000
C_UNIT = (2 * np.pi * EPSILON_0 * EPSILON_R * L_m) / np.log(r_ext / r_int)

# --- Simulation des Signaux Temporels pour Lissajous ---
t_vec = np.linspace(0, 1/freq, 1000)
V_t = v_peak * np.sin(2 * np.pi * freq * t_vec)

# Facteur Plasma Recalibré : Augmente drastiquement après V_TH
# À 23kV, ce facteur doit être significatif
plasma_expansion = max(0, (v_peak - V_TH) * 0.5) 
Q_t = (C_UNIT * nb_reacteurs * 1e6) * v_peak * (np.sin(2 * np.pi * freq * t_vec + 0.6) + plasma_expansion * np.sign(V_t))

# --- CALCUL DE LA SURFACE DE LISSAJOUS ---
if hasattr(np, 'trapezoid'):
    energie_mJ = np.abs(np.trapezoid(Q_t, V_t))
else:
    energie_mJ = np.abs(np.trapz(Q_t, V_t))

puissance_reelle = energie_mJ * (freq / 1000)

# --- MODÈLE CHIMIQUE REHAUSSÉ ---
# Rendement alpha proportionnel à l'énergie par cycle
ALPHA_LABO = 0.85 
oh_initial = (puissance_reelle * (hum/100) * ALPHA_LABO) / (1 + (temp/500))
o3_ppm = (puissance_reelle * (1 - hum/100) * 0.08) * np.exp(-temp / 70)

# Transport et Décroissance
t_transit = (dist_cm / 100) / v_flux
k_decay = 90 * (1 + (temp / 100))
oh_final = oh_initial * np.exp(-k_decay * t_transit)

# =================================================================
# 6. INDICATEURS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm")
c3.metric("Puissance Réelle", f"{puissance_reelle:.1f} W")
c4.metric("Énergie / Cycle", f"{energie_mJ:.2f} mJ")

st.divider()

# =================================================================
# 7. VISUALISATION
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique I(V)")
    v_range = np.linspace(0, v_peak, 100)
    i_plasma = np.where(v_range > V_TH, 0.002 * (v_range - V_TH)**1.8, 1e-6)
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_range, y=i_plasma * 1000 * nb_reacteurs, fill='tozeroy', line=dict(color='#FF00FF', width=3)))
    fig_iv.update_layout(xaxis_title="V (kV)", yaxis_title="I (mA)", template="plotly_dark", height=300)
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("📈 Profil de Décroissance ·OH")
    dist_x = np.linspace(0, 50, 100)
    oh_x = oh_initial * np.exp(-k_decay * ((dist_x/100)/v_flux))
    fig_oh = go.Figure()
    fig_oh.add_trace(go.Scatter(x=dist_x, y=oh_x, fill='tozeroy', line=dict(color='#00FBFF', width=3)))
    fig_oh.update_layout(xaxis_title="Distance (cm)", yaxis_title="·OH (ppm)", template="plotly_dark", height=300)
    st.plotly_chart(fig_oh, use_container_width=True)


st.subheader("🌀 Analyse de Lissajous (Cycle Q-V)")
fig_liss = go.Figure()
fig_liss.add_trace(go.Scatter(x=V_t, y=Q_t, mode='lines', line=dict(color='#ADFF2F', width=4), fill='toself'))
fig_liss.update_layout(xaxis_title="Tension v(t) [kV]", yaxis_title="Charge q(t) [µC]", template="plotly_dark", height=450)
st.plotly_chart(fig_liss, use_container_width=True)

# =================================================================
# 8. SYSTÈME D'ARCHIVAGE
# =================================================================
st.divider()
st.header("💾 Archivage des Tests de Laboratoire")

if 'historique' not in st.session_state:
    st.session_state.historique = []

col_save, col_clear = st.columns([1, 4])
with col_save:
    if st.button("📥 Enregistrer le Test"):
        nouveau_test = {
            "Heure": datetime.now().strftime("%H:%M:%S"),
            "V_peak (kV)": v_peak,
            "Freq (Hz)": freq,
            "OH_final (ppm)": round(oh_final, 3),
            "P_Watt": round(puissance_reelle, 1)
        }
        st.session_state.historique.append(nouveau_test)
        try:
            db.reference('/historique_tests').push(nouveau_test)
            st.toast("Sync Firebase OK")
        except:
            st.warning("Archive Locale")

if st.session_state.historique:
    df_hist = pd.DataFrame(st.session_state.historique)
    st.table(df_hist)

# =================================================================
# 9. PIED DE PAGE
# =================================================================
st.divider()
st.error("⚠️ Sécurité : Haute Tension (35kV). Ventilation obligatoire.")
st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
