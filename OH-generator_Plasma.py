import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="OH-generator Plasma | UDL-SBA", layout="wide", page_icon="⚡")

# --- TITRE OFFICIEL ---
st.header("Développement d’un Système de Traitement Intelligent des Fumées Industrielles par Réacteur DBD Pulsé")
st.subheader("Optimisation de la Production de Radicaux Hydroxyles (·OH) via une Commande Adaptive à Base d'IA")

st.markdown("---")

# --- SIDEBAR DE CONTRÔLE ---
with st.sidebar:
    st.image("logo.PNG") # Utilise le logo déjà présent sur votre GitHub
    st.title("🎛️ Console de Commande")
    
    v_peak = st.slider("Tension (kV)", 10.0, 35.0, 22.0)
    freq = st.slider("Fréquence Pulsée (Hz)", 1000, 25000, 15000)
    hum = st.slider("Taux d'Humidité H2O (%)", 10, 95, 75)
    
    st.divider()
    if st.button("🚀 Lancer le Réacteur"):
        st.success("Décharge stable - Production de OH en cours")

# --- MOTEUR DE CALCUL IA (CAPTEUR VIRTUEL) ---
# Simulation basée sur l'efficacité énergétique du plasma froid
pwr = (0.5 * 150e-12 * (v_peak*1000)**2) * freq
oh_conc = (pwr * (hum/100) * 0.12) / 10 # Estimation en ppm

# --- AFFICHAGE DES RÉSULTATS ---
col1, col2, col3 = st.columns(3)
col1.metric("Production OH", f"{oh_conc:.2f} ppm")
col2.metric("Puissance Consommée", f"{pwr:.1f} W")
col3.metric("État du Système", "Optimal" if oh_conc > 15 else "Ajustement requis")

# --- GRAPHIQUE DES RADICAUX ---
t = np.linspace(0, 10, 100)
y = oh_conc + np.random.normal(0, 1, 100)
fig = go.Figure(data=go.Scatter(x=t, y=y, line=dict(color='#00fbff', width=3)))
fig.update_layout(title="Concentration de ·OH en temps réel", template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- GÉNÉRATION DU QR CODE ---
st.sidebar.markdown("### 📱 QR Code de l'Installation")
qr = segno.make("https://edt-udl-2026.streamlit.app") # Remplacez par votre URL finale
qr_buf = BytesIO()
qr.save(qr_buf, kind='png', scale=4)
st.sidebar.image(qr_buf.getvalue(), caption="Scan pour monitoring mobile")
