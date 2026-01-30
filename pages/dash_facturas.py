# =============================================================================
# IMPORTS
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from utils.pdf_generador_pac import generar_pdf_pac
from data.data_loader import load_pac26_data

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================
st.set_page_config(layout="wide")


def cargar_css():
    try:
        with open("style/style.css") as f:
            css_content = f.read().replace("\n", "").strip()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")
cargar_css()


from data.data_loader import load_facturas_data  # Importamos tu nueva función

# =============================================================================
# 1. CARGA Y FILTRADO DE DATOS
# =============================================================================
df_facturas = load_facturas_data()

if df_facturas is not None:
    # --- BARRA LATERAL: FILTROS ---
    st.sidebar.header("🔍 Filtros de Facturación")
    
    # Filtro por Fecha de Ingreso
    min_date = df_facturas['fecha_ingreso'].min().date()
    max_date = df_facturas['fecha_ingreso'].max().date()
    
    rango_fecha = st.sidebar.date_input(
        "Rango de Fecha de Ingreso",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filtro por Estado SII
    estados = st.sidebar.multiselect(
        "Estado SII",
        options=df_facturas['estado_sii'].unique(),
        default=df_facturas['estado_sii'].unique()
    )

    # Aplicar Filtros
    mask = (
        (df_facturas['fecha_ingreso'].dt.date >= rango_fecha[0]) & 
        (df_facturas['fecha_ingreso'].dt.date <= rango_fecha[1]) &
        (df_facturas['estado_sii'].isin(estados))
    )
    df_filtrado_fact = df_facturas.loc[mask]

    # =============================================================================
    # 2. SECCIÓN DE KPIs
    # =============================================================================
    st.title("📑 Control de Facturación y Documentos")
    
    monto_total = df_filtrado_fact['monto_total'].sum()
    total_docs = len(df_filtrado_fact)
    pendientes = len(df_filtrado_fact[df_filtrado_fact['estado_acepta'] != 'ACEPTADO'])

    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.metric("Monto Total Filtrado", f"$ {monto_total:,.0f}")
    with kpi2:
        st.metric("Total Documentos", f"{total_docs} uds.")
    with kpi3:
        st.metric("Pendientes de Aceptación", f"{pendientes} uds.", delta_color="inverse")

    st.markdown("---")

    # =============================================================================
    # 3. VISUALIZACIÓN (Gráfico de Tendencia)
    # =============================================================================
    st.subheader("📈 Tendencia de Ingreso de Facturas")
    
    # Agrupamos por fecha para el gráfico
    df_timeline = df_filtrado_fact.groupby(df_filtrado_fact['fecha_ingreso'].dt.date)['monto_total'].sum().reset_index()
    
    fig = px.line(
        df_timeline, 
        x='fecha_ingreso', 
        y='monto_total',
        title="Flujo Financiero por Fecha de Ingreso",
        labels={'fecha_ingreso': 'Fecha', 'monto_total': 'Monto ($)'},
        line_shape="spline",
        render_mode="svg"
    )
    
    fig.update_traces(line_color='#138AEC', fill='tozeroy') # Estilo corporativo
    st.plotly_chart(fig, use_container_width=True)

    # =============================================================================
    # 4. DETALLE TÉCNICO (Tabla)
    # =============================================================================
    with st.expander("📄 Ver listado detallado de facturas"):
        # Mostramos columnas clave para no saturar
        cols_mostrar = ['fecha_ingreso', 'folio_oc', 'tipo_documento', 'monto_total', 'estado_sii', 'uri']
        st.dataframe(df_filtrado_fact[cols_mostrar], use_container_width=True)

else:
    st.error("No se pudieron cargar los datos de facturas. Verifique la carpeta data/Data_Facturas/")