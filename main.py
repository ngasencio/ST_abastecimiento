import streamlit as st
import sys
import os

st.set_page_config(
    page_title="Portal DSSO",
    page_icon="resources/logosso.jpg",
    layout="wide"
)

# ===== SIDEBAR COMPLETO =====
with st.sidebar:

    # 1️⃣ IMAGEN PRIMERO
    st.image("resources/logoaba2.png", width=200)

    # 2️⃣ TITULO
    #st.markdown("## 📌 Menú Dashboard")

    #st.markdown("---")

    # 3️⃣ NAVEGACIÓN DENTRO DEL SIDEBAR
    pg = st.navigation([
        st.Page("app.py", title="Inicio", icon="🏠"),
        st.Page("pages/dash_pac.py", title="Plan de Compras", icon="🛒"),
        st.Page("pages/dash_convenios.py", title="Convenios", icon="🤝"),
        st.Page("pages/dash_licitaciones.py", title="Licitaciones", icon="📄"),
        st.Page("pages/dash_ordencompra.py", title="Ordenes de Compra", icon="🧾"),
        st.Page("pages/dash_compradores.py", title="Compradores", icon="👥"),
    ])

# EJECUCIÓN DE PÁGINA
pg.run()