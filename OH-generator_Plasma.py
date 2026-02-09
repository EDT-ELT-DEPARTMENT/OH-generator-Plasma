import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import segno
from io import BytesIO
from datetime import datetime

# =================================================================
# 1. CONFIGURATION ET STYLE
# =================================================================
st.set_page_config(
    page_title="OH-generator Plasma | UDL-SBA",
    layout="wide",
    page_icon="⚡"
)

# --- TITRE OFFICIEL ET RAPPEL ---
# Plateforme de commande de génération d'hydroxcile par plasma froid-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA
st.title("⚡ Start-up-OH Generator Plasma")
st.subheader("Module : OH-generator Plasma - Système Intelligent de Traitement des Fumées")
st.markdown("#### Optimisation de la Production de Radicaux (·OH) par Commande Adaptive IA")
st.caption(f"Département d'Électrotechnique - Faculté de Génie Électrique - UDL-SBA | Date : {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# =================================================================
# 2. CONSOLE DE COMMANDE (SIDEBAR)
# =================================================================
with st.sidebar:
    try:
        st.image("logo.PNG")
    except:
        st.info("Logo UDL-SBA")
    
    st.header("🎮 Paramètres du Réacteur")
    v_peak = st.slider("Tension Crête (kV)", 10.0, 35.0, 25.0)
    freq = st.slider("Fréquence (Hz)", 1000, 25000, 15000)
    hum = st.slider("Humidité H2O (%)", 10, 95, 70)
    temp = st.slider("Température des Fumées (°C)", 20, 250, 60)
    
    st.divider()
    
    st.subheader("📱 Monitoring Mobile")
    qr = segno.make("https://oh-generator-plasma.streamlit.app")
    qr_buf = BytesIO()
    qr.save(qr_buf, kind='png', scale=4)
    st.image(qr_buf.getvalue(), caption="Accès distant")
    
    if st.button("🛑 ARRÊT D'URGENCE", type="primary", use_container_width=True):
        st.error("HAUTE TENSION COUPÉE")

# =================================================================
# 3. FONDEMENTS THÉORIQUES (LES ÉQUATIONS)
# =================================================================
with st.expander("📚 Bases Physico-Chimiques et Équations du Modèle"):
    st.markdown("### 1. Modélisation Électrique")
    st.latex(r"P_{abs} = E_{pulse} \cdot f = \left( \frac{1}{2} C_{cell} V_{peak}^2 \right) \cdot f")
    st.latex(r"I_{plasma} = k \cdot (V - V_{th})^{1.55} \text{ pour } V > V_{th}")
    
    st.markdown("### 2. Génération des Radicaux Hydroxyles (·OH)")
    st.write("Le plasma dissocie la vapeur d'eau par impact électronique :")
    st.latex(r"e^- + H_2O \rightarrow e^- + \cdot OH + H\cdot")
    st.latex(r"[\cdot OH]_{ppm} = \frac{P_{abs} \cdot \text{Humidité} \cdot \alpha}{1 + \frac{T}{1000}}")
    
    st.markdown("### 3. Cinétique de l'Ozone (O3) et Effet Thermique")
    st.write("L'ozone est produit par l'oxygène de l'air mais se dégrade avec la chaleur :")
    st.latex(r"e^- + O_2 \rightarrow e^- + O + O \xrightarrow{O_2} O_3")
    st.latex(r"[O_3]_{final} = [O_3]_{initial} \cdot e^{-\frac{T}{\beta}}")
    st.info("Note : Beta (β) représente la constante de décomposition thermique de l'Ozone.")

# =================================================================
# 4. MOTEUR DE CALCUL IA
# =================================================================
# Constantes physiques du réacteur
C_CELL = 150e-12 
V_TH = 12.0
ALPHA = 0.09  # Coeff de rendement OH
BETA = 85     # Coeff de dégradation O3 (Température)

# Puissance
pwr = (0.5 * C_CELL * (v_peak * 1000)**2) * freq

# Courant I = f(V)
v_range = np.linspace(0, v_peak, 100)
i_plasma = np.where(v_range > V_TH, 0.00065 * (v_range - V_TH)**1.55, 1e-7)
i_max = i_plasma[-1] * 1000

# Chimie
oh_val = (pwr * (hum/100) * ALPHA) / (1 + (temp/1000))
o3_initial = (pwr * (1 - hum/100) * 0.045)
o3_val = o3_initial * np.exp(-temp / BETA)

# =================================================================
# 5. AFFICHAGE DES RÉSULTATS (METRICS)
# =================================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Production ·OH", f"{oh_val:.2f} ppm")
c2.metric("Résiduel O3", f"{o3_val:.2f} ppm", delta="Décomposition ON" if temp > 70 else None)
c3.metric("Puissance Active", f"{pwr:.1f} W")
c4.metric("Courant Crête", f"{i_max:.2f} mA")

st.divider()

# =================================================================
# 6. VISUALISATION (GRAPHIQUES)
# =================================================================
g1, g2 = st.columns(2)

with g1:
    st.subheader("⚡ Caractéristique Électrique I(V)")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=v_range, y=i_plasma*1000, name="Courant", fill='tozeroy', line=dict(color='#FF00FF')))
    fig_iv.update_layout(xaxis_title="Tension (kV)", yaxis_title="Intensité (mA)", template="plotly_dark")
    st.plotly_chart(fig_iv, use_container_width=True)

with g2:
    st.subheader("📈 Concentrations des Espèces")
    t_sim = np.linspace(0, 60, 50)
    oh_hist = oh_val + np.random.normal(0, oh_val*0.02, 50)
    o3_hist = o3_val + np.random.normal(0, o3_val*0.02, 50)
    fig_chem = go.Figure()
    fig_chem.add_trace(go.Scatter(x=t_sim, y=oh_hist, name="·OH", line=dict(color='#00FBFF')))
    fig_chem.add_trace(go.Scatter(x=t_sim, y=o3_hist, name="O3", line=dict(color='orange')))
    fig_chem.update_layout(xaxis_title="Temps (s)", yaxis_title="Concentration (ppm)", template="plotly_dark")
    st.plotly_chart(fig_chem, use_container_width=True)

# =================================================================
# 7. BROCHURE TECHNIQUE ET SÉCURITÉ
# =================================================================
st.divider()
col_b1, col_b2 = st.columns(2)

with col_b1:
    st.subheader("📝 Fiche Technique du Réacteur")
    brochure = f"""
    ### SPÉCIFICATIONS MÉCANIQUES
    - **Type :** DBD Coaxial (Cylindrique)
    - **Longueur active :** 200 mm
    - **Électrode centrale :** Ø 10 mm (Inox 316L)
    - **Diélectrique :** Quartz (Ø ext 24 mm, épaisseur 2 mm)
    - **Gap de décharge :** 5 mm
    
    ### PERFORMANCES CIBLES
    - **Capacité :** {C_CELL*1e12} pF
    - **Taux OH optimal :** 20 - 35 ppm
    """
    st.markdown(brochure)
    st.download_button("📥 Télécharger Fiche Technique", brochure, "Brochure_Plasma.txt")

with col_b2:
    st.subheader("⚠️ Notice de Sécurité (UDL-SBA)")
    st.warning("""
    1. **HAUTE TENSION :** Risque d'électrocution. Ne pas manipuler sans mise à la terre.
    2. **OZONE :** Gaz toxique. Utilisation obligatoire sous hotte aspirante.
    3. **RAYONNEMENT UV :** Ne pas regarder la décharge sans lunettes de protection.
    4. **TEMPÉRATURE :** Risque de brûlure sur le tube de quartz (P > 200W).
    """)

# =================================================================
# 8. EXPORT DE DONNÉES
# =================================================================
st.divider()
df_exp = pd.DataFrame({"Temps": t_sim, "OH_ppm": oh_hist, "O3_ppm": o3_hist})
st.download_button("💾 Exporter les mesures (Excel)", df_exp.to_csv(), "donnees_plasma.csv", "text/csv", use_container_width=True)

st.markdown("---")
st.center = st.write("© 2026 OH-generator Plasma - Électrotechnique UDL-SBA")

