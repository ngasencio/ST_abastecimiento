# main.py

import streamlit as st
import sys
import os
# Asegura la accesibilidad de data_loader.py
sys.path.append(os.path.abspath(os.path.dirname(__file__))) 

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
    page_icon="logosso.jpg",
    layout="wide"
)

# Separador
st.sidebar.markdown("---")

# 3️⃣ MENU DE PÁGINAS

# 3.1️⃣ GRUPO 1: REPORTES OPERATIVOS Y GENERALES
menu_operativo = [
    st.Page("app.py", title="Inicio / Dashboard Principal", icon="🏠"),
    st.Page("pages/dash_general.py", title="Reporte General", icon="📊"),
    st.Page("pages/dash_ventas.py", title="Análisis de Ventas", icon="💰"),
    st.Page("pages/dash_pac.py", title="Plan de Compras", icon="🛒"),
]

# 3.2️⃣ SEPARADOR Y TÍTULO DE SECCIÓN: COMPRADORES
st.sidebar.markdown("---") # Separador visual extra
st.sidebar.markdown("### 👥 Reportes por Comprador") # El encabezado que querías

# 3.3️⃣ GRUPO 2: REPORTES DE COMPRADORES
menu_compradores = [
    # Esta es tu página actual de compradores:
    st.Page("pages/dash_compradores.py", title="Desempeño General", icon="👥"), 
    
    # Aquí puedes añadir tus futuras páginas:
    st.Page("pages/dash_compradores_general.py", title="Desglose por OC", icon="👤"),
    # st.Page("pages/dash_compradores_individual.py", title="Análisis por Tiempos", icon="⏱️"),
]

# 3.4️⃣ COMBINACIÓN DE PAGINAS Y EJECUCIÓN
# Concatenamos las listas para que st.navigation las ejecute todas
pg = st.navigation(menu_operativo + menu_compradores)

pg.run()

# 4️⃣ LOGO ABASTECIMIENTO PEGADO ABAJO
st.sidebar.markdown('<div class="footer-img">', unsafe_allow_html=True)
st.sidebar.image(
    "logoaba.png",
    caption="Departamento de Abastecimiento y Operaciones",
    width=200
)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

##### KPIS ####
st.markdown("## 📈 KPIs Principales")
col1, col2, col3, col4 = st.columns(4)
with col1:
    montos_estimados = df_filtrado["monto estimado"].sum()
    st.metric("💰 Montos Estimados", 
            f"${montos_estimados:,.0f}",
            f"{np.random.uniform(5, 15):.1f}%")
    
with col2:
    Total_FSC = df_filtrado["newiD"].count()
    st.metric("📋 Total FSC", 
            f"{Total_FSC:,.0f}",
            f"{np.random.uniform(2, 8):.1f}%")

with col3:
    conversion_prom = df_filtrado["monto estimado"].mean()
    st.metric("🎯 Tasa de Conversión", 
            f"{conversion_prom:.2f}%",
            f"{np.random.uniform(0.5, 2):.1f}%")
    
with col4:
    cac_prom = df_fsc["monto estimado"].mean()
    st.metric("💸Costo de Adquisición", 
            f"${cac_prom:.2f}",
            f"-{np.random.uniform(1, 5):.1f}%")
st.subheader("Datos de Muestra")
st.dataframe(df_general, use_container_width=True)