import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# --- EN TU ARCHIVO DE STREAMLIT ---
from api.Consolidar_OC import ejecutar_consolidacion_oc

# ===== CARGAR CSS =====
def cargar_css():
    try:
        with open("style/style.css") as f:
            # Usamos una sola línea y eliminamos espacios innecesarios con .strip()
            css_content = f.read().replace("\n", "").strip()
            st.markdown(
                f"<style>{css_content}</style>", 
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")

# Llama a la función al principio de todo, justo después de st.set_page_config
cargar_css()
#linea tiempo
#from streamlit_timeline import st_timeline


# Cargar las bases
bases_oc = ejecutar_consolidacion_oc()
df_oc_res = bases_oc["RESUMEN"]

st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #1748EB, #3f6ef2);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            🧾 Ordenes de Compra DSSO
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega la planificación del PAC 2026 buscando su cumplimiento de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================== Filtros ========================
# 1. Normalización previa (Evita errores por espacios o tipos de datos)
for col in ["EstadoOC", "C_Unidad", "C_Contacto"]:
    df_oc_res[col] = df_oc_res[col].astype(str).str.strip()

# =============================== FILTROS ================================================================

# Definimos 4 columnas para los widgets
col1, col2, col3, col4 = st.columns(4)

# --- LÓGICA DE CASCADA (Dataframe temporal para opciones dinámicas) ---
df_cascada = df_oc_res.copy()

# ---- 1. ESTADO OC ----
opciones_estado = sorted(df_cascada["EstadoOC"].dropna().unique())
with col1:
    estado_oc_sel = st.multiselect("📌 Estado OC", opciones_estado, placeholder="Seleccione")

if estado_oc_sel:
    df_cascada = df_cascada[df_cascada["EstadoOC"].isin(estado_oc_sel)]

# ---- 2. UNIDAD ----
opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
with col2:
    unidad_sel = st.multiselect("🏢 Unidad", opciones_unidad, placeholder="Seleccione")

if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# ---- 3. CONTACTO ----
opciones_contacto = sorted(df_cascada["C_Contacto"].dropna().unique())
with col3:
    contacto_sel = st.multiselect("👤 Contacto", opciones_contacto, placeholder="Seleccione")

if contacto_sel:
    df_cascada = df_cascada[df_cascada["C_Contacto"].isin(contacto_sel)]

# ---- 4. ESPACIO (Pass) ----
with col4:
    # Espacio reservado para futuros filtros de OC
    pass

# =============================== APLICAR FILTROS FINAL =================================================

# Creamos la copia filtrada basada en las selecciones
df_filtrado = df_oc_res.copy()

if estado_oc_sel:
    df_filtrado = df_filtrado[df_filtrado["EstadoOC"].isin(estado_oc_sel)]

if unidad_sel:
    df_filtrado = df_filtrado[df_filtrado["C_Unidad"].isin(unidad_sel)]

if contacto_sel:
    df_filtrado = df_filtrado[df_filtrado["C_Contacto"].isin(contacto_sel)]

# ================================== KPIS ===============================================

st.markdown("## 📊 Indicadores de Gestión OC")
c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

with c_kpi1:
    # --- TOTAL ÓRDENES DE COMPRA ---
    # Usamos el conteo de filas de la base resumen de OC
    total_oc_gral = len(df_oc_res)
    total_oc_filt = len(df_filtrado)

    porcentaje_oc = (
        (total_oc_filt / total_oc_gral) * 100
        if total_oc_gral > 0 else 0
    )

    st.metric(
        "📝 Cantidad de OC",
        f"{total_oc_filt:,}",
        f"{porcentaje_oc:.1f}% del total"
    )

with c_kpi2:
    # --- TOTAL MONTO BRUTO ---
    monto_col_oc = "TotalBruto"
    
    monto_oc_gral = df_oc_res[monto_col_oc].sum()
    monto_oc_filt = df_filtrado[monto_col_oc].sum()

    porcentaje_monto_oc = (
        (monto_oc_filt / monto_oc_gral) * 100
        if monto_oc_gral > 0 else 0
    )

    st.metric(
        "💰 Monto Total (Bruto)",
        f"${monto_oc_filt:,.0f}",
        f"{porcentaje_monto_oc:.1f}% del monto total"
    )

with c_kpi3:
    # Espacio para futura métrica (ej. Cantidad de proveedores)
    pass

with c_kpi4:
    # Espacio para futura métrica (ej. Ticket promedio)
    pass

# ================================== GRAFICOS ===============================================
# ##### GRAFICOS OC CON MESES EN ESPAÑOL ####
st.markdown("## 📊 Análisis Gráfico de Órdenes de Compra")

# 1. Asegurar que FechaCreacion sea datetime
df_filtrado["FechaCreacion"] = pd.to_datetime(
    df_filtrado["FechaCreacion"],
    errors="coerce",
    dayfirst=True
)

# 2. Crear columna mensual
df_filtrado["Mes"] = df_filtrado["FechaCreacion"].dt.to_period("M").dt.to_timestamp()

# Diccionario para traducir (Opcional, pero para el eje X usaremos tickformat y ticklabel)
meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

col1, col2 = st.columns(2)

# ======================================
# 📊 A) Cantidad de OC por Mes
# ======================================
with col1:
    conteo_mes_oc = (
        df_filtrado
        .copy()
    )

    # Asegurar que Mes es datetime
    conteo_mes_oc["Mes"] = pd.to_datetime(conteo_mes_oc["Mes"])

    conteo_mes_oc = (
        conteo_mes_oc
        .groupby(["Mes", "EstadoOC"])
        .size()
        .reset_index(name="Cantidad OC")
        .sort_values("Mes")
    )

    fig_q_oc = px.bar(
        conteo_mes_oc,
        x="Mes",
        y="Cantidad OC",
        color="EstadoOC",
        title="📝 Cantidad de OC por Mes y Estado",
        labels={
            "Mes": "Mes",
            "Cantidad OC": "N° de Órdenes",
            "EstadoOC": "Estado"
        },
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig_q_oc.update_layout(
        barmode="stack",
        height=400,
        template="plotly_white",
        xaxis=dict(
            tickvals=conteo_mes_oc["Mes"].unique(),
            ticktext=[
                meses_es[m.month-1] + f" {m.year}"
                for m in conteo_mes_oc["Mes"].unique()
            ]
        )
    )

    st.plotly_chart(fig_q_oc, use_container_width=True)
# ======================================
# 💰 B) Monto Total Bruto por Mes
# ======================================
with col2:
    monto_mes_oc = df_filtrado.copy()

    monto_mes_oc["Mes"] = pd.to_datetime(monto_mes_oc["Mes"])

    monto_mes_oc = (
        monto_mes_oc
        .groupby(["Mes", "EstadoOC"])["TotalBruto"]
        .sum()
        .reset_index(name="Monto Total Bruto")
        .sort_values("Mes")
    )

    fig_m_oc = px.bar(
        monto_mes_oc,
        x="Mes",
        y="Monto Total Bruto",
        color="EstadoOC",
        title="💰 Monto Total Bruto por Mes y Estado",
        labels={
            "Mes": "Mes",
            "Monto Total Bruto": "Monto Bruto (CLP)",
            "EstadoOC": "Estado"
        },
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig_m_oc.update_layout(
        barmode="stack",
        height=400,
        template="plotly_white",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",

        xaxis=dict(
            tickvals=monto_mes_oc["Mes"].unique(),
            ticktext=[
                meses_es[m.month-1] + f" {m.year}"
                for m in monto_mes_oc["Mes"].unique()
            ]
        )
    )

    st.plotly_chart(fig_m_oc, use_container_width=True)

st.markdown("## 🛒 Órdenes de Compra Consolidadas")

with st.expander("📅 Ver Tabla Maestra de OCs"):
    st.dataframe(df_oc_res.style.format({
        # Formatos de Dinero
        "TotalNeto": "${:,.0f}".format,
        "Total": "${:,.0f}".format,
        "Impuestos": "${:,.0f}".format,
        # Formatos de Texto/ID
        "Codigo": str,
        "CodigoLicitacion": str,
        "Estado": str,
        # Formato de Porcentajes
        "PorcentajeIva": "{:.1f}%".format,
    }), height=400, use_container_width=True)