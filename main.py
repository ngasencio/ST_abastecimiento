# main.py

import streamlit as st

# 1️⃣ LOGO SSO ARRIBA Y CENTRADO
#st.sidebar.markdown('<div class="center-img">', unsafe_allow_html=True)
#st.sidebar.image("logosso.jpg", width=220)
#st.sidebar.markdown('</div>', unsafe_allow_html=True)

# 2️⃣ TEXTO INTRODUCTORIO
st.sidebar.markdown("""
**Este informe presenta una visión ejecutiva del desempeño operacional y financiero,
considerando los principales indicadores de la organización.**
""")

# 1. Configuración de la aplicación
st.set_page_config(
    page_title="Portal de Dashboards DSSO",
    page_icon=":rocket:",
    layout="wide"
)

# Separador
st.sidebar.markdown("---")

# 3️⃣ MENU DE PÁGINAS
pg = st.navigation([
    st.Page("app.py", title="Inicio / Dashboard Principal", icon="🏠"),
    st.Page("pages/dash_general.py", title="Reporte General", icon="📊"),
    st.Page("pages/dash_ventas.py", title="Análisis de Ventas", icon="💰"),
    st.Page("pages/dash_compras.py", title="Gestión de Compras", icon="🛒"),
])

pg.run()

# 4️⃣ LOGO ABASTECIMIENTO PEGADO ABAJO
st.sidebar.markdown('<div class="footer-img">', unsafe_allow_html=True)
st.sidebar.image(
    "logoaba.png",
    caption="Departamento de Abastecimiento y Operaciones",
    width=200
)
st.sidebar.markdown('</div>', unsafe_allow_html=True)
