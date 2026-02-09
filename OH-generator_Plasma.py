import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO
from datetime import datetime

# =================================================================
# CONFIGURATION DE LA PLATEFORME OH-GENERATOR PLASMA
# =================================================================
st.set_page_config(
    page_title="OH-generator Plasma | UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# --- TITRE OFFICIEL ---
st.title("⚡ OH-generator Plasma")
st.markdown("### Développement d’un Système de Traitement Intelligent des Fumées Industrielles par Réacteur DBD Pulsé")
st.markdown("#### Optimisation de la Production de Radicaux Hydroxyles (·OH) via une Commande Adaptive à Base d'IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# BARRE LATÉRALE (CONSOLE DE COMMANDE)
# =================================================================
with st.sidebar:
    # Tentative d'affichage du logo (désactivé par défaut pour éviter l'erreur si absent)
    # st.image("logo.PNG") 
    
    st.header("🎮 Console de Commande")
    st.info("Ajustez les paramètres d'entrée du réacteur DBD.")
    
    # Paramètres réglables
    v_peak = st.slider("Tension Crête Appliquée (kV)", 10.0, 35.0, 25.0)
    freq = st.slider("Fréquence de Récurrence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité du Gaz H2O (%)", 10, 95, 70)
    temp = st.slider("Température de la Fumée (°C)", 20, 200, 60)
    
    st.divider()
    
    # Génération du QR Code dynamique pour monitoring mobile
    st.subheader("📱 Monitoring Mobile")
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Scan pour suivi en direct")
    
    if st.button("🛑 ARRÊT D'URGENCE", type="primary"):
        st.error("Système mis hors tension.")

# =================================================================
# MOTEUR DE CALCUL (MODÉLISATION ÉLECTRIQUE ET CHIMIQUE)
# =================================================================

# 1. Calculs Électriques
capa_dbd = 150e-12  # Capacité estimée du réacteur (150 pF)
v_breakdown = 12.0  # Tension de claquage du gaz (kV)

# Calcul de la puissance réelle déposée (P = E_pulse * f)
e_pulse = 0.5 * capa_dbd * (v_peak * 1000)**2
puissance_watt = e_pulse * freq

# Modélisation du Courant de décharge I = f(V)
v_range = np.linspace(0, v_peak, 100)
k_plasma = 0.0006  # Coefficient de conductance du plasma
i_plasma = np.where(v_range > v_breakdown, k_plasma * (v_range - v_breakdown)**1.6, 1e-6)
i_max_ma = i_plasma[-1] * 1000

# 2. Modélisation Chimique (Radicaux OH- et O3)
# Production de OH favorisée par l'humidité et la puissance
oh_conc = (puissance_watt * (hum/100) * 0.085) / (1 + (temp/500))
# Production d'Ozone (favorisée par l'air sec)
o3_conc = (puissance_watt * (1 - hum/100) * 0.04)

# =================================================================
# AFFICHAGE DES INDICATEURS (METRICS)
# =================================================================
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Production ·OH", f"{oh_conc:.2f} ppm", delta="Optimal" if oh_conc > 20 else "Faible")
with m2:
    st.metric("Résiduel O3", f"{o3_conc:.2f} ppm", delta="-Ozone", delta_color="inverse")
with m3:
    st.metric("Puissance Totale", f"{puissance_watt:.1f} W")
with m4:
    st.metric("Courant Crête", f"{i_max_ma:.2f} mA")

st.divider()

# =================================================================
# GRAPHIQUES ET ANALYSES
# =================================================================
col_left, col_right = st.columns(2)

# --- GAUCHE : CARACTÉRISTIQUE ÉLECTRIQUE I(V) ---
with col_left:
    st.subheader("⚡ Caractéristique Électrique I = f(V)")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=v_range, 
        y=i_plasma * 1000, 
        name="Signature Plasma",
        line=dict(color='#FF00FF', width=4)
    ))
    fig_iv.update_layout(
        xaxis_title="Tension (kV)",
        yaxis_title="Intensité de Décharge (mA)",
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig_iv, use_container_width=True)

# --- DROITE : ANALYSE DES RADICAUX ---
with col_right:
    st.subheader("📈 Cinétique des Radicaux")
    time_sim = np.linspace(0, 10, 50)
    # Simulation de fluctuations réelles
    oh_noise = oh_conc + np.random.normal(0, oh_conc*0.05, 50)
    o3_noise = o3_conc + np.random.normal(0, o3_conc*0.05, 50)
    
    fig_chem = go.Figure()
    fig_chem.add_trace(go.Scatter(x=time_sim, y=oh_noise, name="·OH", line=dict(color='#00FBFF', width=3)))
    fig_chem.add_trace(go.Scatter(x=time_sim, y=o3_noise, name="O3", line=dict(color='orange', dash='dash')))
    fig_chem.update_layout(
        xaxis_title="Temps (s)",
        yaxis_title="Concentration (ppm)",
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig_chem, use_container_width=True)

# =================================================================
# EXPORTATION DES DONNÉES (ARCHIVE STARTUP)
# =================================================================
st.divider()
st.subheader("📥 Exportation des Résultats Expérimentaux")

exp_data = pd.DataFrame({
    "Horodatage": [datetime.now().strftime('%H:%M:%S')] * 50,
    "Tension (kV)": [v_peak] * 50,
    "Fréquence (Hz)": [freq] * 50,
    "Production OH (ppm)": oh_noise,
    "Production O3 (ppm)": o3_noise,
    "Intensité (mA)": [i_max_ma] * 50
})

c_table, c_download = st.columns([3, 1])
with c_table:
    st.dataframe(exp_data.head(5), use_container_width=True)

with c_download:
    # Création du fichier Excel en mémoire
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        exp_data.to_excel(writer, index=False, sheet_name='Mesures_Plasma')
    
    st.download_button(
        label="📥 Télécharger Rapport .xlsx",
        data=output.getvalue(),
        file_name=f"OH_Generator_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.ms-excel",
        help="Cliquez pour enregistrer les mesures dans un fichier Excel compatible avec vos rapports UDL-SBA."
    )

# --- PIED DE PAGE ---
st.markdown("---")
st.center = st.write("© 2026 OH-generator Plasma - Innovation IA & Génie Électrique")
