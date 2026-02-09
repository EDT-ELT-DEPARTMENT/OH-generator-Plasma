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
st.title("⚡ Start-up-OH Generator Plasma")
st.markdown("### OH-generator Plasma - Système Intelligent de Traitement des Fumées")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. BARRE LATÉRALE (SIDEBAR)
# =================================================================
with st.sidebar:
    st.header("🎮 Configuration du Système")
    
    # Sélecteur de nombre de réacteurs
    nb_reacteurs = st.number_input(
        "Nombre de réacteurs (en parallèle)", 
        min_value=1, 
        max_value=20, 
        value=2
    )
    st.caption(f"Configuration actuelle : {nb_reacteurs} réacteurs DBD coaxiaux")
    
    st.divider()
    
    st.header("⚙️ Paramètres Opérationnels")
    # Sliders de commande
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 70)
    temp = st.slider("Température des Fumées (°C)", 20, 250, 60)
    
    st.divider()
    
    # Section Monitoring QR Code
    st.subheader("📱 Monitoring Mobile")
    url_app = "https://oh-generator-plasma.streamlit.app"
    qr = segno.make(url_app)
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Accès distant")
    
    # Sécurité
    if st.button("🛑 ARRÊT D'URGENCE", type="primary", use_container_width=True):
        st.error("HAUTE TENSION COUPÉE - SYSTÈME SÉCURISÉ")

# =================================================================
# 3. BASES PHYSICO-CHIMIQUES (ÉQUATIONS)
# =================================================================
with st.expander("📚 Bases Physico-Chimiques et Équations du Modèle"):
    st.markdown("### 1. Modélisation Électrique Multi-Réacteur")
    st.write("La puissance totale est proportionnelle au nombre de réacteurs $n$ en parallèle :")
    st.latex(r"P_{active} = n \cdot \left( \frac{1}{2} C_{unit} V_{peak}^2 f \right)")
    st.latex(r"I_{total} = n \cdot k \cdot (V - V_{th})^{1.55}")
    
    st.markdown("### 2. Génération de Radicaux Hydroxyles (·OH)")
    st.write("La production dépend de l'énergie des électrons et de la densité de vapeur d'eau :")
    st.latex(r"e^- + H_2O \rightarrow e^- + \cdot OH + H\cdot")
    st.latex(r"[\cdot OH]_{ppm} = \frac{P_{active} \cdot \text{Humidité} \cdot \alpha}{1 + \frac{T}{1000}}")
    
    st.markdown("### 3. Cinétique et Dégradation de l'Ozone (O3)")
    st.write("L'ozone est instable thermiquement. Son taux de survie suit une loi d'Arrhenius simplifiée :")
    st.latex(r"[O_3]_{final} = [O_3]_{initial} \cdot e^{-\frac{T}{\beta}}")
    st.info("Où β (bêta) est la constante de stabilité thermique (≈ 85°C pour ce réacteur).")

# =================================================================
# 4. MOTEUR DE CALCUL (LOGIQUE IA)
# =================================================================
# Paramètres fixes du design
C_UNIT = 150e-12 
V_TH = 12.0
ALPHA = 0.09  
BETA = 85     

# Calcul de la puissance (multipliée par le nombre de réacteurs)
puissance_active = (0.5 * (C_UNIT * nb_reacteurs) * (v_peak * 1000)**2) * freq

# Calcul de l'intensité (multipliée par le nombre de réacteurs)
v_range = np.linspace(0, v_peak, 100)
i_plasma_unit = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_peak_ma = (i_plasma_unit[-1] * 1000) * nb_reacteurs

# Calcul chimique
oh_ppm = (puissance_active * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_base = (puissance_active * (1 - hum/100) * 0.045)
o3_ppm = o3_base * np.exp(-temp / BETA)

# =================================================================
# 5. AFFICHAGE DES INDICATEURS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_ppm:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_ppm:.2f} ppm")
c3.metric("Puissance Active", f"{puissance_active:.1f} W")
c4.metric("Courant Crête", f"{i_peak_ma:.2f} mA")

st.divider()

# =================================================================
# 6. GRAPHIQUES (VISUALISATION)
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique Électrique I(V)")
    
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=v_range, 
        y=i_plasma_unit * 1000 * nb_reacteurs, 
        name="Courant Total", 
        fill='tozeroy', 
        line=dict(color='#FF00FF', width=4)
    ))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Intensité Totale (mA)", template="plotly_dark")
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("📈 Concentrations des Espèces")
    
    t_sim = np.linspace(0, 60, 50)
    oh_noise = oh_ppm + np.random.normal(0, oh_ppm*0.02, 50)
    o3_noise = o3_ppm + np.random.normal(0, o3_ppm*0.02, 50)
    
    fig_chem = go.Figure()
    fig_chem.add_trace(go.Scatter(x=t_sim, y=oh_noise, name="·OH", line=dict(color='#00FBFF', width=3)))
    fig_chem.add_trace(go.Scatter(x=t_sim, y=o3_noise, name="O3", line=dict(color='orange', dash='dash')))
    fig_chem.update_layout(xaxis_title="Temps (s)", yaxis_title="Concentration (ppm)", template="plotly_dark")
    st.plotly_chart(fig_chem, use_container_width=True)

# =================================================================
# 7. FICHE TECHNIQUE ET SÉCURITÉ
# =================================================================
st.divider()
f1, f2 = st.columns(2)

with f1:
    st.subheader("📝 Fiche Technique du Réacteur")
    st.markdown(f"""
    **SPÉCIFICATIONS MÉCANIQUES**
    - **Type :** DBD Coaxial (Cylindrique)
    - **Longueur active :** 200 mm
    - **Électrode centrale :** Ø 10 mm (Inox 316L)
    - **Diélectrique :** Quartz (Ø ext 24 mm, épaisseur 2 mm)
    - **Gap de décharge :** 5 mm
    
    **PERFORMANCES CIBLES**
    - **Capacité Unitaire :** {C_UNIT*1e12} pF
    - **Taux OH optimal :** 20 - 35 ppm
    """)

with f2:
    st.subheader("⚠️ Notice de Sécurité (UDL-SBA)")
    st.warning("**HAUTE TENSION :** Risque d'électrocution. Ne pas manipuler sans mise à la terre.")
    st.warning("**OZONE :** Gaz toxique. Utilisation obligatoire sous hotte aspirante.")
    st.warning("**RAYONNEMENT UV :** Ne pas regarder la décharge sans lunettes de protection.")
    st.warning("**TEMPÉRATURE :** Risque de brûlure sur le tube de quartz (P > 200W).")

# =================================================================
# 8. PIED DE PAGE
# =================================================================
st.divider()
st.markdown("<center>© 2026 OH-generator Plasma - Électrotechnique UDL-SBA</center>", unsafe_allow_html=True)
