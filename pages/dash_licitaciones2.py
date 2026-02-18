import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from style.ui import cargar_css

cargar_css()

# ============== CARGA DE DATOS ===================
@st.cache_data
def obtener_datos():
    df_res, df_det = loader.cargar_maestros()
    return df_res, df_det

try:
    df_MaestroLI_Resumen, df_MaestroLI_Detalle = obtener_datos()
    
    if df_MaestroLI_Resumen.empty:
        st.error("No se encontraron datos. Ejecuta el actualizador primero.")
        st.stop()
    else:
        st.success(f"Datos cargados: {len(df_MaestroLI_Resumen)} licitaciones disponibles.")
        
except Exception as e:
    st.error(f"Ocurrió un error en la carga: {e}")
    st.stop()

# ============== DEFINIR DF ===================
df_res = df_MaestroLI_Resumen.copy()
df_det = df_MaestroLI_Detalle.copy()

# ============== NORMALIZACIÓN DE DATOS ===================
for col in ["Estado", "C_Usuario", "C_Unidad"]:
    if col in df_res.columns:
        df_res[col] = df_res[col].astype(str).str.strip()

# Normalización de fechas
columnas_fechas = [
    "FechaCreacion",
    "FechaCierre",
    "FechaInicio",
    "FechaFinal",
    "FechaPubRespuestas",
    "FechaActoAperturaTecnica",
    "FechaActoAperturaEconomica",
    "FechaPublicacion",
    "FechaAdjudicacion",
    "FechaEstimadaAdjudicacion",
    "FechaSoporteFisico",
    "FechaTiempoEvaluacion",
    "FechaEstimadaFirma",
    "FechaVisitaTerreno",
    "FechaEntregaAntecedentes",
    "FechaInicioContrato"
    ]

for col in columnas_fechas:
    if col in df_res.columns:
        df_res[col] = pd.to_datetime(df_res[col], errors='coerce', dayfirst=True)

# Crear columna FechaClave (fecha más cercana) para df_res
def obtener_fecha_mas_cercana(row):
    fechas_validas = []
    for col in columnas_fechas:
        if col in row.index and pd.notna(row[col]):
            fechas_validas.append(row[col])
    return min(fechas_validas) if fechas_validas else pd.NaT

df_res['FechaClave'] = df_res.apply(obtener_fecha_mas_cercana, axis=1)

# ============== HEADER ===================
st.markdown("""
    <div style="
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #138AEC 0%, #3E9FEF 100%);
        color: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(19, 138, 236, 0.3);
    ">
        <div style="font-size: 32px; font-weight: 800; margin-bottom: 8px;">
            📄 Dashboard de Licitaciones 2026
        </div>
        <div style="font-size: 16px; opacity: 0.95;">
            Gestión y seguimiento semanal de licitaciones - Red de Salud
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============== FILTROS ADICIONALES ===================
st.markdown("### 🔍 Filtros Adicionales")

col1, col2, col3, col4 = st.columns(4)

df_cascada = df_res.copy()

# Filtro Estado
with col1:
    opciones_estado = sorted(df_cascada["Estado"].dropna().unique())
    estado_sel = st.multiselect("📌 Estado", opciones_estado, placeholder="Todos")

if estado_sel:
    df_cascada = df_cascada[df_cascada["Estado"].isin(estado_sel)]

# Filtro Usuario
with col2:
    opciones_usuario = sorted(df_cascada["C_Usuario"].dropna().unique())
    usuario_sel = st.multiselect("👤 Usuario", opciones_usuario, placeholder="Todos")

if usuario_sel:
    df_cascada = df_cascada[df_cascada["C_Usuario"].isin(usuario_sel)]

# Filtro Unidad
with col3:
    opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
    unidad_sel = st.multiselect("🏢 Unidad", opciones_unidad, placeholder="Todos")

if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# ============== APLICAR FILTROS ===================
df_res_filtrado = df_res.copy()

if estado_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["Estado"].isin(estado_sel)]
if usuario_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["C_Usuario"].isin(usuario_sel)]
if unidad_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["C_Unidad"].isin(unidad_sel)]

# La columna FechaClave ya existe en df_res, solo copiamos el dataframe filtrado
# (ya incluye la columna FechaClave porque se copia de df_res)

# Sincronizar con detalle
df_det_filtrado = df_det[df_det["CodigoLicitacion"].isin(df_res_filtrado["CodigoLicitacion"])]

# ==============================================================================
# 1. CONFIGURACIÓN Y CARGA DE DATOS
# ==============================================================================
st.markdown("## 📊 Tablero de Control de Licitaciones (Enfoque Lean)")
st.markdown("Monitorización del flujo de valor, lead times y próximos hitos críticos.")

# --- A. PREPROCESAMIENTO DE DATOS ---
# 1. Normalización de Fechas (ISO a Datetime)
cols_fechas = [
    "FechaCreacion", "FechaPublicacion", "FechaCierre", 
    "FechaAdjudicacion", "FechaInicioContrato", "FechaEstimadaFirma"
]

for col in cols_fechas:
    if col in df_res_filtrado.columns:
        # Coerce maneja errores convirtiéndolos en NaT (Not a Time)
        df_res_filtrado[col] = pd.to_datetime(df_res_filtrado[col], errors='coerce')

# 2. Normalización de Usuarios (C_Usuario)
if "C_Usuario" in df_res_filtrado.columns:
    df_res_filtrado["C_Usuario"] = df_res_filtrado["C_Usuario"].astype(str).str.upper().str.strip()
else:
    df_res_filtrado["C_Usuario"] = "SIN ASIGNAR"

# 3. Lógica de "Próximo Hito" (Determinación de Fecha Clave)
now = pd.Timestamp.now()

def obtener_fecha_clave(row):
    # Lógica: Busca la primera fecha futura en el flujo del proceso
    # Flujo: Cierre -> Adjudicación -> Firma -> Inicio
    if pd.notna(row['FechaCierre']) and row['FechaCierre'] >= now:
        return row['FechaCierre'], "🔴 Por Cerrar"
    elif pd.notna(row['FechaAdjudicacion']) and row['FechaAdjudicacion'] >= now:
        return row['FechaAdjudicacion'], "🟡 Por Adjudicar"
    elif pd.notna(row['FechaEstimadaFirma']) and row['FechaEstimadaFirma'] >= now:
        return row['FechaEstimadaFirma'], "🔵 Por Firmar"
    elif pd.notna(row['FechaInicioContrato']) and row['FechaInicioContrato'] >= now:
        return row['FechaInicioContrato'], "🟢 Por Iniciar"
    else:
        return pd.NaT, "⚪ Histórico/Vencido"

# Aplicamos la lógica y separamos en dos columnas
df_res_filtrado[['FechaClave', 'EstadoFlujo']] = df_res_filtrado.apply(
    lambda row: pd.Series(obtener_fecha_clave(row)), axis=1
)

# ==============================================================================
# 2. INDICADORES LEAN (LEAD TIMES & FLUJO)
# ==============================================================================
# Basado en Lean: "El tiempo total que un cliente espera... (Lead Time)" [cite: 991]

st.markdown("### ⏱️ Indicadores de Flujo (Lead Times)")

# Cálculo de Lead Times (Días)
# Lead Time Administrativo: Creación a Publicación
df_res_filtrado['LT_Admin'] = (df_res_filtrado['FechaPublicacion'] - df_res_filtrado['FechaCreacion']).dt.days
# Lead Time Mercado: Publicación a Cierre
df_res_filtrado['LT_Mercado'] = (df_res_filtrado['FechaCierre'] - df_res_filtrado['FechaPublicacion']).dt.days
# Lead Time Resolución: Cierre a Adjudicación
df_res_filtrado['LT_Resolucion'] = (df_res_filtrado['FechaAdjudicacion'] - df_res_filtrado['FechaCierre']).dt.days

# Métricas Promedio
col1, col2, col3, col4 = st.columns(4)
with col1:
    avg_resolucion = df_res_filtrado['LT_Resolucion'].mean()
    st.metric("Ciclo de Resolución", f"{avg_resolucion:.1f} días", help="Promedio días entre Cierre y Adjudicación")
with col2:
    pendientes_adjudicar = len(df_res_filtrado[df_res_filtrado['EstadoFlujo'] == "🟡 Por Adjudicar"])
    st.metric("Cola de Adjudicación", f"{pendientes_adjudicar}", delta_color="inverse", help="Licitaciones cerradas esperando adjudicación")
with col3:
    prox_cierre = len(df_res_filtrado[df_res_filtrado['EstadoFlujo'] == "🔴 Por Cerrar"])
    st.metric("Cierres Próximos", f"{prox_cierre}", help="Licitaciones activas en mercado")
with col4:
    total_monto = df_res_filtrado['MontoEstimado'].sum()
    st.metric("Volumen en Juego", f"${total_monto:,.0f}")

# ==============================================================================
# 3. GESTIÓN VISUAL Y PRÓXIMOS EVENTOS
# ==============================================================================
# Basado en Lean: "Hacer visibles los problemas" y "Control Visual" [cite: 748, 968]

st.divider()
st.markdown("### 📅 Agenda de Prioridades (Semanal)")

# Filtros de tiempo para "Esta semana" y "Próxima semana"
hoy = pd.Timestamp.now().normalize()
fin_esta_semana = hoy + pd.Timedelta(days=(6 - hoy.weekday()))
fin_prox_semana = fin_esta_semana + pd.Timedelta(days=7)

# Crear un dataframe "Melted" para tener todos los eventos en una sola columna de fecha
# Esto permite ver si cierra o se adjudica en la misma vista
df_eventos = df_res_filtrado.melt(
    id_vars=['CodigoLicitacion', 'Nombre', 'C_Usuario', 'Estado'], 
    value_vars=['FechaCierre', 'FechaAdjudicacion', 'FechaEstimadaFirma'],
    var_name='TipoEvento', 
    value_name='FechaEvento'
).dropna(subset=['FechaEvento'])

# Filtrar eventos próximos
df_eventos_prox = df_eventos[
    (df_eventos['FechaEvento'] >= hoy) & 
    (df_eventos['FechaEvento'] <= fin_prox_semana)
].sort_values('FechaEvento')

# Visualización por Comprador (Carga de trabajo)
if not df_eventos_prox.empty:
    col_graf, col_ag = st.columns([1, 2])
    
    with col_graf:
        st.markdown("**Carga de Trabajo Próxima (Eventos)**")
        fig_carga = px.bar(
            df_eventos_prox, 
            x="C_Usuario", 
            color="TipoEvento",
            title="Eventos por Comprador (Próx. 14 días)",
            labels={"count": "Cantidad de Eventos"},
            color_discrete_map={
                "FechaCierre": "#e74c3c",       # Rojo (Urgente)
                "FechaAdjudicacion": "#f1c40f", # Amarillo (Proceso)
                "FechaEstimadaFirma": "#2ecc71" # Verde (Finalización)
            }
        )
        fig_carga.update_layout(xaxis_title=None, showlegend=True)
        st.plotly_chart(fig_carga, use_container_width=True)
        
    with col_ag:
        st.markdown("**Detalle de Próximos Vencimientos**")
        st.dataframe(
            df_eventos_prox[['FechaEvento', 'CodigoLicitacion', 'TipoEvento', 'C_Usuario', 'Nombre']].style.format({
                "FechaEvento": lambda t: t.strftime("%d-%m-%Y")
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "TipoEvento": st.column_config.TextColumn("Hito", help="Cierre, Adjudicación o Firma"),
                "C_Usuario": "Responsable",
                "CodigoLicitacion": "ID Licitación"
            }
        )
else:
    st.info("✅ No hay eventos críticos (Cierres o Adjudicaciones) programados para los próximos 14 días.")

# ==============================================================================
# 4. TABLA MAESTRA DETALLADA
# ==============================================================================
st.markdown("---")
st.markdown("## 📋 Panel de Control de Procesos (Gemba)")

# Ordenar por fecha clave (lo más urgente arriba)
df_sorted = df_res_filtrado.sort_values(by='FechaClave', ascending=True, na_position='last')

# Columnas a mostrar
cols_view = [
    'EstadoFlujo', 'FechaClave', 'CodigoLicitacion', 'Nombre', 
    'MontoEstimado', 'C_Usuario', 'Tipo', 'Estado'
]

# Filtro rápido por estado de flujo
filtro_estado = st.multiselect(
    "Filtrar por Etapa del Proceso:",
    options=["🔴 Por Cerrar", "🟡 Por Adjudicar", "🔵 Por Firmar", "🟢 Por Iniciar"],
    default=["🔴 Por Cerrar", "🟡 Por Adjudicar"]
)

if filtro_estado:
    df_sorted = df_sorted[df_sorted['EstadoFlujo'].isin(filtro_estado)]

st.dataframe(
    df_sorted[cols_view],
    use_container_width=True,
    hide_index=True,
    column_config={
        "MontoEstimado": st.column_config.NumberColumn("Monto", format="$ %,.0f"),
        "FechaClave": st.column_config.DateColumn(
            "Próx. Hito", 
            format="DD/MM/YYYY",
            help="Fecha del próximo evento crítico"
        ),
        "EstadoFlujo": st.column_config.TextColumn("Urgencia", help="Estado calculado según fechas"),
        "C_Usuario": "Comprador",
        "CodigoLicitacion": "ID"
    },
    height=500
)

# Nota sobre metodología Lean
with st.expander("📘 Referencia Metodológica Lean"):
    st.markdown("""
    * **Lead Time (Tiempo de Respuesta)[cite: 991]:** Tiempo total que transcurre desde que se crea la necesidad hasta que se resuelve (Adjudicación). Reducir este tiempo es clave para el flujo.
    * **Control Visual[cite: 968]:** El uso de semáforos (🔴🟡🟢) permite identificar desviaciones del estándar de manera inmediata.
    * **Heijunka (Nivelación)[cite: 797]:** El gráfico de carga por comprador ayuda a nivelar el trabajo y evitar cuellos de botella en personas específicas.
    """)
