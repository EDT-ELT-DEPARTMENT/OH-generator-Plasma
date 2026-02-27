import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF  # Utilise fpdf2

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Navigation par menu latéral
st.sidebar.title("📂 Menu Principal")
page = st.sidebar.radio("Navigation :", ["📊 Monitoring Temps Réel", "🔬 Prototype & Datasheet"])

# Titre officiel rappelé systématiquement
ST_TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# =================================================================
# 2. FONCTIONS DE SERVICE
# =================================================================

@st.cache_resource
def initialiser_firebase():
    """Initialise la connexion Firebase"""
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
        st.sidebar.error(f"Erreur de connexion Cloud : {e}")
        return False

def generer_pdf_datasheet():
    """Génère un export PDF compatible fpdf2"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, txt="DATASHEET TECHNIQUE - PROTOTYPE HYBRIDE", ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    pdf.cell(190, 10, txt=f"Projet : {ST_TITRE_OFFICIEL}", ln=True)
    pdf.cell(190, 10, txt=f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 10, txt="1. Configuration du Système :", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(190, 10, txt="Le système utilise une Ligne 1 pour la pollution (MQ-9 + ESP) et une Ligne 2 réactive. "
                                "La Ligne 2 comporte une chambre d'humidification unique connectée en série "
                                "par sa sortie haute au réacteur DBD.")
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 10, txt="2. Spécifications du Réacteur DBD :", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 8, txt="- Diélectrique : Quartz (épaisseur 1.5mm)", ln=True)
    pdf.cell(190, 8, txt="- Gap de décharge : 3.0 mm", ln=True)
    pdf.cell(190, 8, txt="- Longueur active : 150 mm", ln=True)
    
    # Retourne les bytes directement (syntaxe fpdf2)
    return pdf.output()

# =================================================================
# PAGE 1 : MONITORING TEMPS RÉEL
# =================================================================
if page == "📊 Monitoring Temps Réel":
    st_autorefresh(interval=2000, key="datarefresh")
    st.title("⚡ Monitoring des Oxydants Hybrides")
    st.markdown(f"**{ST_TITRE_OFFICIEL}**")

    # Initialisation session
    if 'last_temp' not in st.session_state: st.session_state.last_temp = 23.0
    if 'last_hum' not in st.session_state: st.session_state.last_hum = 45.0

    mode_experimental = st.sidebar.toggle("🚀 Mode Wemos D1 (Réel)", value=False)
    
    if mode_experimental and initialiser_firebase():
        try:
            ref = db.reference('/EDT_SBA')
            data_cloud = ref.get()
            if data_cloud:
                st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
        except:
            pass

    # Variables de calcul
    if mode_experimental:
        temp, hum = st.session_state.last_temp, st.session_state.last_hum
        v_peak, freq = 23.0, 15000.0
    else:
        v_peak = st.sidebar.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.sidebar.slider("Fréquence f (Hz)", 1000.0, 25000.0, 15000.0)
        temp = st.sidebar.slider("Température T (°C)", 20.0, 100.0, 25.0)
        hum = st.sidebar.slider("Humidité H2O (%)", 10.0, 95.0, 50.0)

    # Calculs physiques (Modèle)
    v_th = 13.2 * (1 + 0.05 * np.sqrt(3.0))
    C_die = 1.2e-10 # Valeur simplifiée pour l'exemple
    p_watt = 4 * freq * C_die * (v_th * 1000) * ((v_peak - v_th) * 1000) * 2 if v_peak > v_th else 0.0
    oh_final = 0.035 * p_watt * (hum/100)

    # Affichage Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Température", f"{temp:.1f} °C")
    c2.metric("Humidité", f"{hum:.1f} %")
    c3.metric("Production ·OH", f"{oh_final:.2f} ppm")
    st.divider()

# =================================================================
# PAGE 2 : PROTOTYPE & DATASHEET
# =================================================================
elif page == "🔬 Prototype & Datasheet":
    st.title("🔬 Spécifications du Prototype Hybride")
    st.markdown(f"**{ST_TITRE_OFFICIEL}**")
    st.divider()

    col_img, col_info = st.columns([1.6, 1])

    with col_img:
        st.subheader("🖼️ Visualisation du Design Corrigé")
        # --- SOLUTION POUR L'IMAGE ---
        # Si vous n'avez pas encore le fichier local, utilisez l'URL directe
        IMAGE_URL = "https://raw.githubusercontent.com/votre_depot/main/prototype.jpg" 
        # Ou essayez le chargement local
        try:
            st.image("prototype.jpg", caption="Système Hybride Validé - Fond Blanc", use_container_width=True)
        except:
            st.warning("⚠️ Image 'prototype.jpg' non trouvée. Assurez-vous qu'elle est à la racine du dossier.")

    with col_info:
        st.subheader("📋 Résumé du Design")
        st.success("""
        **Configuration Spécifique :**
        - **Ligne 1** : Prélèvement MQ-9 + Filtre ESP.
        - **Ligne 2** : Humidification simple → DBD.
        - **Liaison** : Sortie haute de l'humidificateur vers entrée DBD.
        - **Final** : Chambre de séjour thermique.
        """)

        # Bouton PDF corrigé
        try:
            pdf_bytes = generer_pdf_datasheet()
            st.download_button(
                label="📥 Télécharger la Datasheet (PDF)",
                data=pdf_bytes,
                file_name="Datasheet_SBA_2026.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erreur génération PDF : {e}")

    st.divider()
    st.subheader("📐 Dimensionnement & Capteurs")
    
    # Tableau selon la disposition mémorisée
    tab_data = {
        "Enseignements": ["Oxydes d'Azote", "Monoxyde Carbone", "Humidité/Temp", "Suivi Tension"],
        "Code": ["MQ-135", "MQ-9", "DHT22", "ZMPT101B"],
        "Horaire": ["Temps Réel", "Temps Réel", "Temps Réel", "Temps Réel"],
        "Lieu": ["Sortie", "Entrée L1", "Ligne 2", "Alim DBD"],
        "Promotion": ["M2RE", "M2RE", "M2RE", "M2RE"]
    }
    st.table(pd.DataFrame(tab_data))

# Pied de page
st.markdown("<br><hr><center><small>" + ST_TITRE_OFFICIEL + "</small></center>", unsafe_allow_html=True)
