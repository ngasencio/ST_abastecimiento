import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from style.ui import cargar_css

# Importación de datos
import api.LI_data_loader as loader
cargar_css()

# ============== CONFIGURACIÓN DE PÁGINA ===================
st.set_page_config(
    page_title="Dashboard Licitaciones 2026",
    page_icon="📄",
    layout="wide"
)

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

# ============== FUNCIONES AUXILIARES ===================

def obtener_semana_actual():
    """Retorna el inicio y fin de la semana actual (lunes a domingo)"""
    hoy = pd.Timestamp.now().normalize()
    inicio_semana = hoy - pd.Timedelta(days=hoy.weekday())  # Lunes
    fin_semana = inicio_semana + pd.Timedelta(days=6)  # Domingo
    return inicio_semana, fin_semana

def obtener_proxima_semana():
    """Retorna el inicio y fin de la próxima semana"""
    inicio_actual, _ = obtener_semana_actual()
    inicio_proxima = inicio_actual + pd.Timedelta(days=7)
    fin_proxima = inicio_proxima + pd.Timedelta(days=6)
    return inicio_proxima, fin_proxima

# ============== NORMALIZACIÓN DE DATOS ===================
for col in ["Estado", "C_Usuario", "C_Unidad"]:
    if col in df_res.columns:
        df_res[col] = df_res[col].astype(str).str.strip()

# Normalización de fechas
columnas_fechas = [
    "FechaCreacion", "FechaPublicacion", "FechaCierre", 
    "FechaAdjudicacion", "FechaEstimadaFirma", "FechaInicioContrato"
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

# ============== FILTRO DE VISTA SEMANAL ===================
st.markdown("## 📅 Filtro de Vista Semanal")

col_filtro1, col_filtro2, col_filtro3 = st.columns([2, 2, 1])

with col_filtro1:
    vista_semanal = st.selectbox(
        "Seleccionar Vista",
        ["Todas las Licitaciones", "Esta Semana", "Próxima Semana", "Esta Semana + Próxima Semana"],
        index=0
    )

with col_filtro2:
    inicio_actual, fin_actual = obtener_semana_actual()
    inicio_proxima, fin_proxima = obtener_proxima_semana()
    
    if vista_semanal == "Esta Semana":
        st.info(f"📆 {inicio_actual.strftime('%d/%m/%Y')} - {fin_actual.strftime('%d/%m/%Y')}")
    elif vista_semanal == "Próxima Semana":
        st.info(f"📆 {inicio_proxima.strftime('%d/%m/%Y')} - {fin_proxima.strftime('%d/%m/%Y')}")
    elif vista_semanal == "Esta Semana + Próxima Semana":
        st.info(f"📆 {inicio_actual.strftime('%d/%m/%Y')} - {fin_proxima.strftime('%d/%m/%Y')}")

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

# Aplicar filtro semanal
if vista_semanal == "Esta Semana":
    df_res_filtrado = df_res_filtrado[
        (df_res_filtrado['FechaClave'] >= inicio_actual) & 
        (df_res_filtrado['FechaClave'] <= fin_actual)
    ]
elif vista_semanal == "Próxima Semana":
    df_res_filtrado = df_res_filtrado[
        (df_res_filtrado['FechaClave'] >= inicio_proxima) & 
        (df_res_filtrado['FechaClave'] <= fin_proxima)
    ]
elif vista_semanal == "Esta Semana + Próxima Semana":
    df_res_filtrado = df_res_filtrado[
        (df_res_filtrado['FechaClave'] >= inicio_actual) & 
        (df_res_filtrado['FechaClave'] <= fin_proxima)
    ]

# Sincronizar con detalle
df_det_filtrado = df_det[df_det["CodigoLicitacion"].isin(df_res_filtrado["CodigoLicitacion"])]

# ============== COMPARATIVA SEMANAL ===================
st.markdown("---")
st.markdown("## 📊 Comparativa Semanal")

col_comp1, col_comp2 = st.columns(2)

# Esta Semana
df_esta_semana = df_res[
    (df_res['FechaClave'] >= inicio_actual) & 
    (df_res['FechaClave'] <= fin_actual)
]

# Próxima Semana
df_proxima_semana = df_res[
    (df_res['FechaClave'] >= inicio_proxima) & 
    (df_res['FechaClave'] <= fin_proxima)
]

with col_comp1:
    st.markdown("### 📅 Esta Semana")
    st.metric("Licitaciones", len(df_esta_semana))
    st.metric("Monto Total", f"${df_esta_semana['MontoEstimado'].sum():,.0f}")
    
    if len(df_esta_semana) > 0:
        fig_esta = px.pie(
            df_esta_semana,
            names='Estado',
            title='Distribución por Estado',
            hole=0.4
        )
        fig_esta.update_layout(height=300)
        st.plotly_chart(fig_esta, use_container_width=True)

with col_comp2:
    st.markdown("### 📅 Próxima Semana")
    st.metric("Licitaciones", len(df_proxima_semana))
    st.metric("Monto Total", f"${df_proxima_semana['MontoEstimado'].sum():,.0f}")
    
    if len(df_proxima_semana) > 0:
        fig_proxima = px.pie(
            df_proxima_semana,
            names='Estado',
            title='Distribución por Estado',
            hole=0.4
        )
        fig_proxima.update_layout(height=300)
        st.plotly_chart(fig_proxima, use_container_width=True)

# ==============================================================================
# 1. CONFIGURACIÓN Y CARGA DE DATOS
# ==============================================================================

st.markdown("## 📊 Tablero de Control de Licitaciones (Enfoque Lean)")
st.markdown("Monitorización del flujo de valor, lead times y próximos hitos críticos.")

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

c3, c4 = st.columns([1, 1])


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


# =====================================================================
# 3) PRÓXIMOS EVENTOS (ESTA SEMANA Y PRÓXIMA)
# =====================================================================
st.markdown("## 3) Agenda de Próximos Hitos")

hoy = pd.Timestamp.now().normalize()
fin_esta_semana = hoy + pd.Timedelta(days=(6 - hoy.weekday()))
fin_prox_semana = fin_esta_semana + pd.Timedelta(days=7)

value_vars = [c for c in ["FechaCierre", "FechaAdjudicacion", "FechaInicioContrato", "FechaEstimadaFirma"] if c in df_res_filtrado.columns]

if value_vars:
    df_eventos = df_res_filtrado.melt(
        id_vars=[c for c in ["CodigoLicitacion", "Nombre", "Tipo", "Estado", "C_Usuario"] if c in df_res_filtrado.columns],
        value_vars=value_vars,
        var_name="Evento",
        value_name="FechaEvento",
    ).dropna(subset=["FechaEvento"])

    df_eventos = df_eventos[(df_eventos["FechaEvento"] >= hoy) & (df_eventos["FechaEvento"] <= fin_prox_semana)].copy()
    df_eventos["Semana"] = np.where(df_eventos["FechaEvento"] <= fin_esta_semana, "Esta semana", "Próxima semana")
    df_eventos = df_eventos.sort_values("FechaEvento")

    ce1, ce2 = st.columns([1, 2])

    with ce1:
        st.markdown("### 📌 Carga por comprador")
        if not df_eventos.empty:
            fig_carga = px.bar(
                df_eventos,
                x="C_Usuario" if "C_Usuario" in df_eventos.columns else None,
                color="Evento",
                title="Eventos (14 días) por comprador",
            )
            fig_carga.update_layout(height=330, xaxis_title=None)
            st.plotly_chart(fig_carga, use_container_width=True)
        else:
            st.info("Sin eventos en los próximos 14 días.")

    with ce2:
        st.markdown("### 🗓️ Detalle próximos eventos")
        if df_eventos.empty:
            st.success("No hay hitos próximos en los próximos 14 días.")
        else:
            cols_ev = [c for c in ["Semana", "FechaEvento", "Evento", "CodigoLicitacion", "Nombre", "Tipo", "Estado", "C_Usuario"] if c in df_eventos.columns]
            st.dataframe(
                df_eventos[cols_ev],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "FechaEvento": st.column_config.DateColumn(format="DD-MM-YYYY"),
                },
            )
else:
    st.info("No se encontraron columnas de eventos (FechaCierre / FechaAdjudicacion / FechaInicioContrato / FechaEstimadaFirma).")

# =====================================================================
# 4) TABLA EJECUTIVA DE LICITACIONES RECIENTES + ALERTAS
# =====================================================================
st.markdown("## 4) Licitaciones recientes y urgencias")

cut = now - pd.Timedelta(days=90)
if "FechaCreacion" in df_res_filtrado.columns:
    df_recent = df_res_filtrado[df_res_filtrado["FechaCreacion"] >= cut].copy()
else:
    df_recent = df_res_filtrado.copy()

if "FechaCierre" in df_recent.columns:
    df_recent["Dias_a_Cierre"] = (df_recent["FechaCierre"] - now).dt.days
else:
    df_recent["Dias_a_Cierre"] = pd.NA

if "Estado" in df_recent.columns:
    cerrada_mask = df_recent["Estado"].astype(str).str.contains("Cerrad", case=False, na=False)
else:
    cerrada_mask = pd.Series(False, index=df_recent.index)

cols_show = [
    "CodigoLicitacion",
    "Nombre",
    "Tipo",
    "Estado",
    "EstadoFlujo",
    "FechaCierre",
    "Dias_a_Cierre",
    "C_Usuario",
    "FechaAdjudicacion",
]
cols_show = [c for c in cols_show if c in df_recent.columns]

df_table = df_recent.sort_values(["FechaClave"], ascending=True, na_position="last")

# Mostrar adjudicación solo si es cerrada
if "FechaAdjudicacion" in df_table.columns:
    df_table.loc[~cerrada_mask, "FechaAdjudicacion"] = pd.NaT


def _style_urgencia(df_in: pd.DataFrame):
    if "Dias_a_Cierre" not in df_in.columns:
        return df_in

    def _row_style(row):
        dias = row.get("Dias_a_Cierre")
        if pd.isna(dias):
            return [""] * len(row)
        try:
            dias = int(dias)
        except Exception:
            return [""] * len(row)

        if dias < 0:
            return ["background-color: rgba(108, 117, 125, 0.08)"] * len(row)
        if dias <= 2:
            return ["background-color: rgba(231, 76, 60, 0.18)"] * len(row)
        if dias <= 7:
            return ["background-color: rgba(241, 196, 15, 0.18)"] * len(row)
        return [""] * len(row)

    return df_in.style.apply(_row_style, axis=1)


if df_table.empty:
    st.info("No hay licitaciones recientes para mostrar.")
else:
    st.dataframe(
        _style_urgencia(df_table[cols_show].head(40)),
        use_container_width=True,
        hide_index=True,
        column_config={
            "FechaCierre": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "FechaAdjudicacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Dias_a_Cierre": st.column_config.NumberColumn("Días a cierre"),
        },
    )


# =====================================================================
# 6) ACCIONES PRIORITARIAS
# =====================================================================
st.markdown("## 6) Acciones prioritarias")

acc1, acc2, acc3 = st.columns(3)

with acc1:
    st.markdown("### 🔴 Por cerrar (<= 7 días)")
    if "Dias_a_Cierre" in df_recent.columns:
        urg = df_recent[pd.to_numeric(df_recent["Dias_a_Cierre"], errors="coerce").between(0, 7)].copy()
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


# Nota sobre metodología Lean
with st.expander("📘 Referencia Metodológica Lean"):
    st.markdown("""
    * **Lead Time (Tiempo de Respuesta)[cite: 991]:** Tiempo total que transcurre desde que se crea la necesidad hasta que se resuelve (Adjudicación). Reducir este tiempo es clave para el flujo.
    * **Control Visual[cite: 968]:** El uso de semáforos (🔴🟡🟢) permite identificar desviaciones del estándar de manera inmediata.
    * **Heijunka (Nivelación)[cite: 797]:** El gráfico de carga por comprador ayuda a nivelar el trabajo y evitar cuellos de botella en personas específicas.
    """)
