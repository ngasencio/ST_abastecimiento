import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================================
# 1. CARGA DE DATOS
# ==========================================================

from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()

# ==========================================================
# 2. CARGAR CSS
# ==========================================================

def cargar_css():
    try:
        with open("style/style.css") as f:
            css_content = f.read().replace("\n", "").strip()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")

cargar_css()

# Definición de colores institucionales/Lean para consistencia visual
colores_lean = {
    "Compra Agil": "#0000FF",        # Azul
    "Licitacion": "#87CEEB",         # Celeste
    "Proceso": "#FF0000",            # Rojo
    "Convenio Marco": "#FFC0CB",     # Rosado
    "Trato Directo": "#008000",      # Verde
    "Orden de Compra": "#90EE90"     # Verde Claro
}

# ==========================================================
# 3. HEADER
# ==========================================================

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
            👥 Dashboard de Compradores
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Visión ejecutiva del desempeño de los compradores en eficiencia,
            cumplimiento y volumen de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# 4. PREPARACIÓN DE DATOS
# ==========================================================


df_fsc["fecha derivado"] = pd.to_datetime(
    df_fsc["fecha derivado"],
    format="%d-%m-%Y",
    errors="coerce"
)

df_fsc["Año"] = df_fsc["fecha derivado"].dt.year

# ==========================================================
# 5. FILTROS EN CASCADA
# ==========================================================


# ========= OPCIONES =========
opciones_comprador = sorted(df_fsc["comprador"].dropna().astype(str).unique())
opciones_proceso = sorted(df_fsc["ProcesoCompra"].dropna().astype(str).unique())
opciones_estado = sorted(df_fsc["EstadoProcesoCompra"].dropna().astype(str).unique())
opciones_anio = sorted(df_fsc["Año"].dropna().unique())
opciones_estado_simple = ["Pendientes","Proceso Finalizado"]

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
st.markdown("## 🎯 Datos Principales")
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
    # Identificar procesos finalizados vs pendientes
    fsc_finalizados = df_filtrado[df_filtrado["EstadoProcesoCompra"].str.contains("Finalizado", na=False)].shape[0]
    tasa_cierre = (fsc_finalizados / total_fsc_filtrado * 100) if total_fsc_filtrado > 0 else 0
    st.metric("✅ Tasa de Finalización", f"{tasa_cierre:.1f}%", help="Eficiencia del flujo de valor")

st.markdown("## 📋 Detalles de Orden de Compra")
# Pestañas para organizar la visualización
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9  = st.tabs(["🛒 Plan de Compras", "⏳ Estado Orden de Compra","🗃️ Unidad de Compras", "💼 Gestión de Compra", "📦 Productos","🚚 Recepciones", "👥 Proveedores", "🏭 Proveedores", "📊 Métricas Lean"])

with tab1:
    st.write("Plan de Compras")

with tab2:
    st.write("Estado Orden de Compra")

with tab3:
    st.write("Unidad de Compras")

with tab4:
    st.write("Gestión de Compra")

with tab5:
    st.write("Productos")

with tab6:
    st.write("Recepciones")

with tab7:
    st.write("Proveedores")

with tab8:
    st.write("Proveedores")

with tab9:
    st.write("Métricas Lean")

st.markdown("## 📊 Análisis de Estabilidad y Carga ")
col1, col2, col3= st.columns(3)
with col1:
    # --- 0. Preparación de Fechas ---
    # Convertimos a datetime
    df_filtrado["fecha_dt"] = pd.to_datetime(
        df_filtrado["fecha derivado"], format="%d-%m-%Y", errors="coerce")
    # Creamos una columna de TEXTO "Año-Mes" (ej: "2023-01") para que actúe como categoría
    df_filtrado["Periodo"] = df_filtrado["fecha_dt"].dt.strftime("%Y-%m")

    # --- Conteo ---
    conteo_mes = (
        df_filtrado
        .groupby(["Periodo", "ProcesoCompra"])["newiD"]
        .count()
        .reset_index(name="cantidad")
    )

    # --- Orden (Cronológico) ---
    orden_fechas = sorted(conteo_mes["Periodo"].unique())

    # --- Convertir a categoría ordenada ---
    conteo_mes["Periodo"] = pd.Categorical(
        conteo_mes["Periodo"],
        categories=orden_fechas,
        ordered=True
    )
# --- Gráfico ---
    fig = px.bar(
        conteo_mes,
        x="Periodo",
        y="cantidad",
        color="ProcesoCompra",
        text="cantidad",
        title="📈 Estabilidad del Flujo (Throughput Mensual)",
        barmode="stack"
    ) 
    fig.update_layout(
        xaxis_tickangle=-45,
        barmode="stack",
        template="plotly_white",
        legend_title_text="Tipo de Proceso",
        xaxis_title="Mes",
        yaxis_title="Cantidad de Formularios"
    )

    # Colocamos el texto afuera para que se lea mejor en barras agrupadas
    fig.update_traces(textposition="outside", cliponaxis=False)

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
        color="ProcesoCompra",     
        orientation="h",           
        text="cantidad",
        title="📂 Mix de Trabajo ",
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
        title="⚖️Análisis de Balanceo de Línea (Carga de Compradores)",
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

tabla_pendientes = tabla_base[
    tabla_base["EstadoProcesoCompra"] != "Proceso Finalizado"
]

with st.expander(f"⚠️ Ver FSC Pendientes -   {len(tabla_pendientes):,} registros pendientes.", expanded=False):

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

# ================================
# 🟢 FSC FINALIZADOS
# ================================

tabla_finalizados = tabla_base[
    tabla_base["EstadoProcesoCompra"] == "Proceso Finalizado"
]

with st.expander(f"✅ Ver detalle FSC Finalizados -   {len(tabla_finalizados):,} registros finalizados." , expanded=False):

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

# ==========================================================
# 🚀 MÓDULO: LEAN STRATEGY & OKRs
# ==========================================================
st.markdown("## 🎯 Lean Strategy & OKR Tracker")

# 1. Preparación de métricas de Calidad (Dentro/Fuera PAC)
df_lean = df_filtrado.copy()
df_lean["monto estimado"] = pd.to_numeric(df_lean["monto estimado"], errors='coerce').fillna(0)

# Cálculo de Adherencia
total_solicitudes = len(df_lean)
dentro_pac = len(df_lean[df_lean["DENTRO/FUERA"].str.upper().str.contains("DENTRO", na=False)])
tasa_adherencia = (dentro_pac / total_solicitudes * 100) if total_solicitudes > 0 else 0

# 2. Layout de OKRs (Basado en Manual OKR)
c1, c2, c3 = st.columns(3)

with c1:
    # OKR 1: Calidad de Planificación
    st.info("**Objetivo:** Maximizar Compras Planificadas")
    st.metric(
        label="KR: Tasa de Adherencia al PAC",
        value=f"{tasa_adherencia:.1f}%",
        delta=f"{tasa_adherencia - 85:.1f}% vs Meta (85%)",
        help="Métrica de Lean Startup: Indica qué tanto estamos reaccionando a emergencias vs planificando."
    )

with c2:
    # OKR 2: Eficiencia de Proceso (Muda de Sobre-procesamiento)
    ticket_promedio = df_lean["monto estimado"].mean()
    st.info("**Objetivo:** Optimizar Valor por Transacción")
    st.metric(
        label="KR: Ticket Promedio FSC",
        value=f"${ticket_promedio:,.0f}",
        delta="Eficiencia Operativa",
        delta_color="off"
    )

with c3:
    # OKR 3: Control de Fugas Financieras
    monto_fuera_pac = df_lean[df_lean["DENTRO/FUERA"].str.upper().str.contains("FUERA", na=False)]["monto estimado"].sum()
    st.info("**Objetivo:** Reducir Gasto No Planificado")
    st.metric(
        label="KR: Gasto Fuera de PAC",
        value=f"${monto_fuera_pac:,.0f}",
        delta="Muda de Planificación",
        delta_color="inverse"
    )

# ==========================================================
# 📊 MÓDULO: MATRIZ DE CARGA VS VALOR (PARETO)
# ==========================================================
st.markdown("### ⚖️ Matriz de Eficiencia por Comprador")

# Agrupamos para ver quién maneja más valor vs quién maneja más carga (Muda de Sobrecarga - Muri)
df_comprador_lean = df_lean.groupby("comprador").agg({
    "newiD": "count",
    "monto estimado": "sum"
}).reset_index().rename(columns={"newiD": "Cantidad", "monto estimado": "Monto Total"})

fig_bubble = px.scatter(
    df_comprador_lean,
    x="Cantidad",
    y="Monto Total",
    size="Monto Total",
    color="comprador",
    hover_name="comprador",
    title="Análisis de Carga vs Responsabilidad Financiera",
    labels={"Cantidad": "Volumen de Trabajo (FSC)", "Monto Total": "Presupuesto Gestionado ($)"},
    template="plotly_white"
)

# Añadir línea de promedio de carga para identificar desequilibrios
fig_bubble.add_vline(x=df_comprador_lean["Cantidad"].mean(), line_dash="dash", line_color="red", annotation_text="Carga Promedio")

st.plotly_chart(fig_bubble, use_container_width=True)

# ==========================================================
# ⏱️ MÓDULO: ANÁLISIS DE LEAD TIME (MUDA DE ESPERA)
# ==========================================================
st.markdown("---")
st.markdown("## ⏱️ Análisis de Lead Time: Velocidad de Respuesta")

# 1. Preparación de Fechas y Cálculo de Lead Time
# Aseguramos que ambas columnas sean datetime
df_filtrado["fecha_solicitud"] = pd.to_datetime(df_filtrado["fecha_solicitud"], errors='coerce')
df_filtrado["fecha derivado"] = pd.to_datetime(df_filtrado["fecha derivado"], errors='coerce')

# Calculamos la diferencia en días
df_filtrado["lead_time_dias"] = (df_filtrado["fecha derivado"] - df_filtrado["fecha_solicitud"]).dt.days

# Filtramos valores negativos o nulos (errores de data entry)
df_lead = df_filtrado[df_filtrado["lead_time_dias"] >= 0].copy()

col_lt1, col_lt2 = st.columns([1, 2])

with col_lt1:
    avg_lead_time = df_lead["lead_time_dias"].mean()
    max_lead_time = df_lead["lead_time_dias"].max()
    
    st.metric(
        label="⏳ Lead Time Promedio", 
        value=f"{avg_lead_time:.1f} días",
        delta=f"Máx: {max_lead_time:.0f} días",
        delta_color="inverse",
        help="Días promedio desde la creación de la FSC hasta su asignación/derivación."
    )
    
    # Análisis por Tipo de Proceso
    lt_proceso = df_lead.groupby("ProcesoCompra")["lead_time_dias"].mean().sort_values()
    st.write("**Promedio por Proceso:**")
    st.dataframe(lt_proceso.apply(lambda x: f"{x:.1f} días"), use_container_width=True)

with col_lt2:
    # Gráfico de dispersión para ver la variabilidad (Lean busca reducir variabilidad)
    fig_lt = px.scatter(
        df_lead,
        x="fecha_solicitud",
        y="lead_time_dias",
        color="comprador",
        size="monto estimado",
        title="Variabilidad del Lead Time en el Tiempo",
        labels={"lead_time_dias": "Días de Espera", "fecha_solicitud": "Fecha de Solicitud"},
        hover_data=["newiD", "requerimiento"],
        template="plotly_white"
    )
    
    # Añadimos una línea de meta (ej: 3 días)
    fig_lt.add_hline(y=3, line_dash="dash", line_color="green", annotation_text="Meta Lean (3 días)")
    
    fig_lt.update_layout(height=400)
    st.plotly_chart(fig_lt, use_container_width=True)

# 2. Análisis por Comprador (Boxplot - Distribución)
st.markdown("### 📊 Distribución de Tiempos por Comprador")
fig_box = px.box(
    df_lead,
    x="comprador",
    y="lead_time_dias",
    color="comprador",
    title="Análisis de Consistencia (Eliminación de Mura - Desequilibrio)",
    labels={"lead_time_dias": "Días de Espera", "comprador": "Comprador"},
    points="all" # Muestra todos los puntos para ver valores atípicos
)
fig_box.update_layout(height=400, showlegend=False)
st.plotly_chart(fig_box, use_container_width=True)


# ==========================================================
# 📊 MÓDULO DE EFICIENCIA LEAN & OKRs (ESTADO DE PROCESOS)
# ==========================================================
st.markdown("---")
st.markdown("## 🎯 Objetivos y Resultados Clave (OKR)")

# 1. Procesamiento de Estados
df_lean = df_filtrado.copy()
df_lean["Estado_Simplificado"] = df_lean["EstadoProcesoCompra"].apply(
    lambda x: "Finalizado" if "Finalizado" in str(x) else "En Tramitación"
)

# 2. Cálculo de Métricas Actionables
total = len(df_lean)
finalizados = len(df_lean[df_lean["Estado_Simplificado"] == "Finalizado"])
en_tramitacion = total - finalizados

# Tasa de Finalización (Métrica de Eficiencia)
tasa_finalizacion = (finalizados / total * 100) if total > 0 else 0

# Lead Time Promedio (Muda de Espera)
df_lean["fecha_solicitud"] = pd.to_datetime(df_lean["fecha_solicitud"], errors='coerce')
df_lean["fecha derivado"] = pd.to_datetime(df_lean["fecha derivado"], errors='coerce')
df_lean["lead_time"] = (df_lean["fecha derivado"] - df_lean["fecha_solicitud"]).dt.days
avg_lead_time = df_lean[df_lean["lead_time"] >= 0]["lead_time"].mean()

# KPIs Superiores
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("✅ Tasa de Finalización", f"{tasa_finalizacion:.1f}%", help="OKR: Meta > 80%")
with c2:
    st.metric("📦 WIP (En Tramitación)", f"{en_tramitacion}", delta="Muda de Inventario", delta_color="inverse")
with c3:
    st.metric("⏱️ Lead Time Promedio", f"{avg_lead_time:.1f} días", help="Tiempo desde solicitud a derivación")
with c4:
    # Throughput (Finalizados este mes - asumiendo fecha derivado como fin)
    throughput = finalizados # Simplificado para el set de datos
    st.metric("🚀 Throughput", f"{throughput}", help="Procesos que generaron valor")

# ==========================================================
# 📈 VISUALIZACIÓN DE FLUJO Y CUELLOS DE BOTELLA
# ==========================================================
col_a, col_b = st.columns(2)

with col_a:
    # Eficiencia de Conversión por Comprador
    eficiencia_comprador = df_lean.groupby("comprador")["Estado_Simplificado"].value_counts(normalize=True).unstack().fillna(0)
    if "Finalizado" in eficiencia_comprador.columns:
        eficiencia_comprador = eficiencia_comprador["Finalizado"].sort_values(ascending=False).reset_index()
        eficiencia_comprador.columns = ["Comprador", "Tasa de Cierre"]
        
        fig_conv = px.bar(
            eficiencia_comprador, x="Comprador", y="Tasa de Cierre",
            title="🎯 Eficiencia de Conversión por Comprador",
            labels={"Tasa de Cierre": "% Finalizados"},
            color="Tasa de Cierre", color_continuous_scale="RdYlGn"
        )
        st.plotly_chart(fig_conv, use_container_width=True)

with col_b:
    # Análisis de Estancamiento (Bottlenecks)
    # Definimos estancamiento como procesos en tramitación con días > promedio
    threshold = avg_lead_time if not np.isnan(avg_lead_time) else 5
    stancados = df_lean[
        (df_lean["Estado_Simplificado"] == "En Tramitación") & 
        (df_lean["lead_time"] > threshold)
    ]
    
    fig_bottleneck = px.histogram(
        stancados, x="comprador", title="⚠️ Alerta Jidoka: Procesos Estancados",
        labels={"comprador": "Comprador", "count": "Casos Críticos"},
        color_discrete_sequence=['#EF553B']
    )
    st.plotly_chart(fig_bottleneck, use_container_width=True)