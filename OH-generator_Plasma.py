import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from streamlit_autorefresh import st_autorefresh
import fpdf  # Assurez-vous d'installer fpdf2 via pip install fpdf2

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Rafraîchissement automatique pour le monitoring (2 secondes)
if "datarefresh" not in st.session_state:
    st.session_state.datarefresh = True

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
                # Chemin vers votre fichier JSON local si non déployé sur Streamlit Cloud
                cred = credentials.Certificate("votre-cle.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://oh-generator-plasma-sba-default-rtdb.europe-west1.firebasedatabase.app'
            })
        return True
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion Cloud : {e}")
        return False

def generer_pdf_datasheet():
    """Génère un export PDF de la fiche technique"""
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="FICHE TECHNIQUE DU PROTOTYPE HYBRIDE", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Projet : {ST_TITRE_OFFICIEL}", ln=True)
    pdf.cell(200, 10, txt=f"Date d'export : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, txt="Architecture : Ligne 1 (Pollution ESP) / Ligne 2 (Réactive DBD)", ln=True)
    pdf.cell(200, 10, txt="Configuration : Une seule chambre d'humidification avec sortie haute vers DBD", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# =================================================================
# PAGE 1 : MONITORING TEMPS RÉEL
# =================================================================
if page == "📊 Monitoring Temps Réel":
    st_autorefresh(interval=2000, key="datarefresh")
    
    st.title("⚡ Monitoring des Oxydants Hybrides")
    st.markdown(f"**{ST_TITRE_OFFICIEL}**")
    st.info(f"📅 État du système au : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Logique Firebase
    if 'last_temp' not in st.session_state: st.session_state.last_temp = 23.0
    if 'last_hum' not in st.session_state: st.session_state.last_hum = 45.0

    with st.sidebar:
        st.header("🎮 Contrôle")
        mode_experimental = st.toggle("🚀 Mode Wemos D1 (Réel)", value=False)
        
        if mode_experimental and initialiser_firebase():
            try:
                ref = db.reference('/EDT_SBA')
                data_cloud = ref.get()
                if data_cloud:
                    st.session_state.last_temp = float(data_cloud.get('temperature', 23.0))
                    st.session_state.last_hum = float(data_cloud.get('humidite', 45.0))
                    st.success("📡 Flux Cloud Actif")
            except:
                st.warning("⏳ Synchronisation...")

    # Paramètres (Mesurés ou Simulés)
    if mode_experimental:
        temp, hum = st.session_state.last_temp, st.session_state.last_hum
        v_peak, freq = 23.0, 15000.0
    else:
        v_peak = st.sidebar.slider("Tension Crête Vp (kV)", 10.0, 35.0, 23.0)
        freq = st.sidebar.slider("Fréquence f (Hz)", 1000.0, 25000.0, 15000.0)
        temp = st.sidebar.slider("Température T (°C)", 20.0, 100.0, 25.0)
        hum = st.sidebar.slider("Humidité H2O (%)", 10.0, 95.0, 50.0)

    # --- CALCULS PHYSIQUES ---
    EPS_0, EPS_R_QUARTZ, R_ext, R_int = 8.854e-12, 3.8, 4.0, 2.5
    d_gap, L_act = 3.0, 150.0
    v_th = 13.2 * (1 + 0.05 * np.sqrt(d_gap))
    C_die = (2 * np.pi * EPS_0 * EPS_R_QUARTZ * (L_act/1000.0)) / np.log(R_ext / R_int)
    p_watt = 4 * freq * C_die * (v_th * 1000.0) * ((v_peak - v_th) * 1000.0) * 2 if v_peak > v_th else 0.0
    
    oh_final = 0.03554 * p_watt * (hum/100.0) * np.exp(-(temp - 25.0) / 150.0)
    o3_final = 0.00129 * p_watt * (1.0 - hum/100.0) * np.exp(-(temp - 25.0) / 45.0) if v_peak > v_th else 0.0

    # --- AFFICHAGE ---
    st.subheader("🧪 Données Environnementales " + ("[MESURÉES]" if mode_experimental else "[SIMULÉES]"))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Température", f"{temp:.1f} °C")
    col2.metric("Humidité", f"{hum:.1f} %")
    col3.metric("Production ·OH", f"{oh_final:.2f} ppm")
    col4.metric("Production O3", f"{o3_final:.2f} ppm")

    st.divider()
    
    g_left, g_right = st.columns(2)
    with g_left:
        st.subheader("🌀 Lissajous (Q-V)")
        t_vals = np.linspace(0, 2*np.pi, 500)
        fig_lis = go.Figure(go.Scatter(x=v_peak * np.sin(t_vals), y=(C_die * 1e6 * v_peak) * np.cos(t_vals), fill="toself", line=dict(color='#ADFF2F')))
        fig_lis.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_lis, use_container_width=True)
    with g_right:
        st.subheader("📊 Rendement Énergétique")
        st.metric("Puissance active", f"{p_watt:.1f} Watts")
        st.progress(min(p_watt/500.0, 1.0))

# =================================================================
# PAGE 2 : PROTOTYPE & DATASHEET
# =================================================================
elif page == "🔬 Prototype & Datasheet":
    st.title("🔬 Spécifications du Prototype Hybride")
    st.markdown(f"**{ST_TITRE_OFFICIEL}**")
    
    st.divider()

    # --- SECTION IMAGE ---
    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.subheader("🖼️ Visualisation du Design Corrigé")
        # Note : Assurez-vous que l'image est dans le même dossier que le script
        try:
            st.image("Gemini_Generated_Image_wmaxf1wmaxf1wmax.jpg", 
                     caption="Architecture validée : Ligne 2 avec chambre d'humidification unique et DBD en série.",
                     use_container_width=True)
        except:
            st.error("⚠️ Fichier image introuvable. Veuillez vérifier le nom du fichier.")
    
    with c2:
        st.subheader("📋 Résumé du Design")
        st.info("""
        **Configuration Spécifique :**
        - **Ligne 1** : Prélèvement MQ-9 + Filtre ESP.
        - **Ligne 2** : Humidification simple -> DBD.
        - **Liaison** : Sortie haute de l'humidificateur vers entrée DBD.
        - **Final** : Chambre de séjour thermique.
        """)
        
        pdf_data = generer_pdf_datasheet()
        st.download_button(
            label="📥 Télécharger la Datasheet (PDF)",
            data=pdf_data,
            file_name="Datasheet_Prototype_SBA_2026.pdf",
            mime="application/pdf"
        )

    st.divider()

    # --- TABLEAUX TECHNIQUES ---
    st.subheader("📐 Détails de Dimensionnement")
    tab_geo, tab_sens = st.tabs(["Dimensionnement Physique", "Configuration Capteurs"])
    
    with tab_geo:
        dim_data = {
            "Composant": ["Chambre DBD", "Électrode interne", "Tube Quartz", "Chambre Humidid.", "Vitesse Flux"],
            "Matériau": ["Quartz/Inox", "Cuivre", "SiO2", "PVC/Verre", "Air/H2O"],
            "Dimensions": ["150 mm", "3.0 mm (gap)", "Diam. 20mm", "Capacité 1L", "2.5 m/s"]
        }
        st.table(pd.DataFrame(dim_data))

    with tab_sens:
        # Respect de la disposition : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
        sensor_data = {
            "Enseignements": ["Oxydes d'Azote", "Monoxyde Carbone", "Humidité/Temp", "Suivi Tension"],
            "Code": ["MQ-135", "MQ-9", "DHT22", "ZMPT101B"],
            "Promotion": ["M2RE", "M2RE", "M2RE", "M2RE"],
            "Lieu": ["Sortie", "Entrée L1", "Entrée L2", "Alim DBD"],
            "Statut": ["Actif", "Actif", "Actif", "Actif"]
        }
        st.dataframe(pd.DataFrame(sensor_data), hide_index=True)

# =================================================================
# PIED DE PAGE COMMUN
# =================================================================
st.markdown("<br><br><hr>", unsafe_allow_html=True)
st.markdown(
    f"<center><small>{ST_TITRE_OFFICIEL}</small></center>", 
    unsafe_allow_html=True
)
