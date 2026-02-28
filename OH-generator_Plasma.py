import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# =================================================================
# 1. CONFIGURATION DE LA PAGE & TITRES OFFICIELS
# =================================================================
# Titre mémorisé selon vos instructions
ST_TITRE_OFFICIEL = "Station de supervision et commande d'une unité hybride de traitement de déchets hospitaliers par hydroxyle"
ADMIN_REF = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

st.set_page_config(
    page_title=ST_TITRE_OFFICIEL,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Rafraîchissement automatique toutes les 2 secondes
st_autorefresh(interval=2000, key="datarefresh")

# Navigation par menu latéral
st.sidebar.title("📂 Menu Principal")
page = st.sidebar.radio("Navigation :", ["📊 Monitoring Temps Réel", "🔬 Prototype & Datasheet"])

# =================================================================
# 2. FONCTIONS DE SERVICE (FIREBASE & PDF)
# =================================================================
@st.cache_resource
def initialiser_firebase():
    """Initialise la connexion Firebase de manière sécurisée"""
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                fb_secrets = dict(st.secrets["firebase"])
                if "private_key" in fb_secrets:
                    fb_secrets["private_key"] = fb_secrets["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(fb_secrets)
            else:
                # Fallback local pour développement
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur de liaison Cloud : {e}")
        return False

def generer_pdf_datasheet():
    """Génère l'export PDF de la fiche technique"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="DATASHEET TECHNIQUE DU PROTOTYPE HYBRIDE", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 10, txt=f"Projet : {ST_TITRE_OFFICIEL}", ln=True)
    pdf.cell(190, 10, txt=f"Référence : {ADMIN_REF}", ln=True)
    pdf.cell(190, 10, txt=f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="1. Architecture du Système", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(190, 8, txt="Ce prototype utilise des générateurs d'ozone et un réacteur DBD "
                               "pour la production de radicaux hydroxyles destinés à la "
                               "neutralisation des agents pathogènes hospitaliers.")
    return pdf.output()

# =================================================================
# 3. PAGE 1 : MONITORING TEMPS RÉEL (POLYVALENT)
# =================================================================
if page == "📊 Monitoring Temps Réel":
    st.title("⚡ Monitoring des Oxydants Hybrides")
    st.markdown(f"### {ST_TITRE_OFFICIEL}")
    st.info(f"📅 État du système au : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Initialisation des variables d'état (évite les erreurs de chargement)
    if 'temp' not in st.session_state: st.session_state.temp = 25.0
    if 'hum' not in st.session_state: st.session_state.hum = 45.0

    with st.sidebar:
        st.header("🎮 Contrôle & Réception")
        mode_experimental = st.toggle("🚀 Activer Flux Réel (Wemos/TTGO)", value=False)
        st.divider()
        
        if mode_experimental:
            carte_active = st.selectbox(
                "📡 Source de données :",
                ["Wemos D1 Mini", "TTGO ESP32"]
            )
            # Chemin Firebase harmonisé
            fb_path = f"/EDT_SBA/{carte_active.replace(' ', '')}"
            
            if initialiser_firebase():
                try:
                    ref = db.reference(fb_path)
                    data_cloud = ref.get()
                    if data_cloud:
                        st.session_state.temp = float(data_cloud.get('temperature', 25.0))
                        st.session_state.hum = float(data_cloud.get('humidite', 45.0))
                        st.success(f"✅ Signal reçu : {carte_active}")
                    else:
                        st.warning("⏳ En attente de données...")
                except:
                    st.error("❌ Erreur de flux")
            
            nb_gen = st.slider("Générateurs Actifs", 0, 3, 1)
            debit_aspiration = st.slider("Débit Aspirateur (m³/h)", 1.0, 15.0, 6.0)
        else:
            st.header("💻 Mode Simulation")
            st.session_state.temp = st.slider("Température T (°C)", 15.0, 80.0, 25.0)
            st.session_state.hum = st.slider("Humidité Relative H (%)", 5.0, 95.0, 50.0)
            debit_aspiration = st.slider("Débit d'aspiration (m³/h)", 1.0, 20.0, 5.0)
            nb_gen = 1

    # --- MOTEUR DE CALCULS PHYSIQUES ---
    # Facteurs de correction environnementaux
    f_H = np.exp(-0.025 * (st.session_state.hum - 10)) if st.session_state.hum > 10 else 1.0
    f_T = np.exp(-0.030 * (st.session_state.temp - 25)) if st.session_state.temp > 25 else 1.0
    
    # Calcul des concentrations (PPM)
    o3_ppm = (nb_gen * 120 * f_H * f_T) / debit_aspiration if debit_aspiration > 0 else 0
    oh_ppm = (nb_gen * 45 * (1 - f_H) * f_T) / debit_aspiration if debit_aspiration > 0 else 0
    t_residence = (0.002 / (debit_aspiration / 3600)) if debit_aspiration > 0 else 0

    # --- AFFICHAGE MÉTRIQUES PRINCIPALES ---
    st.subheader(f"Statut : {'🔴 MESURE EN DIRECT' if mode_experimental else '🔵 SIMULATION'}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🌡️ Température", f"{st.session_state.temp:.1f} °C")
    m2.metric("💧 Humidité", f"{st.session_state.hum:.1f} %")
    m3.metric("🌀 Débit d'Air", f"{debit_aspiration:.1f} m³/h")
    m4.metric("⏱️ T. Résidence", f"{t_residence:.3f} s")

    st.markdown("#### 🧪 Analyse Chimique des Radicaux")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Concentration O3", f"{o3_ppm:.2f} ppm")
    c2.metric("Concentration ·OH", f"{oh_ppm:.2f} ppm", delta="Radicaux")
    c3.metric("Production O3", f"{(o3_ppm * debit_aspiration * 2.14):.0f} mg/h")
    c4.metric("Puissance active", f"{nb_gen * 85} W")

    st.divider()
    # Graphique de performance
    q_range = np.linspace(1, 20, 100)
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=q_range, y=[(nb_gen*45*(1-f_H)*f_T)/q for q in q_range], name="·OH (ppm)", line=dict(color='orange')))
    fig_q.update_layout(template="plotly_dark", title="Cinétique de l'hydroxyle en fonction du débit", xaxis_title="Q (m³/h)")
    st.plotly_chart(fig_q, use_container_width=True)

# =================================================================
# 4. PAGE 2 : PROTOTYPE & DATASHEET (TABLEAU EXACT)
# =================================================================
elif page == "🔬 Prototype & Datasheet":
    st.title("🔬 Architecture & Spécifications")
    st.markdown(f"#### {ST_TITRE_OFFICIEL}")
    st.divider()

    col_img, col_desc = st.columns([1.6, 1])
    with col_img:
        st.subheader("🖼️ Vue du Prototype")
        try:
            st.image("prototype.jpg", caption="Unité Hybride : Ligne 1 (Filtration) & Ligne 2 (Hydroxyle).", use_container_width=True)
        except:
            st.error("⚠️ Image 'prototype.jpg' non trouvée.")

    with col_desc:
        st.subheader("📝 Documentation")
        st.success("**Principe :** L'air saturé en humidité traverse le réacteur DBD pour générer des radicaux hydroxyles hautement réactifs.")
        try:
            pdf_data = generer_pdf_datasheet()
            st.download_button("📥 Télécharger le PDF", pdf_data, "Fiche_Technique_SBA.pdf", "application/pdf")
        except: pass

    st.divider()
    st.subheader("📐 Architecture & Nomenclature des Composants")

    # Votre tableau exact corrigé sans condensation
    data_tab = {
        "Bloc/Fonction": [
            "Filtration Électrostatique", 
            "Ionisation Diélectrique", 
            "Analyse de Combustion (CO)", 
            "Analyse des Rejets (NOx)", 
            "Hygrométrie & Température",
            "Supervision & IHM"
        ],
        "Code (Référence)": [
            "ESP-MOD-01", 
            "DBD-RECT-150", 
            "MQ-9-SENS", 
            "MQ-135-SENS", 
            "DHT22-DIGITAL",
            "TTGO-T-POE-V1"
        ],
        "Mode et plage de fonctionnement": [
            "Continu", 
            "15-25 kHz", 
            "10-1000 ppm (Corrigé)", 
            "Multi-gaz (Qualité air)", 
            "-40 à 80°C / 0-100% HR",
            "Dual-Core / Ethernet RJ45"
        ],
        "Temps de traitement": [
            "24h/24", 
            "Cycle Traitement", 
            "Réel (Cycle 5V)", 
            "Permanent", 
            "Échantillonnage 2s",
            "Cloud Sync / RTOS"
        ],
        "Localisation": [
            "Ligne 1 (Top)", 
            "Ligne 2 (Bottom)", 
            "Chambre de Combustion", 
            "Sortie Aspirateur", 
            "Chambre de Réaction",
            "Pupitre de Commande"
        ],
        "Type de fonctionnement": [
            "Haute Tension", 
            "Plasma Froid", 
            "Analogique (Compensé)", 
            "Analogique", 
            "Numérique (One-Wire)",
            "IoT / Firebase"
        ]
    }
    st.table(pd.DataFrame(data_tab))

# =================================================================
# PIED DE PAGE
# =================================================================
st.warning("⚠️ Sécurité : Risque de Haute Tension (35kV). Surveillance active du Département d'Électrotechnique.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<center><b>{ST_TITRE_OFFICIEL}</b><br><small>{ADMIN_REF}</small></center>", unsafe_allow_html=True)
