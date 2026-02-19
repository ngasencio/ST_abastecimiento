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



def procesar_estados_licitacion(df):
    now = pd.Timestamp.now()

    def calcular_hito_y_etapa(row):
        # --- ORDEN CRONOLÓGICO INVERSO PARA DETECTAR ETAPA ACTUAL ---
               
                   
        # 1. Inicio y publicación
        if pd.notna(row.get('FechaPublicacion')) and row['FechaPublicacion'] >= now:
            return row['FechaPublicacion'], "📢 Publicada"
        if pd.notna(row.get('FechaCreacion')) and row['FechaCreacion'] >= now:
            return row['FechaCreacion'], "🆕 Creada"


         # 2. Etapa de consultas
        if pd.notna(row.get('FechaPubRespuestas')) and row['FechaPubRespuestas'] >= now:
            return row['FechaPubRespuestas'], "💬 Respuestas"
        if pd.notna(row.get('FechaEntregaAntecedentes')) and row['FechaEntregaAntecedentes'] >= now:
            return row['FechaEntregaAntecedentes'], "📂 Antecedentes"
        if pd.notna(row.get('FechaVisitaTerreno')) and row['FechaVisitaTerreno'] >= now:
            return row['FechaVisitaTerreno'], "👷 Visita Terreno"

        # 3. Cierre y aperturas
        if pd.notna(row.get('FechaActoAperturaEconomica')) and row['FechaActoAperturaEconomica'] >= now:
            return row['FechaActoAperturaEconomica'], "💰 Apertura Econ."
        if pd.notna(row.get('FechaActoAperturaTecnica')) and row['FechaActoAperturaTecnica'] >= now:
            return row['FechaActoAperturaTecnica'], "🛠️ Apertura Técn."
        if pd.notna(row.get('FechaCierre')) and row['FechaCierre'] >= now:
            return row['FechaCierre'], "⏳ Cierre Ofertas"

        # 4. Evaluación y adjudicación
        if pd.notna(row.get('FechaAdjudicacion')) and row['FechaAdjudicacion'] >= now:
            return row['FechaAdjudicacion'], "🏆 Adjudicación"
        if pd.notna(row.get('FechaEstimadaAdjudicacion')) and row['FechaEstimadaAdjudicacion'] >= now:
            return row['FechaEstimadaAdjudicacion'], "📅 Adj. Estimada"
        if pd.notna(row.get('FechaTiempoEvaluacion')) and row['FechaTiempoEvaluacion'] >= now:
            return row['FechaTiempoEvaluacion'], "🧮 En Evaluación"
            
          
        # 5. Firma y ejecución
        if pd.notna(row.get('FechaFinal')) and row['FechaFinal'] >= now:
            return row['FechaFinal'], "🏁 Finalización"
        if pd.notna(row.get('FechaInicioContrato')) and row['FechaInicioContrato'] >= now:
            return row['FechaInicioContrato'], "🚀 Inicio Contrato"
        if pd.notna(row.get('FechaEstimadaFirma')) and row['FechaEstimadaFirma'] >= now:
            return row['FechaEstimadaFirma'], "✍️ Firma Pendiente"
           
             
        return pd.NaT, "✅ Proceso Finalizado"

    # Aplicamos a df_filtrado (usando tu convención de nombre)
    if not df.empty:
        df[['FechaClave', 'EstadoFlujo']] = df.apply(
            lambda row: pd.Series(calcular_hito_y_etapa(row)), axis=1
        )
    return df

# Procesamos los datos antes de mostrar la tabla
df_res_filtrado = procesar_estados_licitacion(df_res_filtrado)

# ============== KPIs ===================
st.markdown("## 📈 Resumen Ejecutivo")

c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

with c_kpi1:
    total_lic_general = df_res["CodigoLicitacion"].nunique()
    total_lic_filtrado = df_res_filtrado["CodigoLicitacion"].nunique()
    porcentaje_lic = (total_lic_filtrado / total_lic_general) * 100 if total_lic_general > 0 else 0
    
    st.metric(
        "📋 Total Licitaciones",
        f"{total_lic_filtrado:,}",
        f"{porcentaje_lic:.1f}% del total"
    )

with c_kpi2:
    monto_total_gral = df_res["MontoEstimado"].sum()
    monto_total_filt = df_res_filtrado["MontoEstimado"].sum()
    porcentaje_monto = (monto_total_filt / monto_total_gral) * 100 if monto_total_gral > 0 else 0
    
    st.metric(
        "💰 Monto Estimado",
        f"${monto_total_filt:,.0f}",
        f"{porcentaje_monto:.1f}% del total"
    )

with c_kpi3:
    total_items = df_det_filtrado['Cantidad'].sum() if 'Cantidad' in df_det_filtrado.columns else 0
    st.metric(
        "📦 Total Items",
        f"{int(total_items):,}"
    )

with c_kpi4:
    estados_criticos = df_res_filtrado[df_res_filtrado['Estado'].str.contains('Publicada|Cierre', case=False, na=False)]
    st.metric(
        "⚠️ Estados Críticos",
        f"{len(estados_criticos)}"
    )

# =====================================================================
# 2) VISUALIZACIONES
# =====================================================================
st.markdown("## 2) Tendencias y Comparativas")

c1, c2 = st.columns([1, 1])

with c1:
    df_tipo = df_res_filtrado.groupby("Tipo", as_index=False).agg(Cantidad=("CodigoLicitacion", "nunique")) if "CodigoLicitacion" in df_res_filtrado.columns else df_res_filtrado.groupby("Tipo", as_index=False).size().rename(columns={"size": "Cantidad"})
    df_tipo = df_tipo.sort_values("Cantidad", ascending=False).head(12)
    fig_tipo = px.bar(
        df_tipo,
        x="Tipo",
        y="Cantidad",
        title="Distribución por Tipo",
        labels={"Tipo": "Tipo", "Cantidad": "Licitaciones"},
    )
    fig_tipo.update_layout(height=360, xaxis_title=None)
    st.plotly_chart(fig_tipo, use_container_width=True)

with c2:
    df_usr = df_res_filtrado.groupby("C_Usuario", as_index=False).agg(Cantidad=("CodigoLicitacion", "nunique")) if "CodigoLicitacion" in df_res_filtrado.columns else df_res_filtrado.groupby("C_Usuario", as_index=False).size().rename(columns={"size": "Cantidad"})
    df_usr = df_usr.sort_values("Cantidad", ascending=False).head(15)
    fig_usr = px.bar(
        df_usr,
        x="Cantidad",
        y="C_Usuario",
        orientation="h",
        title="Licitaciones por Comprador",
        labels={"C_Usuario": "Comprador", "Cantidad": "Licitaciones"},
    )
    fig_usr.update_layout(height=360, yaxis_title=None)
    st.plotly_chart(fig_usr, use_container_width=True)


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
# 4. TABLA MAESTRA DETALLADA (GEMBA)
# ==============================================================================
st.markdown("---")
st.markdown("## 📋 Panel de Control de Procesos (Gemba)")

# Ordenar por fecha clave (lo más urgente arriba)
df_sorted = df_res_filtrado.sort_values(by='FechaClave', ascending=True, na_position='last')

# Columnas a mostrar
cols_view = [
    'EstadoFlujo', 'FechaClave', 'CodigoLicitacion', 'Nombre', 
    'MontoEstimado', 'C_Usuario', 'Tipo'
]

# Filtro rápido por estado de flujo dinámico
opciones_estado = sorted(df_res_filtrado['EstadoFlujo'].unique())
filtro_estado = st.multiselect(
    "Filtrar por Etapa Actual del Flujo:",
    options=opciones_estado,
    default=[e for e in opciones_estado if "✅" not in e] # Por defecto excluye finalizados
)

if filtro_estado:
    df_sorted = df_sorted[df_sorted['EstadoFlujo'].isin(filtro_estado)]

df_sorted["MontoEstimado"] = df_sorted["MontoEstimado"].apply(
    lambda x: f"${x:,.0f}".replace(",", ".") if pd.notna(x) else ""
)

# Renderizado de la Tabla
st.dataframe(
    df_sorted[cols_view],
    use_container_width=True,
    hide_index=True,
    column_config={
        "EstadoFlujo": st.column_config.TextColumn(
            "📍 Etapa Actual", 
            help="Hito más próximo detectado según el calendario"
        ),
        "FechaClave": st.column_config.DateColumn(
            "📅 Fecha Hito", 
            format="DD/MM/YYYY",
            help="Fecha del evento mostrado en la etapa"
        ),
        "MontoEstimado": st.column_config.NumberColumn(
            "Monto Est.", 
            format="$ %,.0f"
        ),
        "CodigoLicitacion": "ID Licitación",
        "C_Usuario": "Comprador Responsable",
        "Nombre": st.column_config.TextColumn("Nombre del Proceso", width="large"),
        "Tipo": "Tipo"
    },
    height=600
)


# =====================================================================
# 6) ACCIONES PRIORITARIAS
# =====================================================================
st.markdown("## 6) Acciones prioritarias")

acc1, acc2, acc3 = st.columns(3)

with acc1:
    st.markdown("### 🔴 Por cerrar (<= 7 días)")
    if "Dias_a_Cierre" in df_res_filtrado.columns:
        urg = df_res_filtrado[pd.to_numeric(df_res_filtrado["Dias_a_Cierre"], errors="coerce").between(0, 7)].copy()
        urg = urg.sort_values("Dias_a_Cierre")
        if urg.empty:
            st.success("Sin cierres críticos en los próximos 7 días.")
        else:
            cols_u = [c for c in ["CodigoLicitacion", "Nombre", "C_Usuario", "FechaCierre", "Dias_a_Cierre"] if c in urg.columns]
            st.dataframe(
                urg[cols_u].head(15),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "FechaCierre": st.column_config.DateColumn(format="DD-MM-YYYY"),
                },
            )

with acc2:
    st.markdown("### 🟡 Cerradas sin adjudicar")
    if "Estado" in df_res_filtrado.columns and "FechaAdjudicacion" in df_res_filtrado.columns:
        cerr = df_res_filtrado[df_res_filtrado["Estado"].astype(str).str.contains("Cerrad", case=False, na=False)].copy()
        sin_adj = cerr[cerr["FechaAdjudicacion"].isna()].copy()
        if sin_adj.empty:
            st.success("Sin licitaciones cerradas pendientes de adjudicación.")
        else:
            cols_s = [c for c in ["CodigoLicitacion", "Nombre", "C_Usuario", "FechaCierre"] if c in sin_adj.columns]
            st.dataframe(
                sin_adj.sort_values("FechaCierre", ascending=False)[cols_s].head(15),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "FechaCierre": st.column_config.DateColumn(format="DD-MM-YYYY"),
                },
            )

with acc3:
    st.markdown("### 🔵 Concentración por comprador (Top)")
    top_usr = df_res_filtrado.groupby("C_Usuario", as_index=False).size().rename(columns={"size": "Licitaciones"}).sort_values("Licitaciones", ascending=False).head(10)
    st.dataframe(top_usr, use_container_width=True, hide_index=True)
