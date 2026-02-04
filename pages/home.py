import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =============================================================================
# Nota: st.set_page_config se maneja en main.py

# Función para cargar CSS local
def cargar_css():
    try:
        with open("style/style.css", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass # Si no encuentra el estilo, sigue sin él

cargar_css()

# CSS Adicional específico para modificaciones en caliente
st.markdown("""
    <style>
    /* Estilo para el contenedor principal */
    .main {
        background-color: #f8f9fa;
    }
    /* Tarjetas de métricas y contenido */
    .st-emotion-cache-1r6slb0, .css-1r6slb0 { 
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    /* Títulos h1, h2, h3 */
    h1, h2, h3 {
        color: #2c3e50;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Métrica personalizada */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #138AEC;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Botones de enlace */
    .stPageLink {
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 10px;
        transition: all 0.3s;
    }
    .stPageLink:hover {
        border-color: #138AEC;
        background-color: #f0f8ff;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. ENCABEZADO
# =============================================================================
col_logo, col_title, col_user = st.columns([1, 4, 2])

with col_title:
    st.title("Panel de Control de Abastecimiento")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d-%m-%Y')} | **Estado:** Operativo")
st.markdown("---")

# =============================================================================
# 3. RESUMEN EJECUTIVO (KPIs)
# =============================================================================
st.markdown("### 📊 Estado General")

# Datos simulados (Conéctalos a tu `df_pac` o `df_filtrado` real aquí)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Presupuesto PAC 2026", value="$ 1.250 M", delta="3.5% vs 2025")
with col2:
    st.metric(label="Procesos Activos", value="42", delta="-5 Pendientes", delta_color="inverse")
with col3:
    st.metric(label="Ejecución Presupuestaria", value="18.4%", delta="En meta")
with col4:
    st.metric(label="Órdenes de Compra", value="158", delta="+12 esta semana")

st.write("") # Espacio vertical

# =============================================================================
# 4. CUERPO PRINCIPAL
# =============================================================================
col_main, col_side = st.columns([2.5, 1])

# --- COLUMNA IZQUIERDA: GRÁFICOS Y ANÁLISIS ---
with col_main:
    st.subheader("📈 Tendencia de Requerimientos")
    
    # Simulación de datos para gráfico
   

# --- COLUMNA DERECHA: ACCESOS RÁPIDOS Y ALERTAS ---
with col_side:
    # Navegación Rápida
    with st.container(border=True):
        st.markdown("### 🚀 Accesos Rápidos")
        st.write("Navegue a los módulos principales:")
        
        st.page_link("pages/dash_pac.py", label="Planificación PAC 2026", icon="📅")
        st.page_link("pages/dash_ordencompra.py", label="Seguimiento de Órdenes", icon="🛒")
        st.page_link("pages/dash_documentos.py", label="Repositorio Documental", icon="📚")
        
    st.write("")
    
    # Notificaciones
    with st.container(border=True):
        st.markdown("### 🔔 Avisos Recientes")
        st.info("**Cierre de Mes:** Recuerde validar las OC antes del día 30.")
        st.warning("**Mantenimiento:** El sistema estará lento el viernes a las 18:00.")

# =============================================================================
# 5. PIE DE PÁGINA
# =============================================================================
st.markdown("---")
col_footer_l, col_footer_r = st.columns(2)

with col_footer_l:
    st.caption("© 2026 Unidad de Abastecimiento. Todos los derechos reservados.")

with col_footer_r:
    st.caption("Versión 2.1.0 | Última actualización: 30 Ene 2026 | Soporte: soporte@empresa.cl")