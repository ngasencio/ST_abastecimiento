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
df_pac["Mes_nombre"] = df_pac["Fecha de Inicio Compra"].dt.strftime("%B")


# =============================================================================
# FILTROS
# =============================================================================
col1, col2, col3, col4, col5 = st.columns(5)

# --- Filtro 1: Subdirección ---
with col1:
    subdireccion_sel = st.multiselect(
        "🏢 Subdirección",
        sorted(df_pac["Subdirección"].dropna().unique()),
        placeholder="Seleccione"
    )

df_cascada = df_pac.copy()
if subdireccion_sel:
    df_cascada = df_cascada[df_cascada["Subdirección"].isin(subdireccion_sel)]

# --- Filtro 2: Departamento ---
with col2:
    depto_sel = st.multiselect(
        "📊 Departamento",
        sorted(df_cascada["Departamento_SHORT"].dropna().unique()),
        placeholder="Seleccione"
    )

if depto_sel:
    df_cascada = df_cascada[df_cascada["Departamento_SHORT"].isin(depto_sel)]

# --- Filtro 3: Responsable ---
with col3:
    responsable_sel = st.multiselect(
        "👤 Responsable",
        sorted(df_cascada["Nombre responsable"].dropna().unique()),
        placeholder="Seleccione"
    )

if responsable_sel:
    df_cascada = df_cascada[df_cascada["Nombre responsable"].isin(responsable_sel)]

# --- Filtro 4: ID Proyecto ---
with col4:
    proyecto_sel = st.multiselect(
        "🆔 ID Proyecto",
        sorted(df_cascada["ID Proyecto"].dropna().unique()),
        placeholder="Seleccione"
    )

if proyecto_sel:
    df_cascada = df_cascada[df_cascada["ID Proyecto"].isin(proyecto_sel)]

# --- Filtro 5: Año ---
with col5:
    anio_sel = st.multiselect(
        "📅 Año",
        sorted(df_cascada["Año"].dropna().unique()),
        placeholder="Seleccione"
    )

# --- Filtro Final: Mes (Fuera de columnas o en una nueva fila) ---
df_filtrado = df_cascada.copy()
if anio_sel:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(anio_sel)]

mes_sel = st.multiselect(
    "🗓️ Mes",
    sorted(df_filtrado["Mes_nombre"].dropna().unique()),
    placeholder="Seleccione"
)

if mes_sel:
    df_filtrado = df_filtrado[df_filtrado["Mes_nombre"].isin(mes_sel)]

# =============================================================================
# KPIs
# =============================================================================
st.markdown("## 📈 Datos Generales PAC26")

k1, k2 = st.columns(2)

with k1:
    total_proyectos_general = df_pac["ID Proyecto"].nunique()
    total_proyectos_filtrado = df_filtrado["ID Proyecto"].nunique()

    st.metric(
        "🗂️ Cantidad de Proyectos",
        total_proyectos_filtrado,
        f"{(total_proyectos_filtrado / total_proyectos_general * 100):.1f}% del total"
    )

with k2:
    monto_total_general = df_pac["Suma de Monto Total Ítem Año 2026"].sum()
    monto_total_filtrado = df_filtrado["Suma de Monto Total Ítem Año 2026"].sum()

    st.metric(
        "💰 Monto Estimado 2026",
        f"${monto_total_filtrado:,.0f}",
        f"{(monto_total_filtrado / monto_total_general * 100):.1f}% del monto total"
    )


# =============================================================================
# GRÁFICO
# =============================================================================
st.markdown("## 📊 Análisis Gráfico PAC26")

df_grafico = df_filtrado.copy()
df_grafico["Mes_Año"] = (
    df_grafico["Fecha de Inicio Compra"].dt.to_period("M").astype(str)
)

df_mensual = (
    df_grafico
    .groupby("Mes_Año", as_index=False)["ID Proyecto"]
    .nunique()
)

fig = px.bar(
    df_mensual,
    x="Mes_Año",
    y="ID Proyecto",
    text_auto=True,
    labels={"Mes_Año": "Mes", "ID Proyecto": "Cantidad de Proyectos"},
    title="Cantidad de Proyectos por Mes"
)

st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# BOTÓN EXPORTAR PDF
# =============================================================================
st.markdown("## 📄 Exportar Reporte")

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