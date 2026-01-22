# pages/dash_compras.py

# =============================================================================
# IMPORTS
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import tempfile
import os

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
# FUNCIÓN GENERAR PDF
# =============================================================================
def generar_pdf_pac(
    df_datos,
    total_proyectos,
    monto_total,
    fig_plotly
):
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "Reporte_PAC_2026.pdf")
    img_path = os.path.join(temp_dir, "grafico_pac.png")

    fig_plotly.write_image(img_path, width=900, height=400)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    contenido = []

    contenido.append(Paragraph("Reporte Plan Anual de Compras 2026", styles["Title"]))
    contenido.append(Spacer(1, 12))
    contenido.append(
        Paragraph(
            f"Fecha de generación: {datetime.today().strftime('%d-%m-%Y')}",
            styles["Normal"]
        )
    )
    contenido.append(Spacer(1, 20))

    tabla_kpi = Table(
        [
            ["Indicador", "Valor"],
            ["Cantidad de Proyectos", f"{total_proyectos:,}"],
            ["Monto Estimado", f"${monto_total:,.0f}"]
        ],
        colWidths=[220, 180]
    )

    tabla_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT")
    ]))

    contenido.append(Paragraph("Resumen General", styles["Heading2"]))
    contenido.append(tabla_kpi)
    contenido.append(Spacer(1, 20))

    contenido.append(Paragraph("Análisis Mensual", styles["Heading2"]))
    contenido.append(Image(img_path, width=500, height=220))
    contenido.append(Spacer(1, 20))

    df_tabla = (
        df_datos
        .loc[:, ["ID Proyecto", "Departamento_SHORT", "Fecha de Inicio Compra"]]
        .head(20)
    )

    tabla_datos = Table(
        [df_tabla.columns.tolist()] + df_tabla.values.tolist(),
        repeatRows=1
    )

    tabla_datos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    contenido.append(Paragraph("Detalle de Proyectos (primeros 20)", styles["Heading2"]))
    contenido.append(tabla_datos)

    doc.build(contenido)

    return pdf_path


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

with col1:
    subdireccion_sel = st.multiselect(
        "🏢 Subdirección",
        sorted(df_pac["Subdirección"].dropna().unique())
    )

df_cascada = df_pac.copy()
if subdireccion_sel:
    df_cascada = df_cascada[df_cascada["Subdirección"].isin(subdireccion_sel)]

with col2:
    depto_sel = st.multiselect(
        "📊 Departamento",
        sorted(df_cascada["Departamento_SHORT"].dropna().unique())
    )

if depto_sel:
    df_cascada = df_cascada[df_cascada["Departamento_SHORT"].isin(depto_sel)]

with col3:
    responsable_sel = st.multiselect(
        "👤 Responsable",
        sorted(df_cascada["Nombre responsable"].dropna().unique())
    )

if responsable_sel:
    df_cascada = df_cascada[df_cascada["Nombre responsable"].isin(responsable_sel)]

with col4:
    proyecto_sel = st.multiselect(
        "🆔 ID Proyecto",
        sorted(df_cascada["ID Proyecto"].dropna().unique())
    )

if proyecto_sel:
    df_cascada = df_cascada[df_cascada["ID Proyecto"].isin(proyecto_sel)]

with col5:
    anio_sel = st.multiselect(
        "📅 Año",
        sorted(df_cascada["Año"].dropna().unique())
    )

df_filtrado = df_cascada.copy()
if anio_sel:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(anio_sel)]

mes_sel = st.multiselect(
    "🗓️ Mes",
    sorted(df_filtrado["Mes_nombre"].dropna().unique())
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