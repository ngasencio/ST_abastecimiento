# pages/dash_general.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()


st.title("👥 Dashboard de Compradores")
st.header("Visión Ejecutiva del Desempeño de los Compradores")
st.markdown("""Este módulo entrega una visión ejecutiva del desempeño de los compradores de la organización, 
permitiendo analizar su gestión en términos de eficiencia, cumplimiento y volumen de adquisiciones.  
""")
st.markdown("---")



# Simulación de datos clave
data_general = {
    'Métrica': ['Ingresos', 'Usuarios Activos', 'Tasa de Conversión'],
    'Valor Actual': [5500000, 15000, '2.8%'],
    'Variación vs Mes Anterior': ['+12%', '-3%', '+0.5%']
}
df_general = pd.DataFrame(data_general)


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


# ========= SELECT MULTI =========
col1, col2, col3, col4 = st.columns(4)

with col1:
    compradores_sel = st.multiselect("👥 Comprador", opciones_comprador, placeholder="Seleccione")

with col2:
    procesos_sel = st.multiselect("🛒 Proceso de Compra", opciones_proceso, placeholder="Seleccione")

with col3:
    estados_sel = st.multiselect("📌 Estado Proceso", opciones_estado, placeholder="Seleccione")

with col4:
    anio_sel = st.multiselect("📆 Año", opciones_anio, placeholder="Seleccione")


# ========= APLICAR FILTROS =========
df_filtrado = df_fsc.copy()

if compradores_sel:
    df_filtrado = df_filtrado[df_filtrado["comprador"].isin(compradores_sel)]

if procesos_sel:
    df_filtrado = df_filtrado[df_filtrado["ProcesoCompra"].isin(procesos_sel)]

if estados_sel:
    df_filtrado = df_filtrado[df_filtrado["EstadoProcesoCompra"].isin(estados_sel)]

if anio_sel:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(anio_sel)]
# =============================================================================0
    
st.markdown("---")    
##### KPIS ####
st.markdown("## 📈 KPIs Principales")
col1, col2, col3, col4 = st.columns(4)
with col1:
    Total_FSC = df_filtrado["newiD"].count()
    st.metric("📋 Total FSC", 
            f"{Total_FSC:,.0f}",
            f"{np.random.uniform(2, 8):.1f}%")
    
with col2:
    montos_estimados = df_filtrado["monto estimado"].sum()
    st.metric("💰 Montos Estimados", 
            f"${montos_estimados:,.0f}",
            f"{np.random.uniform(5, 15):.1f}%")

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
#st.subheader("Datos de Muestra")
#st.dataframe(df_general, use_container_width=True)

st.markdown("---")

st.markdown("## 📊 Análisis Gráfico ")
col1, col2 = st.columns(2)
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

st.markdown("## 📅 Tabla de Datos")

columnas = [
    "UnionMP",
    "unidad requirente",
    "usuario requirente",
    "requerimiento",
    "monto estimado",
    "ID plan",
    "comprador",
    "ProcesoCompra",
    "EstadoProcesoCompra"
]

# Usar solo columnas que existan para evitar errores
columnas_validas = [c for c in columnas if c in df_filtrado.columns]

tabla = df_filtrado[columnas_validas].copy()


# ====== ESTILO DEL EXPANDER ======
st.markdown("""
    <style>
    /* Cambiar color SOLO del primer expander */
    div.streamlit-expanderHeader {
        background-color: #2ecc71;  /* Verde */
        color: white;               /* Texto blanco */
        font-weight: bold;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)



with st.expander("📅 Ver Datos Completos", expanded=False):

    # Formato de columnas
    formato = {}

    if "monto estimado" in tabla.columns:
        formato["monto estimado"] = "${:,.0f}".format

    st.dataframe(
        tabla.style.format(formato),
        use_container_width=True,
        height=450
    )

st.caption(f"Mostrando {len(tabla):,} registros filtrados.")

