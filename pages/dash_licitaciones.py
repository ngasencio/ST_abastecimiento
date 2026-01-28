import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. Importación Correcta (basada en tu estructura de carpetas)###
import api.LI_data_loader as loader

# Carga de datos (Usando caché de Streamlit para no recargar a cada clic)
@st.cache_data
def obtener_datos():
    df_res, df_det = loader.cargar_maestros()
    return df_res, df_det

# Ejecución
try:
    df_MaestroLI_Resumen, df_MaestroLI_Detalle = obtener_datos()

    if df_MaestroLI_Resumen.empty:
        st.error("No se encontraron datos. Ejecuta el actualizador primero.")
    else:
        st.success(f"Datos cargados: {len(df_MaestroLI_Resumen)} licitaciones disponibles.")
        
        # Aquí empieza tu lógica de filtros
        # df_filtrado = ...

except Exception as e:
    st.error(f"Ocurrió un error en la carga: {e}")

# ============== Definir DF ===================
df_res = df_MaestroLI_Resumen
df_det = df_MaestroLI_Detalle

# ============== CARGAR CSS ===================
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

# ============== INYECCIÓN DE CSS ===================

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
            📄 Licitaciones DSSO
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega la cantidad y detalle de licitaciones en curso.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================== Filtros ========================
# 1. Normalización de datos (Siguiendo tu patrón)
for col in ["Estado", "C_Usuario", "C_Unidad"]:
    df_res[col] = df_res[col].astype(str).str.strip()

# =============================== FILTROS ================================================================

# Definimos 4 columnas para los widgets
col1, col2, col3, col4 = st.columns(4)

# --- LÓGICA DE CASCADA (Dataframe temporal para opciones) ---
df_cascada = df_res.copy()

# ---- 1. ESTADO ----
opciones_estado = sorted(df_cascada["Estado"].dropna().unique())
with col1:
    estado_sel = st.multiselect("📌 Estado", opciones_estado, placeholder="Seleccione")

if estado_sel:
    df_cascada = df_cascada[df_cascada["Estado"].isin(estado_sel)]

# ---- 2. USUARIO ----
opciones_usuario = sorted(df_cascada["C_Usuario"].dropna().unique())
with col2:
    usuario_sel = st.multiselect("👤 Usuario", opciones_usuario, placeholder="Seleccione")

if usuario_sel:
    df_cascada = df_cascada[df_cascada["C_Usuario"].isin(usuario_sel)]

# ---- 3. UNIDAD ----
opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
with col3:
    unidad_sel = st.multiselect("🏢 Unidad", opciones_unidad, placeholder="Seleccione")

if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# ---- 4. ESPACIO (Pass) ----
with col4:
    st.info("Filtro adicional") # Placeholder o espacio vacío
    pass

# =============================== APLICAR FILTROS FINAL =================================================

# Filtramos df_res (Resumen)
df_res_filtrado = df_res.copy()

if estado_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["Estado"].isin(estado_sel)]
if usuario_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["C_Usuario"].isin(usuario_sel)]
if unidad_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["C_Unidad"].isin(unidad_sel)]

# Sincronizamos con df_det (Detalles) usando CodigoLicitacion
# Solo incluimos en detalles lo que sobrevivió al filtro en resumen
df_det_filtrado = df_det[df_det["CodigoLicitacion"].isin(df_res_filtrado["CodigoLicitacion"])]

# Alias para tu uso estándar
df_filtrado = df_res_filtrado.copy()

# ##### KPIS ####
st.markdown("## 📈 Resumen de Licitaciones")
c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

with c_kpi1:
    # --- TOTAL LICITACIONES ---
    # Contamos IDs únicos de licitación
    total_lic_general = df_res["CodigoLicitacion"].nunique()
    total_lic_filtrado = df_filtrado["CodigoLicitacion"].nunique()

    porcentaje_lic = (
        (total_lic_filtrado / total_lic_general) * 100
        if total_lic_general > 0 else 0
    )

    st.metric(
        "📋 Total Licitaciones",
        f"{total_lic_filtrado:,}",
        f"{porcentaje_lic:.1f}% del total"
    )

with c_kpi2:
    # --- TOTAL MONTO TRANSADO ---
    # Nota: Ajusta "MontoTotal" al nombre real de tu columna de dinero
    monto_col = "MontoEstimado" 
    
    monto_total_gral = df_res[monto_col].sum()
    monto_total_filt = df_filtrado[monto_col].sum()

    porcentaje_monto = (
        (monto_total_filt / monto_total_gral) * 100
        if monto_total_gral > 0 else 0
    )

    st.metric(
        "💰 Monto Transado",
        f"${monto_total_filt:,.0f}",
        f"{porcentaje_monto:.1f}% del monto total"
    )

with c_kpi3:
    # Espacio para futura métrica (ej. Tiempo promedio o Eficiencia)
    pass

with c_kpi4:
    # Espacio para futura métrica
    pass

# ===================== GRAFICOS ============================================

# 1. Preparación de datos (Manteniendo tus reglas de 35 caracteres)
df_filtrado["CodigoLicitacion"] = df_filtrado["CodigoLicitacion"].astype(str)
df_filtrado["Nombre"] = df_filtrado["Nombre"].astype(str)

def acortar_nombre(texto):
    if len(texto) > 35:
        return texto[:32] + "..."
    return texto

df_filtrado["Nombre_Corto"] = df_filtrado["Nombre"].apply(acortar_nombre)
df_filtrado["Etiqueta_Y"] = df_filtrado["CodigoLicitacion"] + " | " + df_filtrado["Nombre_Corto"]

# Normalización de fechas
columnas_fechas = [
    "FechaCreacion", "FechaPublicacion", "FechaCierre", 
    "FechaAdjudicacion", "FechaEstimadaFirma", "FechaInicioContrato"
]
for col in columnas_fechas:
    df_filtrado[col] = pd.to_datetime(df_filtrado[col], errors='coerce', dayfirst=True)

# 2. Reestructuración para segmentos
segmentos = [
    ("1. Preparación", "FechaCreacion", "FechaPublicacion"),
    ("2. Publicación", "FechaPublicacion", "FechaCierre"),
    ("3. Evaluación", "FechaCierre", "FechaAdjudicacion"),
    ("4. Adjudicación", "FechaAdjudicacion", "FechaEstimadaFirma"),
    ("5. Firma y Contrato", "FechaEstimadaFirma", "FechaInicioContrato")
]

gantt_data = []
for _, row in df_filtrado.iterrows():
    for etapa, inicio, fin in segmentos:
        if pd.notnull(row[inicio]) and pd.notnull(row[fin]):
            duracion = (row[fin] - row[inicio]).days
            gantt_data.append({
                "Identificador": row["Etiqueta_Y"],
                "Etapa": etapa,
                "Inicio": row[inicio],
                "Fin": row[fin],
                "Días": max(0, duracion), # Evitamos días negativos
                "Texto_Etiqueta": f"{max(0, duracion)} d", # Texto que se verá en la barra
                "Nombre_Completo": row["Nombre"]
            })

df_gantt = pd.DataFrame(gantt_data)

# 3. Renderizado del Gráfico
#st.markdown("### 📅 Cronograma con Duración por Etapa")

#if not df_gantt.empty:
 #   fig = px.timeline(
  #      df_gantt, 
   #     x_start="Inicio", 
    #    x_end="Fin", 
     #   y="Identificador", 
      #  color="Etapa",
       # text="Texto_Etiqueta", # <--- AQUÍ AGREGAMOS LA ETIQUETA
        #hover_data={"Identificador": False, "Nombre_Completo": True, "Días": True, "Texto_Etiqueta": False},
        #color_discrete_sequence=px.colors.qualitative.Prism
    #)

    # --- A) AJUSTE DE POSICIÓN DE TEXTO ---
    #fig.update_traces(
    #    textposition='inside', # Pone el texto dentro de la barra
    #    insidetextanchor='middle', # Lo centra
    #    textfont_size=12
    #)

    # --- B) LÍNEA VERTICAL DE HOY ---
    #hoy = datetime(2026, 1, 17)
    #fig.add_vline(
    #    x=hoy.timestamp() * 1000, 
    #    line_width=3, 
    #    line_dash="dash", 
    #    line_color="red",
    #    annotation_text="HOY", 
    #    annotation_position="top right"
    #)

    # --- C) AJUSTES FINALES ---
    #fig.update_yaxes(autorange="reversed", title="Licitación (ID | Nombre)")
    
    #cantidad_filas = int(len(df_filtrado["Etiqueta_Y"].unique()))
    #alto_grafico = 400 + (cantidad_filas * 35) # Un poco más de espacio por fila para las etiquetas

    #fig.update_layout(
    #    height=alto_grafico,
    #    legend_title="Etapas",
    #    margin=dict(l=10, r=10, t=50, b=10)
    #)

    #st.plotly_chart(fig, use_container_width=True)
#else:
#   st.info("No hay datos suficientes para mostrar el cronograma.")
# ========================================================================  





st.markdown("## 📅 Resumen General de Licitaciones")
with st.expander("🔍 Ver Datos Maestros (Resumen)", expanded=True):
        # Aplicamos formato solo a las columnas que existen
        st.dataframe(
            df_res.style.format({
                "MontoEstimado": "${:,.0f}".format,
                "CodigoLicitacion": str,
                "Estado": str
            }, na_rep="-"), 
            height=400, 
            use_container_width=True
        )


# ==============================================================================
# 🚀 MÓDULO LEAN & OKR: ANÁLISIS DE RENDIMIENTO DE LICITACIONES
# ==============================================================================

st.markdown("---")
st.markdown("## ⏱️ Análisis de Flujo de Valor (Lean VSM) y OKRs")

# 1. PREPARACIÓN DE DATOS DE TIEMPOS (Data Wrangling)
# Usamos df_filtrado para respetar los filtros del usuario
df_lean = df_filtrado.copy()

# Definición de las columnas de fecha clave según tu base de datos
cols_fechas = [
    'FechaCreacion', 'FechaPublicacion', 'FechaCierre', 
    'FechaAdjudicacion', 'FechaInicioContrato'
]

# Conversión robusta a datetime
for col in cols_fechas:
    if col in df_lean.columns:
        df_lean[col] = pd.to_datetime(df_lean[col], errors='coerce')

# --- CÁLCULO DE LEAD TIMES (Días) ---
# LT Total: Desde que nace la necesidad (Creación) hasta que inicia el contrato (Valor entregado)
df_lean['LT_Total'] = (df_lean['FechaInicioContrato'] - df_lean['FechaCreacion']).dt.days

# Desglose por Etapas (Value Stream Breakdown)
# 1. Burocracia Interna Previa: Creación -> Publicación
df_lean['T_Prep'] = (df_lean['FechaPublicacion'] - df_lean['FechaCreacion']).dt.days
# 2. Tiempo de Mercado: Publicación -> Cierre
df_lean['T_Mercado'] = (df_lean['FechaCierre'] - df_lean['FechaPublicacion']).dt.days
# 3. Tiempo de Evaluación: Cierre -> Adjudicación
df_lean['T_Evaluacion'] = (df_lean['FechaAdjudicacion'] - df_lean['FechaCierre']).dt.days
# 4. Formalización: Adjudicación -> Contrato
df_lean['T_Formalizacion'] = (df_lean['FechaInicioContrato'] - df_lean['FechaAdjudicacion']).dt.days

# Limpieza de inconsistencias (fechas negativas o nulas)
cols_tiempos = ['LT_Total', 'T_Prep', 'T_Mercado', 'T_Evaluacion', 'T_Formalizacion']
for col in cols_tiempos:
    df_lean[col] = df_lean[col].apply(lambda x: x if x >= 0 else np.nan)

# ==============================================================================
# 🎯 SECCIÓN 1: OKRs OPERACIONALES (Objectives & Key Results)
# ==============================================================================
st.subheader("🎯 Estado de OKRs Operacionales")

# Cálculo de métricas para OKRs
licitaciones_cerradas = df_lean.dropna(subset=['LT_Total'])
tasa_adjudicacion = 0
if len(df_lean) > 0:
    # Asumiendo que el estado 'Adjudicada' existe o similar
    adjudicadas = df_lean[df_lean['Estado'].str.contains('Adjudicada', case=False, na=False)].shape[0]
    tasa_adjudicacion = (adjudicadas / len(df_lean)) * 100

lt_promedio = licitaciones_cerradas['LT_Total'].mean() if not licitaciones_cerradas.empty else 0

# Visualización de Tarjetas OKR
okr1, okr2, okr3 = st.columns(3)

with okr1:
    st.markdown("**O1: Agilidad del Proceso**")
    st.metric(
        label="KR: Lead Time Promedio",
        value=f"{lt_promedio:.1f} días",
        delta="-5 días (Meta)" if lt_promedio > 0 else None,
        delta_color="inverse", # Menos es mejor
        help="Tiempo promedio desde Creación hasta Inicio Contrato"
    )

with okr2:
    st.markdown("**O2: Eficacia de Licitación**")
    st.metric(
        label="KR: Tasa de Adjudicación",
        value=f"{tasa_adjudicacion:.1f}%",
        delta="vs 85% (Meta)",
        help="Porcentaje de procesos que terminan adjudicados vs desiertos/revocados"
    )

with okr3:
    st.markdown("**O3: Eficiencia Administrativa**")
    # Ratio: Cuánto dinero movemos por cada producto gestionado
    # Si gestionas muchos productos baratos, el ratio baja (posible ineficiencia administrativa)
    total_items = df_det_filtrado['Cantidad'].sum()
    monto_total = df_filtrado['MontoEstimado'].sum()
    ratio_valor = monto_total / total_items if total_items > 0 else 0
    
    st.metric(
        label="KR: Valor por Item Gestionado",
        value=f"${ratio_valor:,.0f}",
        help="Monto total estimado / Cantidad total de productos. Busca identificar carga operativa de bajo valor."
    )

# ==============================================================================
# 📊 SECCIÓN 2: VISUALIZACIÓN DE FLUJO (Lead Time Breakdown)
# ==============================================================================
c_chart1, c_chart2 = st.columns([2, 1])

with c_chart1:
    st.markdown("#### ⏳ Desglose de Tiempos por Tipo de Licitación")
    if not licitaciones_cerradas.empty:
        # Preparamos datos para gráfico apilado (Stacked Bar)
        df_melt = licitaciones_cerradas.groupby('Tipo')[['T_Prep', 'T_Mercado', 'T_Evaluacion', 'T_Formalizacion']].mean().reset_index()
        df_melt = df_melt.melt(id_vars='Tipo', var_name='Etapa', value_name='Días')
        
        # Mapeo de nombres para que sean legibles
        nombres_etapa = {
            'T_Prep': '1. Prep. Interna',
            'T_Mercado': '2. Mercado (Publicado)',
            'T_Evaluacion': '3. Evaluación',
            'T_Formalizacion': '4. Formalización'
        }
        df_melt['Etapa'] = df_melt['Etapa'].map(nombres_etapa)
        
        fig_lt = px.bar(
            df_melt, 
            x='Tipo', 
            y='Días', 
            color='Etapa',
            title="¿Dónde se pierde el tiempo? (Lead Time por Etapas)",
            text_auto='.1f',
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_lt.update_layout(template="plotly_white", xaxis_title=None)
        st.plotly_chart(fig_lt, use_container_width=True)
    else:
        st.info("No hay suficientes datos con ciclo completo para mostrar el desglose de tiempos.")

with c_chart2:
    st.markdown("#### 🐢 vs 🐇 Ranking Velocidad")
    if not licitaciones_cerradas.empty:
        # Top Compradores más ágiles (menor Lead Time)
        top_agiles = licitaciones_cerradas.groupby('C_Usuario')['LT_Total'].mean().sort_values().head(5).reset_index()
        
        fig_rank = px.bar(
            top_agiles,
            x='LT_Total',
            y='C_Usuario',
            orientation='h',
            title="Usuarios con menor Lead Time (Top 5)",
            color='LT_Total',
            color_continuous_scale='Bluered_r' # Azul es rápido, Rojo es lento
        )
        fig_rank.update_layout(template="plotly_white", yaxis={'categoryorder':'total descending'}, showlegend=False)
        st.plotly_chart(fig_rank, use_container_width=True)

# ==============================================================================
# 🔍 SECCIÓN 3: MATRIZ DE EFICIENCIA (Monto vs Cantidad)
# ==============================================================================
with st.expander("🔎 Ver Matriz de Eficiencia (Detectar 'Grasa' Administrativa)"):
    st.markdown("""
    **Interpretación Lean:**
    * **Cuadrante Inferior Derecho (Muchos productos, Poco Monto):** Alta carga administrativa, bajo impacto financiero. Candidatos a automatizar o consolidar (Convenio Marco).
    * **Cuadrante Superior Izquierdo (Pocos productos, Alto Monto):** Licitaciones estratégicas. Requieren atención detallada.
    """)
    
    # Unir resumen con detalle agrupado para tener cantidad de items por licitación
    items_por_lic = df_det_filtrado.groupby('CodigoLicitacion')['Cantidad'].sum().reset_index()
    df_matrix = df_filtrado.merge(items_por_lic, on='CodigoLicitacion', how='inner')
    
    if not df_matrix.empty:
        fig_scatter = px.scatter(
            df_matrix,
            x='Cantidad',
            y='MontoEstimado',
            color='Tipo',
            hover_data=['CodigoLicitacion', 'Nombre', 'C_Usuario'],
            log_x=True, # Escala logarítmica ayuda a ver mejor si hay mucha dispersión
            log_y=True,
            title="Matriz de Impacto: Esfuerzo (Items) vs Valor (Monto)",
            labels={'Cantidad': 'Cantidad de Productos (Log)', 'MontoEstimado': 'Monto Estimado $ (Log)'}
        )
        fig_scatter.update_layout(template="plotly_white")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("No hay datos cruzados entre Resumen y Detalle para generar la matriz.")