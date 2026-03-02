import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


from style.ui import cargar_css
cargar_css()


# Configuración de la página
st.set_page_config(page_title="Análisis de Consumo - Peulla", layout="wide")

# 1. Carga de Datos y Validación
@st.cache_data
def load_data():
    file_path = Path("data/data_peulla/data_peulla.xlsx")
    if not file_path.exists():
        st.error(f"No se encontró el archivo en {file_path}")
        return None
    
    try:
        df = pd.read_excel(file_path)
        # Validar columnas requeridas
        required_cols = ['Cantidad Anual', 'Listado Union', 'Tipo', 'Año']
        if not all(col in df.columns for col in required_cols):
            st.error(f"El Excel debe contener las columnas: {required_cols}")
            return None
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

df_raw = load_data()

if df_raw is not None:
    # --- SIDEBAR / FILTROS ---
    st.sidebar.header("Filtros de Exploración")
    
    tipos_selected = st.sidebar.multiselect(
        "Seleccione Tipo de Alimento", 
        options=df_raw['Tipo'].unique(),
        default=df_raw['Tipo'].unique()
    )
    
    productos_selected = st.sidebar.multiselect(
        "Filtrar por Producto (Listado Union)",
        options=df_raw[df_raw['Tipo'].isin(tipos_selected)]['Listado Union'].unique()
    )

    # Aplicar filtros para obtener df_filtrado
    df_filtrado = df_raw[df_raw['Tipo'].isin(tipos_selected)]
    if productos_selected:
        df_filtrado = df_filtrado[df_filtrado['Listado Union'].isin(productos_selected)]

    # --- PROCESAMIENTO PARA MÉTRICAS ---
    years = sorted(df_raw['Año'].unique())
    year_min, year_max = years[0], years[-1]

    # Identificar Productos Nuevos (No existían en el año mínimo)
    productos_anio_min = set(df_raw[df_raw['Año'] == year_min]['Listado Union'])
    df_filtrado['Es Nuevo'] = df_filtrado.apply(
        lambda x: "Sí" if x['Año'] > year_min and x['Listado Union'] not in productos_anio_min else "No", axis=1
    )
    
    nuevos_count = df_filtrado[df_filtrado['Es Nuevo'] == "Sí"]['Listado Union'].nunique()

    # Cálculo de Crecimiento (Comparativa año actual vs anterior)
    pivot_crecimiento = df_filtrado.pivot_table(
        index=['Listado Union', 'Tipo'], columns='Año', values='Cantidad Anual', aggfunc='sum'
    ).fillna(0)
    
    if len(years) > 1:
        pivot_crecimiento['Crecimiento Absoluto'] = pivot_crecimiento[year_max] - pivot_crecimiento[years[-2]]
        top_crecimiento = pivot_crecimiento.sort_values(by='Crecimiento Absoluto', ascending=False).head(5)
    else:
        pivot_crecimiento['Crecimiento Absoluto'] = 0
        top_crecimiento = pivot_crecimiento.head(5)

    # --- DASHBOARD PRINCIPAL ---
    st.title("📊 Reporte Ejecutivo de Consumo Anual")
    st.markdown(f"Análisis del periodo **{year_min} - {year_max}** para la toma de decisiones.")

    # KPI Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Productos Nuevos", nuevos_count)
    with m2:
        total_cons = df_filtrado['Cantidad Anual'].sum()
        st.metric("Consumo Total Acumulado", f"{total_cons:,.0f}")
    with m3:
        if len(years) > 1:
            inc_percent = ((df_filtrado[df_filtrado['Año']==year_max]['Cantidad Anual'].sum() / 
                           df_filtrado[df_filtrado['Año']==year_min]['Cantidad Anual'].sum()) - 1) * 100
            st.metric("Variación Periodo Extremo", f"{inc_percent:.1f}%", delta=f"{inc_percent:.1f}%")

    st.divider()

    # Visualizaciones
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 Tendencia de Consumo por Tipo")
        fig_line = px.line(
            df_filtrado.groupby(['Año', 'Tipo'])['Cantidad Anual'].sum().reset_index(),
            x='Año', y='Cantidad Anual', color='Tipo',
            markers=True, template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col_right:
        st.subheader("🚀 Top 5 Productos con Mayor Aumento")
        fig_bar = px.bar(
            top_crecimiento.reset_index(),
            x='Crecimiento Absoluto', y='Listado Union', color='Tipo',
            orientation='h', title="Incremento vs Año Anterior",
            template="plotly_white",
            color_discrete_sequence=['#2E7D32'] # Verde ejecutivo
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Tablas de Detalle
    st.divider()
    t1, t2 = st.tabs(["🆕 Productos Nuevos Detectados", "⚖️ Comparativa Interanual"])
    
    with t1:
        st.write("Listado de productos que se incorporaron después del año base:")
        df_nuevos = df_filtrado[df_filtrado['Es Nuevo'] == "Sí"][['Año', 'Tipo', 'Listado Union', 'Cantidad Anual']].sort_values(by='Año')
        st.dataframe(df_nuevos, use_container_width=True, hide_index=True)

    with t2:
        st.write(f"Diferencia de consumo entre {year_min} y {year_max}:")
        st.dataframe(pivot_crecimiento[[year_min, year_max, 'Crecimiento Absoluto']].style.background_gradient(subset=['Crecimiento Absoluto'], cmap='Greens'), use_container_width=True)

else:
    st.info("Cargue el archivo Excel en la ruta especificada para comenzar el análisis.")