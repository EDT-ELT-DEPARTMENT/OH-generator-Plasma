import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO
from datetime import datetime

# =================================================================
# 1. CONFIGURATION DE LA PAGE
# =================================================================
st.set_page_config(
    page_title="OH-generator Plasma | UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# --- TITRE OFFICIEL ---
# Rappel : Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA
# Utilisé ici pour le projet de startup lié au département.
st.title("⚡ OH-generator Plasma")
st.markdown("### Système Intelligent de Traitement des Fumées Industrielles par Réacteur DBD Pulsé")
st.markdown("#### Optimisation de la Production de Radicaux Hydroxyles (·OH) via une Commande Adaptive à Base d'IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Session S2-2026 | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. BARRE LATÉRALE (CONSOLE DE COMMANDE)
# =================================================================
with st.sidebar:
    # Note : Assurez-vous que logo.PNG est présent dans votre dépôt GitHub
    try:
        st.image("logo.PNG")
    except:
        st.warning("Logo non trouvé. Ajoutez 'logo.PNG' à votre dépôt GitHub.")
    
    st.header("🎮 Console de Commande")
    st.info("Ajustez les paramètres physiques pour piloter le réacteur en temps réel.")
    
    # Sliders de contrôle
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0, help="Tension appliquée aux bornes du réacteur DBD.")
    freq = st.slider("Fréquence Pulsée (Hz)", 1000, 25000, 15000, help="Fréquence de répétition des impulsions nanosecondes.")
    hum = st.slider("Humidité H2O (%)", 10, 95, 70, help="Taux d'humidité dans le gaz de traitement (précurseur de OH).")
    temp = st.slider("Température des Gaz (°C)", 20, 250, 60, help="Température de la fumée impactant la survie de l'Ozone.")
    
    st.divider()
    
    # Génération du QR Code pour le monitoring mobile
    st.subheader("📱 Monitoring Mobile")
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Lien direct vers l'interface")
    
    if st.button("🛑 ARRÊT D'URGENCE", type="primary", use_container_width=True):
        st.error("SYSTÈME HORS TENSION - SÉCURITÉ ACTIVÉE")

# =================================================================
# 3. MOTEUR DE CALCUL (MODÉLISATION ÉLECTRO-CHIMIQUE)
# =================================================================

# --- PARTIE ÉLECTRIQUE ---
capa_dbd = 150e-12  # Capacité du réacteur (150 pF)
v_breakdown = 12.0  # Tension de seuil de décharge (kV)

# Puissance déposée P = 0.5 * C * V^2 * f
puissance_watt = (0.5 * capa_dbd * (v_peak * 1000)**2) * freq

# Modélisation du Courant de décharge I = f(V)
v_range = np.linspace(0, v_peak, 100)
k_plasma = 0.00065  # Conductance équivalente du plasma
# Loi de puissance pour le courant de décharge au-delà du claquage
i_plasma = np.where(v_range > v_breakdown, k_plasma * (v_range - v_breakdown)**1.55, 1e-7)
i_max_ma = i_plasma[-1] * 1000

# --- PARTIE CHIMIQUE (AVEC DÉGRADATION THERMIQUE) ---
# 1. Production de OH (Favorisée par Humidité et Puissance)
oh_conc = (puissance_watt * (hum/100) * 0.09) / (1 + (temp/1000))

# 2. Production de O3 (Ozone)
o3_initial = (puissance_watt * (1 - hum/100) * 0.045)
# Application de la décomposition thermique de l'O3 (Loi exponentielle)
# L'ozone se dégrade très vite quand la température monte
taux_survie_o3 = np.exp(-temp / 85) 
o3_final = o3_initial * taux_survie_o3

# =================================================================
# 4. AFFICHAGE DES INDICATEURS CLÉS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Production ·OH", f"{oh_conc:.2f} ppm", delta="Stable")
with c2:
    st.metric("Résiduel O3", f"{o3_final:.2f} ppm", delta="Décomposition Thermique" if temp > 80 else None, delta_color="inverse")
with c3:
    st.metric("Puissance Active", f"{puissance_watt:.1f} W")
with c4:
    st.metric("Intensité Crête", f"{i_max_ma:.2f} mA")

st.divider()

# =================================================================
# 5. VISUALISATION GRAPHIQUE
# =================================================================
col_graph_l, col_graph_r = st.columns(2)

# --- GRAPHIQUE I = f(V) ---
with col_graph_l:
    st.subheader("⚡ Caractéristique Électrique")
    
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=v_range, 
        y=i_plasma * 1000, 
        name="Courant de décharge",
        line=dict(color='#FF00FF', width=4),
        fill='tozeroy'
    ))
    fig_iv.update_layout(
        title="Signature Courant-Tension (I-V)",
        xaxis_title="Tension Appliquée (kV)",
        yaxis_title="Intensité (mA)",
        template="plotly_dark"
    )
    st.plotly_chart(fig_iv, use_container_width=True)

# --- GRAPHIQUE DES RADICAUX ---
with col_graph_r:
    st.subheader("📈 Analyse des Espèces Chimiques")
    
    # Simulation d'un historique temporel (60 secondes)
    t_sim = np.linspace(0, 60, 50)
    oh_history = oh_conc + np.random.normal(0, oh_conc*0.03, 50)
    o3_history = o3_final + np.random.normal(0, o3_final*0.03, 50)
    
    fig_chem = go.Figure()
    fig_chem.add_trace(go.Scatter(x=t_sim, y=oh_history, name="Radicaux ·OH", line=dict(color='#00FBFF', width=3)))
    fig_chem.add_trace(go.Scatter(x=t_sim, y=o3_history, name="Ozone O3", line=dict(color='#FFA500', dash='dash')))
    fig_chem.update_layout(
        title="Évolution des Concentrations (ppm)",
        xaxis_title="Temps de traitement (s)",
        yaxis_title="Concentration (ppm)",
        template="plotly_dark"
    )
    st.plotly_chart(fig_chem, use_container_width=True)

# =================================================================
# 6. ARCHIVAGE ET EXPORTATION EXCEL
# =================================================================
st.divider()
st.subheader("📥 Exportation des Données Expérimentales")

# Création du DataFrame pour l'export
df_export = pd.DataFrame({
    "Date_Heure": [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * 50,
    "Tension_kV": [v_peak] * 50,
    "Frequence_Hz": [freq] * 50,
    "Temp_C": [temp] * 50,
    "OH_ppm": oh_history,
    "O3_ppm": o3_history,
    "Puissance_W": [puissance_watt] * 50
})

c_tab, c_btn = st.columns([3, 1])

with c_tab:
    st.write("Aperçu des 5 dernières secondes de mesures :")
    st.dataframe(df_export.tail(5), use_container_width=True)

with c_btn:
    # Génération du fichier Excel
    output_excel = BytesIO()
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Données_Plasma')
    
    st.download_button(
        label="💾 Télécharger Rapport Excel",
        data=output_excel.getvalue(),
        file_name=f"OH_Generator_SBA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.ms-excel",
        use_container_width=True
    )

# --- PIED DE PAGE ---
st.markdown("---")
st.markdown("<div style='text-align: center;'>Projet startup : <b>OH-generator Plasma</b> | Innovation pour la dépollution atmosphérique</div>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center;'>Électrotechnique - UDL-SBA - 2026</div>", unsafe_allow_html=True)
