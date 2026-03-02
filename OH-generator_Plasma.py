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
ST_TITRE_OFFICIEL = "Plateforme de monitoring à distance de traitemet de dechets hospitaliers DASRI-EPH de Sidi Bel Abbès""
ADMIN_REF = "Plateforme de monitoring à distance de traitemet de dechets hospitaliers DASRI-EPH de Sidi Bel Abbès"

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
    return pdf.output(dest='S').encode('latin-1')

# =================================================================
# 3. PAGE 1 : MONITORING TEMPS RÉEL
# =================================================================
if page == "📊 Monitoring Temps Réel":
    st.title("⚡ Monitoring des Oxydants Hybrides")
    st.markdown(f"### {ST_TITRE_OFFICIEL}")
    st.info(f"📅 État du système au : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Initialisation des états
    if 'temp_reelle' not in st.session_state: st.session_state.temp_reelle = 25.0
    if 'hum_reelle' not in st.session_state: st.session_state.hum_reelle = 50.0
    if 'co_reelle' not in st.session_state: st.session_state.co_reelle = 0.0
    if 'h2_reelle' not in st.session_state: st.session_state.h2_reelle = 0.0
    if 'nox_reelle' not in st.session_state: st.session_state.nox_reelle = 0.0

    with st.sidebar:
        st.header("🎮 Contrôle & Réception")
        mode_experimental = st.toggle("🚀 Activer Flux Réel (Wemos/TTGO)", value=True)
        st.divider()
        
        if mode_experimental:
            carte_active = st.selectbox("📡 Source de données :", ["Wemos D1 Mini", "TTGO ESP32"])
            fb_path = "/EDT_SBA" if "Wemos" in carte_active else "/EDT_SBA/TTGOESP32"
            
            if initialiser_firebase():
                try:
                    ref = db.reference(fb_path)
                    data_cloud = ref.get()
                    if data_cloud:
                        st.session_state.temp_reelle = float(data_cloud.get('temperature', 25.0))
                        st.session_state.hum_reelle = float(data_cloud.get('humidite', 50.0))
                        
                        # Récupération NOx (MQ-135)
                        val_nox = int(data_cloud.get('nox', 0))
                        if val_nox > 0:
                            ratio = (1023.0 / val_nox) - 1.0
                            st.session_state.nox_reelle = round(116.6 * pow(ratio, -2.76), 2)
                        
                        # Récupération CO (MQ-9) et H2
                        st.session_state.co_reelle = float(data_cloud.get('co', 0.0))
                        st.session_state.h2_reelle = float(data_cloud.get('h2', 0.0))
                        
                        st.success(f"✅ Flux Multi-Capteurs Actif")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")
            
            nb_gen = st.slider("Générateurs Actifs", 0, 3, 1)
            debit_aspiration = st.slider("Débit Aspirateur (m³/h)", 1.0, 15.0, 6.0)
        else:
            st.header("💻 Mode Simulation")
            st.session_state.temp_reelle = st.slider("Température T (°C)", 15.0, 80.0, 25.0)
            st.session_state.hum_reelle = st.slider("Humidité Relative H (%)", 5.0, 95.0, 50.0)
            st.session_state.co_reelle = st.slider("Niveau CO (ppm)", 0.0, 500.0, 15.0)
            st.session_state.h2_reelle = st.slider("Niveau H2 (ppm)", 0.0, 500.0, 8.0)
            debit_aspiration = 5.0
            nb_gen = 1

    # Moteur de calculs
    temp_actuelle = st.session_state.temp_reelle
    hum_actuelle = st.session_state.hum_reelle
    f_H = np.exp(-0.025 * (hum_actuelle - 10)) if hum_actuelle > 10 else 1.0
    f_T = np.exp(-0.030 * (temp_actuelle - 25)) if temp_actuelle > 25 else 1.0
    
    # Calcul des concentrations O3 et OH
    o3_ppm = (nb_gen * 120 * f_H * f_T) / debit_aspiration if debit_aspiration > 0 else 0
    oh_ppm = (nb_gen * 45 * (1 - f_H) * f_T) / debit_aspiration if debit_aspiration > 0 else 0

    # Affichage Métriques
    st.subheader(f"Statut : {'🔴 MESURE RÉELLE' if mode_experimental else '🔵 SIMULATION'}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🌡️ Température", f"{temp_actuelle:.1f} °C")
    m2.metric("💧 Humidité", f"{hum_actuelle:.1f} %")
    m3.metric("🧪 Monoxyde CO", f"{st.session_state.co_reelle:.1f} ppm")
    m4.metric("🔋 Hydrogène H2", f"{st.session_state.h2_reelle:.1f} ppm")

    st.markdown("#### 🧪 Analyse Chimique des Oxydants & Radicaux")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌀 Ozone (O3)", f"{o3_ppm:.2f} ppm", delta="Précurseur")
    c2.metric("✨ Hydroxyle (·OH)", f"{oh_ppm:.2f} ppm", delta="Radicalaire")
    c3.metric("💨 Débit d'Air", f"{debit_aspiration:.1f} m³/h")
    c4.metric("⚠️ Niveau NOx", f"{st.session_state.nox_reelle} ppm")

    st.divider()
    
    # =================================================================
    # 3.4 GRAPHIQUE DE CINÉTIQUE & TABLEAU D'EFFICACITÉ (UDL-SBA)
    # =================================================================
    q_range = np.linspace(1, 20, 100)
    
    # Calcul des courbes (Potentiel vs Résiduel)
    y_vals_oh = [(nb_gen * 45 * (1 - f_H) * f_T) / q for q in q_range]
    y_vals_o3 = [(nb_gen * 120 * f_H * f_T) / q for q in q_range]
    
    # Modélisation du NOx résiduel (plus Q est faible, plus le traitement est efficace)
    nox_actuel = st.session_state.nox_reelle if st.session_state.nox_reelle > 0 else 50.0
    y_vals_nox_residuel = [nox_actuel * (1 - (0.8 / (1 + 0.2 * q))) for q in q_range]

    # Affichage du graphique
    fig_q = go.Figure()
    fig_q.add_trace(go.Scatter(x=q_range, y=y_vals_oh, name="Potentiel ·OH", line=dict(color='orange', width=3)))
    fig_q.add_trace(go.Scatter(x=q_range, y=y_vals_o3, name="Potentiel O3", line=dict(color='cyan', width=2, dash='dash')))
    fig_q.add_trace(go.Scatter(x=q_range, y=y_vals_nox_residuel, name="NOx Résiduel (Sortie)", line=dict(color='red', width=3)))

    fig_q.update_layout(
        template="plotly_dark", 
        title="Cinétique de Neutralisation : Corrélation Oxydants / NOx", 
        xaxis_title="Débit Q (m³/h)", 
        yaxis_title="Concentration (ppm)",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig_q, use_container_width=True)

    # --- TABLEAU D'EFFICACITÉ DYNAMIQUE ---
    st.subheader("📊 Rapport d'Efficacité du Traitement")
    
    # Calcul de l'efficacité pour le débit actuel sélectionné dans le slider
    # L'efficacité est inversement proportionnelle au débit (temps de séjour)
    efficacite_actuelle = (0.8 / (1 + 0.2 * debit_aspiration)) * 100
    temps_sejour = 3.6 / debit_aspiration if debit_aspiration > 0 else 0 # Estimation simplifiée en sec

    col_stats1, col_stats2, col_stats3 = st.columns(3)
    
    with col_stats1:
        st.metric("🎯 Efficacité Globale", f"{efficacite_actuelle:.1f} %", 
                  delta=f"{'Optimale' if efficacite_actuelle > 70 else 'Sous-critique'}")
    
    with col_stats2:
        st.metric("⏳ Temps de Séjour estimé", f"{temps_sejour:.2f} s")
        
    with col_stats3:
        taux_reduction = nox_actuel * (efficacite_actuelle / 100)
        st.metric("📉 NOx Neutralisés", f"{taux_reduction:.1f} ppm")

    st.info(f"💡 **Analyse technique :** Pour le projet **{ST_TITRE_OFFICIEL}**, un débit de {debit_aspiration} m³/h "
            f"permet un temps de séjour de {temps_sejour:.2f}s, garantissant une réduction de {efficacite_actuelle:.1f}% des oxydes d'azote.")
# =================================================================
# 4. PAGE 2 : PROTOTYPE & DATASHEET
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
        st.subheader("📝 Documentation Technique")
        st.success("**Principe de fonctionnement :** L'air saturé en humidité traverse le réacteur DBD (Dielectric Barrier Discharge) pour générer des radicaux hydroxyles par dissociation moléculaire.")
        try:
            pdf_data = generer_pdf_datasheet()
            st.download_button("📥 Télécharger la Datasheet (PDF)", pdf_data, "Fiche_Technique_SBA.pdf", "application/pdf")
        except: pass

    st.divider()
    st.subheader("📐 Architecture & Nomenclature des Composants")

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
# 5. PIED DE PAGE
# =================================================================
st.warning("⚠️ Sécurité : Risque de Haute Tension (35kV). Surveillance active du Département d'Électrotechnique.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"<center><b>{ST_TITRE_OFFICIEL}</b><br><small>{ADMIN_REF}</small></center>", unsafe_allow_html=True)



