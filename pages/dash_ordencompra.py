import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os
from style.ui import cargar_css

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================
st.set_page_config(page_title="Dashboard Orden de Compra", layout="wide")

# Aumentar el límite de celdas para el Styler
pd.set_option("styler.render.max_elements", 500000)

import api.OC_data_loader as loader_oc
cargar_css()
# ==========================================
# 0. FUNCIONES DE APOYO (LOGICA PAC)
# ==========================================

@st.cache_data(ttl=3600)
def load_pac_master():
    """Carga el archivo maestro consolidado generado previamente."""
    file_path = os.path.join("data", "data_pac", "OCPAC_Maestro.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path, dtype={"OC Asociada PAC": str, "ID Proyecto": str})
    return pd.DataFrame(columns=["ID Proyecto", "OC Asociada PAC"])

def enriquecer_datos_con_pac(df_principal, df_maestro):
    """Cruce vectorizado Paso A y B para identificar OCs en el plan."""
    df = df_principal.copy()

    col_oc_compras = "CodigoOC"
    keys_compras = df[col_oc_compras].astype(str).str.strip().str.upper()

    if df_maestro.empty or "OC Asociada PAC" not in df_maestro.columns:
        df["PAC"] = "No Enlazada"
        return df

    maestro = df_maestro[["OC Asociada PAC", "ID Proyecto"]].copy()
    maestro["key_tmp"] = maestro["OC Asociada PAC"].astype(str).str.strip().str.upper()
    maestro = maestro.drop_duplicates(subset=["key_tmp"], keep="last")

    pac_set = set(maestro["key_tmp"].dropna().unique())
    df["PAC"] = np.where(keys_compras.isin(pac_set), "Enlazada", "No Enlazada")

    df = df.merge(
        maestro[["key_tmp", "ID Proyecto"]],
        left_on=keys_compras,
        right_on="key_tmp",
        how="left",
    ).drop(columns=["key_tmp"])

    return df

def generar_link_mp(codigo_oc):
    """Genera el link directo a la orden de compra en Mercado Público"""
    base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
    return f"{base_url}{codigo_oc}"

# ==========================================
# 1. CARGA DE DATOS (CACHÉ)
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Cargando Bases de Datos...") 
def obtener_todo():
    df_OCres, df_OCdet = loader_oc.cargar_maestros_oc()
    df_pac = load_pac_master()
    return df_OCres, df_OCdet, df_pac

@st.cache_data(ttl=3600, show_spinner=False)
def preprocesar_oc_resumen(df_raw_res: pd.DataFrame, df_pac_maestro: pd.DataFrame) -> pd.DataFrame:
    df = enriquecer_datos_con_pac(df_raw_res, df_pac_maestro)

    if "CodigoOC" in df.columns:
        df["CodigoOC"] = df["CodigoOC"].astype(str).str.strip()
        base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
        df["Link"] = base_url + df["CodigoOC"]

    cols_fecha = ["FechaCreacion", "FechaEnvio", "FechaAceptacion", "FechaCancelacion", "FechaUltimaModificacion"]
    for col in cols_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    if "FechaAceptacion" in df.columns and "FechaCreacion" in df.columns:
        df["LeadTime_Dias"] = (df["FechaAceptacion"] - df["FechaCreacion"]).dt.days
        df["LeadTime_Dias"] = df["LeadTime_Dias"].clip(lower=0)

    if "TipoOC" not in df.columns:
        df["TipoOC"] = "Desconocido"
    else:
        df["TipoOC"] = df["TipoOC"].fillna("Desconocido")

    if "FechaCreacion" in df.columns:
        df["Año"] = df["FechaCreacion"].dt.year
        df["Mes"] = df["FechaCreacion"].dt.to_period("M").dt.to_timestamp()

    return df

def aplicar_filtros(df: pd.DataFrame, pac_sel, estado_oc_sel, unidad_sel, contacto_sel, fechas_sel, anio_sel) -> pd.DataFrame:
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if pac_sel:
        mask &= df["PAC"].isin(pac_sel)
    if estado_oc_sel:
        mask &= df["EstadoOC"].isin(estado_oc_sel)
    if unidad_sel:
        mask &= df["C_Unidad"].isin(unidad_sel)
    if contacto_sel:
        mask &= df["C_Contacto"].isin(contacto_sel)
    if anio_sel:
        mask &= df["Año"].isin(anio_sel)
    if fechas_sel and len(fechas_sel) == 2 and "FechaCreacion" in df.columns:
        f0 = pd.to_datetime(fechas_sel[0])
        f1 = pd.to_datetime(fechas_sel[1]) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        mask &= df["FechaCreacion"].between(f0, f1)

    return df.loc[mask]

@st.cache_data(ttl=3600, show_spinner=False)
def agregar_productos_por_oc(df_oc_det: pd.DataFrame, ids_filtrados: tuple) -> pd.DataFrame:
    if df_oc_det.empty or not ids_filtrados:
        return pd.DataFrame()

    df_productos_filtrados = df_oc_det[df_oc_det["CodigoOC"].isin(ids_filtrados)]
    if df_productos_filtrados.empty:
        return pd.DataFrame()

    prod_agg = (
        df_productos_filtrados.groupby("Producto", dropna=False)
        .agg({
            "Cantidad": "sum",
            "PrecioNeto": "mean",
            "CodigoOC": "nunique",
        })
        .reset_index()
        .rename(columns={"CodigoOC": "Frecuencia_OC"})
    )

    prod_agg["Monto_Estimado"] = prod_agg["Cantidad"] * prod_agg["PrecioNeto"]
    prod_agg = prod_agg.sort_values("Monto_Estimado", ascending=False)
    return prod_agg

# Ejecución de carga
try:
    df_raw_res, df_oc_det, df_pac_maestro = obtener_todo()
    
    if df_raw_res.empty:
        st.warning("⚠️ No se encontraron datos de Órdenes de Compra.")
        st.stop()

    # --- PROCESAMIENTO INICIAL ---
    df_oc_res = preprocesar_oc_resumen(df_raw_res, df_pac_maestro)

except Exception as e:
    st.error(f"❌ Error al cargar datos: {e}")
    st.stop()


# =============================================================================
# HEADER
# =============================================================================

st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">🧾 Tablero Ordenes de Compra</div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">Análisis de Flujo, Variabilidad y Eficiencia PAC</div>
    </div>
    """, unsafe_allow_html=True
)
# ==========================================================
# 4. PREPARACIÓN DE DATOS
# ==========================================================
opciones_anio = sorted(df_oc_res["Año"].dropna().unique()) if "Año" in df_oc_res.columns else []
# ==========================================================
# 3. FILTROS EN CASCADA
# ==========================================================
# 1. Creamos una copia para la lógica de cascada (opciones dinámicas)
df_cascada = df_oc_res

# Creamos 5 columnas para que quepa todo el flujo
c1, c2, c3, c4, c5, c6 = st.columns(6)

# --- FILTRO 1: ESTADO PAC (PRIORITARIO) ---
with c1:
    opciones_pac = ["Enlazada", "No Enlazada"]
    pac_sel = st.multiselect("📌 Filtro PAC", opciones_pac, placeholder="Todos")

if pac_sel:
    df_cascada = df_cascada[df_cascada["PAC"].isin(pac_sel)]

# --- FILTRO 2: ESTADO OC ---
opciones_estado = sorted(df_cascada["EstadoOC"].dropna().unique())
with c2:
    estado_oc_sel = st.multiselect("📝 Estado OC", opciones_estado, placeholder="Todos")

if estado_oc_sel:
    df_cascada = df_cascada[df_cascada["EstadoOC"].isin(estado_oc_sel)]

# --- FILTRO 3: UNIDAD ---
opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
with c3:
    unidad_sel = st.multiselect("🏢 Unidad de Compra", opciones_unidad, placeholder="Todas")

if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# --- FILTRO 4: CONTACTO ---
opciones_contacto = sorted(df_cascada["C_Contacto"].dropna().unique())
with c4:
    contacto_sel = st.multiselect("👤 Contacto", opciones_contacto, placeholder="Todos")

if contacto_sel:
    df_cascada = df_cascada[df_cascada["C_Contacto"].isin(contacto_sel)]

# --- FILTRO 5: FECHA ---
with c5:
    f_min = df_oc_res['FechaCreacion'].min()
    f_max = df_oc_res['FechaCreacion'].max()
    fechas_sel = st.date_input("📅 Periodo", [f_min, f_max])

# ---- Filtro de Año ----
with c6:
    anio_sel = st.multiselect("📆 Año", opciones_anio, placeholder="Seleccione")
    if anio_sel:
        df_cascada = df_cascada[df_cascada["Año"].isin(anio_sel)]
    
# ==========================================================
# APLICACIÓN FINAL AL DATAFRAME DE TRABAJO
# ==========================================================
df_filtrado = aplicar_filtros(
    df_oc_res,
    pac_sel,
    estado_oc_sel,
    unidad_sel,
    contacto_sel,
    fechas_sel,
    anio_sel,
)

# ==========================================================
# 4. KPIS LEAN Y OKRS (CON DESCRIPCIONES)
# ==========================================================
st.markdown("## 🎯 Métricas de Rendimiento (OKRs)")
c_kpi1, c_kpi2, c_kpi3, c_kpi4, c_kpi5, c_kpi6 = st.columns(6)

with c_kpi1:
    total_count = len(df_filtrado)
    st.metric(
        "📦 Volumen Total", 
        f"{total_count:,}",
        help="Cantidad total de órdenes de compra procesadas según los filtros seleccionados (Output total)."
    )

with c_kpi2:
    monto_total = df_filtrado['TotalBruto'].sum()
    st.metric(
        "💰 Valor Gestionado", 
        f"${monto_total:,.0f}",
        help="Suma total del monto bruto transaccionado. Representa el flujo financiero gestionado en el periodo."
    )

with c_kpi3:
    avg_lt = df_filtrado['LeadTime_Dias'].mean()
    val_lt = f"{avg_lt:.1f} días" if not pd.isna(avg_lt) else "N/A"
    st.metric(
        "⏱️ Lead Time", 
        val_lt,
        help="Promedio de días transcurridos desde la creación de la OC hasta su aceptación por el proveedor (Velocidad de Flujo)."
    )

with c_kpi4:
    ok_count = len(df_filtrado[df_filtrado['EstadoOC'].str.contains('Aceptada|Recepcionada', case=False, na=False)])
    efficiency = (ok_count / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
    st.metric(
        "✅ Tasa Flujo", 
        f"{efficiency:.1f}%",
        help="Porcentaje de órdenes que terminaron con éxito (Aceptada/Recepcionada) vs el total creado (Calidad del proceso)."
    )

with c_kpi5:
    # KPI ADHERENCIA PAC
    enlazadas = len(df_filtrado[df_filtrado["PAC"] == "Enlazada"])
    adherencia = (enlazadas / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
    st.metric(
        "📊 Adherencia PAC", 
        f"{adherencia:.1f}%", 
        help="Nivel de cumplimiento del Plan Anual. Indica el % de órdenes que cuentan con un ID de proyecto válido en el maestro consolidado."
    )

with c_kpi6:
    # KPI DESVIACIÓN
    no_plan = len(df_filtrado[df_filtrado["PAC"] == "No Enlazada"])
    st.metric(
        "🚫 Fuera de Plan", 
        f"{no_plan}", 
        delta_color="inverse", 
        help="Conteo de órdenes de compra generadas que no fueron planificadas o no tienen asociación correcta al PAC."
    )

st.markdown("## 📋 Detalles de Orden de Compra")
# Pestañas para organizar la visualización
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9  = st.tabs(["🛒 Plan de Compras", "⏳ Estado Orden de Compra","🗃️ Unidad de Compras", "💼 Gestión de Compra", "📦 Productos","🚚 Recepciones", "👥 Proveedores", "🏭 Proveedores", "📊 Métricas Lean"])

with tab1:
    # =============================================================================
    # 1. PREPARACIÓN DE DATOS
    # =============================================================================
    if "PAC" not in df_filtrado.columns and "En_PAC_2026" in df_filtrado.columns:
        df_filtrado["PAC"] = np.where(
            df_filtrado["En_PAC_2026"].isin([1, "1", "Si", "SI", "si", True]),
            "Enlazada",
            "No Enlazada",
        )

    # Mapeo de meses en español para todos los ejes X
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    def format_esp_mes(fecha):
        return f"{meses_es[fecha.month-1]} {fecha.year}"
    # Paleta de colores corporativa/profesional
    COLOR_ENLAZADA = "#2ECC71"  # Verde
    COLOR_NO_ENLAZADA = "#E74C3C" # Rojo
    COLOR_DISCRETE_MAP = {"Enlazada": COLOR_ENLAZADA, "No Enlazada": COLOR_NO_ENLAZADA}

    st.markdown("### 📊 Tablero de Control: Rendimiento del Plan de Compras")

    # =============================================================================
    # 2. INDICADORES CLAVE (KPIs) - TAREA 1, 2 y 3
    # =============================================================================
    # Cálculos
    total_ocs = len(df_filtrado)
    monto_total = df_filtrado["TotalBruto"].sum()
    ocs_enlazadas = df_filtrado[df_filtrado["PAC"] == "Enlazada"]
    num_enlazadas = len(ocs_enlazadas)
    monto_enlazado = ocs_enlazadas["TotalBruto"].sum()

    # Porcentajes
    perc_cant_enlazada = (num_enlazadas / total_ocs * 100) if total_ocs > 0 else 0
    perc_monto_enlazado = (monto_enlazado / monto_total * 100) if monto_total > 0 else 0

    # Despliegue de métricas en 4 columnas
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("Total Órdenes", f"{total_ocs:,.0f}")
    with kpi2:
        st.metric("Monto Total ($)", f"${monto_total:,.0f}")
    with kpi3:
        st.metric("% OCs Enlazadas (Cant.)", f"{perc_cant_enlazada:.1f}%", 
                help="Porcentaje de órdenes vinculadas al PAC respecto al conteo total")
    with kpi4:
        st.metric("% Monto Planificado", f"{perc_monto_enlazado:.1f}%",
                help="Porcentaje del dinero gastado que estaba planificado en el PAC")
    st.divider()

    # =============================================================================
    # 3. ANÁLISIS ESTADÍSTICO INTEGRAL (General + Anual)
    # =============================================================================
    with st.expander("📈 Ver Estadísticas Descriptivas y Evolución Anual"):
        
        # --- SECCIÓN 1: RESUMEN GENERAL ---
        st.markdown("##### 📊 Resumen General por Estado")
        st.write("Métricas financieras totales comparando compras planificadas vs no planificadas:")
        
        # Agrupación por Estado PAC
        stats_pac = df_filtrado.groupby("PAC")["TotalBruto"].agg(
            Conteo='count',
            Total='sum',
        ).reset_index()
        
        st.dataframe(
            stats_pac,
            column_config={
                "Total": st.column_config.NumberColumn(format="$ %.2f"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # --- SECCIÓN 2: EVOLUCIÓN ANUAL ---
        st.markdown("##### 📅 Comparativa de Gestión por Año")
        
        # Preparación de datos anuales
        stats_anual = df_filtrado.groupby(["Año", "PAC"])["TotalBruto"].agg(
            Conteo='count',
            Monto_Total='sum'
        ).reset_index()

        # Cálculo del % de enlace
        total_por_año = df_filtrado.groupby("Año").size().reset_index(name="Total_OCs")
        stats_anual = stats_anual.merge(total_por_año, on="Año")
        stats_anual["% Presencia"] = (stats_anual["Conteo"] / stats_anual["Total_OCs"]) * 100
        
        # Función para aplicar colores (Verde/Rojo)
        def color_pac(val):
            color = '#d4edda' if val == "Enlazada" else '#f8d7da' # Verde claro / Rojo claro
            return f'background-color: {color}'

        # Visualización con formato condicional
        st.dataframe(
            stats_anual.style.applymap(color_pac, subset=['PAC']).format({
                "Monto_Total": "${:,.0f}",
                "% Presencia": "{:.1f}%"
            }),
            use_container_width=True,
            hide_index=True
        )
    
    # =============================================================================
    # 4. VISUALIZACIONES GRÁFICAS - TAREA 5
    # =============================================================================
    st.write("### 🏆 Rendimiento y Evolución del Plan (PAC)")
    # Fila superior de gráficos
    row1_col1, row1_col2= st.columns(2)

    # --- GRÁFICO 1: EVOLUCIÓN TEMPORAL (LÍNEAS) ---
    with row1_col1:
        fig_evolucion = px.bar(
            stats_anual, 
            x="Año", 
            y="Conteo", 
            color="PAC",
            barmode="group",
            text_auto=True,
            title="Cant. OCs: Enlazadas vs No Enlazadas",
            color_discrete_map={"Enlazada": "#2ECC71", "No Enlazada": "#E74C3C"}
        )
        fig_evolucion.update_layout(
            xaxis_type='category',
            legend_title=None,
            yaxis_title="Cantidad de Órdenes",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400
        )    
        st.plotly_chart(fig_evolucion, use_container_width=True)
      

    # --- GRÁFICO 2: DISTRIBUCIÓN POR UNIDAD (PIE/DONUT) ---
    with row1_col2:
        df_solo_enlazadas = stats_anual[stats_anual["PAC"] == "Enlazada"]
        
        if not df_solo_enlazadas.empty:
            fig_tendencia = px.line(
                df_solo_enlazadas, 
                x="Año", 
                y="% Presencia",
                title="📈 Tendencia de Efectividad del PAC (% de Enlace)",
                markers=True
            )
            fig_tendencia.update_traces(line_color='#2ECC71', line_width=4)
            fig_tendencia.update_layout(
                yaxis=dict(
                    ticksuffix="%", 
                    range=[0, 100],
                )
            )
            st.plotly_chart(fig_tendencia, use_container_width=True)   
  

    # Agrupamos por Mes y Estado PAC
    df_linea = df_filtrado.groupby(["Mes", "PAC"]).size().reset_index(name="Cantidad")
    
    fig_line = px.line(
        df_linea, 
        x="Mes", 
        y="Cantidad", 
        color="PAC",
        color_discrete_map=COLOR_DISCRETE_MAP,
        markers=True
    )
    fig_line.update_layout(
        xaxis_title=None, 
        yaxis_title="Nº de Órdenes",
        legend_title=None,
        height=350,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # =============================================================================
    # 1. PREPARACIÓN DE DATOS (GLOBAL)
    # =============================================================================
    st.divider()

    # Columnas de tiempo ya vienen preparadas en preprocesar_oc_resumen

    # Configuración Visual
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    COLOR_MAP = {"Enlazada": "#2ECC71", "No Enlazada": "#E74C3C"}

    # =============================================================================
    # FILA 1: ANÁLISIS DE CANTIDAD (VOLUMEN DE ÓRDENES)
    # Izquierda: Evolución Mensual | Derecha: % Anual
    # =============================================================================
    st.markdown("##### 📦 Análisis por Volumen de Órdenes")
    r1_col1, r1_col2 = st.columns(2)

    # --- GRÁFICO 1.1 (IZQ): Evolución Mensual (Original) ---
    with r1_col1:
        df_mes_pac = df_filtrado.groupby(["Mes", "PAC"]).size().reset_index(name="Cant")
        
        fig_q = px.bar(df_mes_pac, x="Mes", y="Cant", color="PAC", 
                    title="Evolución Mensual de OCs",
                    color_discrete_map=COLOR_MAP)
        
        # Formateo eje X en español
        if not df_mes_pac.empty:
            fig_q.update_layout(xaxis=dict(
                tickvals=df_mes_pac["Mes"].unique(),
                ticktext=[meses_es[m.month-1] + f" {m.year}" for m in df_mes_pac["Mes"].unique()]
            ))
        st.plotly_chart(fig_q, use_container_width=True)

    # --- GRÁFICO 1.2 (DER): Porcentaje Anual (Nuevo) ---
    with r1_col2:
        # Calculamos % de cantidad
        df_anual_qty = df_filtrado.groupby(["Año", "PAC"]).size().reset_index(name="Cant")
        # Calculamos el total por año para sacar el %
        df_anual_qty["Total_Año"] = df_anual_qty.groupby("Año")["Cant"].transform("sum")
        df_anual_qty["Porcentaje"] = df_anual_qty["Cant"] / df_anual_qty["Total_Año"]

        fig_q_pct = px.bar(df_anual_qty, x="Año", y="Porcentaje", color="PAC",
                        title="Distribución % Anual (Por Cantidad)",
                        text_auto='.1%', # Formato automático de porcentaje
                        color_discrete_map=COLOR_MAP)
        
        fig_q_pct.update_layout(
            xaxis_type='category', 
            yaxis_tickformat=".0%", 
            yaxis_title="% del Total"
        )
        st.plotly_chart(fig_q_pct, use_container_width=True)


    # =============================================================================
    # FILA 2: ANÁLISIS FINANCIERO (MONTOS)
    # Izquierda: Evolución Mensual | Derecha: % Anual
    # =============================================================================
    st.divider()
    st.markdown("##### 💰 Análisis por Montos de Inversión")
    r2_col1, r2_col2 = st.columns(2)

    # --- GRÁFICO 2.1 (IZQ): Evolución Mensual (Original) ---
    with r2_col1:
        df_monto_pac = df_filtrado.groupby(["Mes", "PAC"])["TotalBruto"].sum().reset_index()
        
        fig_m = px.area(df_monto_pac, x="Mes", y="TotalBruto", color="PAC", 
                        title="Inversión Mensual ($)",
                        color_discrete_map=COLOR_MAP)
        
        if not df_monto_pac.empty:
            fig_m.update_layout(
                yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                xaxis=dict(
                    tickvals=df_monto_pac["Mes"].unique(),
                    ticktext=[meses_es[m.month-1] + f" {m.year}" for m in df_monto_pac["Mes"].unique()]
                )
            )
        st.plotly_chart(fig_m, use_container_width=True)

    # --- GRÁFICO 2.2 (DER): Porcentaje Anual (Nuevo) ---
    with r2_col2:
        # Calculamos % de montos
        df_anual_monto = df_filtrado.groupby(["Año", "PAC"])["TotalBruto"].sum().reset_index()
        df_anual_monto["Total_Año"] = df_anual_monto.groupby("Año")["TotalBruto"].transform("sum")
        df_anual_monto["Porcentaje"] = df_anual_monto["TotalBruto"] / df_anual_monto["Total_Año"]

        fig_m_pct = px.bar(df_anual_monto, x="Año", y="Porcentaje", color="PAC",
                        title="Distribución % Anual (Por Montos)",
                        text_auto='.1%',
                        color_discrete_map=COLOR_MAP)
        
        fig_m_pct.update_layout(
            xaxis_type='category', 
            yaxis_tickformat=".0%",
            yaxis_title="% de Inversión"
        )
        st.plotly_chart(fig_m_pct, use_container_width=True)

    st.divider()
    # =============================================================================
    # 5. TABLA MAESTRA CON FORMATO CONDICIONAL
    # =============================================================================
    def style_pac_rows(row):
        # Aplicamos verde si está enlazado, rojo si no.
        color = 'background-color: rgba(46, 204, 113, 0.2)' if row['PAC'] == 'Enlazada' else 'background-color: rgba(231, 76, 60, 0.2)'
        return [color] * len(row)

    st.markdown("### 🛒 Órdenes de Compra Consolidadas")
    st.markdown("Listado de Órdenes de Compra filtradas por los proyectos seleccionados arriba.")

    # 1. Input de búsqueda
    texto_busqueda = st.text_input(
        "🔍 Buscar en Órdenes de Compra:", 
        placeholder="Escribe código, nombre, proyecto o estado...",
        help="Filtra automáticamente las filas que coincidan con el texto en cualquier columna."
    )

    cols_oc_view = ["Link", "PAC", "CodigoOC", "EstadoOC", "NombreOC", "FechaAceptacion", "TotalBruto", "ID Proyecto","CodigoLicitacion"]
       # Verificamos que existan las columnas antes de mostrar
    cols_existentes = [c for c in cols_oc_view if c in df_filtrado.columns]
    # Creamos una copia para no alterar el dataframe original
    df_display = df_filtrado[cols_existentes].copy()

    # 3. Lógica del Filtro
    if texto_busqueda:
        cols_busqueda = [c for c in df_display.columns if c != "Link"]
        search_blob = df_display[cols_busqueda].astype(str).agg(" | ".join, axis=1)
        df_display = df_display[search_blob.str.contains(texto_busqueda, case=False, na=False, regex=False)]

    # 4. Mostrar Tabla (Solo si hay datos tras la búsqueda) 
    if df_display.empty:
        st.warning(f"No se encontraron resultados para '{texto_busqueda}'")
    else:
        st.markdown(f"Mostrando **{len(df_display)}** registros encontrados.")
        st.dataframe(
            df_display.style.apply(style_pac_rows, axis=1).format({
                    "TotalBruto": "${:,.0f}",
                }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "FechaAceptacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
                "Link": st.column_config.LinkColumn(
                    "Link MercadoPúblico", 
                    display_text="🔗 Abrir OC"
                )
            }
        )
    st.divider()
    
with tab2:
    # ================================== GRAFICOS ===============================================
    # ##### GRAFICOS OC CON MESES EN ESPAÑOL ####
    st.markdown("### 📊 Análisis Gráfico de Órdenes de Compra")

    # Columnas de tiempo ya vienen preparadas en preprocesar_oc_resumen

    # Diccionario para traducir (Opcional, pero para el eje X usaremos tickformat y ticklabel)
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    col1, col2 = st.columns(2)

    # ======================================
    # 📊 A) Cantidad de OC por Mes
    # ======================================
    with col1:
        conteo_mes_oc = (
            df_filtrado
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
        monto_mes_oc = (
            df_filtrado
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
    
with tab3:
    pass

with tab4:
    # ==========================================================
    # 6. ANÁLISIS GRÁFICO LEAN
    # ==========================================================

    # --- FILA 1: FLUJO Y VARIABILIDAD ---
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # 1. EVOLUCIÓN TEMPORAL (Estabilidad del Flujo)
        # Agrupamos por mes para ver tendencias
        periodo = df_filtrado["FechaCreacion"].dt.strftime("%Y-%m")
        evo_mensual = (
            df_filtrado.assign(Periodo=periodo)
            .groupby(["Periodo", "TipoOC"])["TotalBruto"]
            .count()
            .reset_index(name="Cantidad")
        )
        
        fig_evo = px.bar(
            evo_mensual, x='Periodo', y='Cantidad', color='TipoOC',
            title="📈 Evolución del Flujo de Trabajo (Heijunka)",
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
            points="outliers" # Muestra los casos extremos (anomalías)
        )
        fig_box.update_layout(xaxis_title="Tipo de Compra", yaxis_title="Días de Gestión", template="plotly_white")
        st.plotly_chart(fig_box, use_container_width=True)

with tab5:
    # ==========================================================
    # 7. DETALLE DE PRODUCTOS (DRILL-DOWN)
    # ==========================================================
    st.markdown("### 🔍 Detalle de Productos (Gemba)")

    # Filtramos la tabla de detalle usando los IDs de las OCs filtradas
    ids_filtrados = tuple(sorted(df_filtrado["CodigoOC"].dropna().astype(str).unique()))
    prod_agg = agregar_productos_por_oc(df_oc_det, ids_filtrados)

    if not prod_agg.empty:
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

with tab6:
    pass

with tab7:
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

with tab8:
   pass

with tab9:
 # ==========================================================
    # ⏱️ MÓDULO: ANÁLISIS DE CICLO DE VIDA (LEAN VSM)
    # ==========================================================
    st.markdown("### ⏱️ Análisis de Tiempos de Ciclo (Value Stream)")

    # 1. Preparación de Datos de Tiempos
    df_tiempos = df_filtrado.copy()

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
    df_tiempos[cols_tiempos] = df_tiempos[cols_tiempos].mask(df_tiempos[cols_tiempos] < 0)

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




