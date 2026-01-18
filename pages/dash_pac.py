# pages/dash_compras.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

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

from data.data_loader import load_fsc_data, load_pac26_data
df_pac = load_pac26_data()


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
            🛒 Planificación 2026
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega la planificación del PAC 2026 buscando su cumplimiento de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =============================== FILTROS PAC26 ==================================

# ---------- Normalización ----------
cols_texto = [
    "Subdirección",
    "Departamento_SHORT",
    "Nombre responsable",
    "ID Proyecto"
]

for col in cols_texto:
    df_pac[col] = df_pac[col].astype(str).str.strip()

# Fecha a datetime
df_pac["Fecha de Inicio Compra"] = pd.to_datetime(
    df_pac["Fecha de Inicio Compra"],
    errors="coerce"
)

# Crear columnas auxiliares
df_pac["Año"] = df_pac["Fecha de Inicio Compra"].dt.year
df_pac["Mes"] = df_pac["Fecha de Inicio Compra"].dt.month
df_pac["Mes_nombre"] = df_pac["Fecha de Inicio Compra"].dt.strftime("%B")

# =============================== OPCIONES NIVEL 1 ===============================
op_subdireccion = sorted(
    df_pac["Subdirección"].dropna().unique()
)

# =============================== LAYOUT =========================================
col1, col2, col3, col4, col5 = st.columns(5)
# =============================== FILTRO 1: Subdirección ==========================
with col1:
    subdireccion_sel = st.multiselect(
        "🏢 Subdirección",
        op_subdireccion,
        placeholder="Seleccione"
    )

df_cascada = df_pac.copy()

if subdireccion_sel:
    df_cascada = df_cascada[
        df_cascada["Subdirección"].isin(subdireccion_sel)
    ]

# =============================== FILTRO 2: Departamento ==========================
op_depto = sorted(
    df_cascada["Departamento_SHORT"].dropna().unique()
)

with col2:
    depto_sel = st.multiselect(
        "📊 Departamento",
        op_depto,
        placeholder="Seleccione"
    )

if depto_sel:
    df_cascada = df_cascada[
        df_cascada["Departamento_SHORT"].isin(depto_sel)
    ]

# =============================== FILTRO 3: Responsable ===========================
op_responsable = sorted(
    df_cascada["Nombre responsable"].dropna().unique()
)

with col3:
    responsable_sel = st.multiselect(
        "👤 Responsable",
        op_responsable,
        placeholder="Seleccione"
    )

if responsable_sel:
    df_cascada = df_cascada[
        df_cascada["Nombre responsable"].isin(responsable_sel)
    ]

# =============================== FILTRO 4: Proyecto ==============================
op_proyecto = sorted(
    df_cascada["ID Proyecto"].dropna().unique()
)

with col4:
    proyecto_sel = st.multiselect(
        "🆔 ID Proyecto",
        op_proyecto,
        placeholder="Seleccione"
    )

if proyecto_sel:
    df_cascada = df_cascada[
        df_cascada["ID Proyecto"].isin(proyecto_sel)
    ]

# =============================== FILTRO 5: Año y Mes ===============================
op_anio = sorted(
    df_cascada["Año"].dropna().unique()
)

with col5:
    anio_sel = st.multiselect(
        "📅 Año",
        op_anio,
        placeholder="Seleccione"
    )

if anio_sel:
    df_cascada = df_cascada[
        df_cascada["Año"].isin(anio_sel)
    ]

# ---------- Mes (depende del año seleccionado) ----------
op_mes = (
    df_cascada[["Mes", "Mes_nombre"]]
    .dropna()
    .drop_duplicates()
    .sort_values("Mes")
)

mes_opciones = op_mes["Mes_nombre"].tolist()

mes_sel = st.multiselect(
    "🗓️ Mes",
    mes_opciones,
    placeholder="Seleccione"
)

# =============================== APLICAR FILTROS ================================
df_filtrado = df_pac.copy()

if subdireccion_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Subdirección"].isin(subdireccion_sel)
    ]

if depto_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Departamento_SHORT"].isin(depto_sel)
    ]

if responsable_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Nombre responsable"].isin(responsable_sel)
    ]

if proyecto_sel:
    df_filtrado = df_filtrado[
        df_filtrado["ID Proyecto"].isin(proyecto_sel)
    ]

if anio_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Año"].isin(anio_sel)
    ]

if mes_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Mes_nombre"].isin(mes_sel)
    ]

##### KPIS ####
st.markdown("## 📈 Datos Generales PAC26")

col1, col2 = st.columns(2)

# ===================== KPI 1: Cantidad de Proyectos =====================
with col1:

    # --- 2. Lógica de Cálculo (Tus variables) ---
    total_proyectos_general = df_pac["ID Proyecto"].nunique()
    total_proyectos_filtrado = df_filtrado["ID Proyecto"].nunique()

    porcentaje_proyectos = (
        (total_proyectos_filtrado / total_proyectos_general) * 100
        if total_proyectos_general > 0 else 0
    )

    # --- 3. Renderizado de la KPI Card personalizada ---
    
    st.metric(
        "🗂️ Cantidad de Proyectos",
        total_proyectos_filtrado,
        f"{porcentaje_proyectos:.1f}% del total"
    )

# ===================== KPI 2: Monto Estimado =====================
with col2:
    monto_total_general = df_pac["Suma de Monto Total Ítem Año 2026"].sum()
    monto_total_filtrado = df_filtrado["Suma de Monto Total Ítem Año 2026"].sum()

    porcentaje_monto = (
        (monto_total_filtrado / monto_total_general) * 100
        if monto_total_general > 0 else 0
    )

    st.metric(
        "💰 Monto Estimado 2026",
        f"${monto_total_filtrado:,.0f}",
        f"{porcentaje_monto:.1f}% del monto total"
    )

#================= Graficos =====================

st.markdown("## 📊 Análisis Gráfico PAC26")
df_grafico = df_filtrado.copy()

df_grafico = df_filtrado.copy()

df_grafico["Fecha de Inicio Compra"] = pd.to_datetime(
    df_grafico["Fecha de Inicio Compra"],
    errors="coerce"
)

# Mes-Año para el eje X
df_grafico["Mes_Año"] = df_grafico["Fecha de Inicio Compra"].dt.to_period("M").astype(str)

df_mensual = (
    df_grafico
    .groupby("Mes_Año", as_index=False)["ID Proyecto"]
    .nunique()
    .sort_values("Mes_Año")
)

fig = px.bar(
    df_mensual,
    x="Mes_Año",
    y="ID Proyecto",
    title="📊 Cantidad de Proyectos por Mes",
    labels={
        "Mes_Año": "Mes",
        "ID Proyecto": "Cantidad de Proyectos"
    },
    text_auto=True
)

fig.update_layout(
    xaxis_tickangle=-45,
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

#================ Tabla de datos ====================
st.markdown("## 📋 Datos PAC26")

df_base = df_filtrado.copy()

# Asegurar datetime
df_base["Fecha de Inicio Compra"] = pd.to_datetime(
    df_base["Fecha de Inicio Compra"],
    errors="coerce"
)

# Fecha actual
hoy = datetime.today()
anio_actual = hoy.year
mes_actual = hoy.month

# Solo NO ejecutados
df_no_ejecutados = df_base[
    df_base["Ejecución"].str.upper() == "NO EJECUTADO"
]


##📌 Proyectos por ejecutar ESTE MES
df_por_ejecutar_mes = df_no_ejecutados[
    (df_no_ejecutados["Fecha de Inicio Compra"].dt.year == anio_actual) &
    (df_no_ejecutados["Fecha de Inicio Compra"].dt.month == mes_actual)
]



##📌 Proyectos pendientes (otros meses)
df_pendientes = df_no_ejecutados[
    ~(
        (df_no_ejecutados["Fecha de Inicio Compra"].dt.year == anio_actual) &
        (df_no_ejecutados["Fecha de Inicio Compra"].dt.month == mes_actual)
    )
]
st.markdown("""
<div style="
    background-color:#d32f2f;
    color:white;
    padding:12px 16px;
    border-radius:8px;
    font-weight:bold;
    font-size:18px;
    margin-bottom:6px;
">
🚨 Proyectos por ejecutar este mes
</div>
""", unsafe_allow_html=True)
with st.expander("🚨 Proyectos por ejecutar este mes", expanded=True):
    st.write(f"Total proyectos: {df_por_ejecutar_mes['ID Proyecto'].nunique():,}")
    st.dataframe(
        df_por_ejecutar_mes.sort_values("Fecha de Inicio Compra"),
        use_container_width=True,
        column_config={
            "Suma de Monto Total Ítem Año 2026": st.column_config.NumberColumn(
                "Monto Estimado",
                format="$%,.2f"
        )
    }
)
# ---------- HEADER AMARILLO ----------
st.markdown("""
<div style="
    background-color:#fbc02d;
    color:black;
    padding:12px 16px;
    border-radius:8px;
    font-weight:bold;
    font-size:18px;
    margin-bottom:6px;
">
⏳ Proyectos pendientes (otros meses)
</div>
""", unsafe_allow_html=True)

# ---------- EXPANDER ----------
with st.expander("Ver detalle"):
    st.write(f"Total proyectos: {df_pendientes['ID Proyecto'].nunique():,}")
    st.dataframe(
        df_pendientes.sort_values("Fecha de Inicio Compra"),
        use_container_width=True
    )
# ---------- HEADER AZUL ----------
st.markdown("""
<div style="
    background-color:#1976d2;
    color:white;
    padding:12px 16px;
    border-radius:8px;
    font-weight:bold;
    font-size:18px;
    margin-bottom:6px;
">
📋 Todos los proyectos no ejecutados
</div>
""", unsafe_allow_html=True)

# ---------- EXPANDER ----------
with st.expander("Ver detalle"):
    st.write(f"Total proyectos: {df_no_ejecutados['ID Proyecto'].nunique():,}")
    st.dataframe(
        df_no_ejecutados.sort_values("Fecha de Inicio Compra"),
        use_container_width=True
    )