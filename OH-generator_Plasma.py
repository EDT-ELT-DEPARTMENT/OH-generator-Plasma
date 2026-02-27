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
ST_TITRE_OFFICIEL = "Plateforme de supervision et commande d'une unité hybride de traitement de déchets hospitaliers par hydroxyle"

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
    """Génère un export PDF de la fiche technique (Syntaxe fpdf2)"""
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
    pdf.multi_cell(190, 8, txt="Ce prototype est conçu pour la génération d'oxydants hybrides (OH-/O3). "
                               "Il se compose de deux lignes de traitement. La Ligne 2 (Réactive) "
                               "utilise une chambre d'humidification unique connectée en série avec "
                               "un réacteur DBD de grande dimension via sa sortie haute.")
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="2. Paramètres de Dimensionnement", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 8, txt="- Diélectrique : Tube de Quartz (SiO2)", ln=True)
    pdf.cell(190, 8, txt="- Gap de décharge : 3.0 mm", ln=True)
    pdf.cell(190, 8, txt="- Longueur active : 150 mm", ln=True)
    pdf.cell(190, 8, txt="- Capteurs : MQ-9, MQ-135, DHT22, ZMPT101B", ln=True)
    
    # Retourne directement les bytes pour st.download_button
    return pdf.output()

# =================================================================
# PAGE 1 : MONITORING TEMPS RÉEL (VOTRE CODE INITIAL)
# =================================================================
if page == "📊 Monitoring Temps Réel":
    st_autorefresh(interval=2000, key="datarefresh")
    
    st.title("⚡ Monitoring des Oxydants Hybrides")
    st.markdown(f"### {ST_TITRE_OFFICIEL}")
    st.info(f"📅 Date du jour : {datetime.now().strftime('%d/%m/%Y')}")

    if 'last_temp' not in st.session_state: st.session_state.last_temp = 23.0
    if 'last_hum' not in st.session_state: st.session_state.last_hum = 45.0

    with st.sidebar:
        st.header("🎮 Contrôle du Système")
        mode_experimental = st.toggle("🚀 Activer Mode Expérimental (Wemos D1)", value=False)
        st.divider()
        
        if mode_experimental:
            st.header("🔌 Réception [MESURÉE]")
            if initialiser_firebase():
                try:
                    ref = db.reference('/EDT_SBA')
                    data_cloud = ref.get()
                    if data_cloud:
                        st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                        st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
                        st.success("✅ Capteurs en ligne")
                except Exception as e:
                    st.error(f"Erreur flux : {e}")
            temp, hum = st.session_state.last_temp, st.session_state.last_hum
            v_peak, freq = 23.0, 15000.0
        else:
            st.header("💻 Mode [SIMULATION]")
            v_peak = st.slider("Tension Crête Vp (kV) [SIM]", 10.0, 35.0, 23.0)
            freq = st.slider("Fréquence f (Hz) [SIM]", 1000.0, 25000.0, 15000.0)
            temp = st.slider("Température T (°C) [SIM]", 20.0, 100.0, 25.0)
            hum = st.slider("Humidité H2O (%) [SIM]", 10.0, 95.0, 50.0)
        
        st.divider()
        d_gap = st.number_input("Gap de décharge (d) [mm]", value=3.0, step=0.1)
        L_act = st.number_input("Longueur Active (L) [mm]", value=150.0, step=1.0)

    # --- CALCULS PHYSIQUES ---
    EPS_0, EPS_R_QUARTZ, R_ext, R_int = 8.854e-12, 3.8, 4.0, 2.5
    v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap)) 
    C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000.0)) / np.log(R_ext / R_int)
    p_watt = 4 * freq * C_die * (v_th * 1000.0) * ((v_peak - v_th) * 1000.0) * 2 if v_peak > v_th else 0.0
    oh_final = 0.03554 * p_watt * (hum/100.0) * np.exp(-(temp - 25.0) / 150.0)
    o3_final = 0.00129 * p_watt * (1.0 - hum/100.0) * np.exp(-(temp - 25.0) / 45.0) if v_peak > v_th else 0.0
    total = oh_final + o3_final
    pct_oh = (oh_final / total * 100.0) if total > 0 else 0.0
    g_value = (oh_final * 40.0) / p_watt if p_watt > 0 else 0.0

    # --- AFFICHAGE ---
    st.subheader(f"Statut : {'🔴 MODE RÉEL' if mode_experimental else '🔵 MODE SIMULATION'}")
    m1, m2 = st.columns(2)
    m1.metric("Température", f"{temp:.1f} °C", delta=f"{temp-25:.1f}°")
    m2.metric("Humidité relative", f"{hum:.1f} %")

    st.markdown("#### ⚡ Résultats Physico-Chimiques")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Production ·OH", f"{oh_final:.2f} ppm", f"{pct_oh:.1f} %")
    c2.metric("Production O3", f"{o3_final:.2f} ppm")
    c3.metric("Puissance active", f"{p_watt:.1f} W")
    c4.metric("Efficacité (G)", f"{g_value:.3f} g/kWh")

    st.divider()
    g_left, g_right = st.columns(2)
    with g_left:
        t_vals = np.linspace(0, 2*np.pi, 500)
        fig_lis = go.Figure(go.Scatter(x=v_peak * np.sin(t_vals), y=(C_die * 1e6 * v_peak) * np.cos(t_vals), fill="toself", line=dict(color='#ADFF2F')))
        fig_lis.update_layout(template="plotly_dark", xaxis_title="U (kV)", yaxis_title="Q (µC)", title="Cycle de Charge")
        st.plotly_chart(fig_lis, use_container_width=True)
    with g_right:
        v_range = np.linspace(10, 35, 100)
        oh_curve = [0.03554 * (4 * freq * C_die * (v_th * 1000) * ((v - v_th) * 1000) * 2) * (hum/100) if v > v_th else 0 for v in v_range]
        fig_oh = go.Figure(go.Scatter(x=v_range, y=oh_curve, line=dict(color='#00FBFF', width=3)))
        fig_oh.update_layout(template="plotly_dark", xaxis_title="Tension (kV)", yaxis_title="·OH (ppm)", title="Modèle Cinétique")
        st.plotly_chart(fig_oh, use_container_width=True)

# =================================================================
# PAGE 2 : PROTOTYPE & DATASHEET (NOUVELLE PAGE)
# =================================================================
elif page == "🔬 Prototype & Datasheet":
    st.title("🔬 Architecture & Spécifications")
    st.markdown(f"#### {ST_TITRE_OFFICIEL}")
    st.divider()

    col_img, col_desc = st.columns([1.6, 1])
    
    with col_img:
        st.subheader("🖼️ Vue du Prototype (Design Corrigé)")
        # L'image doit être nommée 'prototype.jpg' dans le même dossier
        try:
            st.image("prototype.jpg", caption="Système Hybride : Ligne 2 optimisée avec sortie haute.", use_container_width=True)
        except:
            st.error("⚠️ Image 'prototype.jpg' introuvable à la racine du projet.")
    
    with col_desc:
        st.subheader("📝 Principe & Datasheet")
        st.success("""
        **Fonctionnement :**
        L'air injecté en Ligne 2 est humidifié par un brumisateur ultrasonique. 
        Le flux saturé sort par le haut pour alimenter directement le réacteur DBD 
        où l'énergie du plasma froid dissocie les molécules d'eau en radicaux hydroxyles.
        """)
        
        # Bouton de téléchargement PDF
        try:
            pdf_data = generer_pdf_datasheet()
            st.download_button(
                label="📥 Télécharger la Datasheet (PDF)",
                data=pdf_data,
                file_name="Datasheet_Hybride_SBA_2026.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

    st.divider()
    st.subheader("📐 Détails Techniques & Capteurs")
    
    # =================================================================
# TABLEAU TECHNIQUE DE COMPOSITION DU PROTOTYPE (CORRIGÉ)
# =================================================================
st.subheader("📐 Architecture & Nomenclature des Composants")

data_tab = {
    "Bloc/Foction": [
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
    "Enseignants (Responsable)": [
        "Filtre ESP", 
        "Réacteur DBD", 
        "Capteur CO", 
        "Capteur NOx", 
        "Microcontrôleur"
    ],
    "Horaire (Fréquence)": [
        "Continu", 
        "15-25 kHz", 
        "Temps Réel", 
        "Temps Réel", 
        "2.4 GHz (WiFi)"
    ],
    "Jours (Disponibilité)": [
        "24h/24", 
        "Cycle Traitement", 
        "Permanent", 
        "Permanent", 
        "Cloud Sync"
    ],
    "Lieu (Localisation)": [
        "Ligne 1 (Top)", 
        "Ligne 2 (Bottom)", 
        "Entrée Système", 
        "Sortie Aspirateur", 
        "Pupitre Commande"
    ],
    "Promotion (Niveau)": [
        "Haute Tension", 
        "Plasma Froid", 
        "Analogique", 
        "Analogique", 
        "IoT / Firebase"
    ]
}

# Affichage du tableau avec Pandas pour une présentation propre
st.table(pd.DataFrame(data_tab))

# =================================================================
# PIED DE PAGE
# =================================================================
st.warning("⚠️ Sécurité : Risque de Haute Tension. Système sous surveillance du Département d'Électrotechnique.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<center><b>{ST_TITRE_OFFICIEL}</b></center>", unsafe_allow_html=True)


