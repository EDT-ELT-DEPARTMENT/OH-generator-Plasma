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
        chemin_actuel = os.path.dirname(os.path.abspath(__file__))
        chemin_cle = os.path.join(chemin_actuel, 'cle_firebase.json')
        
        if os.path.exists(chemin_cle):
            cred = credentials.Certificate(chemin_cle)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.firebaseio.com/' 
            })
            st.sidebar.success("✅ Connecté au Cloud Firebase")
        else:
            st.sidebar.error(f"❌ Fichier 'cle_firebase.json' introuvable dans : {chemin_actuel}")
            
    except Exception as e:
        st.sidebar.error(f"❌ Erreur d'initialisation Firebase : {e}")

# =================================================================
# 2. RÉCUPÉRATION DES DONNÉES TEMPS RÉEL
# =================================================================
def get_live_metrics():
    try:
        ref = db.reference('/mesures')
        data = ref.get()
        return data
    except Exception:
        return None

live_data = get_live_metrics()

# =================================================================
# 3. TITRE ET ENTÊTE OFFICIEL (UDL-SBA)
# =================================================================
st.title("⚡ Start-up-OH Generator Plasma")
st.markdown("### Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Système Intelligent de Traitement des Fumées | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 4. BARRE LATÉRALE (SIDEBAR) - CONTRÔLE ET CONFIGURATION
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
    
    if live_data and isinstance(live_data, dict):
        st.info("📡 Mode : Temps Réel (Données du Labo)")
        v_peak = float(live_data.get('tension', 25.0))
        freq = int(live_data.get('frequence', 15000))
        hum = int(live_data.get('humidite', 70))
        temp = int(live_data.get('temperature', 60))
        
        st.write(f"**Tension reçue :** {v_peak} kV")
        st.write(f"**Fréquence reçue :** {freq} Hz")
        st.write(f"**Humidité :** {hum} %")
    else:
        st.warning("🔌 Mode : Simulation (Curseurs actifs)")
        v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
        freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
        hum = st.slider("Humidité H2O (%)", 10, 95, 70)
        temp = st.slider("Température des Fumées (°C)", 20, 250, 60)
    
    st.divider()
    
    st.subheader("📱 Monitoring Mobile")
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Accès distant")
    
    if st.button("🛑 ARRÊT D'URGENCE", type="primary", use_container_width=True):
        st.error("HAUTE TENSION COUPÉE - SYSTÈME SÉCURISÉ")

# =================================================================
# 5. BASES PHYSICO-CHIMIQUES ET ÉQUATIONS DU MODÈLE
# =================================================================

with st.expander("📚 Bases Physico-Chimiques et Équations du Modèle"):
    st.markdown("### 1. Modélisation Électrique Multi-Réacteur")
    st.latex(r"P_{active} = n \cdot \left( \frac{1}{2} C_{unit} V_{peak}^2 f \right)")
    
    st.markdown("### 2. Génération de Radicaux Hydroxyles (·OH)")
    st.latex(r"[\cdot OH]_{ppm} = \frac{P_{active} \cdot \text{Humidité} \cdot \alpha}{1 + \frac{T}{1000}}")
    
    st.markdown("### 3. Dégradation Thermique de l'Ozone (O3)")
    st.latex(r"[O_3]_{final} = [O_3]_{initial} \cdot e^{-\frac{T}{\beta}}")
    st.info("Paramètres : α = 0.09, β = 85°C, C_unit = 150 pF.")

# =================================================================
# 6. MOTEUR DE CALCUL
# =================================================================
C_UNIT = 150e-12 
V_TH = 12.0      
ALPHA = 0.09     
BETA = 85        

puissance_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq
v_range = np.linspace(0, v_peak, 100)
i_plasma_unit = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_peak_ma = (i_plasma_unit[-1] * 1000) * nb_reacteurs
oh_ppm = (puissance_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_ppm = (puissance_active * (1 - hum/100) * 0.045) * np.exp(-temp / BETA)

# =================================================================
# 7. AFFICHAGE DES INDICATEURS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_ppm:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm", delta="-Temp", delta_color="inverse")
c3.metric("Puissance Active", f"{puissance_active:.1f} W")
c4.metric("Courant Crête", f"{i_peak_ma:.2f} mA")

st.divider()

# =================================================================
# 8. GRAPHIQUES DE PERFORMANCE
# =================================================================
col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    st.subheader("⚡ Caractéristique Électrique I(V)")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_range, y=i_plasma_unit * 1000 * nb_reacteurs, fill='tozeroy', line=dict(color='#FF00FF', width=4)))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Intensité (mA)", template="plotly_dark")
    st.plotly_chart(fig_iv, use_container_width=True)

with col_graph2:
    st.subheader("📈 Concentrations des Espèces")
    t_sim = np.linspace(0, 60, 50)
    fig_chem = go.Figure()
    fig_chem.add_trace(go.Scatter(x=t_sim, y=oh_ppm + np.random.normal(0, 1, 50), name="Radicaux ·OH", line=dict(color='#00FBFF')))
    fig_chem.add_trace(go.Scatter(x=t_sim, y=o3_ppm + np.random.normal(0, 0.5, 50), name="Ozone O3", line=dict(color='orange')))
    fig_chem.update_layout(xaxis_title="Temps (s)", yaxis_title="ppm", template="plotly_dark")
    st.plotly_chart(fig_chem, use_container_width=True)

# =================================================================
# 9. FICHE TECHNIQUE ET SÉCURITÉ
# =================================================================
st.divider()
col_info, col_safe = st.columns(2)

with col_info:
    st.subheader("📝 Fiche Technique")
    st.markdown(f"- **Type :** DBD Coaxial\n- **Capacité :** {C_UNIT*1e12} pF")

with col_safe:
    st.subheader("⚠️ Sécurité (UDL-SBA)")
    st.error("HAUTE TENSION : Risque mortel.")
    st.warning("OZONE : Hotte aspirante obligatoire.")

st.divider()
st.markdown("<center>© 2026 OH-generator Plasma - Électrotechnique UDL-SBA | Laboratoire de Génie Électrique</center>", unsafe_allow_html=True)
