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
pagina_fsc = st.Page("pages/dash_fsc.py", title="Formularios de Compra", icon="📄" )
pagina_convenios = st.Page("pages/dash_convenios.py", title=" Cartera de Convenios", icon="📂")
pagina_compradores = st.Page("pages/dash_compradores.py", title="Compradores", icon="👥")

# Grupo: Mercado Público
pagina_licitaciones = st.Page("pages/dash_licitaciones.py", title="Licitaciones", icon="📄")
pagina_pac = st.Page("pages/dash_pac.py", title="Planificación PAC", icon="🛒")
pagina_plan_pac = st.Page("pages/dash_plan_pac.py", title="Planificación PAC", icon="🛒")
pagina_pac_vs_oc = st.Page("pages/dash_pac_vs_oc.py", title="PAC vs OC", icon="🛒")
pagina_ordenes = st.Page("pages/dash_ordencompra.py", title="Ordenes de Compra", icon="🧾")
pagina_compraagil = st.Page("pages/dash_compraagil.py", title="Compra Ágil", icon="⚡")

#Grupo Facturas
pagina_facturas = st.Page("pages/dash_facturas.py", title="Facturas", icon="📥")

#Grupo: Documentos
pagina_documentos = st.Page("pages/dash_documentos.py", title="Documentos", icon="📋")

#Grupo: Generador de Facturas
pagina_generador_facturas = st.Page("pages/streamlitFacturaPDF/streamlitFacturaPDF.py", title="Generador de Facturas", icon="📋"    )

# ==========================================
# 3. CONFIGURACIÓN DE NAVEGACIÓN
# ==========================================
pg = st.navigation(
    {
        "💻 Sistema Interno": [
            pagina_inicio,
            pagina_fsc,
            pagina_convenios,
            pagina_compradores,
            pagina_plan_pac
        ],
       
        "🏛️ Mercado Público": [
            pagina_pac,
            pagina_pac_vs_oc,
            pagina_ordenes,
            pagina_licitaciones,
            pagina_compraagil
        ],
        "📥Facturas":[
            pagina_facturas],

        "📚 Biblioteca Normativa": [
            pagina_documentos
        ],
        "📚 Generador de Facturas": [
            pagina_generador_facturas
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