import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns

# ===== CARGAR CSS =====
def cargar_css():
    with open("style/style.css", encoding="utf-8") as f:
      st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css()


# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()


st.set_page_config(
    page_title="Portal DSSO",
    page_icon="logosso.jpg", 
    layout="wide",
    initial_sidebar_state="expanded")

# Importas Datos
def generar_datos_empresa():
    fechas = pd.date_range(start="2024-01-01", end=datetime.today(), freq='D')
    datos = {
        "Fecha": fechas,
        "ingresos_diarios": np.random.normal(50000, 15000, size=len(fechas)),
        "usuarios_activos": np.random.normal(12000, 3000, size=len(fechas)),
        "conversion_rate": np.random.normal(2.5, 0.8, size=len(fechas)),
        "costo_adquisicion": np.random.normal(45, 12, size=len(fechas)),
        "ltv_cliente": np.random.normal(180, 40, size=len(fechas)),
    }
    
    df=pd.DataFrame(datos)
    df["ingresos_diarios"] *= (1+ np.arange(len(df)) * 0.0001) #tendencia creciente
    return df

df = generar_datos_empresa()

#Titulo
st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #0063AE, #0076D1);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            📊 Panel Formularios Solicitud de Compra
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega una visión general de los formularios de solicitud de compra.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =============================== FILTRO ================================================================

# --- 0. Preparación de Fechas (Extracción de Año) ---
# Convertimos a datetime para extraer el año correctamente
df_fsc["fecha_dt_temp"] = pd.to_datetime(
    df_fsc["fecha derivado"], 
    format="%d-%m-%Y", 
    errors="coerce"
)
# Creamos la columna de año (eliminamos nulos para el filtro)
df_fsc["Año"] = df_fsc["fecha_dt_temp"].dt.year.fillna(0).astype(int)

# --- Normalizar texto ---
df_fsc["SUBDIRECCION"] = df_fsc["SUBDIRECCION"].astype(str).str.strip()
df_fsc["DEPTO"] = df_fsc["DEPTO"].astype(str).str.strip()

# ========= OPCIONES INICIALES =========
# Filtramos el año 0 (errores de fecha) de las opciones
opciones_anio = sorted([a for a in df_fsc["Año"].unique() if a > 0], reverse=True)

# ========= SELECTORES EN COLUMNAS =========
col0, col1, col2 = st.columns([2, 5, 5])

# ---- 📅 Filtro de Año (Nuevo) ----
with col0:
    anio_sel = st.multiselect(
        "📅 Año",
        opciones_anio,
        placeholder="Todos"
    )

# DataFrame base para la cascada (Subdirección depende del Año)
df_cascada_sub = df_fsc.copy()
if anio_sel:
    df_cascada_sub = df_cascada_sub[df_cascada_sub["Año"].isin(anio_sel)]

# ---- 🏢 Subdirección (nivel 1) ----
opciones_subdireccion = sorted(df_cascada_sub["SUBDIRECCION"].dropna().unique())

with col1:
    subdireccion_sel = st.multiselect(
        "🏢 Subdirección",
        opciones_subdireccion,
        placeholder="Seleccione"
    )

# DataFrame base para el Departamento (depende de Año y Subdirección)
df_cascada_depto = df_cascada_sub.copy()
if subdireccion_sel:
    df_cascada_depto = df_cascada_depto[df_cascada_depto["SUBDIRECCION"].isin(subdireccion_sel)]

# ---- 📊 Departamento (nivel 2) ----
opciones_depto = sorted(df_cascada_depto["DEPTO"].dropna().unique())

with col2:
    depto_sel = st.multiselect(
        "📊 Departamento",
        opciones_depto,
        placeholder="Seleccione"
    )

# ========= APLICAR FILTROS FINALES A DF_FILTRADO =========
# Usamos df_filtrado como trabajas habitualmente
df_filtrado = df_fsc.copy()

if anio_sel:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(anio_sel)]

if subdireccion_sel:
    df_filtrado = df_filtrado[df_filtrado["SUBDIRECCION"].isin(subdireccion_sel)]

if depto_sel:
    df_filtrado = df_filtrado[df_filtrado["DEPTO"].isin(depto_sel)]

# Limpieza: eliminamos la columna temporal si no se requiere más adelante
# df_filtrado = df_filtrado.drop(columns=["fecha_dt_temp"])

# ===========================================

# =========================================================================

##### KPIS ####
st.markdown("## 📈 Datos Generales")

# Definimos las proporciones: col1(1) + col2(1) = col3(2)
# Esto hace que col3 ocupe exactamente el 50% del ancho total
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # Usamos df_fsc para el total y df_filtrado para lo seleccionado
    total_fsc_general = df_fsc["newiD"].count()
    total_fsc_filtrado = df_filtrado["newiD"].count()

    porcentaje_fsc = (
        (total_fsc_filtrado / total_fsc_general) * 100
        if total_fsc_general > 0 else 0
    )

    st.metric(
        label="📋 Total FSC",
        value=f"{total_fsc_filtrado:,}",
        delta=f"{porcentaje_fsc:.1f}% del total",
        delta_color="normal"
    )   
    
with col2:
    # Aseguramos conversión a número por si hay errores en el origen
    monto_gen = pd.to_numeric(df_fsc["monto estimado"], errors='coerce').sum()
    monto_filt = pd.to_numeric(df_filtrado["monto estimado"], errors='coerce').sum()

    porcentaje_monto = (
        (monto_filt / monto_gen) * 100
        if monto_gen > 0 else 0
    )

    st.metric(
        label="💰 Montos FSC",
        value=f"${monto_filt:,.0f}",
        delta=f"{porcentaje_monto:.1f}% del monto total",
        delta_color="normal"
    )

with col3:
    # Este espacio ahora ocupa el 50% de la fila
    pass

##### GRAFICOS ####
st.markdown("## 📊 Análisis Grafico")

# Asegurar fecha en datetime
df_filtrado["fecha derivado"] = pd.to_datetime(
    df_filtrado["fecha derivado"],
    errors="coerce"
)

# Crear columna mensual
df_filtrado["Mes"] = df_filtrado["fecha derivado"].dt.to_period("M").dt.to_timestamp()

col1, col2, col3 = st.columns([2, 2, 1])

# ======================================
# 📊 FSC por Mes (Cantidad)
# ======================================

conteo_mes = (
    df_filtrado
    .groupby(["Mes", "DENTRO/FUERA"], as_index=False)
    .agg({"newiD": "count"})
    .rename(columns={"newiD": "Cantidad FSC"})
)

print("COLUMNAS:", conteo_mes.columns.tolist())
print(conteo_mes.head(10))
print("DUPLICADOS:", conteo_mes.duplicated(["Mes","DENTRO/FUERA"]).sum())


with col1:
    conteo_mes = (
        df_filtrado
        .groupby(["Mes", "DENTRO/FUERA"])["newiD"]
        .count()
        .reset_index(name="Cantidad FSC")
    )

    fig_q = px.bar(
        conteo_mes,
        x="Mes",
        y="Cantidad FSC",
        color="DENTRO/FUERA",
        title="📊 Cantidad de FSC por Mes (Dentro / Fuera PAC)",
        labels={
            "Mes": "Mes",
            "Cantidad FSC": "Cantidad de FSC",
            "DENTRO/FUERA": "Estado PAC"
        },
        color_discrete_map={
            "Dentro PAC": "#36e93f",   # verde
            "Fuera PAC": "#ec4545"     # rojo
        }
    )

    fig_q.update_layout(
        barmode="stack",
        height=400,
        template="plotly_white",
        font=dict(family="Segoe UI")
    )

    st.plotly_chart(fig_q, use_container_width=True)

print(
conteo_mes.duplicated(["Mes","DENTRO/FUERA"]).sum()
)
# ======================================
# 💰 FSC por Mes (Monto)
# ======================================
with col2:
    monto_mes = (
        df_filtrado
        .groupby(["Mes", "DENTRO/FUERA"])["monto estimado"]
        .sum()
        .reset_index(name="Monto Estimado")
    )

    fig_m = px.bar(
        monto_mes,
        x="Mes",
        y="Monto Estimado",
        color="DENTRO/FUERA",
        title="💰 Monto Estimado FSC por Mes (Dentro / Fuera PAC)",
        labels={
            "Mes": "Mes",
            "Monto Estimado": "Monto Estimado (CLP)",
            "DENTRO/FUERA": "Estado PAC"
        },
        color_discrete_map={
            "Dentro PAC": "#36e93f",   # verde
            "Fuera PAC": "#ec4545"     # rojo
        }
    )

    fig_m.update_layout(
        barmode="stack",
        height=400,
        template="plotly_white",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
font=dict(family="Segoe UI")
    )

    st.plotly_chart(fig_m, use_container_width=True)

with col3:
    # --- Lógica Métrica 1 (Cantidad) ---
    serie_pac = df_filtrado["DENTRO/FUERA"].astype(str).str.strip().str.upper()
    total_f = len(df_filtrado)
    
    if total_f > 0:
        dentro_pac_q = serie_pac.str.contains("DENTRO", na=False).sum()
        porc_q = (dentro_pac_q / total_f) * 100
    else:
        dentro_pac_q, porc_q = 0, 0.0

    st.metric(
        label="✅ FSC Dentro PAC (%)", 
        value=f"{porc_q:.1f}%", 
        delta=f"{dentro_pac_q} Unds",
        help="Porcentaje basado en la cantidad de formularios."
    )

    # Espaciador pequeño entre métricas
    st.write("") 

    # --- Lógica Métrica 2 (Monto) ---
    monto_total_g = df_filtrado["monto estimado"].sum()
    
    if monto_total_g > 0:
        mask_d = serie_pac.str.contains("DENTRO", na=False)
        monto_d = df_filtrado.loc[mask_d, "monto estimado"].sum()
        porc_m = (monto_d / monto_total_g) * 100
    else:
        monto_d, porc_m = 0, 0.0

    st.metric(
        label="💰 Monto Dentro PAC (%)", 
        value=f"{porc_m:.1f}%", 
        delta=f"$ {monto_d:,.0f}",
        help="Porcentaje basado en el valor monetario total."
    )



st.markdown("## 📈 Tabla Dinámica: Análisis por Departamento y PAC")

# Aseguramos que el monto sea numérico para los cálculos
df_filtrado["monto estimado"] = pd.to_numeric(df_filtrado["monto estimado"], errors="coerce").fillna(0)

# Definimos las columnas
col1, col2 = st.columns(2)

with col1:
    # --- 1. Creación de la Tabla Dinámica ---
    # Usamos pivot_table para cruzar Departamentos con el estado DENTRO/FUERA
    tabla_dinamica = df_filtrado.pivot_table(
        index="DEPTO_unido",
        columns="DENTRO/FUERA",
        values=["newiD", "monto estimado"],
        aggfunc={
            "newiD": "count",          # Recuento de registros (FSC)
            "monto estimado": "sum"    # Suma de montos estimados
        },
        fill_value=0,
        margins=True,                  # Totales por fila y columna
        margins_name="TOTAL GENERAL"
    )

    # --- 2. Aplanar niveles de columnas para visualización limpia ---
    tabla_dinamica.columns = [f"{col[0]} ({col[1]})" for col in tabla_dinamica.columns]
    tabla_dinamica = tabla_dinamica.reset_index()

    # --- 3. Ordenar por cantidad total de registros ---
    col_orden = [c for c in tabla_dinamica.columns if "newiD (TOTAL GENERAL)" in c]
    if col_orden:
        tabla_dinamica = tabla_dinamica.sort_values(by=col_orden[0], ascending=False)

    # --- 4. Renderizado con Estilos ---
    st.dataframe(
        tabla_dinamica.style.format({
            col: "$ {:,.0f}" for col in tabla_dinamica.columns if "monto" in col
        }).background_gradient(
            subset=[c for c in tabla_dinamica.columns if "newiD" in c], 
            cmap="Blues"
        ),
        use_container_width=True,
        hide_index=True
    )
    # --- 6. Resumen rápido en texto ---
total_monto_dinamico = df_filtrado["monto estimado"].sum()
st.caption(f"💰 **Monto Total Filtrado:** $ {total_monto_dinamico:,.0f} | 📋 **Total Registros:** {len(df_filtrado)}")
with col2:
    pass

st.markdown("## 🚦 Centro de Control y Alertas")

# =============================================================================
# 1. PREPARACIÓN DE DATOS PARA ALERTAS
# =============================================================================
# Aseguramos tipos de datos correctos
df_alertas = df_filtrado.copy()
df_alertas["monto estimado"] = pd.to_numeric(df_alertas["monto estimado"], errors='coerce').fillna(0)
df_alertas["DENTRO/FUERA"] = df_alertas["DENTRO/FUERA"].astype(str).str.strip().str.upper()

# Filtros base
df_fuera = df_alertas[~df_alertas["DENTRO/FUERA"].str.contains("DENTRO")]
df_dentro = df_alertas[df_alertas["DENTRO/FUERA"].str.contains("DENTRO")]

total_docs = len(df_alertas)
total_fuera = len(df_fuera)
monto_fuera = df_fuera["monto estimado"].sum()
monto_total = df_alertas["monto estimado"].sum()

# Cálculo de KPIs
if total_docs > 0:
    pct_cumplimiento = (len(df_dentro) / total_docs) * 100
    pct_fuga_monto = (monto_fuera / monto_total * 100) if monto_total > 0 else 0
else:
    pct_cumplimiento = 100
    pct_fuga_monto = 0

# =============================================================================
# 2. SEMÁFORO DE ESTADO GENERAL (KPIs Visuales)
# =============================================================================
c_kpi1, c_kpi2, c_kpi3 = st.columns(3)

with c_kpi1:
    st.metric(
        "Nivel de Cumplimiento PAC", 
        f"{pct_cumplimiento:.1f}%",
        delta="- Bajo Meta" if pct_cumplimiento < 80 else "En rango",
        delta_color="normal" if pct_cumplimiento >= 80 else "inverse"
    )

with c_kpi2:
    st.metric(
        "Riesgo Financiero (Fuera PAC)",
        f"${monto_fuera:,.0f}",
        delta=f"{pct_fuga_monto:.1f}% del presupuesto filtrado",
        delta_color="inverse", # Rojo si aumenta
        help="Monto total acumulado de proyectos no planificados"
    )

with c_kpi3:
    # Identificar el departamento con más casos FUERA de PAC
    if not df_fuera.empty:
        top_offender = df_fuera["DEPTO"].value_counts().idxmax()
        count_offender = df_fuera["DEPTO"].value_counts().max()
        st.metric(
            "Área con Mayor Desviación",
            f"{count_offender} casos",
            delta=top_offender[:15] + "..." if len(top_offender)>15 else top_offender,
            delta_color="inverse"
        )
    else:
        st.metric("Área con Mayor Desviación", "0 casos", delta="Todo OK")

st.markdown("---")

# =============================================================================
# 3. MOTOR DE ALERTAS INTELIGENTE
# =============================================================================

# --- ALERTA 1: NIVEL CRÍTICO DE CUMPLIMIENTO ---
if pct_cumplimiento < 50:
    st.error(
        f"🚨 **ESTADO CRÍTICO:** El cumplimiento del PAC es peligrosamente bajo ({pct_cumplimiento:.1f}%). "
        "La mayoría de los procesos están fuera de planificación. Se requiere intervención inmediata."
    )
elif pct_cumplimiento < 80:
    st.warning(
        f"⚠️ **ATENCIÓN:** El cumplimiento ({pct_cumplimiento:.1f}%) está por debajo del estándar recomendado (80%). "
        "Revise los casos fuera de norma."
    )
else:
    st.success(
        f"✅ **Bajo Control:** El proceso opera con un {pct_cumplimiento:.1f}% de apego a la planificación."
    )

# --- ALERTA 2: IMPACTO PRESUPUESTARIO (Solo si hay dinero involucrado) ---
if monto_fuera > 0:
    # Umbral arbitrario de ejemplo: si más del 20% del dinero está fuera de PAC
    tipo_alerta = st.error if pct_fuga_monto > 20 else st.warning
    
    with tipo_alerta(f"💰 **Alerta Presupuestaria:** Se han detectado **${monto_fuera:,.0f}** gestionados FUERA de PAC."):
        st.markdown(f"Esto representa el **{pct_fuga_monto:.1f}%** del monto total visible en este filtro.")
        with st.expander("🔍 Ver proyectos que generan este impacto"):
            # Mostrar tabla simplificada
            st.dataframe(
                df_fuera[["newiD", "SUBDIRECCION", "DEPTO", "monto estimado"]]
                .sort_values("monto estimado", ascending=False)
                .head(10)
                .style.format({"monto estimado": "${:,.0f}"}),
                use_container_width=True,
                hide_index=True
            )

# --- ALERTA 3: FOCO DE GESTIÓN (Detectar quién necesita ayuda) ---
if not df_fuera.empty:
    top_depto = df_fuera["DEPTO"].value_counts().idxmax()
    casos_top = df_fuera["DEPTO"].value_counts().max()
    
    # Solo mostramos si representa una cantidad relevante (ej: más de 2 casos)
    if casos_top > 2:
        st.info(
            f"📢 **Foco de Gestión:** El departamento **{top_depto}** concentra la mayor cantidad de desviaciones "
            f"(**{casos_top}** formularios fuera de PAC). Se sugiere contactar al área para regularizar."
        )

# --- ALERTA 4: MENSAJE DE "SIN DATOS" ---
if total_docs == 0:
    st.info("ℹ️ No hay datos para analizar con los filtros seleccionados.")


# =============================================================================
# 🚀 DASHBOARD DE CONTROL DE CUMPLIMIENTO (PAC)
# =============================================================================

st.markdown("---")
st.markdown("## 🎯 Monitor de Desempeño PAC")

# 1. PREPARACIÓN DE DATOS ----------------------------------------------------
# Creamos una copia para no afectar el flujo anterior
df_pac_dashboard = df_filtrado.copy()

# Limpieza y Conversión de tipos
df_pac_dashboard["monto estimado"] = pd.to_numeric(df_pac_dashboard["monto estimado"], errors='coerce').fillna(0)
df_pac_dashboard["DENTRO/FUERA"] = df_pac_dashboard["DENTRO/FUERA"].astype(str).str.strip().str.upper()

# Cálculos Base
total_registros = len(df_pac_dashboard)
if total_registros > 0:
    # Conteos
    dentro_pac = df_pac_dashboard[df_pac_dashboard["DENTRO/FUERA"].str.contains("DENTRO")].copy()
    fuera_pac = df_pac_dashboard[~df_pac_dashboard["DENTRO/FUERA"].str.contains("DENTRO")].copy()
    
    cant_dentro = len(dentro_pac)
    cant_fuera = len(fuera_pac)
    
    # Montos
    monto_fuera = fuera_pac["monto estimado"].sum()
    
    # Porcentajes
    tasa_cumplimiento = (cant_dentro / total_registros) * 100
    tasa_fuga = (cant_fuera / total_registros) * 100
else:
    tasa_cumplimiento, tasa_fuga, cant_fuera, monto_fuera = 0, 0, 0, 0

# 2. INDICADORES KPI (MÉTRICAS) ---------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric(
        label="Tasa de Cumplimiento",
        value=f"{tasa_cumplimiento:.1f}%",
        delta=f"Meta: 90%",
        delta_color="normal" if tasa_cumplimiento >= 90 else "inverse",
        help="Porcentaje de formularios que están DENTRO de PAC"
    )

with kpi2:
    st.metric(
        label="Casos Fuera de PAC",
        value=f"{cant_fuera}",
        delta="Atención Requerida" if cant_fuera > 0 else "Óptimo",
        delta_color="inverse", # Rojo si sube
        help="Cantidad de formularios no planificados"
    )

with kpi3:
    st.metric(
        label="Monto No Planificado",
        value=f"${monto_fuera:,.0f}",
        delta="Impacto Presupuestario",
        delta_color="off",
        help="Suma de montos de proyectos FUERA de PAC"
    )

with kpi4:
    # Depto con más casos fuera de PAC (Top Offender)
    if not fuera_pac.empty:
        top_depto = fuera_pac["DEPTO"].value_counts().idxmax()
        count_top = fuera_pac["DEPTO"].value_counts().max()
        val_metric = f"{count_top} casos"
    else:
        top_depto = "N/A"
        val_metric = "0 casos"
        
    st.metric(
        label="Dpto. Crítico (Fuera PAC)",
        value=top_depto[:15] + "..." if len(top_depto) > 15 else top_depto,
        delta=val_metric,
        delta_color="inverse"
    )

with kpi5:
    st.metric(
        label="Total Gestionado",
        value=total_registros,
        help="Total de formularios en el filtro actual"
    )

# 3. VISUALIZACIÓN GRÁFICA Y TABLA DETALLADA -------------------------------
c_chart, c_table = st.columns([1, 2])

# --- GRÁFICO DE DONA (Plotly) ---
with c_chart:
    st.caption("Distribución de Cumplimiento")
    if total_registros > 0:
        # Preparamos datos agrupados
        df_chart = df_pac_dashboard["DENTRO/FUERA"].value_counts().reset_index()
        df_chart.columns = ["Estado", "Cantidad"]
        
        # Asignamos colores específicos
        color_map = {
            "DENTRO PAC": "#2ecc71", # Verde
            "FUERA PAC": "#e74c3c",  # Rojo
            "DENTRO": "#2ecc71",
            "FUERA": "#e74c3c"
        }
        
        fig_donut = px.pie(
            df_chart, 
            values="Cantidad", 
            names="Estado",
            hole=0.6,
            color="Estado",
            color_discrete_map=color_map
        )
        fig_donut.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=300,
            showlegend=True,
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("Sin datos para graficar")

# --- TABLA ESTILIZADA ---
with c_table:
    st.caption("Detalle de Registros (Últimos 100)")
    
    # Seleccionamos columnas relevantes para la vista
    cols_view = ["ID Proyecto", "DEPTO", "fecha derivado", "monto estimado", "DENTRO/FUERA"]
    # Verificamos que existan en el DF (para evitar errores si cambian nombres)
    cols_existing = [c for c in cols_view if c in df_pac_dashboard.columns]
    
    df_view = df_pac_dashboard[cols_existing].head(100).copy()
    
    # Función para colorear la celda de estado
    def color_estado_pac(val):
        val_str = str(val).upper()
        if 'DENTRO' in val_str:
            return 'background-color: #d4edda; color: #155724; font-weight: bold;' # Verde claro
        elif 'FUERA' in val_str:
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold;' # Rojo claro
        return ''

    # Aplicamos formato
    st.dataframe(
        df_view.style
        .format({
            "monto estimado": "${:,.0f}",
            "fecha derivado": lambda x: pd.to_datetime(x).strftime('%d-%m-%Y') if pd.notnull(x) else "-"
        })
        .map(color_estado_pac, subset=["DENTRO/FUERA"]), # Aplica color solo a la columna de estado
        use_container_width=True,
        height=300,
        hide_index=True
    )


    # =============================================================================
# 📋 TABLA DETALLADA DE REGISTROS (EXPANDER)
# =============================================================================
st.markdown("### 🔎 Revisión de Registros")

with st.expander("📂 Ver Tabla Completa de Registros (df_filtrado)", expanded=False):
    
    # 1. Preparación de la Vista (Copia para no alterar el original)
    df_ver = df_filtrado.copy()

    # 2. Selección de Columnas Clave (Ajusta según tus nombres exactos)
    # Intenta seleccionar estas columnas, si no existen, usa todas.
    cols_deseadas = [
        "newiD", "fecha derivado", "SUBDIRECCION", "DEPTO", 
        "monto estimado", "Estado_PAC", "DENTRO/FUERA"
    ]
    # Filtramos solo las que realmente existen en tu DF para evitar errores
    cols_finales = [c for c in cols_deseadas if c in df_ver.columns]
    
    if cols_finales:
        df_ver = df_ver[cols_finales]

    # 3. Conversión de Fecha para visualización limpia
    if "fecha derivado" in df_ver.columns:
        df_ver["fecha derivado"] = pd.to_datetime(df_ver["fecha derivado"], errors='coerce')

    # 4. Función de Estilo para DENTRO/FUERA
    def color_fondo_pac(val):
        val = str(val).upper()
        if "DENTRO" in val:
            return 'background-color: #d1e7dd; color: #0f5132' # Verde suave
        elif "FUERA" in val:
            return 'background-color: #f8d7da; color: #842029' # Rojo suave
        return ''

    # 5. Renderizar Dataframe con Configuración de Columnas
    st.dataframe(
        df_ver.style.map(color_fondo_pac, subset=["DENTRO/FUERA"]),
        column_config={
            "monto estimado": st.column_config.NumberColumn(
                "Monto Estimado",
                help="Monto en pesos chilenos",
                format="$%d",  # Formato moneda sin decimales
            ),
            "fecha derivado": st.column_config.DateColumn(
                "Fecha Ingreso",
                format="DD-MM-YYYY",
            ),
            "newiD": st.column_config.TextColumn("ID Solicitud"),
            "Estado_PAC": st.column_config.TextColumn("Estado Actual"),
        },
        use_container_width=True,
        hide_index=True,
        height=500  # Altura fija con scroll
    )

    # 6. Botón de Descarga
    csv = df_ver.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv,
        file_name='registros_filtrados_pac.csv',
        mime='text/csv',
    )