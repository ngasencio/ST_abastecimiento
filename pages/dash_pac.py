# pages/dash_compras.py

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

# =============================================================================
# CARGA DE DATOS
# =============================================================================
df_pac = load_pac26_data()



# =============================================================================
# HEADER
# =============================================================================
st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #138AEC, #3E9FEF);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            🛒 Planificación 2026
        </div>
        <div style="font-size: 15px; opacity: 0.9;">
            Módulo de seguimiento del Plan Anual de Compras 2026.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =============================================================================
# NORMALIZACIÓN DE DATOS
# =============================================================================
cols_texto = [
    "Subdirección",
    "Departamento_SHORT",
    "Nombre responsable",
    "ID Proyecto"
]

for col in cols_texto:
    df_pac[col] = df_pac[col].astype(str).str.strip()

df_pac["Fecha de Inicio Compra"] = pd.to_datetime(
    df_pac["Fecha de Inicio Compra"], errors="coerce"
)

df_pac["Año"] = df_pac["Fecha de Inicio Compra"].dt.year
df_pac["Mes"] = df_pac["Fecha de Inicio Compra"].dt.month
# Esto genera el nombre en inglés (January, February...)
df_pac["Mes_nombre"] = df_pac["Fecha de Inicio Compra"].dt.strftime("%B") 

# --- 🔄 TRADUCCIÓN DE MESES (NUEVO) ---
# Mapeamos manualmente para asegurar español sin depender de la configuración del servidor
meses_es = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}
df_pac["Mes_nombre"] = df_pac["Mes_nombre"].replace(meses_es)

# =============================================================================
# FILTROS (6 COLUMNAS)
# =============================================================================
col1, col2, col3, col4, col5, col6 = st.columns(6)

df_cascada = df_pac.copy()

# --- Filtro 1: Subdirección ---
with col1:
    subdireccion_sel = st.multiselect("🏢 Subdirección", sorted(df_cascada["Subdirección"].dropna().unique()), placeholder="Seleccione")

if subdireccion_sel:
    df_cascada = df_cascada[df_cascada["Subdirección"].isin(subdireccion_sel)]

# --- Filtro 2: Departamento ---
with col2:
    depto_sel = st.multiselect("📊 Depto.", sorted(df_cascada["Departamento_SHORT"].dropna().unique()), placeholder="Seleccione")

if depto_sel:
    df_cascada = df_cascada[df_cascada["Departamento_SHORT"].isin(depto_sel)]

# --- Filtro 3: Responsable ---
with col3:
    responsable_sel = st.multiselect("👤 Resp.", sorted(df_cascada["Nombre responsable"].dropna().unique()), placeholder="Seleccione")

if responsable_sel:
    df_cascada = df_cascada[df_cascada["Nombre responsable"].isin(responsable_sel)]

# --- Filtro 4: ID Proyecto ---
with col4:
    proyecto_sel = st.multiselect("🆔 ID Proy.", sorted(df_cascada["ID Proyecto"].dropna().unique()), placeholder="Seleccione")

if proyecto_sel:
    df_cascada = df_cascada[df_cascada["ID Proyecto"].isin(proyecto_sel)]

# --- Filtro 5: Año ---
with col5:
    anio_sel = st.multiselect("📅 Año", sorted(df_cascada["Año"].dropna().unique()), placeholder="Seleccione")

if anio_sel:
    df_cascada = df_cascada[df_cascada["Año"].isin(anio_sel)]

# --- Filtro 6: Mes (Ahora detectará correctamente el Español) ---
with col6:
    # Lista fija para forzar el orden cronológico
    orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    # Obtenemos los meses que realmente existen en los datos filtrados
    meses_disponibles = df_cascada["Mes_nombre"].dropna().unique()
    
    # Intersección: Solo mostramos los meses disponibles pero en el orden correcto
    meses_opciones = [m for m in orden_meses if m in meses_disponibles]

    mes_sel = st.multiselect(
        "🗓️ Mes",
        meses_opciones,
        placeholder="Seleccione"
    )

if mes_sel:
    df_cascada = df_cascada[df_cascada["Mes_nombre"].isin(mes_sel)]

# --- Resultado Final ---
df_filtrado = df_cascada.copy()
# =============================================================================
# DASHBOARD: KPIs + GRÁFICO (2 Columnas)
# =============================================================================
st.markdown("## 📈 Dashboard General PAC26")

# Definimos proporciones: [1, 3] significa que la col_grafico es 3 veces más ancha
col_kpis, col_grafico = st.columns([1, 3])

# --- COLUMNA 1: MÉTRICAS APILADAS ---
with col_kpis:
    # --- Métrica 1: Cantidad de Proyectos ---
    total_proyectos_general = df_pac["ID Proyecto"].nunique()
    total_proyectos_filtrado = df_filtrado["ID Proyecto"].nunique()

    # Cálculo seguro del porcentaje
    porc_proyectos = (total_proyectos_filtrado / total_proyectos_general * 100) if total_proyectos_general > 0 else 0

    st.metric(
        "🗂️ Cantidad de Proyectos",
        total_proyectos_filtrado,
        f"{porc_proyectos:.1f}% del total"
    )
    
    # Espaciador o línea divisoria para separar visualmente la métrica de arriba con la de abajo
    #st.markdown("---") 
    
    # --- Métrica 2: Montos ---
    monto_total_general = df_pac["Suma de Monto Total Ítem Año 2026"].sum()
    monto_total_filtrado = df_filtrado["Suma de Monto Total Ítem Año 2026"].sum()
    
    # Cálculo seguro del porcentaje
    porc_monto = (monto_total_filtrado / monto_total_general * 100) if monto_total_general > 0 else 0

    st.metric(
        "💰 Monto Estimado 2026",
        f"${monto_total_filtrado:,.0f}",
        f"{porc_monto:.1f}% del total"
    )

# --- COLUMNA 2: GRÁFICO ---
with col_grafico:
    
    # Preparación de datos
    df_grafico = df_filtrado.copy()
    
    # Convertimos a formato Periodo para agrupar y luego a String para graficar
    df_grafico["Mes_Año"] = df_grafico["Fecha de Inicio Compra"].dt.to_period("M").astype(str)

    df_mensual = (
        df_grafico
        .groupby("Mes_Año", as_index=False)["ID Proyecto"]
        .nunique()
    )

    # Creación del gráfico
    fig = px.bar(
        df_mensual,
        x="Mes_Año",
        y="ID Proyecto",
        text_auto=True,
        labels={"Mes_Año": "Mes", "ID Proyecto": "Proyectos"},
        title="📊 Cantidad de Proyectos por Mes"
    )
    
    # Ajustes visuales para que se vea bien en el contenedor
    fig.update_layout(
        height=450, # Altura fija para alinear mejor con las 2 métricas
        xaxis_title=None
    )

    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# --- 🔄 EXPANSIÓN DE ÓRDENES DE COMPRA (RELACIONAL) ---
# Creamos un DataFrame expandido: una fila por cada fecha en 'Meses envío OC'
df_expandido = df_filtrado.copy()

# 1. Convertir la columna a string y separar por comas
df_expandido['Meses envío OC'] = df_expandido['Meses envío OC'].astype(str).str.split(',')

# 2. 'Explode' convierte cada elemento de la lista en una nueva fila
df_expandido = df_expandido.explode('Meses envío OC')

# 3. Limpiar espacios y convertir a fecha
df_expandido['Meses envío OC'] = pd.to_datetime(df_expandido['Meses envío OC'].str.strip(), errors='coerce')
df_expandido = df_expandido.dropna(subset=['Meses envío OC'])



st.markdown("---")
st.markdown("### 📋 Detalle de Compras y Cronograma de OC")

# Pestañas para organizar la visualización
tab1, tab2 = st.tabs(["🔍 Vista por Proyecto", "📅 Cronograma de Órdenes (Expandido)"])

with tab1:
    st.dataframe(
        df_filtrado[[
            "ID Proyecto", "Nombre Proyecto", "Nombre ítem", 
            "Nombre responsable", "Fecha de Inicio Compra", "Suma de Monto Total Ítem Año 2026"
        ]],
        use_container_width=True,
        hide_index=True
    )

with tab2:
    # Mostramos la data normalizada (una fila por cada fecha de OC proyectada)
    st.write("Cada fila representa una Orden de Compra individual programada:")
    df_display_oc = df_expandido[[
        "Meses envío OC", "Nombre ítem", "ID Proyecto", "Nombre responsable", "Departamento_SHORT"
    ]].sort_values("Meses envío OC")
    
    st.dataframe(df_display_oc, use_container_width=True, hide_index=True)






# =============================================================================
# BOTÓN EXPORTAR PDF
# =============================================================================
st.markdown("## 📄 Exportar Reporte (Por Crear)")

if st.button("📥 Generar PDF PAC 2026"):
    pdf_path = generar_pdf_pac(
        df_datos=df_filtrado,
        total_proyectos=total_proyectos_filtrado,
        monto_total=monto_total_filtrado,
        fig_plotly=fig
    )

    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇️ Descargar PDF",
            f,
            file_name="Reporte_PAC_2026.pdf",
            mime="application/pdf"
        )


# =============================================================================
# EXPORTACIÓN
# =============================================================================
st.sidebar.markdown("### 📥 Reportes")
if st.sidebar.button("Generar Reporte PDF"):
    pdf_buffer = generar_pdf_pac(df_filtrado)
    st.sidebar.download_button(
        label="Descargar PDF",
        data=pdf_buffer,
        file_name=f"PAC_2026_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )