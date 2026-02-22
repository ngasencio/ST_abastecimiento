import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from style.ui import cargar_css
from api import LI_data_loader as loader
import plotly.graph_objects as go
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
import os
import logging
from pathlib import Path

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
        pass
        
except Exception as e:
    st.error(f"Ocurrió un error en la carga: {e}")
    st.stop()

# ============== EJECUCIÓN DE CARGA ===================
df_res, df_det = df_MaestroLI_Resumen, df_MaestroLI_Detalle
df_filtrado = df_res.copy()


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


# =============================================================================
# 2. HEADER Y FILTROS LATERALES
# =============================================================================

st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">🧾 Tablero de Control de Licitaciones</div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">Seguimiento de flujo continuo, alertas y eficiencia del proceso.</div>
    </div>
    """, unsafe_allow_html=True
)


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
        # Orden de hitos según flujo completo (sin considerar FechaFinal para el cálculo)
        orden_fechas_hitos = [
            "FechaCreacion",
            "FechaInicio",
            "FechaPublicacion",
            "FechaPubRespuestas",
            "FechaSoporteFisico",
            "FechaVisitaTerreno",
            "FechaEntregaAntecedentes",
            "FechaCierre",
            "FechaActoAperturaTecnica",
            "FechaActoAperturaEconomica",
            "FechaTiempoEvaluacion",
            "FechaAdjudicacion",
            "FechaEstimadaAdjudicacion",
            "FechaEstimadaFirma",
            "FechaInicioContrato",
        ]

        iconos_estado = {
            "FechaCreacion": "🆕 Creada",
            "FechaInicio": "🚀 Inicio",
            "FechaPublicacion": "📢 Publicada",
            "FechaPubRespuestas": "💬 Respuestas",
            "FechaSoporteFisico": "📎 Soporte Físico",
            "FechaVisitaTerreno": "👷 Visita Terreno",
            "FechaEntregaAntecedentes": "📂 Antecedentes",
            "FechaCierre": "⏳ Cierre Ofertas",
            "FechaActoAperturaTecnica": "🛠️ Apertura Técn.",
            "FechaActoAperturaEconomica": "💰 Apertura Econ.",
            "FechaTiempoEvaluacion": "🧮 En Evaluación",
            "FechaAdjudicacion": "🏆 Adjudicación",
            "FechaEstimadaAdjudicacion": "📅 Adj. Estimada",
            "FechaEstimadaFirma": "✍️ Firma Pendiente",
            "FechaInicioContrato": "🚀 Inicio Contrato",
        }

        # Buscar el hito futuro más cercano considerando fecha y hora
        fecha_clave = pd.NaT
        estado = "✅ Proceso Finalizado"

        for col in orden_fechas_hitos:
            valor = row.get(col)
            if pd.notna(valor) and valor >= now:
                if pd.isna(fecha_clave) or valor < fecha_clave:
                    fecha_clave = valor
                    estado = iconos_estado.get(col, "📍 Próximo Hito")

        return fecha_clave, estado

    def calcular_estado_flujo_simple(row):
        pub = row.get("FechaPublicacion")
        preguntas = row.get("FechaPubRespuestas") if "FechaPubRespuestas" in row.index else row.get("FechaPreguntas")
        cierre = row.get("FechaCierre")
        estimada_adj = row.get("FechaEstimadaAdjudicacion")

        # Asegurar comparación con fecha y hora completa
        if pd.notna(pub) and pd.notna(preguntas) and pub <= now < preguntas:
            return "💬 Responder Preguntas"
        if pd.notna(preguntas) and pd.notna(cierre) and preguntas <= now < cierre:
            return "⏳ Por Cerrar"
        if pd.notna(cierre) and pd.notna(estimada_adj) and cierre <= now < estimada_adj:
            return "🧮 En Evaluación"

        # Estados complementarios simplificados
        if pd.notna(pub) and now < pub:
            return "📢 Pendiente de Publicación"
        if pd.notna(estimada_adj) and now >= estimada_adj:
            return "🏁 Post Adjudicación"

        return "Sin Clasificar"

    # Aplicamos a df_filtrado (usando tu convención de nombre)
    if not df.empty:
        df[["FechaClave", "EstadoFlujo"]] = df.apply(
            lambda row: pd.Series(calcular_hito_y_etapa(row)), axis=1
        )
        df["EstadoFlujoSimple"] = df.apply(calcular_estado_flujo_simple, axis=1)
    return df

# Procesamos los datos antes de mostrar la tabla
df_res_filtrado = procesar_estados_licitacion(df_res_filtrado)


# ==============================================================================
# 4. TABLA MAESTRA DETALLADA (GEMBA)
# ==============================================================================

st.markdown("## 📋 Panel de Control de Procesos (Gemba)")

# Ordenar por fecha clave (lo más urgente arriba)
df_sorted = df_res_filtrado.sort_values(by='FechaClave', ascending=True, na_position='last')

# Columnas a mostrar
cols_view = [
    "EstadoFlujo",
    "EstadoFlujoSimple",
    "FechaClave",
    "CodigoLicitacion",
    "Nombre",
    "MontoEstimado",
    "C_Usuario",
    "Tipo",
]

# Filtro rápido por estado de flujo dinámico
iconos_excluir = ["✅", "✍️"]
opciones_estado = sorted(df_res_filtrado['EstadoFlujo'].unique())
filtro_estado = st.multiselect(
    "Filtrar por Etapa Actual del Flujo:",
    options=opciones_estado,
    default=[e for e in opciones_estado if not any(icono in e for icono in iconos_excluir)]
)

if filtro_estado:
    df_sorted = df_sorted[df_sorted['EstadoFlujo'].isin(filtro_estado)]

st.caption(f"Total licitaciones en la tabla: {len(df_sorted):,}")

# Renderizado de la Tabla
df_view = df_sorted[cols_view].copy()
if "MontoEstimado" in df_view.columns:
    def _fmt_clp(v):
        if pd.isna(v):
            return ""
        try:
            return f"$ {float(v):,.0f}".replace(",", ".")
        except Exception:
            return str(v)

    df_view["MontoEstimado"] = df_view["MontoEstimado"].apply(_fmt_clp)


gemba_sel = st.dataframe(
    df_view,
    use_container_width=True,
    hide_index=True,
    column_config={
        "EstadoFlujo": st.column_config.TextColumn(
            "📍 Etapa Actual",
            help="Hito más próximo detectado según el calendario",
        ),
        "FechaClave": st.column_config.DateColumn(
            "📅 Fecha Hito",
            format="DD/MM/YYYY",
            help="Fecha del evento mostrado en la etapa",
        ),
        "MontoEstimado": st.column_config.TextColumn("Monto Est. (CLP)"),
        "CodigoLicitacion": "ID Licitación",
        "C_Usuario": "Comprador Responsable",
        "Nombre": st.column_config.TextColumn("Nombre del Proceso", width="large"),
        "Tipo": "Tipo",
    },
    height=600,
    on_select="rerun",
    selection_mode="single-row",
    key="gemba_table",
)


def _fmt_fecha(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    try:
        ts = pd.to_datetime(v, errors="coerce")
        if pd.isna(ts):
            return str(v)
        return ts.strftime("%d-%m-%Y %H:%M:%S")
    except Exception:
        return str(v)


def _render_detalle_licitacion(codigo_licitacion: str) -> None:
    row = df_res_filtrado[df_res_filtrado["CodigoLicitacion"].astype(str) == str(codigo_licitacion)].head(1)
    if row.empty:
        st.info("No se encontró la licitación seleccionada con los filtros actuales.")
        return

    r = row.iloc[0]

    # Header compacto
    st.markdown(f"### 📄 `{codigo_licitacion}`")
    if "Nombre" in row.columns:
        st.markdown(f"**{r.get('Nombre', '')}**")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Layout de dos columnas: Datos Generales y Fechas lado a lado
    col_datos, col_fechas = st.columns(2, gap="medium")

    with col_datos:
        st.markdown("#### 📋 Datos Generales")
        estado_raw = str(r.get("Estado", "") or "").strip()
        estado_norm = estado_raw.lower()
        if "adjudic" in estado_norm:
            estado_view = "🏆 Adjudicada"
        elif "desierta" in estado_norm:
            estado_view = "🚫 Desierta"
        elif "publicad" in estado_norm:
            estado_view = "📢 Publicada"
        elif "cerrad" in estado_norm:
            estado_view = "⏳ Cerrada"
        else:
            estado_view = estado_raw

        # Formatear MontoEstimado en CLP
        monto_val = r.get("MontoEstimado", "")
        monto_formateado = ""
        if monto_val is not None and str(monto_val).strip():
            try:
                monto_float = float(monto_val)
                monto_formateado = f"$ {monto_float:,.0f}".replace(",", ".")
            except (ValueError, TypeError):
                monto_formateado = str(monto_val)

        datos_generales = {
            "Estado": estado_view,
            "Tipo": r.get("Tipo", ""),
            "Moneda": r.get("Moneda", ""),
            "Monto Estimado": monto_formateado,
            "Comprador": r.get("C_Usuario", ""),
            "Unidad": r.get("C_Unidad", ""),
            "Organismo": r.get("C_NombreOrganismo", ""),
            "Región": r.get("C_RegionUnidad", ""),
            "Comuna": r.get("C_ComunaUnidad", ""),
        }
        dg_df = pd.DataFrame(
            [{"Campo": k, "Valor": ("" if v is None else str(v))} for k, v in datos_generales.items() if k is not None],
        )
        st.dataframe(
            dg_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Campo": st.column_config.TextColumn("Campo", width="small"),
                "Valor": st.column_config.TextColumn("Valor", width="medium"),
            },
            height=350,
        )

    with col_fechas:
        st.markdown("#### 📅 Fechas")
        orden_fechas = [
            "FechaCreacion",
            "FechaInicio",
            "FechaPublicacion",
            "FechaPubRespuestas",
            "FechaSoporteFisico",
            "FechaVisitaTerreno",
            "FechaEntregaAntecedentes",
            "FechaCierre",
            "FechaActoAperturaTecnica",
            "FechaActoAperturaEconomica",
            "FechaTiempoEvaluacion",
            "FechaAdjudicacion",
            "FechaEstimadaAdjudicacion",
            "FechaEstimadaFirma",
            "FechaInicioContrato",
            "FechaFinal",
        ]
        iconos_fechas = {
            "FechaCreacion": "🆕",
            "FechaInicio": "🚀",
            "FechaPublicacion": "📢",
            "FechaPubRespuestas": "💬",
            "FechaSoporteFisico": "📎",
            "FechaVisitaTerreno": "👷",
            "FechaEntregaAntecedentes": "📂",
            "FechaCierre": "⏳",
            "FechaActoAperturaTecnica": "🛠️",
            "FechaActoAperturaEconomica": "💰",
            "FechaTiempoEvaluacion": "🧮",
            "FechaAdjudicacion": "🏆",
            "FechaEstimadaAdjudicacion": "📅",
            "FechaEstimadaFirma": "✍️",
            "FechaInicioContrato": "📄",
            "FechaFinal": "🏁",
        }
        nombres_fechas = {
            "FechaCreacion": "Creación",
            "FechaInicio": "Inicio",
            "FechaPublicacion": "Publicación",
            "FechaPubRespuestas": "Publicación Respuestas",
            "FechaSoporteFisico": "Soporte Físico",
            "FechaVisitaTerreno": "Visita Terreno",
            "FechaEntregaAntecedentes": "Entrega Antecedentes",
            "FechaCierre": "Cierre",
            "FechaActoAperturaTecnica": "Apertura Técnica",
            "FechaActoAperturaEconomica": "Apertura Económica",
            "FechaTiempoEvaluacion": "Tiempo Evaluación",
            "FechaAdjudicacion": "Adjudicación",
            "FechaEstimadaAdjudicacion": "Adj. Estimada",
            "FechaEstimadaFirma": "Firma Estimada",
            "FechaInicioContrato": "Inicio Contrato",
            "FechaFinal": "Final",
        }

        def _fmt_tiempo_evaluacion(val, row) -> str:
            """
            Muestra la fecha de término de evaluación e incluye, cuando es posible,
            la cantidad de días disponibles para evaluar.
            """
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ""

            # Si viene como timestamp/fecha (formato 2025-10-21T16:19:29.53)
            if isinstance(val, (pd.Timestamp, datetime)):
                texto_fecha = _fmt_fecha(val)
                # Usamos como referencia el cierre de ofertas (o, en su defecto, la apertura técnica)
                base = row.get("FechaCierre") or row.get("FechaActoAperturaTecnica")
                if isinstance(base, (pd.Timestamp, datetime)):
                    delta = val - base
                    dias = delta.days
                    if dias > 0:
                        return f"{texto_fecha} ({dias} días para evaluar)"
                return texto_fecha

            s = str(val).strip()
            if not s:
                return ""

            # Si viene como número de días
            try:
                n = float(s.replace(",", "."))
                if n.is_integer():
                    return f"{int(n)} días de evaluación"
                return f"{n:g} días de evaluación"
            except Exception:
                pass

            # Intentar parsear como fecha para extraer día si viene como 1900-01-16
            try:
                ts = pd.to_datetime(s, errors="coerce")
                if pd.notna(ts):
                    if ts.year <= 1900:
                        return f"{ts.day} días de evaluación"
                    return _fmt_fecha(ts)
            except Exception:
                pass

            return s

        cols_fechas_det = [c for c in orden_fechas if c in row.columns]
        if cols_fechas_det:
            fechas_df = pd.DataFrame(
                [
                    {
                        "Hito": f"{iconos_fechas.get(c, '📅')} {nombres_fechas.get(c, c)}",
                        "Fecha": _fmt_tiempo_evaluacion(r.get(c), r) if c == "FechaTiempoEvaluacion" else _fmt_fecha(r.get(c)),
                    }
                    for c in cols_fechas_det
                ]
            )
            st.dataframe(
                fechas_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Hito": st.column_config.TextColumn("Hito", width="small"),
                    "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
                },
                height=350,
            )
        else:
            st.info("No hay columnas de fechas disponibles para esta licitación.")

    # Sección de productos a ancho completo debajo
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📦 Productos a Licitar")
    df_prod = df_det_filtrado[df_det_filtrado["CodigoLicitacion"].astype(str) == str(codigo_licitacion)].copy()
    if df_prod.empty:
        st.info("No se encontraron productos/detalles para esta licitación.")
    else:
        cols_prod = [
            "Correlativo",
            "NombreProducto",
            "DescripcionItem",
            "UnidadMedida",
            "Cantidad",
            "RutGanador",
            "NombreGanador",
            "MontoUnitarioGanador",
            "CantidadAdjudicada",
        ]
        cols_prod = [c for c in cols_prod if c in df_prod.columns]
        
        # Formatear MontoUnitarioGanador si existe
        if "MontoUnitarioGanador" in df_prod.columns:
            def _fmt_monto_unitario(val):
                if pd.isna(val) or val is None:
                    return ""
                try:
                    return f"$ {float(val):,.0f}".replace(",", ".")
                except (ValueError, TypeError):
                    return str(val)
            df_prod_display = df_prod.copy()
            df_prod_display["MontoUnitarioGanador"] = df_prod_display["MontoUnitarioGanador"].apply(_fmt_monto_unitario)
        else:
            df_prod_display = df_prod.copy()
        
        st.dataframe(
            df_prod_display[cols_prod].sort_values(by=[c for c in ["Correlativo"] if c in cols_prod], ascending=True),
            use_container_width=True,
            hide_index=True,
            height=300,
            column_config={
                "MontoUnitarioGanador": st.column_config.TextColumn("Monto Unitario (CLP)", width="medium") if "MontoUnitarioGanador" in cols_prod else None,
            },
        )


st.markdown("### 📄 Revisar licitación (detalle)")
rows_sel = []
try:
    rows_sel = (gemba_sel.selection.rows or []) if gemba_sel is not None else []
except Exception:
    rows_sel = []

codigo_sel = None
if rows_sel:
    try:
        codigo_sel = str(df_view.iloc[int(rows_sel[0])]["CodigoLicitacion"]) if "CodigoLicitacion" in df_view.columns else None
    except Exception:
        codigo_sel = None

col_det_1, col_det_2 = st.columns([3, 1])
with col_det_1:
    if codigo_sel:
        st.info(f"Fila seleccionada: {codigo_sel}")
    else:
        st.info("Selecciona una fila en la tabla GEMBA para habilitar el detalle.")

with col_det_2:
    abrir = st.button("📄 Ver", use_container_width=True, disabled=not bool(codigo_sel))

if abrir and codigo_sel:
    dlg = getattr(st, "dialog", None)
    if callable(dlg):
        st.markdown(
            """
            <style>
            div[role="dialog"] {
                width: min(95vw, 1500px) !important;
                max-width: min(95vw, 1500px) !important;
            }
            div[data-testid="stDialog"] div[role="dialog"] {
                width: min(95vw, 1500px) !important;
                max-width: min(95vw, 1500px) !important;
            }
            div[data-testid="stDialog"] div[role="dialog"] > div {
                padding: 1rem 1.5rem !important;
            }
            div[data-testid="stDialog"] [data-testid="stDataFrame"] {
                margin-bottom: 0.5rem !important;
            }
            div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] {
                margin-bottom: 0.3rem !important;
            }
            div[data-testid="stDialog"] h3 {
                margin-bottom: 0.5rem !important;
                margin-top: 0.5rem !important;
            }
            div[data-testid="stDialog"] h4 {
                margin-bottom: 0.4rem !important;
                margin-top: 0.3rem !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        @dlg("Detalle de Licitación")
        def _dlg_detalle() -> None:
            _render_detalle_licitacion(codigo_sel)

        _dlg_detalle()
    else:
        with st.expander("📄 Detalle de Licitación", expanded=True):
            _render_detalle_licitacion(codigo_sel)


# =====================================================================
# 6) ACCIONES PRIORITARIAS
# =====================================================================
st.markdown("## 🔴🟡🔵 Acciones prioritarias")

acc1, acc2, acc3 = st.columns(3)

with acc1:
    st.markdown("### 🔴 Por cerrar (<= 7 días)")
    if "Estado" not in df_res_filtrado.columns or "FechaCierre" not in df_res_filtrado.columns:
        st.info("No están disponibles las columnas necesarias (Estado, FechaCierre).")
    else:
        hoy = pd.Timestamp.now().normalize()
        urg = df_res_filtrado.copy()
        urg["Dias_a_Cierre"] = (urg["FechaCierre"] - hoy).dt.days

        urg = urg[
            (urg["Estado"].astype(str).str.strip().str.lower() == "publicada")
            & (urg["Dias_a_Cierre"].between(0, 7, inclusive="both"))
        ].copy()
        urg = urg.sort_values("Dias_a_Cierre")

        if urg.empty:
            st.success("Sin licitaciones 'Publicada' con cierre en los próximos 7 días.")
        else:
            cols_u = [c for c in ["CodigoLicitacion", "Nombre", "C_Usuario", "FechaCierre", "Dias_a_Cierre"] if c in urg.columns]
            st.dataframe(
                urg[cols_u].head(20),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "FechaCierre": st.column_config.DateColumn(format="DD-MM-YYYY"),
                    "Dias_a_Cierre": st.column_config.NumberColumn(format="%d"),
                },
            )

with acc2:
    st.markdown("### 🟡 Cerradas sin adjudicar")
    if "Estado" not in df_res_filtrado.columns or "FechaAdjudicacion" not in df_res_filtrado.columns:
        st.info("No están disponibles las columnas necesarias (Estado, FechaAdjudicacion).")
    else:
        cerr = df_res_filtrado[
            df_res_filtrado["Estado"].astype(str).str.strip().str.lower().eq("cerrada")
        ].copy()
        sin_adj = cerr[cerr["FechaAdjudicacion"].isna()].copy()
        if sin_adj.empty:
            st.success("Sin licitaciones 'Cerrada' pendientes de adjudicación.")
        else:
            cols_s = [c for c in ["CodigoLicitacion", "Nombre", "C_Usuario", "FechaCierre"] if c in sin_adj.columns]
            if "FechaCierre" in sin_adj.columns:
                sin_adj = sin_adj.sort_values("FechaCierre", ascending=False)
            st.dataframe(
                sin_adj[cols_s].head(15),
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


st.markdown("---")
st.markdown("## ✅ Procesos Adjudicados")

if "Estado" not in df_res_filtrado.columns:
    st.info("No está disponible la columna 'Estado' para identificar procesos adjudicados.")
else:
    df_adj = df_res_filtrado[
        df_res_filtrado["Estado"].astype(str).str.strip().str.lower().eq("adjudicada")
    ].copy()

    if df_adj.empty:
        st.info("No hay procesos con Estado = 'Adjudicada' para los filtros actuales.")
    else:
        cols_adj = [
            "CodigoLicitacion",
            "Nombre",
            "C_Usuario",
            "MontoEstimado",
            "FechaAdjudicacion",
            "Adj_UrlActa",
        ]
        cols_adj = [c for c in cols_adj if c in df_adj.columns]
        if "FechaAdjudicacion" in df_adj.columns:
            df_adj = df_adj.sort_values("FechaAdjudicacion", ascending=False)

        column_config_adj = {
            "MontoEstimado": st.column_config.NumberColumn(format="$ %,.0f"),
            "FechaAdjudicacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
        }
        if "Adj_UrlActa" in df_adj.columns:
            column_config_adj["Adj_UrlActa"] = st.column_config.LinkColumn("Acta", display_text="🔗 Acta")

        st.dataframe(
            df_adj[cols_adj].head(50),
            use_container_width=True,
            hide_index=True,
            column_config=column_config_adj,
        )
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





st.markdown("---")
st.markdown("## 🎯 Análisis LEAN y OKRs de Eficiencia Operacional")
st.markdown("Evaluación de desperdicios (tiempos de espera), predictibilidad y cumplimiento del cronograma.")

# ------------------------------------------------------------------------------
# PREPARACIÓN DE DATOS (MÉTRICAS LEAN)
# ------------------------------------------------------------------------------
df_metrics = df_res_filtrado.copy()

# Solo evaluamos procesos que ya tienen FechaAdjudicacion para medir tiempos reales
df_eval = df_metrics.dropna(subset=['FechaAdjudicacion']).copy()


# 1. Desviación de Adjudicación (Días de retraso o adelanto)
df_eval['Desviacion_Dias'] = (df_eval['FechaAdjudicacion'] - df_eval['FechaEstimadaAdjudicacion']).dt.days

# 2. Cycle Time (Tiempo total desde Publicación hasta Adjudicación)
df_eval['Cycle_Time_Dias'] = (df_eval['FechaAdjudicacion'] - df_eval['FechaPublicacion']).dt.days

# 3. Predictibilidad (1 si cumplió plazo estimado <= 0 días de desviación, 0 si se retrasó)
df_eval['Cumple_Plazo'] = (df_eval['Desviacion_Dias'] <= 0).astype(int)

# 4. Serie temporal (Mes-Año de Adjudicación)
df_eval['Mes_Adjudicacion'] = df_eval['FechaAdjudicacion'].dt.to_period('M').astype(str)

# ------------------------------------------------------------------------------
# OKRs PRINCIPALES (Tarjetas de KPI)
# ------------------------------------------------------------------------------
# OKR 1: Reducir tiempo promedio entre fecha estimada y real
avg_desviacion = df_eval['Desviacion_Dias'].mean()

# OKR 2: Mejorar predictibilidad del proceso (Tasa de cumplimiento)
tasa_predictibilidad = df_eval['Cumple_Plazo'].mean() * 100

# OKR 3: Reducir Cycle Time general
avg_cycle_time = df_eval['Cycle_Time_Dias'].mean()

col_okr1, col_okr2, col_okr3 = st.columns(3)
with col_okr1:
    st.metric(
        label="🎯 OKR 1: Desviación Promedio", 
        value=f"{avg_desviacion:.1f} días",
        help="Días promedio de retraso/adelanto respecto a la fecha estimada de adjudicación."
    )
with col_okr2:
    st.metric(
        label="🎯 OKR 2: Predictibilidad del Proceso", 
        value=f"{tasa_predictibilidad:.1f}%",
        help="Porcentaje de licitaciones adjudicadas en o antes de la fecha estimada."
    )
with col_okr3:
    st.metric(
        label="⏱️ LEAN: Cycle Time Promedio", 
        value=f"{avg_cycle_time:.1f} días",
        help="Días promedio transcurridos desde Publicación hasta Adjudicación."
    )

st.divider()

# ------------------------------------------------------------------------------
# 1. TABLA DE ESTADÍSTICAS LEAN POR TIPO DE LICITACIÓN
# ------------------------------------------------------------------------------
st.markdown("### 📊 Variabilidad y Desempeño por Tipo de Licitación")

# Agrupación y cálculo estadístico corregido
df_lean_stats = df_eval.groupby('Tipo').agg(
    Total_Procesos=('CodigoLicitacion', 'count'),
    Cycle_Time_Prom=('Cycle_Time_Dias', 'mean'),
    Desviacion_Prom=('Desviacion_Dias', 'mean'),
    Variabilidad_Desviacion=('Desviacion_Dias', 'std'), 
    Predictibilidad=('Cumple_Plazo', lambda x: x.mean() * 100) # <-- CORREGIDO AQUÍ
).reset_index()

# Rellenar nulos en variabilidad (ocurre si solo hay 1 proceso y no se puede calcular desviación estándar)
df_lean_stats['Variabilidad_Desviacion'] = df_lean_stats['Variabilidad_Desviacion'].fillna(0)

st.dataframe(
    df_lean_stats.sort_values(by='Desviacion_Prom', ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Tipo": st.column_config.TextColumn("Tipo de Licitación"),
        "Total_Procesos": st.column_config.NumberColumn("Nº Procesos", format="%d"),
        "Cycle_Time_Prom": st.column_config.NumberColumn("Cycle Time (días)", format="%.1f"),
        "Desviacion_Prom": st.column_config.NumberColumn("Desviación Prom. (días)", format="%.1f"),
        "Variabilidad_Desviacion": st.column_config.NumberColumn("Variabilidad (Std Dev)", format="%.1f", help="A mayor número, más inestable es el proceso"),
        "Predictibilidad": st.column_config.ProgressColumn("Tasa Predictibilidad", format="%.1f%%", min_value=0, max_value=100)
    }
)

# ------------------------------------------------------------------------------
# 2. GRÁFICO: SERIES TEMPORALES DE DESVIACIÓN MENSUAL (Identificación de Cuellos de Botella)
# ------------------------------------------------------------------------------

col_graf1, col_graf2 = st.columns(2)
with col_graf1:
    st.markdown("#### 📈 Evolución de Desviaciones")
    st.caption("Promedio de días de retraso por mes de adjudicación")
    
    df_trend = df_eval.groupby('Mes_Adjudicacion')['Desviacion_Dias'].mean().reset_index()
    df_trend = df_trend.sort_values('Mes_Adjudicacion')
    
    fig_trend = px.line(
        df_trend, 
        x='Mes_Adjudicacion', 
        y='Desviacion_Dias', 
        markers=True,
        labels={'Mes_Adjudicacion': 'Mes', 'Desviacion_Dias': 'Desviación Promedio (Días)'},
        color_discrete_sequence=['#e74c3c']
    )
    # Línea base de Cero desviaciones (Objetivo OKR)
    fig_trend.add_hline(y=0, line_dash="dash", line_color="green", annotation_text="Meta Cero Retraso")
    st.plotly_chart(fig_trend, use_container_width=True)

# ------------------------------------------------------------------------------
# 3. HEATMAP: CUMPLIMIENTO DE FECHAS POR TIPO Y PERÍODO
# ------------------------------------------------------------------------------

with col_graf2:
    st.markdown("#### 🗺️ Mapa de Calor: Predictibilidad (%)")
    st.caption("Tasa de cumplimiento de plazos por Tipo y Mes")
    
    # Preparar matriz para el heatmap
    df_heatmap = df_eval.pivot_table(
        index='Tipo', 
        columns='Mes_Adjudicacion', 
        values='Cumple_Plazo', 
        aggfunc='mean'
    ) * 100 # Porcentaje
    
    # Rellenar con 0s si no hay datos en ese cruce para evitar huecos en el gráfico
    df_heatmap = df_heatmap.fillna(0)
    
    fig_heat = px.imshow(
        df_heatmap,
        text_auto=".0f",
        aspect="auto",
        color_continuous_scale="RdYlGn", # Rojo (Malo/0%) a Verde (Bueno/100%)
        labels=dict(x="Mes", y="Tipo Licitación", color="% Cumplimiento")
    )
    fig_heat.update_xaxes(side="bottom")
    st.plotly_chart(fig_heat, use_container_width=True)

# ==============================================================================
# 7. MÓDULO DE ENVÍO DE CORREOS AUTOMATIZADOS
# ==============================================================================

# Configuración de correo (puede usar variables de entorno)
OUTLOOK_SMTP_SERVER = os.getenv("OUTLOOK_SMTP_SERVER", "smtp-mail.outlook.com")
OUTLOOK_SMTP_PORT = int(os.getenv("OUTLOOK_SMTP_PORT", "587"))
OUTLOOK_EMAIL = os.getenv("OUTLOOK_EMAIL", "nicolas.asencio@redsalud.gob.cl")
OUTLOOK_PASSWORD = os.getenv("OUTLOOK_PASSWORD", "nias$2023")

# Servidores SMTP alternativos para Microsoft 365
SMTP_SERVERS_ALTERNATIVOS = [
    ("smtp-mail.outlook.com", 587),
    ("smtp.office365.com", 587),
    ("smtp-mail.outlook.com", 465),  # Puerto SSL alternativo
]

# Diccionario de compradores y correos
#COMPRADORES = {
 #   "ALICIA VIDAL PAREDES": "alicia.vidal@redsalud.gob.cl",
  #  "ARIELA ACEVEDO": "ariela.acevedo@redsalud.gob.cl",
   # "IVAN VARGAS OJEDA": "ivan.vargas@redsalud.gob.cl",
    #"JACQUELINE OYARZUN ALVAREZ": "jacqueline.oyarzuna@redsalud.gob.cl",
    #"LESLY ANDREA DÍAZ ABURTO": "lesly.diaz@redsalud.gob.cl",
    #"MIGUEL ARO": "miguel.aro@redsalud.gob.cl",
    #"ROSA VASQUEZ": "rosae.vasquez@redsalud.gob.cl",
    #"RUBÉN URIBE": "ruben.uribe@redsalud.gob.cl",
    #"JUAN FELIPE ROJEL HUENTRO": "juan.rojelh@redsalud.gob.cl",
    #"NICOLAS ASENCIO MOREIRA": "nicolas.asencio@redsalud.gob.cl",
    #"VERÓNICA ARACELY MÁRQUEZ AGUILAR": "veronica.marquez.a@redsalud.gob.cl",
    #"BASTIAN MIRANDA CORONADO": "bastian.miranda@redsalud.gob.cl"
#}

# Diccionario de compradores y correos
COMPRADORES = {
    "ALICIA VIDAL PAREDES": "nicolas.asencio@redsalud.gob.cl",
    "ARIELA ACEVEDO": "nicolas.asencio@redsalud.gob.cl",
    "IVAN VARGAS OJEDA": "nicolas.asencio@redsalud.gob.cl",
    "JACQUELINE OYARZUN ALVAREZ": "nicolas.asencio@redsalud.gob.cl",
    "LESLY ANDREA DÍAZ ABURTO": "nicolas.asencio@redsalud.gob.cl",
    "MIGUEL ARO": "nicolas.asencio@redsalud.gob.cl",
    "ROSA VASQUEZ": "nicolas.asencio@redsalud.gob.cl",
    "RUBÉN URIBE": "nicolas.asencio@redsalud.gob.cl",
    "JUAN FELIPE ROJEL HUENTRO": "nicolas.asencio@redsalud.gob.cl",
    "NICOLAS ASENCIO MOREIRA": "nicolas.asencio@redsalud.gob.cl",
    "VERÓNICA ARACELY MÁRQUEZ AGUILAR": "nicolas.asencio@redsalud.gob.cl",
    "BASTIAN MIRANDA CORONADO": "nicolas.asencio@redsalud.gob.cl"
}



JEFATURAS = {
    #"Cristina Flores": "cristina.flores@redsalud.gob.cl",
    #"Sandra Espinoza": "sandrap.espinoza@redsalud.gob.cl",
    "NICOLAS ASENCIO MOREIRA": "nicolas.asencio@redsalud.gob.cl"
}

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def obtener_ruta_logo(logo_nombre):
    """Obtiene la ruta absoluta del logo"""
    base_path = Path(__file__).parent.parent
    logo_path = base_path / "resources" / logo_nombre
    
    # Si no existe con el nombre exacto, intentar variaciones
    if not logo_path.exists():
        # Intentar con .png si viene .jpg y viceversa
        if logo_nombre.endswith('.png'):
            logo_path_alt = base_path / "resources" / logo_nombre.replace('.png', '.jpg')
            if logo_path_alt.exists():
                return str(logo_path_alt)
        elif logo_nombre.endswith('.jpg'):
            logo_path_alt = base_path / "resources" / logo_nombre.replace('.jpg', '.png')
            if logo_path_alt.exists():
                return str(logo_path_alt)
    
    return str(logo_path)

def codificar_imagen_base64(ruta_imagen):
    """Codifica una imagen en base64 para incrustarla en HTML"""
    try:
        if os.path.exists(ruta_imagen):
            with open(ruta_imagen, 'rb') as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        else:
            logger.warning(f"Logo no encontrado: {ruta_imagen}")
            return None
    except Exception as e:
        logger.error(f"Error al codificar imagen {ruta_imagen}: {e}")
        return None

def generar_tablero_gemba_html_comprador(df_comprador, nombre_comprador):
    """Genera HTML del tablero gemba para un comprador específico"""
    if df_comprador.empty:
        return "<p>No hay licitaciones asignadas para este comprador.</p>"
    
    # Ordenar por fecha clave
    df_sorted = df_comprador.sort_values(by='FechaClave', ascending=True, na_position='last')
    
    html = """
    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
        <thead>
            <tr style="background-color: #138AEC; color: white;">
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">📍 Etapa Actual</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">📅 Fecha Hito</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">ID Licitación</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Nombre del Proceso</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Monto Est. (CLP)</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Tipo</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in df_sorted.head(20).iterrows():  # Limitar a 20 para el correo
        estado_flujo = str(row.get('EstadoFlujo', 'Sin estado'))
        fecha_clave = row.get('FechaClave', '')
        codigo = str(row.get('CodigoLicitacion', ''))
        nombre = str(row.get('Nombre', ''))[:80] + ('...' if len(str(row.get('Nombre', ''))) > 80 else '')
        monto = row.get('MontoEstimado', '')
        tipo = str(row.get('Tipo', ''))
        
        # Formatear fecha
        if pd.notna(fecha_clave):
            fecha_str = pd.to_datetime(fecha_clave).strftime("%d/%m/%Y")
        else:
            fecha_str = "Sin fecha"
        
        # Formatear monto
        try:
            if pd.notna(monto):
                monto_str = f"$ {float(monto):,.0f}".replace(",", ".")
            else:
                monto_str = "Sin monto"
        except:
            monto_str = str(monto)
        
        html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px; border: 1px solid #ddd;">{estado_flujo}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{fecha_str}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{codigo}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{nombre}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{monto_str}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{tipo}</td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    """
    
    if len(df_sorted) > 20:
        html += f"<p style='margin-top: 10px; color: #666;'><em>Mostrando 20 de {len(df_sorted)} licitaciones. Consulte el sistema para ver el listado completo.</em></p>"
    
    return html

def generar_tablero_gemba_html_consolidado(df_resumen):
    """Genera HTML del tablero gemba consolidado para jefaturas"""
    if df_resumen.empty:
        return "<p>No hay datos disponibles para el período.</p>"
    
    # Estadísticas generales
    total_licitaciones = len(df_resumen)
    monto_total = df_resumen['MontoEstimado'].sum()
    
    # Por estado
    estados_count = df_resumen['EstadoFlujo'].value_counts().head(10)
    
    # Por comprador
    compradores_count = df_resumen.groupby('C_Usuario').agg({
        'CodigoLicitacion': 'count',
        'MontoEstimado': 'sum'
    }).sort_values('CodigoLicitacion', ascending=False).head(10)
    
    html = f"""
    <div style="margin-top: 20px;">
        <h3 style="color: #138AEC;">Resumen Ejecutivo del Mes</h3>
        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 8px; flex: 1;">
                <strong>Total Licitaciones:</strong> {total_licitaciones:,}
            </div>
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 8px; flex: 1;">
                <strong>Monto Total Estimado:</strong> $ {monto_total:,.0f}
            </div>
        </div>
    </div>
    
    <h3 style="color: #138AEC; margin-top: 30px;">Distribución por Estado</h3>
    <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
        <thead>
            <tr style="background-color: #138AEC; color: white;">
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Estado</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Cantidad</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for estado, cantidad in estados_count.items():
        html += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">{estado}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{cantidad}</td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    
    <h3 style="color: #138AEC; margin-top: 30px;">Top 10 Compradores por Carga de Trabajo</h3>
    <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
        <thead>
            <tr style="background-color: #138AEC; color: white;">
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Comprador</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Licitaciones</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Monto Total</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for comprador, row in compradores_count.iterrows():
        monto_comprador = row['MontoEstimado']
        html += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">{comprador}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{int(row['CodigoLicitacion'])}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">$ {monto_comprador:,.0f}</td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    """
    
    return html

def generar_pasos_a_realizar(estado_flujo):
    """Genera pasos a realizar según el estado del flujo"""
    pasos_genericos = {
        "🆕 Creada": [
            "Revisar documentación base de la licitación",
            "Verificar requisitos técnicos y administrativos",
            "Preparar cronograma de trabajo"
        ],
        "🚀 Inicio": [
            "Iniciar proceso de licitación",
            "Coordinar con unidades solicitantes",
            "Revisar especificaciones técnicas"
        ],
        "📢 Publicada": [
            "Monitorear publicación en Mercado Público",
            "Responder consultas de proveedores",
            "Preparar documentación para apertura"
        ],
        "💬 Responder Preguntas": [
            "Revisar preguntas recibidas",
            "Preparar respuestas oficiales",
            "Publicar respuestas en plazo establecido"
        ],
        "⏳ Por Cerrar": [
            "Verificar cierre de ofertas",
            "Preparar acta de apertura",
            "Coordinar con comité evaluador"
        ],
        "🧮 En Evaluación": [
            "Supervisar proceso de evaluación",
            "Revisar informes técnicos",
            "Preparar documentación para adjudicación"
        ],
        "🏆 Adjudicación": [
            "Revisar acta de adjudicación",
            "Notificar a proveedor ganador",
            "Preparar documentación para firma"
        ]
    }
    
    # Buscar pasos según el estado
    for key, pasos in pasos_genericos.items():
        if key in estado_flujo:
            return pasos
    
    return [
        "Revisar estado actual de la licitación",
        "Coordinar con unidades involucradas",
        "Actualizar información en el sistema"
    ]

def crear_plantilla_html_comprador(nombre_comprador, email_comprador, tablero_html, pasos_html):
    """Crea la plantilla HTML para correo a comprador"""
    # Codificar logos (intentar diferentes extensiones)
    logo_aba_path = obtener_ruta_logo("logoaba.png")
    if not os.path.exists(logo_aba_path):
        logo_aba_path = obtener_ruta_logo("logoaba2.png")
    logo_sso_path = obtener_ruta_logo("logosso2.png")
    if not os.path.exists(logo_sso_path):
        logo_sso_path = obtener_ruta_logo("logosso2.jpg")
    
    logo_aba_b64 = codificar_imagen_base64(logo_aba_path)
    logo_sso_b64 = codificar_imagen_base64(logo_sso_path)
    
    # Determinar extensión para el tipo MIME
    ext_aba = 'png' if logo_aba_path.endswith('.png') else 'jpg'
    ext_sso = 'png' if logo_sso_path.endswith('.png') else 'jpg'
    
    logo_aba_img = f'<img src="data:image/{ext_aba};base64,{logo_aba_b64}" style="max-height: 60px; margin-right: 20px;">' if logo_aba_b64 else '<div style="display: inline-block; width: 60px; height: 60px; background-color: #138AEC; margin-right: 20px;"></div>'
    logo_sso_img = f'<img src="data:image/{ext_sso};base64,{logo_sso_b64}" style="max-height: 60px;">' if logo_sso_b64 else '<div style="display: inline-block; width: 60px; height: 60px; background-color: #138AEC;"></div>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(90deg, #138AEC, #3E9FEF);
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .section {{
                margin-bottom: 30px;
            }}
            .section h2 {{
                color: #138AEC;
                border-bottom: 2px solid #138AEC;
                padding-bottom: 10px;
            }}
            .pasos {{
                background-color: #f9f9f9;
                padding: 15px;
                border-left: 4px solid #138AEC;
                margin-top: 10px;
            }}
            .pasos ul {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .pasos li {{
                margin: 8px 0;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                color: #666;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th {{
                background-color: #138AEC;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .header-logos img {
                height: 80px; /* Puedes subir o bajar este valor según necesites */
                width: auto;
                object-fit: contain; /* Asegura que los logos no se deformen ni se estiren */
            }
        </style>
    </head>
    <body>
        <div class="container">
          <div class="header" style="text-align: center; font-family: Arial, sans-serif; padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
    
            <div class="header-logos" style="display: flex; justify-content: center; align-items: center; gap: 40px; margin-bottom: 20px;">
                {logo_aba_img}
                {logo_sso_img}
            </div>

            <div style="color: #0f355c;">
                <h1 style="margin: 0; font-size: 26px;">📋 Reporte de Licitaciones - Tablero Gemba</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">
                    Servicio de Salud Osorno - Departamento de Abastecimiento y Operaciones
                </p>
            </div>
            
            <div class="section">
                <h2>👤 Información del Comprador</h2>
                <p><strong>Nombre:</strong> {nombre_comprador}</p>
                <p><strong>Correo:</strong> {email_comprador}</p>
                <p><strong>Fecha del Reporte:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            </div>
            
            <div class="section">
                <h2>📊 Tablero Gemba Personalizado</h2>
                {tablero_html}
            </div>
            
            <div class="section">
                <h2>✅ Pasos a Realizar</h2>
                <div class="pasos">
                    {pasos_html}
                </div>
            </div>
            
            <div class="section">
                <h2>📝 Notas Generales</h2>
                <div class="pasos">
                    <ul>
                        <li>Revise regularmente el estado de sus licitaciones asignadas</li>
                        <li>Mantenga actualizada la información en el sistema</li>
                        <li>Comunique cualquier retraso o inconveniente a su jefatura</li>
                        <li>Priorice las licitaciones con fechas de cierre próximas</li>
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>Este es un correo automatizado del Sistema de Gestión de Abastecimiento</p>
                <p>Servicio de Salud Osorno - Departamento de Recursos</p>
                <p>Para consultas, contacte a su jefatura directa</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def crear_plantilla_html_jefaturas(tablero_html):
    """Crea la plantilla HTML para correo a jefaturas"""
    # Codificar logos (intentar diferentes extensiones)
    logo_aba_path = obtener_ruta_logo("logoaba.png")
    if not os.path.exists(logo_aba_path):
        logo_aba_path = obtener_ruta_logo("logoaba2.png")
    logo_sso_path = obtener_ruta_logo("logosso2.png")
    if not os.path.exists(logo_sso_path):
        logo_sso_path = obtener_ruta_logo("logosso2.jpg")
    
    logo_aba_b64 = codificar_imagen_base64(logo_aba_path)
    logo_sso_b64 = codificar_imagen_base64(logo_sso_path)
    
    # Determinar extensión para el tipo MIME
    ext_aba = 'png' if logo_aba_path.endswith('.png') else 'jpg'
    ext_sso = 'png' if logo_sso_path.endswith('.png') else 'jpg'
    
    logo_aba_img = f'<img src="data:image/{ext_aba};base64,{logo_aba_b64}" style="max-height: 60px; margin-right: 20px;">' if logo_aba_b64 else '<div style="display: inline-block; width: 60px; height: 60px; background-color: #138AEC; margin-right: 20px;"></div>'
    logo_sso_img = f'<img src="data:image/{ext_sso};base64,{logo_sso_b64}" style="max-height: 60px;">' if logo_sso_b64 else '<div style="display: inline-block; width: 60px; height: 60px; background-color: #138AEC;"></div>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(90deg, #138AEC, #3E9FEF);
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .section {{
                margin-bottom: 30px;
            }}
            .section h2 {{
                color: #138AEC;
                border-bottom: 2px solid #138AEC;
                padding-bottom: 10px;
            }}
            .section h3 {{
                color: #138AEC;
                margin-top: 20px;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                color: #666;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th {{
                background-color: #138AEC;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div style="margin-bottom: 15px;">
                    {logo_aba_img}
                    {logo_sso_img}
                </div>
                <h1>📊 Reporte Consolidado Mensual - Tablero Gemba</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Servicio de Salud Osorno - Departamento de Recursos</p>
            </div>
            
            <div class="section">
                <h2>📅 Información del Reporte</h2>
                <p><strong>Período:</strong> {datetime.now().strftime("%B %Y")}</p>
                <p><strong>Fecha de Generación:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            </div>
            
            <div class="section">
                <h2>📈 Resumen Ejecutivo</h2>
                {tablero_html}
            </div>
            
            <div class="footer">
                <p>Este es un correo automatizado del Sistema de Gestión de Abastecimiento</p>
                <p>Servicio de Salud Osorno - Departamento de Recursos</p>
                <p>Para consultas adicionales, acceda al sistema de gestión</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def enviar_correo(destinatario, asunto, cuerpo_html, servidor=None, puerto=None, email=None, password=None):
    """Envía un correo usando SMTP de Outlook con manejo mejorado de errores"""
    # Usar parámetros proporcionados o valores por defecto
    servidor_smtp = servidor or OUTLOOK_SMTP_SERVER
    puerto_smtp = puerto or OUTLOOK_SMTP_PORT
    email_smtp = email or OUTLOOK_EMAIL
    password_smtp = password or OUTLOOK_PASSWORD
    
    # Crear mensaje
    msg = MIMEMultipart('alternative')
    msg['From'] = email_smtp
    msg['To'] = destinatario
    msg['Subject'] = asunto
    
    # Agregar cuerpo HTML
    parte_html = MIMEText(cuerpo_html, 'html', 'utf-8')
    msg.attach(parte_html)
    
    # Intentar con el servidor principal primero
    servidores_a_probar = [(servidor_smtp, puerto_smtp)] + SMTP_SERVERS_ALTERNATIVOS
    
    ultimo_error = None
    for servidor_intento, puerto_intento in servidores_a_probar:
        try:
            logger.info(f"Intentando conectar a {servidor_intento}:{puerto_intento}")
            
            # Crear conexión SMTP
            if puerto_intento == 465:
                # Puerto SSL
                import ssl
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(servidor_intento, puerto_intento, context=context)
            else:
                # Puerto TLS estándar
                server = smtplib.SMTP(servidor_intento, puerto_intento, timeout=30)
                server.starttls()
            
            # Intentar login
            server.login(email_smtp, password_smtp)
            
            # Enviar mensaje
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Correo enviado exitosamente a {destinatario} usando {servidor_intento}:{puerto_intento}")
            return True, None
            
        except smtplib.SMTPAuthenticationError as e:
            ultimo_error = f"Error de autenticación (535): Credenciales incorrectas o cuenta requiere autenticación avanzada. Detalles: {str(e)}"
            logger.error(f"Error de autenticación con {servidor_intento}:{puerto_intento} - {ultimo_error}")
            # No continuar con otros servidores si es error de autenticación
            break
            
        except smtplib.SMTPException as e:
            ultimo_error = f"Error SMTP con {servidor_intento}:{puerto_intento}: {str(e)}"
            logger.warning(f"Error con {servidor_intento}:{puerto_intento}, intentando siguiente servidor...")
            continue
            
        except Exception as e:
            ultimo_error = f"Error inesperado con {servidor_intento}:{puerto_intento}: {str(e)}"
            logger.warning(f"Error con {servidor_intento}:{puerto_intento}, intentando siguiente servidor...")
            continue
    
    # Si llegamos aquí, todos los intentos fallaron
    logger.error(f"Todos los intentos de envío fallaron para {destinatario}. Último error: {ultimo_error}")
    return False, ultimo_error or "Error desconocido al enviar correo"

def enviar_a_compradores(email_override=None, password_override=None):
    """Envía correos individuales a cada comprador"""
    resultados = []
    total_enviados = 0
    total_fallidos = 0
    
    # Usar credenciales proporcionadas o las por defecto
    email_usar = email_override or OUTLOOK_EMAIL
    password_usar = password_override or OUTLOOK_PASSWORD
    
    # Procesar cada comprador
    for nombre_comprador, email_comprador in COMPRADORES.items():
        try:
            # Filtrar datos del comprador (normalizar nombre para búsqueda)
            df_comprador = df_res_filtrado[
                df_res_filtrado['C_Usuario'].str.upper().str.strip() == nombre_comprador.upper()
            ].copy()
            
            if df_comprador.empty:
                logger.warning(f"No se encontraron licitaciones para {nombre_comprador}")
                resultados.append({
                    'comprador': nombre_comprador,
                    'email': email_comprador,
                    'estado': 'Sin datos',
                    'error': None
                })
                continue
            
            # Generar tablero gemba
            tablero_html = generar_tablero_gemba_html_comprador(df_comprador, nombre_comprador)
            
            # Generar pasos a realizar (usar el estado más común o el primero)
            estados_disponibles = df_comprador['EstadoFlujo'].dropna()
            if not estados_disponibles.empty:
                estado_principal = estados_disponibles.mode()[0] if not estados_disponibles.mode().empty else estados_disponibles.iloc[0]
                pasos = generar_pasos_a_realizar(str(estado_principal))
            else:
                pasos = generar_pasos_a_realizar("")
            pasos_html = "<ul>" + "".join([f"<li>{paso}</li>" for paso in pasos]) + "</ul>"
            
            # Crear plantilla HTML
            cuerpo_html = crear_plantilla_html_comprador(nombre_comprador, email_comprador, tablero_html, pasos_html)
            
            # Enviar correo
            asunto = f"Reporte de Licitaciones - Tablero Gemba - {nombre_comprador}"
            exito, error = enviar_correo(email_comprador, asunto, cuerpo_html, email=email_usar, password=password_usar)
            
            if exito:
                total_enviados += 1
                resultados.append({
                    'comprador': nombre_comprador,
                    'email': email_comprador,
                    'estado': '✅ Enviado',
                    'error': None
                })
            else:
                total_fallidos += 1
                # Mejorar mensaje de error para errores 535
                error_msg = error
                if "535" in str(error) or "Authentication" in str(error):
                    error_msg = f"Error de autenticación: Verifica credenciales o usa contraseña de aplicación. {error}"
                resultados.append({
                    'comprador': nombre_comprador,
                    'email': email_comprador,
                    'estado': '❌ Error',
                    'error': error_msg
                })
                
        except Exception as e:
            total_fallidos += 1
            logger.error(f"Error procesando comprador {nombre_comprador}: {e}")
            resultados.append({
                'comprador': nombre_comprador,
                'email': email_comprador,
                'estado': 'Error',
                'error': str(e)
            })
    
    return resultados, total_enviados, total_fallidos

def enviar_a_jefaturas(email_override=None, password_override=None):
    """Envía correo consolidado a jefaturas"""
    try:
        # Usar credenciales proporcionadas o las por defecto
        email_usar = email_override or OUTLOOK_EMAIL
        password_usar = password_override or OUTLOOK_PASSWORD
        
        # Generar tablero consolidado (usar df_res_filtrado completo)
        tablero_html = generar_tablero_gemba_html_consolidado(df_res_filtrado)
        
        # Crear plantilla HTML
        cuerpo_html = crear_plantilla_html_jefaturas(tablero_html)
        
        # Enviar a ambas jefaturas
        destinatarios = list(JEFATURAS.values())
        asunto = f"Reporte Consolidado Mensual - Tablero Gemba - {datetime.now().strftime('%B %Y')}"
        
        resultados = []
        total_enviados = 0
        total_fallidos = 0
        
        for nombre_jefatura, email_jefatura in JEFATURAS.items():
            exito, error = enviar_correo(email_jefatura, asunto, cuerpo_html, email=email_usar, password=password_usar)
            
            if exito:
                total_enviados += 1
                resultados.append({
                    'jefatura': nombre_jefatura,
                    'email': email_jefatura,
                    'estado': '✅ Enviado',
                    'error': None
                })
            else:
                total_fallidos += 1
                # Mejorar mensaje de error para errores 535
                error_msg = error
                if "535" in str(error) or "Authentication" in str(error):
                    error_msg = f"Error de autenticación: Verifica credenciales o usa contraseña de aplicación. {error}"
                resultados.append({
                    'jefatura': nombre_jefatura,
                    'email': email_jefatura,
                    'estado': '❌ Error',
                    'error': error_msg
                })
        
        return resultados, total_enviados, total_fallidos
        
    except Exception as e:
        logger.error(f"Error en enviar_a_jefaturas: {e}")
        return [], 0, 1

# ==============================================================================
# 8. INTERFAZ DE ENVÍO DE CORREOS
# ==============================================================================

st.markdown("---")
st.markdown("## 📧 Envío de Reportes por Correo")

# Sección de configuración y ayuda
with st.expander("⚙️ Configuración y Solución de Problemas", expanded=False):
    st.markdown("""
    ### 🔐 Configuración de Credenciales
    
    Si recibes un error **535 (Authentication unsuccessful)**, sigue estos pasos:
    
    #### Opción 1: Usar Contraseña de Aplicación (Recomendado si tienes 2FA activado)
    1. Ve a [Microsoft Account Security](https://account.microsoft.com/security)
    2. Activa la verificación en dos pasos si no está activada
    3. Ve a "Contraseñas de aplicación" o "App passwords"
    4. Genera una nueva contraseña de aplicación para "Correo"
    5. Usa esa contraseña en lugar de tu contraseña normal
    
    #### Opción 2: Verificar Credenciales
    - Asegúrate de que el correo y contraseña sean correctos
    - Verifica que no haya espacios adicionales
    
    #### Opción 3: Configuración de Seguridad de la Cuenta
    - Algunas cuentas corporativas requieren habilitar "Aplicaciones menos seguras"
    - Contacta al administrador de TI si es una cuenta corporativa
    
    ### 📝 Configurar Credenciales Manualmente
    """)
    
    col_config1, col_config2 = st.columns(2)
    with col_config1:
        email_config = st.text_input(
            "Correo Electrónico",
            value=OUTLOOK_EMAIL,
            help="Correo desde el cual se enviarán los reportes"
        )
    with col_config2:
        password_config = st.text_input(
            "Contraseña",
            value="",
            type="password",
            help="Contraseña o contraseña de aplicación",
            placeholder="Dejar vacío para usar la configuración por defecto"
        )
    
    if st.button("💾 Guardar Configuración Temporal"):
        # Las credenciales se usarán en las funciones de envío
        st.session_state['email_config'] = email_config
        st.session_state['password_config'] = password_config if password_config else None
        st.success("Configuración guardada para esta sesión")
    
    st.markdown("---")
    st.markdown("""
    ### ⚠️ Nota Importante
    - Las credenciales configuradas aquí solo se guardan durante la sesión actual
    - Para producción, considera usar variables de entorno o un gestor de secretos
    - No compartas tus credenciales con otros usuarios
    """)

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("📨 Enviar a Compradores", use_container_width=True, type="primary"):
        # Obtener credenciales de la sesión si están configuradas
        email_usar = st.session_state.get('email_config', OUTLOOK_EMAIL)
        password_usar = st.session_state.get('password_config', OUTLOOK_PASSWORD)
        
        with st.spinner("Enviando correos a compradores..."):
            # Modificar función para usar credenciales de sesión
            resultados, enviados, fallidos = enviar_a_compradores(email_usar, password_usar)
            
            if enviados > 0:
                st.success(f"✅ Se enviaron {enviados} correos exitosamente")
            if fallidos > 0:
                st.error(f"❌ Fallaron {fallidos} envíos")
            
            # Mostrar resultados detallados
            if resultados:
                df_resultados = pd.DataFrame(resultados)
                st.dataframe(df_resultados, use_container_width=True, hide_index=True)
                
                # Mostrar ayuda adicional si hay errores de autenticación
                if fallidos > 0:
                    errores_auth = [r for r in resultados if r.get('error') and ('535' in str(r.get('error')) or 'Authentication' in str(r.get('error')))]
                    if errores_auth:
                        st.warning("""
                        ⚠️ **Error de Autenticación Detectado**
                        
                        Si recibes error 535 (Authentication unsuccessful), necesitas:
                        1. **Generar una Contraseña de Aplicación** (si tienes 2FA activado):
                           - Ve a: https://account.microsoft.com/security
                           - Activa verificación en dos pasos
                           - Genera una contraseña de aplicación
                           - Úsala en la configuración de arriba
                        
                        2. **Verificar credenciales** en la sección de configuración
                        
                        3. **Contactar al administrador** si es cuenta corporativa con restricciones
                        """)

with col_btn2:
    if st.button("📊 Enviar a Jefaturas", use_container_width=True, type="primary"):
        # Obtener credenciales de la sesión si están configuradas
        email_usar = st.session_state.get('email_config', OUTLOOK_EMAIL)
        password_usar = st.session_state.get('password_config', OUTLOOK_PASSWORD)
        
        with st.spinner("Enviando correo consolidado a jefaturas..."):
            # Modificar función para usar credenciales de sesión
            resultados, enviados, fallidos = enviar_a_jefaturas(email_usar, password_usar)
            
            if enviados > 0:
                st.success(f"✅ Se enviaron {enviados} correos a jefaturas exitosamente")
            if fallidos > 0:
                st.error(f"❌ Fallaron {fallidos} envíos")
            
            # Mostrar resultados detallados
            if resultados:
                df_resultados = pd.DataFrame(resultados)
                st.dataframe(df_resultados, use_container_width=True, hide_index=True)
                
                # Mostrar ayuda adicional si hay errores de autenticación
                if fallidos > 0:
                    errores_auth = [r for r in resultados if r.get('error') and ('535' in str(r.get('error')) or 'Authentication' in str(r.get('error')))]
                    if errores_auth:
                        st.warning("""
                        ⚠️ **Error de Autenticación Detectado**
                        
                        Si recibes error 535 (Authentication unsuccessful), necesitas:
                        1. **Generar una Contraseña de Aplicación** (si tienes 2FA activado):
                           - Ve a: https://account.microsoft.com/security
                           - Activa verificación en dos pasos
                           - Genera una contraseña de aplicación
                           - Úsala en la configuración de arriba
                        
                        2. **Verificar credenciales** en la sección de configuración
                        
                        3. **Contactar al administrador** si es cuenta corporativa con restricciones
                        """)

