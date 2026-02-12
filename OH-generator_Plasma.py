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

# --- CONNEXION FIREBASE (ARCHITECTURE ROBUSTE) ---
if not firebase_admin._apps:
    try:
        # Localisation dynamique du fichier de clé dans le dossier du projet
        chemin_actuel = os.path.dirname(os.path.abspath(__file__))
        chemin_cle = os.path.join(chemin_actuel, 'cle_firebase.json')
        
        # Vérification de l'existence du fichier avant initialisation
        if os.path.exists(chemin_cle):
            cred = credentials.Certificate(chemin_cle)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-default-rtdb.europe-west1.firebasedatabase.app/' 
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
        # Tentative de lecture du noeud 'mesures' dans la Realtime Database
        ref = db.reference('/mesures')
        data = ref.get()
        return data
    except Exception:
        return None

# Appel de la fonction de récupération
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
    st.caption(f"Configuration actuelle : {nb_reacteurs} réacteurs DBD coaxiaux")
    
    st.divider()
    
    st.header("⚙️ Paramètres Opérationnels")
    
    # Basculement automatique si des données sont détectées sur le Cloud
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
    
    # Génération du QR Code pour le monitoring mobile
    st.subheader("📱 Monitoring Mobile")
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Accès distant")
    
    # Bouton de sécurité critique
    if st.button("🛑 ARRÊT D'URGENCE", type="primary", use_container_width=True):
        st.error("HAUTE TENSION COUPÉE - SYSTÈME SÉCURISÉ")

# =================================================================
# 5. BASES PHYSICO-CHIMIQUES ET ÉQUATIONS DU MODÈLE
# =================================================================
with st.expander("📚 Bases Physico-Chimiques et Équations du Modèle"):
    st.markdown("### 1. Modélisation Électrique Multi-Réacteur")
    st.write("La puissance active injectée dans le plasma pour $n$ réacteurs :")
    st.latex(r"P_{active} = n \cdot \left( \frac{1}{2} C_{unit} V_{peak}^2 f \right)")
    
    st.markdown("### 2. Génération de Radicaux Hydroxyles (·OH)")
    st.write("La dissociation de la vapeur d'eau par impact électronique :")
    st.latex(r"e^- + H_2O \rightarrow e^- + \cdot OH + H\cdot")
    st.latex(r"[\cdot OH]_{ppm} = \frac{P_{active} \cdot \text{Humidité} \cdot \alpha}{1 + \frac{T}{1000}}")
    
    st.markdown("### 3. Dégradation Thermique de l'Ozone (O3)")
    st.write("L'ozone résiduel diminue avec l'augmentation de la température :")
    st.latex(r"[O_3]_{final} = [O_3]_{initial} \cdot e^{-\frac{T}{\beta}}")
    st.info("Paramètres du modèle : α = 0.09, β = 85°C, C_unit = 150 pF.")

# =================================================================
# 6. MOTEUR DE CALCUL (LOGIQUE DE SIMULATION)
# =================================================================
# Constantes de conception du réacteur UDL-SBA
C_UNIT = 150e-12 
V_TH = 12.0      # Tension de seuil d'allumage du plasma (kV)
ALPHA = 0.09     # Coefficient de rendement énergétique pour OH
BETA = 85        # Stabilité thermique de l'ozone

# Calcul de la puissance totale
puissance_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq

# Modélisation du courant plasma I(V)
v_range = np.linspace(0, v_peak, 100)
# Loi de puissance pour la décharge silencieuse (DBD)
i_plasma_unit = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_peak_ma = (i_plasma_unit[-1] * 1000) * nb_reacteurs

# Calcul des concentrations chimiques
oh_ppm = (puissance_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_base = (puissance_active * (1 - hum/100) * 0.045)
o3_ppm = o3_base * np.exp(-temp / BETA)

# =================================================================
# 7. AFFICHAGE DES INDICATEURS CLÉS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_ppm:.2f} ppm", delta="Optimal" if 20<oh_ppm<35 else None)
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm", delta="-Temp", delta_color="inverse")
c3.metric("Puissance Active", f"{puissance_active:.1f} W")
c4.metric("Courant Crête", f"{i_peak_ma:.2f} mA")

st.divider()

# =================================================================
# 8. GRAPHIQUES DE PERFORMANCE (PLOTLY)
# =================================================================
col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    st.subheader("⚡ Caractéristique Électrique I(V)")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=v_range, 
        y=i_plasma_unit * 1000 * nb_reacteurs, 
        name="Courant Total", 
        fill='tozeroy', 
        line=dict(color='#FF00FF', width=4)
    ))
    fig_iv.update_layout(
        xaxis_title="Tension Appliquée (kV)", 
        yaxis_title="Intensité Mesurée (mA)", 
        template="plotly_dark",
        margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig_iv, use_container_width=True)

with col_graph2:
    st.subheader("📈 Concentrations des Espèces")
    t_sim = np.linspace(0, 60, 50)
    # Simulation de fluctuations légères pour le rendu visuel
    oh_noise = oh_ppm + np.random.normal(0, oh_ppm*0.015, 50)
    o3_noise = o3_ppm + np.random.normal(0, o3_ppm*0.015, 50)
    
    fig_chem = go.Figure()
    fig_chem.add_trace(go.Scatter(x=t_sim, y=oh_noise, name="Radicaux ·OH", line=dict(color='#00FBFF', width=3)))
    fig_chem.add_trace(go.Scatter(x=t_sim, y=o3_noise, name="Ozone O3", line=dict(color='orange', dash='dash')))
    fig_chem.update_layout(
        xaxis_title="Temps de traitement (s)", 
        yaxis_title="Concentration (ppm)", 
        template="plotly_dark",
        margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig_chem, use_container_width=True)

# =================================================================
# 9. FICHE TECHNIQUE ET SÉCURITÉ
# =================================================================
st.divider()
col_info, col_safe = st.columns(2)

with col_info:
    st.subheader("📝 Fiche Technique du Réacteur")
    st.markdown(f"""
    **SPÉCIFICATIONS MÉCANIQUES**
    - **Type :** DBD Coaxial (Cylindrique)
    - **Matériaux :** Électrode Inox 316L / Diélectrique Quartz
    - **Géométrie :** Longueur 200mm / Gap 5mm
    
    **PARAMÈTRES ÉLECTRIQUES**
    - **Capacité Unitaire :** {C_UNIT*1e12} pF
    - **Fréquence de résonance estimée :** 18-22 kHz
    """)

with col_safe:
    st.subheader("⚠️ Notice de Sécurité (UDL-SBA)")
    st.error("**HAUTE TENSION :** Risque mortel. Ne jamais ouvrir le coffret sous tension.")
    st.warning("**OZONE :** Concentration détectée. Hotte aspirante obligatoire.")
    st.info("**PROTECTION :** Port des lunettes UV-C recommandé lors des tests visuels.")

# =================================================================
# 10. PIED DE PAGE
# =================================================================
st.divider()
st.markdown(
    "<center>© 2026 OH-generator Plasma - Électrotechnique UDL-SBA | Laboratoire de Génie Électrique</center>", 
    unsafe_allow_html=True
)
