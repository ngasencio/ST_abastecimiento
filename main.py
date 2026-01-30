import streamlit as st
import sys
import os

# Configuración inicial
st.set_page_config(
    page_title="Portal DSSO",
    page_icon="resources/logosso.jpg",
    layout="wide"
)

# ==========================================
# 1. EL LOGO SUPERIOR (ESTO VA PRIMERO)
# ==========================================
# st.logo coloca la imagen automáticamente ENCIMA del menú de navegación.
# No acepta 'width' manual, se ajusta automáticamente al ancho de la barra.
st.logo("resources/logosso2.jpg")

# ==========================================
# 2. DEFINICIÓN DE PÁGINAS
# ==========================================
# Grupo: Sistema Interno
pagina_inicio = st.Page("pages/home.py", title="Inicio", icon="🏠", default=True)
pagina_fsc = st.Page("pages/dash_fsc.py", title="Formularios de Compra", icon="📄", default=True)
pagina_pac = st.Page("pages/dash_pac.py", title="Plan de Compras", icon="🛒")
pagina_convenios = st.Page("pages/dash_convenios.py", title="Convenios", icon="🤝")
pagina_compradores = st.Page("pages/dash_compradores.py", title="Compradores", icon="👥")

# Grupo: Mercado Público
pagina_licitaciones = st.Page("pages/dash_licitaciones.py", title="Licitaciones", icon="📄")
pagina_ordenes = st.Page("pages/dash_ordencompra.py", title="Ordenes de Compra", icon="🧾")


# ==========================================
# 3. CONFIGURACIÓN DE NAVEGACIÓN
# ==========================================
pg = st.navigation(
    {
        "💻 Sistema Interno": [
            pagina_inicio,
            pagina_fsc,
            pagina_pac,
            pagina_convenios,
            pagina_compradores
        ],
       
        "🏛️ Mercado Público": [
            pagina_ordenes,
            pagina_licitaciones
        ],
    }
)

with st.sidebar:
    col_logo, col_text = st.columns([1, 3])
    with col_logo:
        st.image("resources/logoaba2.png", width=60)
    with col_text:
        st.markdown("**Sistema Gestión Abastecimiento**")

# ==========================================
# 4. EJECUCIÓN
# ==========================================
pg.run()