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
    
    # Normalización para asegurar el cruce (Paso A)
    # Ajusta 'CodigoOC' al nombre real de tu columna en el maestro de compras
    col_oc_compras = "CodigoOC" 
    
    # Creamos llaves limpias temporales
    keys_compras = df[col_oc_compras].astype(str).str.strip().str.upper()
    keys_pac = df_maestro["OC Asociada PAC"].astype(str).str.strip().str.upper()
    
    # Creación de columna indicadora (Paso B)
    df["PAC"] = "No Enlazada"
    mask = keys_compras.isin(keys_pac)
    df.loc[mask, "PAC"] = "Enlazada"
    
    # Traemos el ID Proyecto del maestro
    # Usamos merge sobre las llaves normalizadas
    df_maestro_clean = df_maestro.copy()
    df_maestro_clean["key_tmp"] = keys_pac
    
    df = df.merge(
        df_maestro_clean[["key_tmp", "ID Proyecto"]],
        left_on=keys_compras,
        right_on="key_tmp",
        how="left"
    ).drop(columns=["key_tmp"])
    
    return df

# ==========================================
# 1. CARGA DE DATOS (CACHÉ)
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Cargando Bases de Datos...") 
def obtener_todo():
    df_OCres, df_OCdet = loader_oc.cargar_maestros_oc()
    df_pac = load_pac_master()
    return df_OCres, df_OCdet, df_pac

# Ejecución de carga
try:
    df_raw_res, df_oc_det, df_pac_maestro = obtener_todo()
    
    if df_raw_res.empty:
        st.warning("⚠️ No se encontraron datos de Órdenes de Compra.")
        st.stop()

    # --- PROCESAMIENTO INICIAL ---
    df_oc_res = enriquecer_datos_con_pac(df_raw_res, df_pac_maestro)
    
    # Normalización de Fechas
    cols_fecha = ['FechaCreacion', 'FechaEnvio', 'FechaAceptacion', 'FechaCancelacion']
    for col in cols_fecha:
        if col in df_oc_res.columns:
            df_oc_res[col] = pd.to_datetime(df_oc_res[col], errors='coerce')

    # Lead Time y Limpieza
    df_oc_res['LeadTime_Dias'] = (df_oc_res['FechaAceptacion'] - df_oc_res['FechaCreacion']).dt.days
    df_oc_res['LeadTime_Dias'] = df_oc_res['LeadTime_Dias'].apply(lambda x: x if x >= 0 else np.nan)
    df_oc_res['TipoOC'] = df_oc_res.get('TipoOC', pd.Series(["Desconocido"]*len(df_oc_res))).fillna('Desconocido')

except Exception as e:
    st.error(f"❌ Error al cargar datos: {e}")
    st.stop()

# ==========================================================
# 2. CONFIGURACIÓN VISUAL (CSS)
# ==========================================================
def cargar_css():
    try:
        with open("style/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError: pass

cargar_css()

# Header
st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">🧾 Tablero Lean de Adquisiciones</div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">Análisis de Flujo, Variabilidad y Eficiencia PAC</div>
    </div>
    """, unsafe_allow_html=True
)
# ==========================================================
# 4. PREPARACIÓN DE DATOS
# ==========================================================

df_oc_res["FechaCreacion"] = pd.to_datetime(
    df_oc_res["FechaCreacion"],
    format="%d-%m-%Y",
    errors="coerce"
)
df_oc_res["Año"] = df_oc_res["FechaCreacion"].dt.year

opciones_anio = sorted(df_oc_res["Año"].dropna().unique())
# ==========================================================
# 3. FILTROS EN CASCADA
# ==========================================================
# 1. Creamos una copia para la lógica de cascada (opciones dinámicas)
df_cascada = df_oc_res.copy()

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

# Aquí generamos el df_filtrado definitivo que usarán los KPIs y Gráficos
df_filtrado = df_oc_res.copy()

if pac_sel:
    df_filtrado = df_filtrado[df_filtrado["PAC"].isin(pac_sel)]
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
    # Aseguramos que existan las columnas derivadas necesarias
    if "Mes" not in df_filtrado.columns:
        df_filtrado["Mes"] = df_filtrado["FechaCreacion"].dt.to_period("M").dt.to_timestamp()

    # Mapeo para asegurar que la columna PAC tenga nombres amigables si viene como booleano o código
    if "PAC" not in df_filtrado.columns and "En_PAC_2026" in df_filtrado.columns:
        df_filtrado["PAC"] = df_filtrado["En_PAC_2026"].apply(lambda x: "Enlazada" if x == 1 or x == "Si" else "No Enlazada")

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
    # 3. ANÁLISIS ESTADÍSTICO DESCRIPTIVO - TAREA 1
    # =============================================================================
    with st.expander("📈 Ver Estadísticas Descriptivas Detalladas"):
        # Agrupación por Estado PAC para ver promedios y desviaciones
        stats_pac = df_filtrado.groupby("PAC")["TotalBruto"].agg(
            Conteo='count',
            Total='sum',
            Promedio='mean',
            Mediana='median',
            Maximo='max'
        ).reset_index()
        
        st.write("Comparativa de métricas financieras entre compras planificadas (Enlazadas) y no planificadas:")
        st.dataframe(
            stats_pac,
            column_config={
                "Total": st.column_config.NumberColumn(format="$ %.2f"),
                "Promedio": st.column_config.NumberColumn(format="$ %.2f"),
                "Mediana": st.column_config.NumberColumn(format="$ %.2f"),
                "Maximo": st.column_config.NumberColumn(format="$ %.2f"),
            },
            use_container_width=True,
            hide_index=True
        )
    with st.expander("📈 Evolución y Estadísticas del Enlace PAC por Año"):
        # --- 1. PREPARACIÓN DE LA TABLA COMPARATIVA ANUAL ---
        # Agrupamos por Año y PAC para ver la mejora en el tiempo
        stats_anual = df_filtrado.groupby(["Año", "PAC"])["TotalBruto"].agg(
            Conteo='count',
            Monto_Total='sum'
        ).reset_index()

        # Calculamos el % de enlace por año para ver la mejora real
        total_por_año = df_filtrado.groupby("Año").size().reset_index(name="Total_OCs")
        stats_anual = stats_anual.merge(total_por_año, on="Año")
        stats_anual["% Presencia"] = (stats_anual["Conteo"] / stats_anual["Total_OCs"]) * 100

        st.write("### Comparativa de Gestión Anual")
        
        # --- 2. FORMATO CONDICIONAL PARA EL DATAFRAME ---
        # Función para aplicar colores según el estado PAC
        def color_pac(val):
            color = '#d4edda' if val == "Enlazada" else '#f8d7da' # Verde claro / Rojo claro
            return f'background-color: {color}'

        # Aplicamos el estilo y mostramos
        st.dataframe(
            stats_anual.style.applymap(color_pac, subset=['PAC']).format({
                "Monto_Total": "${:,.0f}",
                "% Presencia": "{:.1f}%"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # --- 3. GRÁFICO DE COMPARATIVA ANUAL ---
  
    # =============================================================================
    # 4. VISUALIZACIONES GRÁFICAS - TAREA 5
    # =============================================================================
    st.write("### 📊 Evolución de Órdenes (Enlazadas vs No Enlazadas)")
    # Fila superior de gráficos
    row1_col1, row1_col2, row1_col3 = st.columns([3, 2, 2])

    # --- GRÁFICO 1: EVOLUCIÓN TEMPORAL (LÍNEAS) ---
    with row1_col1:
        
        
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

    # --- GRÁFICO 2: DISTRIBUCIÓN POR UNIDAD (PIE/DONUT) ---
    with row1_col2:
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
    
    with row1_col3:
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
                    range=[0, 100]
                )
            )
            st.plotly_chart(fig_tendencia, use_container_width=True)

    # =============================================================================
    # 6. ANÁLISIS GRÁFICO (TAREA 6)
    # =============================================================================
  
    st.markdown("### 📊 Análisis Gráfico")

    # Preparar datos mensuales
    df_filtrado["Mes"] = df_filtrado["FechaCreacion"].dt.to_period("M").dt.to_timestamp()
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    cg1, cg2 = st.columns(2)

    with cg1:
        # Cantidad por Mes y PAC
        df_mes_pac = df_filtrado.groupby(["Mes", "PAC"]).size().reset_index(name="Cant")
        fig_q = px.bar(df_mes_pac, x="Mes", y="Cant", color="PAC", 
                    title="📝 OCs por Mes y Estado PAC",
                    color_discrete_map={"Enlazada": "#2ECC71", "No Enlazada": "#E74C3C"})
        
        # Ajustar etiquetas de meses a español
        fig_q.update_layout(xaxis=dict(tickvals=df_mes_pac["Mes"].unique(),
                            ticktext=[meses_es[m.month-1] + f" {m.year}" for m in df_mes_pac["Mes"].unique()]))
        st.plotly_chart(fig_q, use_container_width=True)

    with cg2:
        # Monto por Mes y PAC
        df_monto_pac = df_filtrado.groupby(["Mes", "PAC"])["TotalBruto"].sum().reset_index()
        fig_m = px.area(df_monto_pac, x="Mes", y="TotalBruto", color="PAC", 
                        title="💰 Inversión Planificada vs No Planificada",
                        color_discrete_map={"Enlazada": "#2ECC71", "No Enlazada": "#E74C3C"})
        
        fig_m.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("### 🛒 Órdenes de Compra Consolidadas")
    with st.expander("📅 Ver Tabla Maestra de OCs"):
        # Agregamos las nuevas columnas a la visualización
        cols_to_show = ["Codigo", "En_PAC_2026", "ID_Proyecto_PAC", "EstadoOC", "TotalBruto", "FechaCreacion"]
        # Filtramos columnas que existan
        cols_existentes = [c for c in cols_to_show if c in df_filtrado.columns]
        
        st.dataframe(df_filtrado[cols_existentes].style.format({
            "TotalBruto": "${:,.0f}".format
        }), use_container_width=True)

with tab2:
    # ================================== GRAFICOS ===============================================
    # ##### GRAFICOS OC CON MESES EN ESPAÑOL ####
    st.markdown("### 📊 Análisis Gráfico de Órdenes de Compra")

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
        df_filtrado['Periodo'] = df_filtrado['FechaCreacion'].dt.strftime('%Y-%m')
        evo_mensual = df_filtrado.groupby(['Periodo', 'TipoOC'])['TotalBruto'].count().reset_index(name='Cantidad')
        
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




