import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF  # Nécessite pip install fpdf2

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Station de supervision et commande d'une unité hybride de traitement de déchets hospitaliers par hydroxyle",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Navigation par menu latéral
st.sidebar.title("📂 Menu Principal")
page = st.sidebar.radio("Navigation :", ["📊 Monitoring Temps Réel", "🔬 Prototype & Datasheet"])

# Titre officiel rappelé systématiquement
ST_TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# =================================================================
# 2. FONCTIONS DE SERVICE (FIREBASE & PDF)
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
                # Utiliser le fichier JSON local si non sur Streamlit Cloud
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur Firebase : {e}")
        return False

def generer_pdf_datasheet():
    """Génère un export PDF de la fiche technique"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="DATASHEET TECHNIQUE DU PROTOTYPE HYBRIDE", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 10, txt=f"Projet : {ST_TITRE_OFFICIEL}", ln=True)
    pdf.cell(190, 10, txt=f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="1. Architecture du Système", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(190, 8, txt="Ce prototype utilise des générateurs d'ozone industriels NU-12V (10g/h par unité). "
                               "L'innovation réside dans la conversion de l'Ozone en radicaux Hydroxyles "
                               "par le biais d'une humidification contrôlée en amont du réacteur DBD.")
    
    return pdf.output()

# =================================================================
# PAGE 1 : MONITORING TEMPS RÉEL
# =================================================================
if page == "📊 Monitoring Temps Réel":
    st_autorefresh(interval=2000, key="datarefresh")
    
    st.title("⚡ Monitoring des Oxydants Hybrides")
    st.markdown(f"### {ST_TITRE_OFFICIEL}")
    st.info(f"📅 Date du jour : {datetime.now().strftime('%d/%m/%Y')}")

    if 'last_temp' not in st.session_state: st.session_state.last_temp = 25.0
    if 'last_hum' not in st.session_state: st.session_state.last_hum = 15.0

    with st.sidebar:
        st.header("🎮 Contrôle du Système")
        mode_experimental = st.toggle("🚀 Activer Mode Expérimental", value=False)
        st.divider()
        
        if mode_experimental:
            st.header("🔌 Réception [MESURÉE]")
            carte_active = st.selectbox(
                "📡 Choisir l'unité source :",
                ["Wemos D1 Mini (WiFi)", "TTGO T-Internet-POE (Ethernet)"]
            )
            
            fb_path = "/EDT_SBA/Wemos" if "Wemos" in carte_active else "/EDT_SBA/TTGO"
            st.caption(f"Flux actif : `{fb_path}`")

            if initialiser_firebase():
                try:
                    ref = db.reference(fb_path)
                    data_cloud = ref.get()
                    if data_cloud:
                        st.session_state.last_temp = float(data_cloud.get('temperature', 25.0))
                        st.session_state.last_hum = float(data_cloud.get('humidite', 15.0))
                        st.success(f"✅ {carte_active} en ligne")
                except Exception as e:
                    st.error(f"Erreur flux : {e}")
            
            temp, hum = st.session_state.last_temp, st.session_state.last_hum
            nb_gen = st.slider("Générateurs Actifs (Relais)", 0, 3, 1)
        else:
            st.header("💻 Mode [SIMULATION]")
            nb_gen = st.select_slider("Nombre de générateurs NU 12V (10g/h unité)", options=[0, 1, 2, 3], value=1)
            temp = st.slider("Température du Gaz T (°C) [SIM]", 15.0, 80.0, 25.0)
            hum = st.slider("Humidité Relative H (%) [SIM]", 5.0, 95.0, 15.0)
        
        st.divider()
        st.caption("Débit d'air constant : 6 m³/h")

    # =================================================================
    # MOTEUR DE CALCUL (BASÉ SUR ÉTUDES ET PRODUCTION NU-12V)
    # =================================================================
    # 1. Capacité brute (10g/h = 10000 mg/h par module)
    prod_nominale_mg_h = nb_gen * 10000 
    
    # 2. Facteurs de décroissance (Ozone)
    # Décroissance O3 (100% à 10% HR et 25°C)
    facteur_H_o3 = np.exp(-0.025 * (hum - 10)) if hum > 10 else 1.0
    facteur_T_o3 = np.exp(-0.030 * (temp - 25)) if temp > 25 else 1.0
    
    o3_mg_h_reel = prod_nominale_mg_h * facteur_H_o3 * facteur_T_o3
    
    # 3. Facteurs de croissance (Hydroxyle OH)
    # Transformation de la perte d'Ozone due à l'humidité en OH
    perte_H = 1.0 - facteur_H_o3
    taux_conversion_oh = 0.20 # Rendement de transformation OH estimé
    oh_mg_h_reel = prod_nominale_mg_h * perte_H * taux_conversion_oh * facteur_T_o3

    # --- AFFICHAGE ---
    status_text = f"🔴 MODE RÉEL ({nb_gen} GEN)" if mode_experimental else "🔵 MODE SIMULATION"
    st.subheader(f"Statut : {status_text}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Température", f"{temp:.1f} °C", delta=f"{temp-25:.1f}°")
    m2.metric("Humidité", f"{hum:.1f} %", delta="Formation OH active" if hum > 30 else "Zone O3 pure")
    m3.metric("Puissance Active", f"{nb_gen * 85:.1f} W")

    st.markdown("#### 🧪 Concentrations et Rendements")
    c1, c2, c3, c4 = st.columns(4)
    # PPM O3 (Densité ~2.14) | PPM OH (Densité ~0.76 estimée pour air)
    c1.metric("Ozone (O3)", f"{(o3_mg_h_reel / (6.0 * 2.14)):.2f} ppm")
    c2.metric("Hydroxyle (·OH)", f"{(oh_mg_h_reel / (6.0 * 0.76)):.2f} ppm")
    c3.metric("Production O3", f"{o3_mg_h_reel:.0f} mg/h")
    c4.metric("Efficacité (G)", f"{(o3_mg_h_reel/(nb_gen*85) if nb_gen>0 else 0):.2f} mg/W")

    st.divider()
    
    # Graphique de conversion croisée
    h_range = np.linspace(5, 95, 100)
    o3_plot = [prod_nominale_mg_h * (np.exp(-0.025 * (h - 10)) if h > 10 else 1.0) * facteur_T_o3 for h in h_range]
    oh_plot = [prod_nominale_mg_h * (1.0 - (np.exp(-0.025 * (h - 10)) if h > 10 else 1.0)) * taux_conversion_oh * facteur_T_o3 for h in h_range]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h_range, y=o3_plot, name="Ozone (O3)", line=dict(color='cyan', width=3)))
    fig.add_trace(go.Scatter(x=h_range, y=oh_plot, name="Hydroxyle (·OH)", line=dict(color='orange', width=3)))
    fig.add_vline(x=hum, line_dash="dash", line_color="white", annotation_text="Fonctionnement Actuel")
    fig.update_layout(template="plotly_dark", title="Modélisation de la conversion radicalaire (Transformation O3 en ·OH)", xaxis_title="Humidité Relative (%)", yaxis_title="Production (mg/h)")
    st.plotly_chart(fig, use_container_width=True)

# =================================================================
# PAGE 2 : PROTOTYPE & DATASHEET
# =================================================================
elif page == "🔬 Prototype & Datasheet":
    st.title("🔬 Architecture & Spécifications")
    st.markdown(f"#### {ST_TITRE_OFFICIEL}")
    st.divider()

    col_img, col_desc = st.columns([1.6, 1])
    
    with col_img:
        st.subheader("🖼️ Vue du Prototype")
        try:
            st.image("prototype.jpg", caption="Unité hybride de traitement par hydroxyle - UDL-SBA.", use_container_width=True)
        except:
            st.error("⚠️ Image 'prototype.jpg' introuvable.")
    
    with col_desc:
        st.subheader("📝 Principe de fonctionnement")
        st.info("Le système utilise des générateurs NU-12V pour créer un plasma froid. L'injection de vapeur d'eau transforme l'ozone en radicaux hydroxyles (·OH), augmentant le pouvoir oxydant pour les déchets hospitaliers.")
        
        try:
            pdf_data = generer_pdf_datasheet()
            st.download_button(label="📥 Télécharger PDF", data=pdf_data, file_name="Datasheet_SBA_2026.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

    st.divider()
    
    # =================================================================
    # TABLEAU TECHNIQUE RÉVISÉ ET MÉMORISÉ
    # =================================================================
    st.subheader("📐 Architecture & Nomenclature des Composants")

    data_tab = {
        "Bloc/Fonction": [
            "Filtration Électrostatique", 
            "Ionisation Diélectrique", 
            "Analyse de Combustion", 
            "Analyse de Neutralisation", 
            "Supervision & IHM"
        ],
        "Code (Référence)": [
            "ESP-MOD-01", 
            "DBD-RECT-150", 
            "MQ-9-SENS", 
            "MQ-135-SENS", 
            "WEMOS-D1-R1"
        ],
        "Mode et plage de fonctionnement": [
            "Continu", 
            "15-25 kHz", 
            "Temps Réel", 
            "Temps Réel", 
            "2.4 GHz (WiFi)"
        ],
        "Temps de traitement": [
            "24h/24", 
            "Cycle Traitement", 
            "Permanent", 
            "Permanent", 
            "Cloud Sync"
        ],
        "Localisation": [
            "Ligne 1 (Top)", 
            "Ligne 2 (Bottom)", 
            "Entrée Système", 
            "Sortie Aspirateur", 
            "Pupitre Commande"
        ],
        "Type de fonctionnement": [
            "Haute Tension", 
            "Plasma Froid", 
            "Analogique", 
            "Analogique", 
            "IoT / Firebase"
        ]
    }

    st.table(pd.DataFrame(data_tab))

# =================================================================
# PIED DE PAGE
# =================================================================
st.warning("⚠️ Sécurité : Risque de Haute Tension. Système sous surveillance du Département d'Électrotechnique.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<center><b>{ST_TITRE_OFFICIEL}</b></center>", unsafe_allow_html=True)
