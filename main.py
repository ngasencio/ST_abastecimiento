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
st.logo("resources/logosso2.jpg")
# ==========================================
# 2. DEFINICIÓN DE PÁGINAS
# ==========================================
# Grupo: Sistema Interno
pagina_inicio = st.Page("pages/home.py", title="Inicio", icon="🏠", default=True)
pagina_fsc = st.Page("pages/dash_fsc.py", title="Formularios de Compra", icon="📄" )
pagina_convenios = st.Page("pages/dash_convenios.py", title=" Cartera de Convenios", icon="📂")
pagina_compradores = st.Page("pages/dash_compradores.py", title="Compradores", icon="👥")
pagina_plan_pac = st.Page("pages/dash_plan_pac.py", title="Planificación PAC", icon="🛒")

# Grupo: Mercado Público
pagina_ejecucionpac = st.Page("pages/dash_ejecucionpac.py", title="Ejecución PAC", icon="🛒")
pagina_ejecucionpac2 = st.Page("pages/dash_ejecucionpac2.py", title="Ejecución PAC2", icon="🛒")
pagina_ordenes = st.Page("pages/dash_ordencompra.py", title="Ordenes de Compra", icon="🧾")
pagina_compraagil = st.Page("pages/dash_compraagil.py", title="Compra Ágil", icon="⚡")
pagina_licitaciones = st.Page("pages/dash_licitaciones.py", title="Licitaciones", icon="📄")
pagina_activofijo = st.Page("pages/dash_activofijo.py", title="Activos Fijos", icon="🏢")

#Grupo: Documentos
pagina_documentos = st.Page("pages/dash_documentos.py", title="Documentos", icon="📋")

#Grupo: Herramientas
pagina_api_sso = st.Page("pages/dash_extractor_sso_oc.py", title="API OC SSO", icon="🔗")
pagina_api_licitaciones = st.Page("pages/dash_extractor_sso_licitaciones.py", title="API LI SSO", icon="🔗")
pagina_buscadorOC = st.Page("pages/tools_buscadorOC.py", title="Buscador OC", icon="🔍")
#pagina_okr = st.Page("pages/page_okr.py", title="OKR", icon="🎯")
#pagina_okr2 = st.Page("pages/page_okr2.py", title="OKR2", icon="🎯")
#pagina_okr3 = st.Page("pages/page_okr3.py", title="OKR3", icon="🎯")
#pagina_correos = st.Page("pages/page_correos.py", title="Correos", icon="📧")
#pagina_data_panel = st.Page("pages/page_data_panel.py", title="Data Panel", icon="📊")


#Grupo: Finanzas
pagina_anexo1 = st.Page("pages/dash_anexo1.py", title="Anexo N°1", icon="🧮")
pagina_anexo2 = st.Page("pages/dash_anexo2.py", title="Anexo N°2 (DEBUG)", icon="🧮")
pagina_anexo3 = st.Page("pages/dash_anexo3.py", title="Anexo N°3", icon="🧮")
pagina_anexo4 = st.Page("pages/dash_anexo4.py", title="Anexo N°4", icon="🧮")


#Grupo Nuevo
pagina_peulla = st.Page("pages/dash_Peulla.py", title="Peulla", icon="🧮")


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
            pagina_ejecucionpac,
            pagina_ejecucionpac2,
            pagina_ordenes,
            pagina_licitaciones,    
            pagina_compraagil,
            pagina_activofijo
        ],
        "🛠 Herramientas SSO": [
            pagina_api_sso,
            pagina_api_licitaciones,
            pagina_buscadorOC,
            #pagina_okr,
            #pagina_okr2,
            #pagina_okr3,
            #pagina_correos,
            #pagina_data_panel
        ],
        "📚 Biblioteca Normativa": [
            pagina_documentos
        ],
        "🧮 Finanzas": [
            pagina_anexo1,
            pagina_anexo2,
            pagina_anexo3,
            pagina_anexo4,
        ],
        "🧮 Peulla": [
            pagina_peulla,
        ]
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