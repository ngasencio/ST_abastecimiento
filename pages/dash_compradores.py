import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import plotly.graph_objects as go


# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()

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
            📊 Dashboard de Compradores
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega una visión ejecutiva del desempeño de los compradores de la organización, 
permitiendo analizar su gestión en términos de eficiencia, cumplimiento y volumen de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

#st.title("👥 Dashboard de Compradores")
#st.header("Visión Ejecutiva de los Compradores")
#st.markdown("""Este módulo entrega una visión ejecutiva del desempeño de los compradores de la organización, 
#permitiendo analizar su gestión en términos de eficiencia, cumplimiento y volumen de adquisiciones.  
#""")


# =============================== FILTRO ================================================================
# --- Normalizar fecha ---
df_fsc["fecha derivado"] = pd.to_datetime(
    df_fsc["fecha derivado"],
    format="%d-%m-%Y",
    errors="coerce"
)
df_fsc["Año"] = df_fsc["fecha derivado"].dt.year


# ========= OPCIONES =========
opciones_comprador = sorted(df_fsc["comprador"].dropna().astype(str).unique())
opciones_proceso = sorted(df_fsc["ProcesoCompra"].dropna().astype(str).unique())
opciones_estado = sorted(df_fsc["EstadoProcesoCompra"].dropna().astype(str).unique())
opciones_anio = sorted(df_fsc["Año"].dropna().unique())
opciones_estado_simple = ["Pendientes","Proceso Finalizado"]

# ========= SELECT MULTI =========
# ========= SELECT MULTI =========
col1, col2, col3, col4, col5 = st.columns(5)

# ---- Año (nivel 1) ----
with col4:
    anio_sel = st.multiselect("📆 Año", opciones_anio, placeholder="Seleccione")

# DataFrame base para cascada
df_cascada = df_fsc.copy()

if anio_sel:
    df_cascada = df_cascada[df_cascada["Año"].isin(anio_sel)]

# ---- Comprador (nivel 2) ----
opciones_comprador = sorted(
    df_cascada["comprador"].dropna().astype(str).unique()
)

with col1:
    compradores_sel = st.multiselect("👥 Comprador", opciones_comprador, placeholder="Seleccione")

if compradores_sel:
    df_cascada = df_cascada[df_cascada["comprador"].isin(compradores_sel)]

# ---- Proceso de Compra (nivel 3) ----
opciones_proceso = sorted(
    df_cascada["ProcesoCompra"].dropna().astype(str).unique()
)

with col2:
    procesos_sel = st.multiselect("🛒 Proceso de Compra", opciones_proceso, placeholder="Seleccione")

if procesos_sel:
    df_cascada = df_cascada[df_cascada["ProcesoCompra"].isin(procesos_sel)]

# ---- Estado Proceso (nivel 4) ----
opciones_estado = sorted(
    df_cascada["EstadoProcesoCompra"].dropna().astype(str).unique()
)

with col3:
    estados_sel = st.multiselect("📌 Estado Proceso", opciones_estado, placeholder="Seleccione")

# ---- Estado FSC (lógico, no cascada) ----
with col5:
    estado_simple_sel = st.multiselect(
        "🚦 Estado FSC",
        opciones_estado_simple,
        placeholder="Seleccione"
    )
# ========= APLICAR FILTROS =========
df_filtrado = df_fsc.copy()

if anio_sel:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(anio_sel)]

if compradores_sel:
    df_filtrado = df_filtrado[df_filtrado["comprador"].isin(compradores_sel)]

if procesos_sel:
    df_filtrado = df_filtrado[df_filtrado["ProcesoCompra"].isin(procesos_sel)]

if estados_sel:
    df_filtrado = df_filtrado[df_filtrado["EstadoProcesoCompra"].isin(estados_sel)]

if estado_simple_sel:
    if "Pendientes" in estado_simple_sel and "Proceso Finalizado" not in estado_simple_sel:
        df_filtrado = df_filtrado[
            df_filtrado["EstadoProcesoCompra"].astype(str).str.strip()
            != "Proceso Finalizado"
        ]

    elif "Proceso Finalizado" in estado_simple_sel and "Pendientes" not in estado_simple_sel:
        df_filtrado = df_filtrado[
            df_filtrado["EstadoProcesoCompra"].astype(str).str.strip()
            == "Proceso Finalizado"
        ]
# =============================================================================0
    
##### KPIS ####
st.markdown("## 📈 Datos Principales")
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_fsc_general = df_fsc["newiD"].count()
    total_fsc_filtrado = df_filtrado["newiD"].count()

    porcentaje_fsc = (
        (total_fsc_filtrado / total_fsc_general) * 100
        if total_fsc_general > 0 else 0
    )

    st.metric(
        "📋 Total FSC",
        f"{total_fsc_filtrado:,}",
        f"{porcentaje_fsc:.1f}% del total"
    )   
    
with col2:
    monto_total_general = df_fsc["monto estimado"].sum()
    monto_filtrado = df_filtrado["monto estimado"].sum()

    porcentaje_monto = (
        (monto_filtrado / monto_total_general) * 100
        if monto_total_general > 0 else 0
    )

    st.metric(
        "💰 Montos FSC",
        f"${monto_filtrado:,.0f}",
        f"{porcentaje_monto:.1f}% del monto total"
    )

with col3:
    total_fsc = df_filtrado.shape[0]

    fsc_pendientes = df_filtrado[
        df_filtrado["EstadoProcesoCompra"]
        .astype(str)
        .str.strip() != "Proceso Finalizado"
    ].shape[0]

    porcentaje_pendientes = (
        (fsc_pendientes / total_fsc) * 100
        if total_fsc > 0 else 0
    )

    st.metric(
        "⚠️ FSC Pendientes",
        f"{fsc_pendientes:,}",
        f"{porcentaje_pendientes:.1f}% del total"
    )
with col4:
  st.empty()

st.markdown("## 📊 Análisis Gráfico ")
col1, col2, col3= st.columns(3)
with col1:

    # --- 1) Convertir fecha desde formato DD-MM-YYYY ---
    df_filtrado["fecha derivado"] = pd.to_datetime(
        df_filtrado["fecha derivado"],
        format="%d-%m-%Y",
        errors="coerce"
    )
    # --- 2) Crear columna de MES (año + mes) ---
    df_filtrado["mes"] = df_filtrado["fecha derivado"].dt.to_period("M").dt.to_timestamp()
    # --- 3) Agrupar por mes y contar formularios ---
    serie = (
        df_filtrado
        .groupby("mes")["newiD"]
        .count()
        .reset_index(name="cantidad")
        .sort_values("mes")
    )

    # --- 4) Gráfico de líneas mensual ---
    fig = px.line(
        serie,
        x="mes",
        y="cantidad",
        markers=True,
        title="Evolución Mensual de Formularios Derivados",
        labels={
            "mes": "Mes",
            "cantidad": "Cantidad de Formularios"
        }
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Mes",
        yaxis_title="Cantidad",
    )

    # --- 5) (Opcional) Mostrar etiquetas sobre cada punto ---
    fig.update_traces(text=serie["cantidad"], textposition="top center")

    st.plotly_chart(fig, use_container_width=True)
    
with col2:
    # --- Conteo por ProcesoCompra ---
    conteo_pc = (
        df_filtrado
        .groupby("ProcesoCompra")["newiD"]
        .count()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)   # mayor -> menor
    )

    # --- Gráfico horizontal con color por ProcesoCompra ---
    fig_pc = px.bar(
        conteo_pc,
        y="ProcesoCompra",
        x="cantidad",
        color="ProcesoCompra",     # 👈 color por categoría
        orientation="h",           # 👈 horizontal
        text="cantidad",
        title="Cantidad de Formularios por Proceso de Compra",
        labels={
            "ProcesoCompra": "Proceso de Compra",
            "cantidad": "Cantidad de Formularios"
        }
    )

    fig_pc.update_layout(
        template="plotly_white",
        showlegend=False,          # opcional: ocultar leyenda si se repite
        xaxis_title="Cantidad",
        yaxis_title="Proceso de Compra",
        bargap=0.2
    )
    fig_pc.update_traces(textposition="outside")
    st.plotly_chart(fig_pc, use_container_width=True)

with col3:
# --- 1. Conteo ---
    conteo = (
    df_filtrado
    .groupby(["comprador","ProcesoCompra"])["newiD"]
    .count()
    .reset_index(name="formularios")
)

# --- 2. Orden por total de formularios ---
    orden = (
    conteo
    .groupby("comprador")["formularios"]
    .sum()
    .sort_values(ascending=False)   # 👈 mayor → menor
    .index
)

# --- 3. Convertir a categoría ordenada ---
    conteo["comprador"] = pd.Categorical(
    conteo["comprador"],
    categories=orden,
    ordered=True
)

    # --- 4. ORDENAR explícitamente el dataframe ---
    conteo = conteo.sort_values("comprador")   # 👈 clave

    # --- 5. Gráfico ---
    fig = px.bar(
        conteo,
        x="comprador",
        y="formularios",
        color="ProcesoCompra",
        text="formularios",
        title="Cantidad de Formularios por Comprador",
        )

    fig.update_layout(
        barmode="stack",
        xaxis_tickangle=-30,
        template="plotly_white"
    )

    fig.update_traces(textposition="inside")

    st.plotly_chart(fig, use_container_width=True)


#======================================== TABLA DE DATOS ==================================================
# --- 1) Asegurar tipo fecha (SOLO UNA VEZ) ---
if "fecha derivado" in df_filtrado.columns:
    df_filtrado["fecha derivado"] = pd.to_datetime(
        df_filtrado["fecha derivado"],
        errors="coerce"
    )


st.markdown("## 📅 Tabla de Detalle FSC")

columnas = [
    "UnionMP",
    "unidad requirente",
    "usuario requirente",
    "requerimiento",
    "fecha derivado",
    "monto estimado",
    "ID plan",
    "comprador",
    "ProcesoCompra",
    "EstadoProcesoCompra",
]



# Usar solo columnas existentes
columnas_validas = [c for c in columnas if c in df_filtrado.columns]

tabla_base = df_filtrado[columnas_validas].copy()

# Normalizar texto para evitar errores por espacios
tabla_base["EstadoProcesoCompra"] = (
    tabla_base["EstadoProcesoCompra"]
    .astype(str)
    .str.strip()
)

# ===============================
# 🟡 FSC PENDIENTES
# ===============================

st.markdown(
    """
    <div style="
        padding: 0.75rem 1rem;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        background-color: #f9a825;
        color: black;
        border-radius: 10px;
        font-weight: 700;
        font-size: 16px;
    ">
        🟡 FSC PENDIENTES
    </div>
    """,
    unsafe_allow_html=True
)
tabla_pendientes = tabla_base[
    tabla_base["EstadoProcesoCompra"] != "Proceso Finalizado"
]

with st.expander("⚠️ Ver FSC Pendientes", expanded=False):

 st.dataframe(
        tabla_pendientes,
        use_container_width=True,
        height=450,
        hide_index=True,
        column_config={
            "UnionMP": st.column_config.TextColumn(
                "UnionMP",
                pinned=True
            ),
            "fecha derivado": st.column_config.DateColumn(
                "Fecha derivado",
                format="DD-MM-YYYY"
            ),
          "monto estimado": st.column_config.NumberColumn(
    "Monto estimado (CLP)",
    format="$ %,.0f"
)
        }
    )

st.caption(f"Mostrando {len(tabla_pendientes):,} registros pendientes.")

# ================================
# 🟢 FSC FINALIZADOS
# ================================


st.markdown(
    """
    <div style="
        padding: 0.75rem 1rem;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        background-color: #2e7d32;
        color: white;
        border-radius: 10px;
        font-weight: 700;
        font-size: 16px;
    ">
        🟢 FSC FINALIZADOS
    </div>
    """,
    unsafe_allow_html=True
)


tabla_finalizados = tabla_base[
    tabla_base["EstadoProcesoCompra"] == "Proceso Finalizado"
]

with st.expander("✅ Ver detalle FSC Finalizados", expanded=False):

    st.dataframe(
        tabla_finalizados,
        use_container_width=True,
        height=450,
        hide_index=True,
        column_config={
            "UnionMP": st.column_config.TextColumn(
                "UnionMP",
                pinned=True
            ),
            "fecha derivado": st.column_config.DateColumn(
                "Fecha derivado",
                format="DD-MM-YYYY"
            ),
            "monto estimado": st.column_config.NumberColumn(
                "Monto estimado (CLP)",
                format="$ %,.0f"
            )
        }
    )

st.caption(f"Mostrando {len(tabla_finalizados):,} registros finalizados.")