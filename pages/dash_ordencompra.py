import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os

# Aumentar el límite de celdas para el Styler
pd.set_option("styler.render.max_elements", 500000)

import api.OC_data_loader as loader_oc

# ==========================================
# CARGA DE DATOS OPTIMIZADA (CACHÉ)
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Cargando Base de Datos de Compras...") 
def obtener_datos_oc():
    df_OCres, df_OCdet = loader_oc.cargar_maestros_oc()
    return df_OCres, df_OCdet

# ==========================================
# EJECUCIÓN EN EL DASHBOARD
# ==========================================
try:
    # 1. Llamada a la función con caché (OCs)
    df_MaestroOC_Resumen, df_MaestroOC_Detalle = obtener_datos_oc()

    # ### NUEVO: CARGAR Y CRUZAR PAC 2026 ###
    # Cargamos el PAC desde caché    
    if not df_MaestroOC_Resumen.empty:
        st.success(f"✅ Datos cargados: {len(df_MaestroOC_Resumen)} OCs. Validación PAC 2026 aplicada.")
    else:
        st.warning("⚠️ No se encontraron datos de Órdenes de Compra.")

except Exception as e:
    st.error(f"❌ Ocurrió un error al cargar los datos: {e}")

# ==========================================================
# 1. PREPROCESAMIENTO LEAN (CALCULOS DE CICLO)
# ==========================================================
df_oc_res = df_MaestroOC_Resumen.copy()
df_oc_det = df_MaestroOC_Detalle.copy()

# A. Normalización de Tipos de Datos
cols_fecha = ['FechaCreacion', 'FechaEnvio', 'FechaAceptacion', 'FechaCancelacion']
for col in cols_fecha:
    if col in df_oc_res.columns:
        df_oc_res[col] = pd.to_datetime(df_oc_res[col], errors='coerce')

# B. Imputación Dinámica de TipoOC (Evitar vacíos en gráficos)
if 'TipoOC' in df_oc_res.columns:
    df_oc_res['TipoOC'] = df_oc_res['TipoOC'].fillna('Desconocido')
    # Normalización simple de texto
    df_oc_res['TipoOC'] = df_oc_res['TipoOC'].astype(str).str.strip()
else:
    df_oc_res['TipoOC'] = "Desconocido"

# C. Cálculo de Lead Time (Velocidad del Flujo)
# Tiempo desde Creación hasta Aceptación (Ciclo de Aprobación)
df_oc_res['LeadTime_Dias'] = (df_oc_res['FechaAceptacion'] - df_oc_res['FechaCreacion']).dt.days

# Limpieza de valores negativos o errores
df_oc_res['LeadTime_Dias'] = df_oc_res['LeadTime_Dias'].apply(lambda x: x if x >= 0 else np.nan)

# ==========================================================
# 2. CONFIGURACIÓN INICIAL
# ==========================================================

# ----- Cargar CSS -----
def cargar_css():
    try:
        with open("style/style.css") as f:
            css_content = f.read().replace("\n", "").strip()
            st.markdown(
                f"<style>{css_content}</style>",
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")
cargar_css()

# ==========================================================
# 3. HEADER
# ==========================================================
st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">🧾 Tablero Lean de Adquisiciones</div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">Análisis de Flujo, Variabilidad y Eficiencia de Compras</div>
    </div>
    """, unsafe_allow_html=True
)
# ==========================================================
# 4. FILTROS EN CASCADA
# ==========================================================
for col in ["EstadoOC", "C_Unidad", "C_Contacto"]:
    df_oc_res[col] = df_oc_res[col].astype(str).str.strip()

col1, col2, col3, col4  = st.columns(4)
df_cascada = df_oc_res.copy()

# 1. Estado
opciones_estado = sorted(df_cascada["EstadoOC"].dropna().unique())
with col1:
    estado_oc_sel = st.multiselect("📌 Estado OC", opciones_estado, placeholder="Todos")
if estado_oc_sel:
    df_cascada = df_cascada[df_cascada["EstadoOC"].isin(estado_oc_sel)]

# 2. Unidad (Filtrado por selección anterior)
opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
with col2:
    unidad_sel = st.multiselect("🏢 Unidad", opciones_unidad, placeholder="Todas")
if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# 3. Contacto (Filtrado por selección anterior)
opciones_contacto = sorted(df_cascada["C_Contacto"].dropna().unique())
with col3:
    contacto_sel = st.multiselect("👤 Contacto (Comprador)", opciones_contacto, placeholder="Todos")

# 4. Rango de Fechas (Nuevo Filtro Temporal)
with col4:
    fecha_min = df_oc_res['FechaCreacion'].min()
    fecha_max = df_oc_res['FechaCreacion'].max()
    fechas_sel = st.date_input("📅 Periodo de Creación", [fecha_min, fecha_max])



# --- APLICAR FILTROS AL DATAFRAME FINAL ---
df_filtrado = df_oc_res.copy()

if estado_oc_sel:
    df_filtrado = df_filtrado[df_filtrado["EstadoOC"].isin(estado_oc_sel)]
if unidad_sel:
    df_filtrado = df_filtrado[df_filtrado["C_Unidad"].isin(unidad_sel)]
if contacto_sel:
    df_filtrado = df_filtrado[df_filtrado["C_Contacto"].isin(contacto_sel)]

if len(fechas_sel) == 2:
    df_filtrado = df_filtrado[
        (df_filtrado['FechaCreacion'].dt.date >= fechas_sel[0]) & 
        (df_filtrado['FechaCreacion'].dt.date <= fechas_sel[1])
    ]

# ==========================================================
# 5. KPIS LEAN Y OKRS
# ==========================================================

# Calculamos métricas PAC sobre los datos filtrados

st.markdown("## 🎯 Métricas de Rendimiento (OKRs)")
c_kpi1, c_kpi2, c_kpi3, c_kpi4, c_kpi5, c_kpi6 = st.columns(6)

with c_kpi1:
    total_oc_filt = len(df_filtrado)
    st.metric("📦 Volumen Total (Output)", f"{total_oc_filt:,}")

with c_kpi2:
    monto_filt = df_filtrado["TotalBruto"].sum()
    st.metric("💰 Valor Gestionado", f"${monto_filt:,.0f}")

with c_kpi3:
    # LEAD TIME PROMEDIO (Velocidad)
    avg_lead_time = df_filtrado['LeadTime_Dias'].mean()
    if pd.isna(avg_lead_time):
        val_lt = "N/A"
    else:
        val_lt = f"{avg_lead_time:.1f} días"
    st.metric("⏱️ Lead Time Promedio", val_lt, help="Tiempo promedio desde Creación hasta Aceptación")

with c_kpi4:
    # TASA DE EFICIENCIA (Calidad a la Primera)
    # Asumimos que "Aceptada" o "Recepcionada" es éxito, "Cancelada" es defecto
    ok_count = len(df_filtrado[df_filtrado['EstadoOC'].str.contains('Aceptada|Recepcionada', case=False, na=False)])
    efficiency = (ok_count / total_oc_filt * 100) if total_oc_filt > 0 else 0
    st.metric("✅ Tasa de Flujo Efectivo", f"{efficiency:.1f}%", help="% de Órdenes procesadas exitosamente")

with c_kpi5:
   pass

with c_kpi6:
    # NUEVO KPI DESVIACION
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

# ==========================================================

st.markdown("## 🛒 Órdenes de Compra Consolidadas")
with st.expander("📅 Ver Tabla Maestra de OCs"):
    # Agregamos las nuevas columnas a la visualización
    cols_to_show = ["Codigo", "En_PAC_2026", "ID_Proyecto_PAC", "EstadoOC", "TotalBruto", "FechaCreacion"]
    # Filtramos columnas que existan
    cols_existentes = [c for c in cols_to_show if c in df_filtrado.columns]
    
    st.dataframe(df_filtrado[cols_existentes].style.format({
        "TotalBruto": "${:,.0f}".format
    }), use_container_width=True)


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

# ==========================================================
# 6. ANÁLISIS GRÁFICO LEAN
# ==========================================================

# --- FILA 1: FLUJO Y VARIABILIDAD ---
col_g1, col_g2 = st.columns(2)

with col_g1:
    # 1. EVOLUCIÓN TEMPORAL (Estabilidad del Flujo)
    # Agrupamos por mes para ver tendencias
    df_filtrado['Periodo'] = df_filtrado['FechaCreacion'].dt.strftime('%Y-%m')
    evo_mensual = df_filtrado.groupby(['Periodo', 'TipoOC'])['TotalBruto'].count().reset_index(name='Cantidad')
    
    fig_evo = px.bar(
        evo_mensual, x='Periodo', y='Cantidad', color='TipoOC',
        title="📈 Evolución del Flujo de Trabajo (Heijunka)",
        #color_discrete_map=COLOR_MAP,
        barmode='stack'
    )
    fig_evo.update_layout(xaxis_title="Mes", yaxis_title="N° Órdenes", template="plotly_white")
    st.plotly_chart(fig_evo, use_container_width=True)

with col_g2:
    # 2. VARIABILIDAD DE TIEMPOS (Boxplot - Mura)
    # Esto muestra qué tipos de compra tienen tiempos impredecibles
    fig_box = px.box(
        df_filtrado, x='TipoOC', y='LeadTime_Dias', color='TipoOC',
        title="⏱️ Variabilidad de Tiempos de Ciclo (Mura)",
        #color_discrete_map=COLOR_MAP,
        points="outliers" # Muestra los casos extremos (anomalías)
    )
    fig_box.update_layout(xaxis_title="Tipo de Compra", yaxis_title="Días de Gestión", template="plotly_white")
    st.plotly_chart(fig_box, use_container_width=True)

# --- FILA 2: CARGA Y PROVEEDORES ---
col_g3, col_g4 = st.columns([2, 1])

with col_g3:
    # 3. CARGA DE TRABAJO POR COMPRADOR (Balanceo)
    carga_comprador = df_filtrado.groupby(['C_Contacto', 'TipoOC'])['TotalBruto'].count().reset_index(name='Cantidad')
    # Ordenar por volumen total
    order_buyer = carga_comprador.groupby('C_Contacto')['Cantidad'].sum().sort_values(ascending=False).index
    
    fig_buyer = px.bar(
        carga_comprador, x='C_Contacto', y='Cantidad', color='TipoOC',
        title="⚖️ Balance de Carga por Comprador",
        #color_discrete_map=COLOR_MAP,
        category_orders={'C_Contacto': list(order_buyer)},
        barmode='stack'
    )
    fig_buyer.update_layout(xaxis_tickangle=-45, template="plotly_white")
    st.plotly_chart(fig_buyer, use_container_width=True)

with col_g4:
    # 4. PARETO DE PROVEEDORES (Concentración)
    top_prov = df_filtrado.groupby('P_Nombre')['TotalBruto'].sum().reset_index()
    top_prov = top_prov.sort_values('TotalBruto', ascending=False).head(10)
    
    fig_pareto = px.bar(
        top_prov, y='P_Nombre', x='TotalBruto', orientation='h',
        title="🏭 Top 10 Proveedores (Valor)",
        text_auto='.2s'
    )
    fig_pareto.update_layout(yaxis_title="", template="plotly_white")
    st.plotly_chart(fig_pareto, use_container_width=True)

# ==========================================================
# 7. DETALLE DE PRODUCTOS (DRILL-DOWN)
# ==========================================================
st.markdown("## 🔍 Detalle de Productos (Gemba)")

# Filtramos la tabla de detalle usando los IDs de las OCs filtradas
ids_filtrados = df_filtrado['CodigoOC'].unique()
df_productos_filtrados = df_oc_det[df_oc_det['CodigoOC'].isin(ids_filtrados)]

if not df_productos_filtrados.empty:
    # Agregación por producto para ver qué es lo que más se compra en este filtro
    prod_agg = df_productos_filtrados.groupby('Producto').agg({
        'Cantidad': 'sum',
        'PrecioNeto': 'mean', # Precio promedio
        'CodigoOC': 'nunique' # En cuántas OCs aparece
    }).reset_index().rename(columns={'CodigoOC': 'Frecuencia_OC'})
    
    prod_agg['Monto_Estimado'] = prod_agg['Cantidad'] * prod_agg['PrecioNeto']
    prod_agg = prod_agg.sort_values('Monto_Estimado', ascending=False)

    col_tbl1, col_tbl2 = st.columns([2, 1])
    
    with col_tbl1:
        st.subheader("📦 Listado de Productos (Resumen)")
        st.dataframe(
            prod_agg[['Producto', 'Cantidad', 'PrecioNeto', 'Frecuencia_OC', 'Monto_Estimado']],
            use_container_width=True,
            hide_index=True
        )
    
    with col_tbl2:
        st.subheader("📊 Distribución de Costos")
        fig_prod = px.pie(prod_agg.head(10), values='Monto_Estimado', names='Producto', hole=0.4)
        fig_prod.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_prod, use_container_width=True)

else:
    st.info("No hay detalles de productos disponibles para la selección actual.")

# ==========================================================
# ⏱️ MÓDULO: ANÁLISIS DE CICLO DE VIDA (LEAN VSM)
# ==========================================================
st.markdown("---")
st.markdown("## ⏱️ Análisis de Tiempos de Ciclo (Value Stream)")

# 1. Preparación de Datos de Tiempos
df_tiempos = df_filtrado.copy()

# Conversión de fechas a datetime (aseguramos formato)
cols_fechas = ['FechaCreacion', 'FechaEnvio', 'FechaAceptacion', 'FechaUltimaModificacion']
for col in cols_fechas:
    if col in df_tiempos.columns:
        df_tiempos[col] = pd.to_datetime(df_tiempos[col], errors='coerce')

# 2. Cálculo de Deltas (Tiempos entre etapas)
# Etapa 1: Gestión Interna (Creación -> Envío)
df_tiempos['T_Gestion'] = (df_tiempos['FechaEnvio'] - df_tiempos['FechaCreacion']).dt.days

# Etapa 2: Respuesta Proveedor (Envío -> Aceptación)
df_tiempos['T_Proveedor'] = (df_tiempos['FechaAceptacion'] - df_tiempos['FechaEnvio']).dt.days

# Etapa 3: Entrega/Recepción (Aceptación -> Recepción Conforme)
# Usamos FechaUltimaModificacion como proxy de recepción si el estado es Recepción Conforme
df_tiempos['T_Entrega'] = np.where(
    df_tiempos['EstadoOC'].astype(str).str.contains("Recepción Conforme", case=False, na=False),
    (df_tiempos['FechaUltimaModificacion'] - df_tiempos['FechaAceptacion']).dt.days,
    np.nan
)

# Lead Time Total (Solo para casos cerrados exitosamente)
df_tiempos['LeadTime_Total'] = df_tiempos['T_Gestion'] + df_tiempos['T_Proveedor'] + df_tiempos['T_Entrega']

# Limpieza de valores negativos o errores lógicos
cols_tiempos = ['T_Gestion', 'T_Proveedor', 'T_Entrega', 'LeadTime_Total']
for col in cols_tiempos:
    df_tiempos[col] = df_tiempos[col].apply(lambda x: x if x >= 0 else np.nan)

# Filtramos solo los registros que tienen el ciclo completo para el análisis de "Recepción Conforme"
df_ciclo_completo = df_tiempos.dropna(subset=['LeadTime_Total'])

if not df_ciclo_completo.empty:
    # --- KPIs DE TIEMPO ---
    t_prom_total = df_ciclo_completo['LeadTime_Total'].mean()
    
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.metric("⏳ Lead Time Total", f"{t_prom_total:.1f} días", help="Promedio Creación -> Recepción Conforme")
    with col_t2:
        val = df_ciclo_completo['T_Gestion'].mean()
        st.metric("1️⃣ Gestión Interna", f"{val:.1f} días", help="Creación -> Envío")
    with col_t3:
        val = df_ciclo_completo['T_Proveedor'].mean()
        st.metric("2️⃣ Respuesta Prov.", f"{val:.1f} días", help="Envío -> Aceptación")
    with col_t4:
        val = df_ciclo_completo['T_Entrega'].mean()
        st.metric("3️⃣ Entrega/Recep.", f"{val:.1f} días", help="Aceptación -> Recepción Conforme")

    # --- GRÁFICOS DE ANÁLISIS DE FLUJO ---
    c_flow1, c_flow2 = st.columns([2, 1])
    
    with c_flow1:
        # Gráfico de Barras Apiladas: Desglose del Tiempo por Comprador
        # Esto permite ver en qué etapa se demora más cada comprador (Análisis de Cuello de Botella)
        df_melt = df_ciclo_completo.melt(
            id_vars=['C_Contacto'], 
            value_vars=['T_Gestion', 'T_Proveedor', 'T_Entrega'],
            var_name='Etapa', 
            value_name='Días'
        )
        # Renombramos para mejor visualización
        df_melt['Etapa'] = df_melt['Etapa'].map({
            'T_Gestion': '1. Gestión Interna',
            'T_Proveedor': '2. Aprobación Prov.',
            'T_Entrega': '3. Recepción'
        })
        
        fig_breakdown = px.bar(
            df_melt.groupby(['C_Contacto', 'Etapa'])['Días'].mean().reset_index(),
            x='C_Contacto', 
            y='Días', 
            color='Etapa',
            title="🔍 Desglose de Tiempos por Comprador (¿Dónde está la demora?)",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_breakdown.update_layout(template="plotly_white", xaxis_tickangle=-45)
        st.plotly_chart(fig_breakdown, use_container_width=True)
        
    with c_flow2:
        # Gráfico de Violín/Box: Distribución del Lead Time Total
        # Fundamental en Lean para ver la VARIABILIDAD (Mura)
        fig_var = px.box(
            df_ciclo_completo, 
            y='LeadTime_Total', 
            x='TipoOC',
            color='TipoOC',
            title="Variabilidad del Ciclo Total",
            #color_discrete_map=COLOR_MAP
        )
        fig_var.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_var, use_container_width=True)

    # --- MATRIZ DE RETRASOS (JIDOKA - ALERTA) ---
    with st.expander("🚨 Ver Órdenes con Lead Time Crítico (+30 días)"):
        criticos = df_ciclo_completo[df_ciclo_completo['LeadTime_Total'] > 30].sort_values('LeadTime_Total', ascending=False)
        st.dataframe(
            criticos[['CodigoOC', 'TipoOC', 'C_Contacto', 'P_Nombre', 'FechaCreacion', 'LeadTime_Total', 'TotalBruto']],
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("ℹ️ No hay suficientes datos con ciclo completo (Recepción Conforme) para calcular los tiempos detallados en el periodo seleccionado.")




st.markdown("---")
st.markdown("### 📋 Detalle de Compras y Cronograma de OC")

# Pestañas para organizar la visualización
tab1, tab2, tab3 = st.tabs(["🔍 Vista por Proyecto", "📅 Cronograma de Órdenes (Expandido)", "📊 Análisis de Costos"])

with tab1:
    pass

with tab2:
    pass

with tab3:
    pass