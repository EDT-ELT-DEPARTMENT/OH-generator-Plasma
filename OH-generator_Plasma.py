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
        # Nettoyage de la clé pour éviter l'erreur PEM
        fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n").strip()
        
        cred = credentials.Certificate(fb_secrets)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.firebaseio.com/' 
        })
        st.sidebar.success("✅ Cloud Firebase Connecté")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur de configuration : {e}")

# =================================================================
# 2. TITRE OFFICIEL (Mémorisé)
# =================================================================
# Rappel : Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA
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
    # Ajout des dimensions physiques demandées
    rayon_interne = st.number_input("Rayon Électrode Interne (mm)", value=2.5, step=0.1)
    epaisseur_dielectrique = st.number_input("Épaisseur Quartz (mm)", value=1.5, step=0.1)
    longueur_decharge = st.number_input("Longueur Active (mm)", value=150.0, step=10.0)
    gap_gaz = st.number_input("Gap de gaz (mm)", value=3.0, step=0.1)
    
    st.divider()
    
    st.header("🎮 Configuration Système")
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

    # QR Code Monitoring
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
        st.latex(r"P_{active} = n \cdot (\frac{1}{2} C_{unit} V_{peak}^2 f)")
    with col_eq2:
        st.markdown("**2. Génération & Décroissance**")
        st.latex(r"[\cdot OH]_{ppm} = \frac{P_{active} \cdot \text{Hum} \cdot \alpha}{1 + T/1000}")
        st.latex(r"[\cdot OH](t) = [\cdot OH]_0 \cdot e^{-k_{decay} \cdot t}")

# =================================================================
# 5. MOTEUR DE CALCUL PHYSIQUE
# =================================================================
# Constantes diélectriques (Quartz)
EPSILON_R = 3.8 
EPSILON_0 = 8.854e-12
V_TH = 12.0 # Seuil d'amorçage
ALPHA = 0.09 # Rendement radicalaire

# Calcul de la capacité géométrique du réacteur
r_ext = (rayon_interne + epaisseur_dielectrique + gap_gaz) / 1000
r_int = rayon_interne / 1000
L_m = longueur_decharge / 1000

# Capacité par réacteur (F)
C_UNIT = (2 * np.pi * EPSILON_0 * EPSILON_R * L_m) / np.log(r_ext / r_int)

# Calcul Puissance et Courant
puissance_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq
v_range = np.linspace(0, v_peak, 100)
i_plasma_unit = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_peak_ma = (i_plasma_unit[-1] * 1000) * nb_reacteurs

# Calcul Chimie (·OH et Ozone)
oh_initial = (puissance_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_ppm = (puissance_active * (1 - hum/100) * 0.045) * np.exp(-temp / 85)

# Transport et Décroissance cinétique
t_transit = (dist_cm / 100) / v_flux
k_decay = 120 * (1 + (temp / 100))
oh_final = oh_initial * np.exp(-k_decay * t_transit)

# =================================================================
# 6. TABLEAU DE BORD (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_final:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm")
c3.metric("Puissance Active", f"{puissance_active:.1f} W")
c4.metric("Capacité Totale", f"{(C_UNIT*nb_reacteurs)*1e12:.1f} pF")

st.divider()

# =================================================================
# 7. GRAPHIQUES ET VISUALISATION
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique I(V)")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_range, y=i_plasma_unit * 1000 * nb_reacteurs, fill='tozeroy', line=dict(color='#FF00FF')))
    fig_iv.update_layout(xaxis_title="V (kV)", yaxis_title="I (mA)", template="plotly_dark", height=300)
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("📈 Profil de Décroissance ·OH")
    dist_x = np.linspace(0, 50, 100)
    oh_x = oh_initial * np.exp(-k_decay * ((dist_x/100)/v_flux))
    fig_oh = go.Figure()
    fig_oh.add_trace(go.Scatter(x=dist_x, y=oh_x, fill='tozeroy', line=dict(color='#00FBFF')))
    fig_oh.update_layout(xaxis_title="Distance (cm)", yaxis_title="·OH (ppm)", template="plotly_dark", height=300)
    st.plotly_chart(fig_oh, use_container_width=True)

# =================================================================
# 8. SYSTÈME D'ARCHIVAGE DES DONNÉES (HISTORIQUE)
# =================================================================
st.header("💾 Archivage des Tests de Laboratoire")

# On utilise le session_state de Streamlit pour garder les données en mémoire locale
if 'historique' not in st.session_state:
    st.session_state.historique = []

col_save, col_clear = st.columns([1, 4])
with col_save:
    if st.button("📥 Enregistrer le Test"):
        nouveau_test = {
            "Heure": datetime.now().strftime("%H:%M:%S"),
            "V_kV": v_peak,
            "F_Hz": freq,
            "Hum_%": hum,
            "OH_ppm": round(oh_final, 3),
            "P_Watt": round(puissance_active, 1)
        }
        st.session_state.historique.append(nouveau_test)
        
        # Envoi optionnel vers Firebase pour sauvegarde permanente
        try:
            db.reference('/historique_tests').push(nouveau_test)
            st.toast("Données envoyées au Cloud !")
        except:
            pass

with col_clear:
    if st.button("🗑️ Effacer l'historique"):
        st.session_state.historique = []

# Affichage du tableau de résultats
if st.session_state.historique:
    df_hist = pd.DataFrame(st.session_state.historique)
    st.table(df_hist)
    
    # Bouton de téléchargement CSV
    csv = df_hist.to_csv(index=False).encode('utf-8')
    st.download_button("📂 Télécharger rapport (.csv)", data=csv, file_name="test_plasma_udl.csv", mime="text/csv")
else:
    st.info("Aucune donnée enregistrée pour le moment.")

# =================================================================
# 9. PIED DE PAGE ET SÉCURITÉ
# =================================================================
st.divider()
f1, f2 = st.columns(2)
with f1:
    st.error("⚠️ Sécurité : Haute Tension active (35kV Max).")
with f2:
    st.info(f"Dimensions : {rayon_interne}x{longueur_decharge}mm | Flux : {v_flux} m/s")

st.markdown("<center>© 2026 OH-generator Plasma - Département d'Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
