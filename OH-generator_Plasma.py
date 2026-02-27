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
ST_TITRE_OFFICIEL = "Station de supervision et commande d'une unité hybride de traitement de déchets hospitaliers par hydroxyle"

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
    pdf.multi_cell(190, 8, txt="Ce prototype utilise des générateurs d'ozone NU-12V combinés à une "
                               "aspiration variable permettant de moduler le temps de traitement "
                               "des gaz hospitaliers contaminés.")
    
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
            
            if initialiser_firebase():
                try:
                    ref = db.reference(fb_path)
                    data_cloud = ref.get()
                    if data_cloud:
                        st.session_state.last_temp = float(data_cloud.get('temperature', 25.0))
                        st.session_state.last_hum = float(data_cloud.get('humidite', 15.0))
                        # Simulation du débit mesuré par Firebase si disponible
                        debit_aspiration = float(data_cloud.get('debit', 6.0)) 
                except Exception as e:
                    st.error(f"Erreur flux : {e}")
            
            temp, hum = st.session_state.last_temp, st.session_state.last_hum
            nb_gen = st.slider("Générateurs Actifs", 0, 3, 1)
            debit_aspiration = st.slider("Débit Aspirateur (m³/h)", 1.0, 15.0, 6.0)
        else:
            st.header("💻 Mode [SIMULATION]")
            nb_gen = st.select_slider("Nombre de générateurs NU 12V", options=[0, 1, 2, 3], value=1)
            debit_aspiration = st.slider("Débit d'aspiration variable (m³/h)", 1.0, 20.0, 6.0)
            temp = st.slider("Température T (°C)", 15.0, 80.0, 25.0)
            hum = st.slider("Humidité Relative H (%)", 5.0, 95.0, 50.0)
        
        st.divider()
        st.caption(f"Vitesse d'air estimée : {(debit_aspiration/3600)/0.007:.2f} m/s")

    # =================================================================
    # MOTEUR DE CALCUL AVEC DÉBIT VARIABLE
    # =================================================================
    # 1. Production brute (mg/h)
    prod_nominale_mg_h = nb_gen * 10000 
    
    # 2. Facteurs environnementaux
    f_H = np.exp(-0.025 * (hum - 10)) if hum > 10 else 1.0
    f_T = np.exp(-0.030 * (temp - 25)) if temp > 25 else 1.0
    
    # 3. Masses produites (mg/h)
    o3_mg_h = prod_nominale_mg_h * f_H * f_T
    perte_H = 1.0 - f_H
    taux_conv_oh = 0.20
    oh_mg_h = prod_nominale_mg_h * perte_H * taux_conv_oh * f_T

    # 4. CALCUL DES CONCENTRATIONS (PPM) - DÉPENDANT DU DÉBIT Q
    # Formule : PPM = Production(mg/h) / (Débit(m3/h) * Densité(kg/m3))
    # Densité O3 = 2.14 kg/m3 | Densité air (pour OH) = 1.2 kg/m3
    o3_ppm = o3_mg_h / (debit_aspiration * 2.14) if debit_aspiration > 0 else 0
    oh_ppm = oh_mg_h / (debit_aspiration * 1.2) if debit_aspiration > 0 else 0

    # 5. Temps de résidence (Volume réacteur estimé à 0.002 m3)
    t_residence = (0.002 / (debit_aspiration / 3600)) # en secondes

    # --- AFFICHAGE MÉTRIQUES ---
    st.subheader(f"Statut : {status_text if 'status_text' in locals() else 'ACTIF'}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Débit d'Air", f"{debit_aspiration:.1f} m³/h", delta="Variable")
    m2.metric("Humidité", f"{hum:.1f} %")
    m3.metric("Temps de Résidence", f"{t_residence:.3f} s")
    m4.metric("Puissance active", f"{nb_gen * 85} W")

    st.markdown("#### 🧪 Analyse de la Neutralisation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Concentration O3", f"{o3_ppm:.2f} ppm")
    c2.metric("Concentration ·OH", f"{oh_ppm:.2f} ppm")
    c3.metric("Production O3", f"{o3_mg_h:.0f} mg/h")
    c4.metric("Dose Oxydante", f"{(o3_ppm * t_residence):.2f} ppm.s")

    st.divider()
    
    # Graphique interactif : Impact du débit sur les concentrations
    st.subheader("📈 Influence du Débit sur la Concentration")
    q_range = np.linspace(1, 20, 100)
    o3_q = [o3_mg_h / (q * 2.14) for q in q_range]
    oh_q = [oh_mg_h / (q * 1.2) for q in q_range]
    
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=q_range, y=o3_q, name="Ozone (ppm)", line=dict(color='cyan')))
    fig_q.add_trace(go.Scatter(x=q_range, y=oh_q, name="Hydroxyle (ppm)", line=dict(color='orange')))
    fig_q.add_vline(x=debit_aspiration, line_dash="dot", annotation_text="Débit actuel")
    fig_q.update_layout(template="plotly_dark", xaxis_title="Débit d'aspiration (m³/h)", yaxis_title="Concentration (ppm)")
    st.plotly_chart(fig_q, use_container_width=True)

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
            st.image("prototype.jpg", caption="Unité hybride avec ventilateur d'aspiration variable.", use_container_width=True)
        except:
            st.error("⚠️ Image 'prototype.jpg' introuvable.")
    
    with col_desc:
        st.subheader("📝 Contrôle du Débit")
        st.info("""
        Le débit est piloté par un signal PWM envoyé au ventilateur d'extraction. 
        - **Débit faible :** Maximise la concentration et le temps de traitement.
        - **Débit élevé :** Assure un renouvellement rapide de l'air de la chambre de stockage.
        """)
        
        try:
            pdf_data = generer_pdf_datasheet()
            st.download_button(label="📥 Télécharger PDF", data=pdf_data, file_name="Datasheet_SBA_2026.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

    st.divider()
    
    # =================================================================
    # TABLEAU TECHNIQUE RÉVISÉ
    # =================================================================
    st.subheader("📐 Architecture & Nomenclature des Composants")
    data_tab = {
        "Bloc/Fonction": ["Filtration Électrostatique", "Ionisation Diélectrique", "Analyse de Combustion", "Analyse de Neutralisation", "Supervision & IHM"],
        "Code (Référence)": ["ESP-MOD-01", "DBD-RECT-150", "MQ-9-SENS", "MQ-135-SENS", "WEMOS-D1-R1"],
        "Mode et plage de fonctionnement": ["Continu", "15-25 kHz", "Temps Réel", "Temps Réel", "2.4 GHz (WiFi)"],
        "Temps de traitement": ["24h/24", "Cycle Traitement", "Permanent", "Permanent", "Cloud Sync"],
        "Localisation": ["Ligne 1 (Top)", "Ligne 2 (Bottom)", "Entrée Système", "Sortie Aspirateur", "Pupitre Commande"],
        "Type de fonctionnement": ["Haute Tension", "Plasma Froid", "Analogique", "Analogique", "IoT / Firebase"]
    }
    st.table(pd.DataFrame(data_tab))

# =================================================================
# PIED DE PAGE
# =================================================================
st.warning("⚠️ Sécurité : Risque de Haute Tension. Système sous surveillance du Département d'Électrotechnique.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<center><b>{ST_TITRE_OFFICIEL}</b></center>", unsafe_allow_html=True)

