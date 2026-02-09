import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="OH-generator Plasma", layout="wide", page_icon="⚡")

# --- TITRE ---
st.title("⚡ OH-generator Plasma")
st.markdown("### Système Intelligent de Traitement des Fumées Industrielles")
st.caption(f"Plateforme de gestion - Département d'Électrotechnique - SBA - {datetime.now().strftime('%d/%m/%Y')}")

# --- SIDEBAR ---
with st.sidebar:
    # st.image("logo.PNG") # Décommentez si le fichier est présent
    st.header("🎮 Paramètres d'Entrée")
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 10000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 65)
    
    st.divider()
    # Génération QR Code
    qr = segno.make("https://oh-generator-plasma.streamlit.app")
    buf = BytesIO()
    qr.save(buf, kind='png', scale=4)
    st.image(buf.getvalue(), caption="Scan pour monitoring mobile")

# --- CALCULS IA (MODÈLE PHYSIQUE) ---
# Puissance P = E_pulse * f | E_pulse = 0.5 * C * V^2
capa_dbd = 150e-12 
pwr = (0.5 * capa_dbd * (v_peak*1000)**2) * freq
# Modèle de production OH- (Production favorisée par V et Humidité)
oh_base = (pwr * (hum/100) * 0.08)
o3_base = (pwr * (1 - hum/100) * 0.05)

# --- AFFICHAGE METRICS ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_base:.2f} ppm")
c2.metric("Ozone O3", f"{o3_base:.2f} ppm")
c3.metric("Puissance", f"{pwr:.1f} W")
status = "OPTIMAL" if oh_base > 15 else "AJUSTEMENT REQUIS"
c4.metric("Statut IA", status, delta=None, delta_color="normal")

# --- GRAPHIQUES DYNAMIQUES ---
st.divider()
col_graph, col_data = st.columns([2, 1])

# Création de données temporelles simulées
time_axis = np.linspace(0, 60, 50)
oh_curve = oh_base + np.random.normal(0, oh_base*0.03, 50)
o3_curve = o3_base + np.random.normal(0, o3_base*0.03, 50)

with col_graph:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_axis, y=oh_curve, name="Radicaux ·OH", line=dict(color='#00fbff', width=3)))
    fig.add_trace(go.Scatter(x=time_axis, y=o3_curve, name="Ozone O3", line=dict(color='orange', dash='dash')))
    fig.update_layout(title="Analyse Temporelle de la Décharge", xaxis_title="Temps (s)", yaxis_title="Concentration (ppm)", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# --- EXPORT EXCEL ---
with col_data:
    st.write("### 📥 Archive de l'Essai")
    df = pd.DataFrame({
        "Temps (s)": time_axis,
        "OH (ppm)": oh_curve,
        "O3 (ppm)": o3_curve,
        "Puissance (W)": [pwr]*50
    })
    
    st.dataframe(df.head(10), height=300)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data_Plasma')
    
    st.download_button(
        label="Télécharger Rapport Excel",
        data=output.getvalue(),
        file_name=f"Rapport_Plasma_{datetime.now().strftime('%H%M%S')}.xlsx",
        mime="application/vnd.ms-excel"
    )
