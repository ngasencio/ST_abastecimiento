# pages/licitaciones.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. Importación Correcta (basada en tu estructura de carpetas)###
from api.Consolidar_Licitaciones import ejecutar_consolidacion_LI

# 2. Llamada segura
# Esto ejecuta la lógica de unión y limpieza
bases = ejecutar_consolidacion_LI()

# 3. Asignación defensiva (evita el KeyError)
df_res = bases.get("RESUMEN", pd.DataFrame())
df_det = bases.get("DETALLES", pd.DataFrame())

# ===== CARGAR CSS =====
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

# --- INYECCIÓN DE CSS (Tus estilos) ---

st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #1748EB, #3f6ef2);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            📊 Licitaciones DSSO
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
st.markdown("### 📅 Cronograma con Duración por Etapa")

if not df_gantt.empty:
    fig = px.timeline(
        df_gantt, 
        x_start="Inicio", 
        x_end="Fin", 
        y="Identificador", 
        color="Etapa",
        text="Texto_Etiqueta", # <--- AQUÍ AGREGAMOS LA ETIQUETA
        hover_data={"Identificador": False, "Nombre_Completo": True, "Días": True, "Texto_Etiqueta": False},
        color_discrete_sequence=px.colors.qualitative.Prism
    )

    # --- A) AJUSTE DE POSICIÓN DE TEXTO ---
    fig.update_traces(
        textposition='inside', # Pone el texto dentro de la barra
        insidetextanchor='middle', # Lo centra
        textfont_size=12
    )

    # --- B) LÍNEA VERTICAL DE HOY ---
    hoy = datetime(2026, 1, 17)
    fig.add_vline(
        x=hoy.timestamp() * 1000, 
        line_width=3, 
        line_dash="dash", 
        line_color="red",
        annotation_text="HOY", 
        annotation_position="top right"
    )

    # --- C) AJUSTES FINALES ---
    fig.update_yaxes(autorange="reversed", title="Licitación (ID | Nombre)")
    
    cantidad_filas = int(len(df_filtrado["Etiqueta_Y"].unique()))
    alto_grafico = 400 + (cantidad_filas * 35) # Un poco más de espacio por fila para las etiquetas

    fig.update_layout(
        height=alto_grafico,
        legend_title="Etapas",
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos suficientes para mostrar el cronograma.")
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