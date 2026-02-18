import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

# Importamos tu loader. 
# Si LI_data_loader.py está en la misma carpeta, se importa así:
import api.LI_data_loader as loader 
# Si está dentro de una carpeta llamada 'api', sería: import api.LI_data_loader as loader

from style.ui import cargar_css

# =============================================================================
# CONFIGURACIÓN E ESTILO
# =============================================================================
st.set_page_config(page_title="Gestión de Licitaciones", layout="wide", page_icon="📊")
cargar_css()

# =============================================================================
# 1. LÓGICA DE NEGOCIO Y PROCESAMIENTO (CACHÉ)
# =============================================================================
@st.cache_data(ttl=3600, show_spinner="Procesando Inteligencia de Negocios...")
def cargar_y_procesar_datos():
    """
    Carga usando tu LI_data_loader y aplica la lógica de estados y métricas Lean.
    """
    # 1. CARGA USANDO TU LOADER ORIGINAL
    try:
        # Llamamos a la función pública de tu archivo LI_data_loader.py
        df_res, df_det = loader.cargar_maestros()
    except Exception as e:
        st.error(f"Error crítico al cargar datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if df_res.empty:
        return df_res, df_det

    df = df_res.copy()

    # 2. LIMPIEZA Y NORMALIZACIÓN (Complementaria al loader)
    # Normalizamos textos clave para los filtros
    cols_texto = ["Estado", "C_Usuario", "C_Unidad", "Tipo"]
    for col in cols_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            if col == "C_Usuario": 
                df[col] = df[col].replace(["NAN", "nan", "None"], "SIN ASIGNAR")

    # 3. LÓGICA DE ESTADOS DEL PROCESO (Máquina de Estados)
    now = pd.Timestamp.now()

    def determinar_estado_flujo(row):
        # Prioridad 1: Estados administrativos finales
        estado_admin = row.get("Estado", "")
        if "ADJUDICADA" in estado_admin or "DESIERTA" in estado_admin or "REVOCADA" in estado_admin:
            return "8. Finalizado/Cerrado"
        
        # Prioridad 2: Estados basados en fechas (Secuencial)
        if pd.notna(row.get('FechaInicioContrato')):
            return "7. En Ejecución"
        
        if pd.notna(row.get('FechaAdjudicacion')):
            return "6. En Formalización"
            
        if pd.notna(row.get('FechaCierre')):
            if row['FechaCierre'] < now:
                # Ya pasó el cierre, pero no hay adjudicación -> Está evaluando
                return "5. En Evaluación"
            else:
                # Fecha cierre futura -> Licitación Abierta
                if pd.notna(row.get('FechaPubRespuestas')) and row['FechaPubRespuestas'] > now:
                    return "2. En Consultas"
                return "3. Publicada / Ofertas"
        
        if pd.notna(row.get('FechaPublicacion')):
            return "1. Publicada"
            
        return "0. En Preparación"

    df_res["Etapa_Actual"] = df_res.apply(determinar_estado_flujo, axis=1)

    # 4. CÁLCULO DE LEAD TIMES (Métricas Lean)
    # Usamos .dt.days para obtener números enteros
    if "FechaAdjudicacion" in df_res.columns and "FechaPublicacion" in df_res.columns:
        df_res["LT_Proceso_Compra"] = (df_res["FechaAdjudicacion"] - df_res["FechaPublicacion"]).dt.days
    
    if "FechaAdjudicacion" in df_res.columns and "FechaCierre" in df_res.columns:
        df_res["LT_Evaluacion"] = (df_res["FechaAdjudicacion"] - df_res["FechaCierre"]).dt.days

    # 5. ALERTAS DE GESTIÓN (Semáforo)
    def get_proximo_hito(row):
        # Definimos qué fechas queremos monitorear
        hitos = {
            "FechaCierre": "Cierre Ofertas",
            "FechaAdjudicacion": "Adjudicación",
            "FechaEstimadaFirma": "Firma Contrato"
        }
        min_date = pd.NaT
        hito_name = "Sin Hitos Próximos"
        
        for col, name in hitos.items():
            if col in row and pd.notna(row[col]) and row[col] >= now:
                if pd.isna(min_date) or row[col] < min_date:
                    min_date = row[col]
                    hito_name = name
        return min_date, hito_name

    df_res[["Fecha_Prox_Hito", "Nombre_Hito"]] = df_res.apply(lambda row: pd.Series(get_proximo_hito(row)), axis=1)
    
    # Días faltantes
    df_res["Dias_para_Hito"] = (df_res["Fecha_Prox_Hito"] - now).dt.days
    
    # Categorización de Urgencia
    df_res["Urgencia"] = np.where(
        (df_res["Dias_para_Hito"] >= 0) & (df_res["Dias_para_Hito"] <= 7), "🔴 Crítico (7 días)",
        np.where((df_res["Dias_para_Hito"] > 7) & (df_res["Dias_para_Hito"] <= 14), "🟡 Alerta (14 días)", "🟢 Normal")
    )

    return df_res, df_det

# --- EJECUCIÓN DE CARGA ---
df_res, df_det = cargar_y_procesar_datos()

if df_res.empty:
    st.error("⚠️ No se pudieron cargar los datos. Verifica que los archivos CSV existan en la carpeta 'LI_DSSO/MAESTROS'.")
    st.stop()
# =============================================================================
# 2. HEADER Y FILTROS LATERALES
# =============================================================================
st.markdown("""
    <div style="padding: 1rem; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #138AEC;">
        <h2 style="margin:0; color: #0f2c4a;">🚀 Centro de Control de Licitaciones</h2>
        <p style="margin:0; font-size: 14px; color: #555;">Seguimiento de flujo continuo, alertas y eficiencia del proceso.</p>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 Filtros de Gestión")
    
    # Filtros Dinámicos
    etapas_disp = sorted(df_res["Etapa_Actual"].unique())
    sel_etapa = st.multiselect("Fase del Proceso", etapas_disp)
    
    usuarios_disp = sorted(df_res["C_Usuario"].unique())
    sel_user = st.multiselect("Comprador Responsable", usuarios_disp)
    
    tipos_disp = sorted(df_res["Tipo"].unique())
    sel_tipo = st.multiselect("Tipo Licitación", tipos_disp)
    
    st.divider()
    ver_criticos = st.checkbox("🔥 Ver solo Urgencias (Próx. 7 días)", value=False)

# Aplicación de Filtros
df_view = df_res.copy()
if sel_etapa: df_view = df_view[df_view["Etapa_Actual"].isin(sel_etapa)]
if sel_user: df_view = df_view[df_view["C_Usuario"].isin(sel_user)]
if sel_tipo: df_view = df_view[df_view["Tipo"].isin(sel_tipo)]
if ver_criticos: df_view = df_view[df_view["Urgencia"] == "🔴 Crítico (7 días)"]

# =============================================================================
# 3. KPIs ESTRATÉGICOS (LEAN)
# =============================================================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    n_activos = len(df_view[~df_view["Etapa_Actual"].str.contains("Finalizado")])
    st.metric("Procesos Activos", n_activos, "En curso")

with kpi2:
    # Lead Time Promedio de Evaluación (Eficiencia Interna)
    lt_eval = df_view["LT_Evaluacion"].mean()
    st.metric("Tiempo Prom. Evaluación", f"{lt_eval:.1f} días", help="Días desde Cierre a Adjudicación")

with kpi3:
    # Procesos en Evaluación (Cuello de botella potencial)
    n_eval = len(df_view[df_view["Etapa_Actual"] == "5. En Evaluación"])
    st.metric("En Evaluación", n_eval, "Esperando Adjudicación", delta_color="inverse")

with kpi4:
    # Urgencias Inmediatas
    n_criticos = len(df_view[df_view["Urgencia"] == "🔴 Crítico (7 días)"])
    st.metric("Alertas Semanales", n_criticos, "Vencen < 7 días", delta_color="inverse")

st.divider()

# =============================================================================
# 4. PESTAÑAS DE GESTIÓN
# =============================================================================
tab_agenda, tab_analisis, tab_detalle = st.tabs(["📅 Agenda de Vencimientos", "📊 Análisis de Flujo", "📋 Tabla Maestra"])

# --- TAB 1: AGENDA (PRÓXIMOS EVENTOS) ---
with tab_agenda:
    st.subheader("Próximos Hitos Críticos (Semana Vista)")
    
    # Filtramos solo lo que tiene fecha futura próxima
    df_agenda = df_view[
        (df_view["Fecha_Prox_Hito"].notna()) & 
        (df_view["Dias_para_Hito"] >= 0) & 
        (df_view["Dias_para_Hito"] <= 30)
    ].sort_values("Fecha_Prox_Hito")
    
    if not df_agenda.empty:
        # Creamos una línea de tiempo visual simple con tabla
        st.dataframe(
            df_agenda,
            column_order=["Urgencia", "Fecha_Prox_Hito", "Nombre_Hito", "CodigoLicitacion", "Nombre", "C_Usuario", "Etapa_Actual"],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Urgencia": st.column_config.TextColumn("Prioridad"),
                "Fecha_Prox_Hito": st.column_config.DateColumn("Fecha Límite", format="DD/MM/YYYY"),
                "Nombre_Hito": st.column_config.TextColumn("Evento"),
                "CodigoLicitacion": "ID Licitación",
                "Etapa_Actual": st.column_config.TextColumn("Fase Actual")
            }
        )
    else:
        st.info("✅ No hay vencimientos críticos en los próximos 30 días para los filtros seleccionados.")

# --- TAB 2: ANÁLISIS (GRÁFICOS) ---
with tab_analisis:
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("**Distribución por Etapa del Proceso (Kanban)**")
        # Agrupamos por etapa para ver dónde están los "tapones"
        df_etapas = df_view["Etapa_Actual"].value_counts().reset_index()
        df_etapas.columns = ["Etapa", "Cantidad"]
        df_etapas = df_etapas.sort_values("Etapa")
        
        fig_funnel = px.funnel(df_etapas, x='Cantidad', y='Etapa', title="Embudo de Licitaciones")
        st.plotly_chart(fig_funnel, use_container_width=True)
        
    with col_g2:
        st.markdown("**Carga de Trabajo por Comprador (Heijunka)**")
        # Contamos licitaciones activas por usuario
        df_activos = df_view[~df_view["Etapa_Actual"].str.contains("Finalizado")]
        df_carga = df_activos["C_Usuario"].value_counts().reset_index().head(10)
        df_carga.columns = ["Comprador", "Procesos Activos"]
        
        fig_bar = px.bar(df_carga, x="Procesos Activos", y="Comprador", orientation='h', 
                         color="Procesos Activos", color_continuous_scale="Blues")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Gráfico de Lead Times (Boxplot para ver variabilidad)
    st.markdown("**Variabilidad de Tiempos de Evaluación (Días)**")
    fig_box = px.box(df_view, x="Tipo", y="LT_Evaluacion", points="all", 
                     title="Tiempo de Evaluación por Tipo de Licitación")
    st.plotly_chart(fig_box, use_container_width=True)

# --- TAB 3: DETALLE MAESTRO ---
with tab_detalle:
    st.markdown("### Listado Completo de Procesos")
    
    # Preparamos columnas para visualización limpia
    cols_mostrar = [
        "CodigoLicitacion", "Nombre", "Tipo", "Etapa_Actual", 
        "FechaCierre", "FechaAdjudicacion", "C_Usuario", "MontoEstimado"
    ]
    
    st.dataframe(
        df_view.sort_values("FechaCreacion", ascending=False),
        column_order=cols_mostrar,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CodigoLicitacion": st.column_config.TextColumn("ID", help="Código Mercado Público"),
            "MontoEstimado": st.column_config.NumberColumn("Monto Est.", format="$ %,.0f"),
            "FechaCierre": st.column_config.DateColumn("Cierre", format="DD/MM/YYYY"),
            "FechaAdjudicacion": st.column_config.DateColumn("Adjudicación", format="DD/MM/YYYY"),
            "Etapa_Actual": st.column_config.TextColumn("Estado", help="Fase calculada del proceso"),
        }
    )

# =============================================================================
# NOTAS METODOLÓGICAS
# =============================================================================
with st.expander("📘 Guía de Interpretación Lean"):
    st.markdown("""
    * **Estados de Flujo:** Se calculan dinámicamente según las fechas. Si la fecha de cierre ya pasó y no hay adjudicación, el sistema asume **"En Evaluación"**.
    * **Gestión Visual:** Los colores Rojo/Amarillo en la Agenda indican prioridad inmediata (Just-in-Time).
    * **Lead Time:** El tiempo de evaluación es un indicador clave de "Desperdicio" (Espera) si supera los estándares definidos.
    """)