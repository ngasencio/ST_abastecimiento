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

    def _norm_estado(v: object) -> str:
        return str(v or "").strip().lower()

    def _dias_hasta(ts: pd.Timestamp) -> int:
        """Días restantes considerando fecha+hora (ceil si futuro, floor si pasado)."""
        try:
            delta = ts - now
            secs = float(delta.total_seconds())
            if secs >= 0:
                return int(np.ceil(secs / 86400))
            return int(np.floor(secs / 86400))
        except Exception:
            return 0

    def _semaforo_dias(dias: int) -> str:
        if dias > 7:
            return "🟢"
        if 3 <= dias <= 7:
            return "🟡"
        return "🔴"

    def calcular_flujo(row):
        """
        Integra Estado (fuente de verdad) + fechas de hitos.
        Retorna: FechaClave, EstadoFlujo, EstadoFlujoSimple, DiasParaProximoHito
        """
        estado_raw = _norm_estado(row.get("Estado"))

        # 1) Estados finalizados (independiente de fechas)
        if estado_raw == "adjudicada":
            fecha = row.get("FechaAdjudicacion")
            return (fecha if pd.notna(fecha) else pd.NaT, "Adjudicada", "Adjudicada", "")

        if estado_raw.startswith("desierta"):
            # Incluye: "Desierta (o art. 3 ó 9 Ley 19.886)"
            fecha = row.get("FechaCierre")
            return (fecha if pd.notna(fecha) else pd.NaT, "Desierta", "Desierta", "")

        # 2) Estados en proceso: Publicada / Cerrada -> mantener lógica por hitos
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

        # EstadoFlujoSimple (mantener lógica actual)
        pub = row.get("FechaPublicacion")
        preguntas = row.get("FechaPubRespuestas") if "FechaPubRespuestas" in row.index else row.get("FechaPreguntas")
        cierre = row.get("FechaCierre")
        estimada_adj = row.get("FechaEstimadaAdjudicacion")

        # Asegurar comparación con fecha y hora completa
        if pd.notna(pub) and pd.notna(preguntas) and pub <= now < preguntas:
            estado_simple = "💬 Responder Preguntas"
        elif pd.notna(preguntas) and pd.notna(cierre) and preguntas <= now < cierre:
            estado_simple = "⏳ Por Cerrar"
        elif pd.notna(cierre) and pd.notna(estimada_adj) and cierre <= now < estimada_adj:
            estado_simple = "🧮 En Evaluación"
        elif pd.notna(pub) and now < pub:
            estado_simple = "📢 Pendiente de Publicación"
        elif pd.notna(estimada_adj) and now >= estimada_adj:
            estado_simple = "🏁 Post Adjudicación"
        else:
            estado_simple = "Sin Clasificar"

        # Días para próximo hito (solo para estados activos)
        dias_txt = ""
        if pd.notna(fecha_clave):
            dias = _dias_hasta(fecha_clave)
            dias_txt = f"{_semaforo_dias(dias)} {dias}d"

        return fecha_clave, estado, estado_simple, dias_txt

    # Aplicamos al dataframe
    if not df.empty:
        df[["FechaClave", "EstadoFlujo", "EstadoFlujoSimple", "DiasParaProximoHito"]] = df.apply(
            lambda row: pd.Series(calcular_flujo(row)),
            axis=1,
        )

    return df

# Procesamos los datos antes de mostrar la tabla
df_res_filtrado = procesar_estados_licitacion(df_res_filtrado)

st.markdown("## 📋 Detalles de licitaciones")
# Pestañas para organizar la visualización
tab1, tab2= st.tabs(["🛒 Panel de Control", "👥 Compradores"])

with tab1:
# ==============================================================================
# 4. TABLA MAESTRA DETALLADA (GEMBA)
# ==============================================================================
    st.markdown("### 📋 Panel de Control de Procesos (Gemba)")

    # GEMBA: solo procesos activos (Publicada / Cerrada)
    if "Estado" in df_res_filtrado.columns:
        df_gemba = df_res_filtrado[
            df_res_filtrado["Estado"].astype(str).str.strip().str.lower().isin(["publicada", "cerrada"])
        ].copy()
    else:
        df_gemba = df_res_filtrado.copy()

    # Ordenar por fecha clave (lo más urgente arriba)
    df_sorted = df_gemba.sort_values(by="FechaClave", ascending=True, na_position="last")

    # Columnas a mostrar
    cols_view = [
        "Tipo",
        "CodigoLicitacion",
        "Nombre",
        "C_Usuario",
        "EstadoFlujo",
        "EstadoFlujoSimple",
        "DiasParaProximoHito",
        "FechaClave",
        "MontoEstimado",
    ]

    # Filtro rápido por estado de flujo dinámico
    iconos_excluir = ["✅", "✍️"]
    opciones_estado = sorted(df_gemba["EstadoFlujo"].dropna().unique())
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
    def _fmt_clp(v):
        if pd.isna(v):
            return ""
        try:
            return f"$ {float(v):,.0f}".replace(",", ".")
        except Exception:
            return str(v)

    if "MontoEstimado" in df_view.columns:
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
            "DiasParaProximoHito": st.column_config.TextColumn(
                "⏱️ Días Próx. Hito",
                help="Días restantes al próximo hito (🟢>7 | 🟡3-7 | 🔴<3)",
                width="small",
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
        
        top_usr = (
            df_res_filtrado
            .groupby("C_Usuario", as_index=False)
            .agg(
                Licitaciones=("C_Usuario", "count"),
                MontoEstimado=("MontoEstimado", "sum")
            )
            .sort_values("MontoEstimado", ascending=False)
            .head(10)
        )
        top_usr["MontoEstimado"] = top_usr["MontoEstimado"].map("${:,.0f}".format)

        st.dataframe(top_usr, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("## ✅ Procesos Finalizados")

    def _fmt_var_adj(v) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        try:
            d = int(v)
        except Exception:
            return str(v)
        if d <= 0:
            return f"🟢 {abs(d)}d adelanto" if d < 0 else "🟢 0d a tiempo"
        return f"🔴 {d}d atraso"

    if "Estado" not in df_res_filtrado.columns:
        st.info("No está disponible la columna 'Estado' para separar adjudicadas/desiertas.")
        df_adjudicadas = df_res_filtrado.iloc[0:0].copy()
        df_desiertas = df_res_filtrado.iloc[0:0].copy()
    else:
        estado_norm = df_res_filtrado["Estado"].astype(str).str.strip().str.lower()
        df_adjudicadas = df_res_filtrado[estado_norm.eq("adjudicada")].copy()
        df_desiertas = df_res_filtrado[estado_norm.str.startswith("desierta")].copy()

    col_fin_1, col_fin_2 = st.columns(2, gap="large")

    with col_fin_1:
        st.markdown("### 🏆 Adjudicadas")
        if df_adjudicadas.empty:
            st.info("No hay procesos adjudicados para los filtros actuales.")
        else:
            st.caption(f"Total adjudicadas: {len(df_adjudicadas):,}")

            # Variación vs fecha estimada (negativo=adelanto, positivo=atraso)
            if "FechaAdjudicacion" in df_adjudicadas.columns and "FechaEstimadaAdjudicacion" in df_adjudicadas.columns:
                df_adjudicadas["VarAdjDias"] = (
                    pd.to_datetime(df_adjudicadas["FechaAdjudicacion"], errors="coerce")
                    - pd.to_datetime(df_adjudicadas["FechaEstimadaAdjudicacion"], errors="coerce")
                ).dt.days
                df_adjudicadas["DesempeñoAdjudicación"] = df_adjudicadas["VarAdjDias"].apply(_fmt_var_adj)
            else:
                df_adjudicadas["VarAdjDias"] = np.nan
                df_adjudicadas["DesempeñoAdjudicación"] = ""

            cols_adj = [
                "CodigoLicitacion",
                "Estado",
                "C_Usuario",
                "MontoEstimado",
                "FechaEstimadaAdjudicacion",
                "FechaAdjudicacion",
                "DesempeñoAdjudicación",
                "Adj_UrlActa",
            ]
            cols_adj = [c for c in cols_adj if c in df_adjudicadas.columns]
            df_adj_view = df_adjudicadas[cols_adj].copy()

            if "MontoEstimado" in df_adj_view.columns:
                df_adj_view["MontoEstimado"] = df_adj_view["MontoEstimado"].apply(_fmt_clp)

            st.dataframe(
                df_adj_view.sort_values(
                    by=[c for c in ["FechaAdjudicacion"] if c in df_adj_view.columns],
                    ascending=False,
                ).head(50),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "MontoEstimado": st.column_config.TextColumn("Monto (CLP)"),
                    "FechaEstimadaAdjudicacion": st.column_config.DateColumn("Fecha Estimada", format="DD-MM-YYYY"),
                    "FechaAdjudicacion": st.column_config.DateColumn("Fecha Real", format="DD-MM-YYYY"),
                    "Adj_UrlActa": st.column_config.LinkColumn("Acta", display_text="🔗 Acta") if "Adj_UrlActa" in df_adj_view.columns else None,
                },
            )

            with st.expander("📊 Desempeño por comprador (Adjudicación)", expanded=False):
                df_perf = df_adjudicadas.dropna(subset=["C_Usuario", "VarAdjDias"]).copy()
                if df_perf.empty:
                    st.info("No hay datos suficientes (fechas estimada/real) para analizar desempeño.")
                else:
                    resumen = (
                        df_perf.groupby("C_Usuario", as_index=False)
                        .agg(
                            Procesos=("CodigoLicitacion", "nunique"),
                            Promedio_Var_Días=("VarAdjDias", "mean"),
                            Mediana_Var_Días=("VarAdjDias", "median"),
                            A_Tiempo_o_Antes=("VarAdjDias", lambda s: int((s <= 0).sum())),
                            Atrasadas=("VarAdjDias", lambda s: int((s > 0).sum())),
                            Pct_Cumple=("VarAdjDias", lambda s: float((s <= 0).mean() * 100)),
                        )
                        .sort_values(["Pct_Cumple", "Procesos"], ascending=[False, False])
                    )
                    st.dataframe(
                        resumen,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Promedio_Var_Días": st.column_config.NumberColumn(format="%.1f"),
                            "Mediana_Var_Días": st.column_config.NumberColumn(format="%.1f"),
                            "Pct_Cumple": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                        },
                    )

    with col_fin_2:
        st.markdown("### 🚫 Desiertas")
        if df_desiertas.empty:
            st.info("No hay procesos desiertos para los filtros actuales.")
        else:
            st.caption(f"Total desiertas: {len(df_desiertas):,}")
            cols_des = [
                "CodigoLicitacion",
                "Estado",
                "C_Usuario",
                "MontoEstimado",
                "FechaPublicacion",
                "FechaCierre",
                "Adj_UrlActa",
            ]
            cols_des = [c for c in cols_des if c in df_desiertas.columns]
            df_des_view = df_desiertas[cols_des].copy()
            if "MontoEstimado" in df_des_view.columns:
                df_des_view["MontoEstimado"] = df_des_view["MontoEstimado"].apply(_fmt_clp)

            st.dataframe(
                df_des_view.sort_values(
                    by=[c for c in ["FechaCierre", "FechaPublicacion"] if c in df_des_view.columns],
                    ascending=False,
                ).head(50),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "MontoEstimado": st.column_config.TextColumn("Monto (CLP)"),
                    "FechaPublicacion": st.column_config.DateColumn(format="DD-MM-YYYY") if "FechaPublicacion" in df_des_view.columns else None,
                    "FechaCierre": st.column_config.DateColumn(format="DD-MM-YYYY") if "FechaCierre" in df_des_view.columns else None,
                    "Adj_UrlActa": st.column_config.LinkColumn("Acta", display_text="🔗 Acta") if "Adj_UrlActa" in df_des_view.columns else None,
                },
            )

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
    COMPRADORES = {
        "ALICIA VIDAL PAREDES": "alicia.vidal@redsalud.gob.cl",
        "ARIELA ACEVEDO": "ariela.acevedo@redsalud.gob.cl",
        "IVAN VARGAS OJEDA": "ivan.vargas@redsalud.gob.cl",
        "JACQUELINE OYARZUN ALVAREZ": "jacqueline.oyarzuna@redsalud.gob.cl",
        "LESLY ANDREA DÍAZ ABURTO": "lesly.diaz@redsalud.gob.cl",
        "MIGUEL ARO": "miguel.aro@redsalud.gob.cl",
        "ROSA VASQUEZ": "rosae.vasquez@redsalud.gob.cl",
        "RUBÉN URIBE": "ruben.uribe@redsalud.gob.cl",
        "JUAN FELIPE ROJEL HUENTRO": "juan.rojelh@redsalud.gob.cl",
        "VERÓNICA ARACELY MÁRQUEZ AGUILAR": "veronica.marquez.a@redsalud.gob.cl",
        "BASTIAN MIRANDA CORONADO": "bastian.miranda@redsalud.gob.cl",
        "NICOLAS ASENCIO MOREIRA": "nicolas.asencio@redsalud.gob.cl",
    }

    JEFATURAS = {
        "Cristina Flores": "cristina.flores@redsalud.gob.cl",
        "Sandra Espinoza": "sandrap.espinoza@redsalud.gob.cl",
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
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">ID Licitación</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Nombre del Proceso</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">📍 Etapa Actual</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">📅 Fecha Hito</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Monto Est. (CLP)</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Tipo</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for _, row in df_sorted.head(20).iterrows():  # Limitar a 20 para el correo
            codigo = str(row.get('CodigoLicitacion', ''))
            nombre = str(row.get('Nombre', ''))[:80] + ('...' if len(str(row.get('Nombre', ''))) > 80 else '')
            estado_flujo = str(row.get('EstadoFlujo', 'Sin estado'))
            fecha_clave = row.get('FechaClave', '')
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
        """Genera HTML del tablero GEMBA consolidado para jefaturas (autónomo para envío por correo)."""
        if df_resumen.empty:
            return "<p>No hay datos disponibles para el período.</p>"

        df = df_resumen.copy()

        # Normalizar columnas clave
        if "MontoEstimado" in df.columns:
            df["MontoEstimado"] = pd.to_numeric(df["MontoEstimado"], errors="coerce").fillna(0)
        else:
            df["MontoEstimado"] = 0

        def _fmt_clp(v) -> str:
            try:
                v = float(v)
                return f"$ {v:,.0f}".replace(",", ".")
            except Exception:
                return str(v)

        def _fmt_fecha(v) -> str:
            try:
                ts = pd.to_datetime(v, errors="coerce")
                if pd.isna(ts):
                    return ""
                return ts.strftime("%d-%m-%Y")
            except Exception:
                return ""

        # =========================
        # Cálculos base
        # =========================
        if "Estado" in df.columns:
            estado_norm = df["Estado"].astype(str).str.strip().str.lower()
            mask_activas = estado_norm.isin(["publicada", "cerrada"])
        else:
            mask_activas = pd.Series(True, index=df.index)

        df_activas = df[mask_activas].copy()

        total_activas = len(df_activas)
        monto_total_activas = df_activas["MontoEstimado"].sum()

        # Para ordenamiento por comprador (GEMBA, datos generales)
        if "C_Usuario" in df_activas.columns:
            resumen_act_por_comprador = (
                df_activas.groupby("C_Usuario")
                .agg(
                    Cantidad=("CodigoLicitacion", "nunique"),
                    MontoEstimado=("MontoEstimado", "sum"),
                )
                .reset_index()
            )
        else:
            resumen_act_por_comprador = pd.DataFrame(columns=["C_Usuario", "Cantidad", "MontoEstimado"])

        # Para tipos principales por comprador
        if {"C_Usuario", "Tipo"}.issubset(df_activas.columns):
            tipos_top = (
                df_activas.groupby(["C_Usuario", "Tipo"])
                .size()
                .reset_index(name="n")
                .sort_values(["C_Usuario", "n"], ascending=[True, False])
                .drop_duplicates("C_Usuario")
                .set_index("C_Usuario")["Tipo"]
            )
        else:
            tipos_top = {}

        # =========================
        # Bloque: Resumen Ejecutivo + Métrica Total Licitaciones Activas
        # =========================
        html = """
        <div class="gemba-email-root" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; color: #333;">
        <style>
            .gemba-section { margin-top: 24px; }
            .gemba-section h3 { color: #138AEC; margin-bottom: 10px; }
            .gemba-card-container { display: flex; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }
            .gemba-card {
                background-color: #f0f0f0;
                padding: 12px 16px;
                border-radius: 8px;
                flex: 1 1 220px;
                box-sizing: border-box;
            }
            .gemba-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
                font-size: 13px;
            }
            .gemba-table th {
                padding: 8px 10px;
                border: 1px solid #ddd;
                background-color: #138AEC;
                color: white;
                text-align: left;
            }
            .gemba-table td {
                padding: 6px 10px;
                border: 1px solid #ddd;
                text-align: left;
            }
            .gemba-bar-row {
                display: flex;
                align-items: center;
                margin-bottom: 6px;
                gap: 6px;
            }
            .gemba-bar-label {
                width: 35%;
                font-size: 12px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .gemba-bar-track {
                flex: 1;
                background-color: #eee;
                border-radius: 999px;
                overflow: hidden;
                height: 14px;
            }
            .gemba-bar-fill {
                background: linear-gradient(90deg, #138AEC, #3E9FEF);
                height: 100%;
                position: relative;
            }
            .gemba-bar-value {
                position: absolute;
                right: 6px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 11px;
                color: white;
            }
            .gemba-bar-type {
                width: 20%;
                font-size: 11px;
                color: #555;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .gemba-flex-row {
                display: flex;
                flex-wrap: wrap;
                gap: 18px;
            }
            .gemba-flex-col {
                flex: 1 1 260px;
                box-sizing: border-box;
            }
            .gemba-details {
                margin-bottom: 10px;
                border-radius: 6px;
                border: 1px solid #ddd;
                background-color: #fafafa;
                padding: 6px 10px;
            }
            .gemba-details summary {
                cursor: pointer;
                font-weight: 600;
                color: #2c3e50;
                outline: none;
            }
            .gemba-tag-proceso {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 999px;
                font-size: 11px;
                background-color: #FF6B6B;
                color: white;
            }
        </style>
        """

        html += """
        <div class="gemba-section">
            <h3>Resumen Ejecutivo del Mes</h3>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 8px;">
                <tr>
                    <td width="50%" valign="top" style="padding-right: 8px;">
                        <div class="gemba-card" style="background-color: #f0f0f0; padding: 12px 16px; border-radius: 8px; box-sizing: border-box;">
                            <strong>Total Licitaciones Activas:</strong><br>
                            <span style="font-size: 20px; font-weight: 700;">{total_activas}</span>
                        </div>
                    </td>
                    <td width="50%" valign="top" style="padding-left: 8px;">
                        <div class="gemba-card" style="background-color: #f0f0f0; padding: 12px 16px; border-radius: 8px; box-sizing: border-box;">
                            <strong>Monto Total Estimado (Activas):</strong><br>
                            <span style="font-size: 18px; font-weight: 600;">{monto_total}</span>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
        """.format(
            total_activas=total_activas,
            monto_total=_fmt_clp(monto_total_activas),
        )

        # =========================
        # Bloque 1: Datos Generales
        # =========================
        html += """
        <div class="gemba-section">
            <h3>1) Datos Generales</h3>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout: fixed;">
                <tr>
                    <td width="55%" valign="top" style="padding-right: 15px;">
                        <h4 style="margin: 4px 0 8px;">Licitaciones Activas por Comprador</h4>
        """

        if not resumen_act_por_comprador.empty:
            resumen_act_por_comprador = resumen_act_por_comprador.sort_values(
                "MontoEstimado", ascending=False
            )
            max_cant = float(resumen_act_por_comprador["Cantidad"].max() or 1)

            for _, row in resumen_act_por_comprador.iterrows():
                comprador = row["C_Usuario"]
                cant = int(row["Cantidad"])
                width_pct = max(8, int(cant / max_cant * 100))
                tipo_principal = tipos_top.get(comprador, "") if isinstance(tipos_top, dict) or hasattr(tipos_top, "get") else ""

                html += """
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 6px;">
                        <tr>
                            <td width="35%" style="font-size: 12px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 6px;" title="{comprador}">
                                {comprador}
                            </td>
                            <td width="45%" valign="middle">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #eee; border-radius: 4px; height: 16px;">
                                    <tr>
                                        <td width="{width}%" style="background-color: #138AEC; border-radius: 4px; height: 16px; text-align: right; vertical-align: middle;">
                                            <span style="font-size: 11px; color: white; margin-right: 6px; font-weight: bold;">{cant}</span>
                                        </td>
                                        <td width="{rem_width}%" style="border-radius: 4px; height: 16px;"></td>
                                    </tr>
                                </table>
                            </td>
                            
                        </tr>
                    </table>
                """.format(
                    comprador=comprador,
                    width=width_pct,
                    rem_width=100 - width_pct,
                    cant=cant,
                    tipo=tipo_principal or "",
                )
        else:
            html += "<p>No hay licitaciones activas para mostrar.</p>"

        html += """
                    </td>
                    <td width="45%" valign="top">
                        <h4 style="margin: 4px 0 8px;">Resumen por Comprador</h4>
                        <table class="gemba-table" width="100%">
                            <thead>
                                <tr>
                                    <th>Comprador</th>
                                    <th>Licitaciones Activas</th>
                                    <th>Monto Total (CLP)</th>
                                </tr>
                            </thead>
                            <tbody>
        """

        if not resumen_act_por_comprador.empty:
            for _, row in resumen_act_por_comprador.iterrows():
                html += """
                            <tr>
                                <td>{comprador}</td>
                                <td>{cant}</td>
                                <td>{monto}</td>
                            </tr>
                """.format(
                    comprador=row["C_Usuario"],
                    cant=int(row["Cantidad"]),
                    monto=_fmt_clp(row["MontoEstimado"]),
                )
        else:
            html += """
                            <tr>
                                <td colspan="3">No hay información de compradores para licitaciones activas.</td>
                            </tr>
            """

        html += """
                        </tbody>
                    </table>
                    </td>
                </tr>
            </table>
        </div>
        """

        # =========================
        # Bloque 2: Tablero GEMBA por Comprador
        # =========================
        html += """
        <div class="gemba-section">
            <h3>2) Tablero Mercado Público - Licitaciones Activas por Comprador</h3>
        """

        if not df_activas.empty and "C_Usuario" in df_activas.columns:
            montos_por_comprador = (
                df_activas.groupby("C_Usuario")["MontoEstimado"].sum().sort_values(ascending=False)
            )
            for comprador, monto_total_comp in montos_por_comprador.items():
                df_c = df_activas[df_activas["C_Usuario"] == comprador].copy()
                df_c = df_c.sort_values(
                    by=["FechaClave", "CodigoLicitacion"] if "FechaClave" in df_c.columns else "CodigoLicitacion"
                )

                html += """
            <details class="gemba-details">
                <br>
                <summary> <strong>{comprador} — {n} licitaciones activas, Monto: {monto}</strong></summary>
                <table class="gemba-table" style="table-layout: fixed; width: 100%; text-align: left;">
                    <thead>
                        <tr>
                            <th style="width: 12%;">ID Licitación</th>
                            <th style="width: 30%;">Nombre</th>
                            <th style="width: 15%;">Etapa Actual</th>
                            <th style="width: 15%;">Estado Simple</th>
                            <th style="width: 8%;" style="text-align: center;">Días</th>
                            <th style="width: 10%;" style="text-align: center;">Fecha</th>
                            <th style="width: 10%;" style="text-align: center;">Monto</th>
                        </tr>
                    </thead>
                    <br>
                    <tbody>
                """.format(
                    comprador=comprador,
                    n=len(df_c),
                    monto=_fmt_clp(monto_total_comp),
                )

                for _, r in df_c.iterrows():
                    codigo = r.get("CodigoLicitacion", "")
                    nombre = r.get("Nombre", "")
                    etapa = r.get("EstadoFlujo", "")
                    estado_simple = r.get("EstadoFlujoSimple", "")
                    dias = r.get("DiasParaProximoHito", "")
                    fecha = _fmt_fecha(r.get("FechaClave"))
                    monto = _fmt_clp(r.get("MontoEstimado", 0))

                    html += """
                        <tr>
                            <td>{codigo}</td>
                            <td>{nombre}</td>
                            <td>{etapa}</td>
                            <td>{estado_simple}</td>
                            <td style="text-align: center;">{dias}</td>
                            <td style="text-align: center;">{fecha}</td>
                            <td style="text-align: center;">{monto}</td>
                        </tr>
                    """.format(
                        codigo=codigo,
                        nombre=nombre,
                        etapa=etapa,
                        estado_simple=estado_simple,
                        dias=dias,
                        fecha=fecha,
                        monto=monto,
                    )

                html += """
                    </tbody>
                </table>
            </details>
                """
        else:
            html += "<p>No hay licitaciones activas para construir el tablero GEMBA.</p>"

        html += "</div>"  # cierre sección GEMBA

        # =========================
        # Bloque 3: Licitaciones Adjudicadas (últimas 10)
        # =========================
        html += """
        <div class="gemba-section">
            <h3>3) ✅ Licitaciones Adjudicadas (Últimas 10)</h3>
            <table class="gemba-table">
                <thead>
                    <tr>
                        <th>ID Licitación</th>
                        <th>Nombre</th>
                        <th>Fecha Adjudicación</th>
                        <th>Comprador</th>
                        <th>Monto Estimado</th>
                        <th>URL</th>
                    </tr>
                </thead>
                <tbody>
        """

        if "Estado" in df.columns:
            estado_norm_all = df["Estado"].astype(str).str.strip().str.lower()
            df_adj = df[estado_norm_all.str.contains("adjudic", na=False)].copy()
        else:
            df_adj = df[df.get("EstadoFlujoSimple", "").astype(str).str.contains("adjudic", na=False)].copy()

        if not df_adj.empty:
            if "FechaAdjudicacion" in df_adj.columns:
                df_adj = df_adj.sort_values("FechaAdjudicacion", ascending=False)
            df_adj = df_adj.head(10)

            url_col = None
            for candidate in ["Adj_UrlActa", "URL", "UrlLicitacion", "Link"]:
                if candidate in df_adj.columns:
                    url_col = candidate
                    break

            for _, r in df_adj.iterrows():
                codigo = r.get("CodigoLicitacion", "")
                nombre = r.get("Nombre", "")
                fecha_adj = _fmt_fecha(r.get("FechaAdjudicacion"))
                comprador = r.get("C_Usuario", "")
                monto = _fmt_clp(r.get("MontoEstimado", 0))
                url_val = r.get(url_col, "") if url_col else ""
                if url_val:
                    url_html = f'<a href="{url_val}" target="_blank">Ver</a>'
                else:
                    url_html = "-"

                html += """
                    <tr>
                        <td>{codigo}</td>
                        <td>{nombre}</td>
                        <td>{fecha}</td>
                        <td>{comprador}</td>
                        <td>{monto}</td>
                        <td>{url}</td>
                    </tr>
                """.format(
                    codigo=codigo,
                    nombre=nombre,
                    fecha=fecha_adj,
                    comprador=comprador,
                    monto=monto,
                    url=url_html,
                )
        else:
            html += """
                    <tr>
                        <td colspan="6">No se encontraron licitaciones adjudicadas para el período.</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        # =========================
        # Bloque 4: Procesos Desiertos (últimos 10)
        # =========================
        html += """
        <div class="gemba-section">
            <h3>4) 🚫 Procesos Desiertos (Últimos 10)</h3>
            <table class="gemba-table">
                <thead>
                    <tr>
                        <th>ID Licitación</th>
                        <th>Nombre</th>
                        <th>Fecha Adjudicación</th>
                        <th>Comprador</th>
                        <th>Monto Estimado</th>
                        <th>URL</th>
                    </tr>
                </thead>
                <tbody>
        """

        if "Estado" in df.columns:
            mask_desierta = estado_norm_all.str.contains("desierta", na=False) | estado_norm_all.str.contains(
                "art. 3", na=False
            ) | estado_norm_all.str.contains("art. 9", na=False) | estado_norm_all.str.contains("19.886", na=False)
            df_des = df[mask_desierta].copy()
        else:
            df_des = df[df.get("EstadoFlujoSimple", "").astype(str).str.contains("desiert", na=False)].copy()

        if not df_des.empty:
            if "FechaAdjudicacion" in df_des.columns:
                df_des = df_des.sort_values("FechaAdjudicacion", ascending=False)
            df_des = df_des.head(10)

            url_col_des = None
            for candidate in ["Adj_UrlActa", "URL", "UrlLicitacion", "Link"]:
                if candidate in df_des.columns:
                    url_col_des = candidate
                    break

            for _, r in df_des.iterrows():
                codigo = r.get("CodigoLicitacion", "")
                nombre = r.get("Nombre", "")
                fecha_adj = _fmt_fecha(r.get("FechaAdjudicacion"))
                comprador = r.get("C_Usuario", "")
                monto = _fmt_clp(r.get("MontoEstimado", 0))
                url_val = r.get(url_col_des, "") if url_col_des else ""
                if url_val:
                    url_html = f'<a href="{url_val}" target="_blank">Ver</a>'
                else:
                    url_html = "-"

                html += """
                    <tr>
                        <td>{codigo}</td>
                        <td>{nombre}</td>
                        <td>{fecha}</td>
                        <td>{comprador}</td>
                        <td>{monto}</td>
                        <td>{url}</td>
                    </tr>
                """.format(
                    codigo=codigo,
                    nombre=nombre,
                    fecha=fecha_adj,
                    comprador=comprador,
                    monto=monto,
                    url=url_html,
                )
        else:
            html += """
                    <tr>
                        <td colspan="6">No se encontraron procesos desiertos para el período.</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        </div>
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
            "Revisar el estado actual de la licitación.",
            "Coordinar con las unidades involucradas y realizar las citaciones a la comisión evaluadora.",
            "Realizar la creación de las resoluciones correspondientes a cada etapa del proceso, respetando las fechas establecidas en el cronograma de la licitación."
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
                    <h1 style="margin: 0; font-size: 26px;">📋 Reporte de Licitaciones - Tablero Mercado Público</h1>
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
                    <h2>📊 Tablero Mercado Público Personalizado</h2>
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
                           <li>Revise regularmente el estado de sus licitaciones asignadas.</li>
                           <li>Priorice las licitaciones con fechas de cierre próximas.</li>
                           <li>Revise periódicamente consultas y respuestas para evitar omisiones.</li>
                           <li>Verifique el cumplimiento de los plazos establecidos en el cronograma oficial.</li>
                           <li>Confirme que toda la documentación requerida esté completa y correctamente publicada.</li>
                           <li>Mantenga respaldo digital de resoluciones, actas y antecedentes relevantes.</li>
                           <li>Coordine oportunamente con la comisión evaluadora y las unidades técnicas.</li>    
                           <li>Comunique cualquier retraso o inconveniente a su jefatura.</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Este es un correo automatizado del Sistema de Gestión de Abastecimiento</p>
                    <p>Servicio de Salud Osorno - Departamento de Abastecimiento y Operaciones</p>
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
                    <h1 style="color:#001C41;">
                        📊 Reporte Consolidado Mensual - Tablero Mercado Público
                    </h1>
                    <p style="margin: 10px 0 0 0; 
                        color: #001C41; 
                        font-weight: 500; 
                        opacity: 0.85;">
                        Servicio de Salud Osorno - Departamento de Abastecimiento y Operaciones
                    </p>
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
                    <p>Servicio de Salud Osorno - Departamento de Abastecimiento y Operaciones</p>
                    <p>Para consultas adicionales, acceda al Sistema de Gestión de Abastecimiento</p>
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
                asunto = f"Reporte de Licitaciones - Tablero Mercado Público - {nombre_comprador}"
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
            asunto = f"Reporte Consolidado Mensual - Tablero Mercado Público - {datetime.now().strftime('%B %Y')}"
            
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

with tab2:
    st.markdown("## 👥 Análisis de Compradores")
    st.markdown("Vista consolidada y ejecutiva del desempeño de cada comprador para optimizar asignación de recursos y supervisión.")
    
    # ==============================================================================
    # FUNCIONES AUXILIARES
    # ==============================================================================
    
    def calcular_ponderacion(tipo: str) -> int:
        """Calcula el peso de carga laboral según el tipo de licitación"""
        pesos = {"LR": 5, "LP": 4, "LE": 3, "L1": 2}
        tipo_clean = str(tipo).strip().upper() if pd.notna(tipo) else ""
        # Buscar coincidencias parciales (ej: "LP25" -> "LP")
        for key, peso in pesos.items():
            if tipo_clean.startswith(key):
                return peso
        return 1  # Peso por defecto si no coincide
    
    def clasificar_estado(row) -> str:
        """Clasifica el estado de la licitación"""
        estado_raw = str(row.get("Estado", "") or "").strip().lower()
        estado_flujo = str(row.get("EstadoFlujo", "") or "").strip()
        
        if estado_raw == "adjudicada":
            return "Adjudicada"
        if estado_raw.startswith("desierta"):
            return "Desierta"
        if estado_raw == "publicada":
            return "Publicada"
        if estado_raw == "cerrada":
            return "Cerrada"
        # Si tiene EstadoFlujo que indica proceso activo
        if any(x in estado_flujo for x in ["📢", "💬", "⏳", "🧮", "🛠️", "💰"]):
            return "En Proceso"
        return "Otro"
    
    # ==============================================================================
    # PREPARACIÓN DE DATOS
    # ==============================================================================
    
    # Asegurar que tenemos las columnas necesarias
    df_analisis = df_res_filtrado.copy()
    
    # Agregar columnas calculadas
    if "Tipo" in df_analisis.columns:
        df_analisis["Ponderacion"] = df_analisis["Tipo"].apply(calcular_ponderacion)
        df_analisis["CargaPonderada"] = df_analisis["Ponderacion"]  # 1 licitación = 1 unidad ponderada
    else:
        df_analisis["Ponderacion"] = 1
        df_analisis["CargaPonderada"] = 1
    
    df_analisis["EstadoClasificado"] = df_analisis.apply(clasificar_estado, axis=1)
    
    # Normalizar montos
    if "MontoEstimado" not in df_analisis.columns:
        df_analisis["MontoEstimado"] = 0
    df_analisis["MontoEstimado"] = pd.to_numeric(df_analisis["MontoEstimado"], errors="coerce").fillna(0)
    
    # ==============================================================================
    # SELECTOR DE COMPRADOR
    # ==============================================================================
    
    st.markdown("### 🔍 Selección de Comprador")
    
    compradores_disponibles = sorted(df_analisis["C_Usuario"].dropna().unique().tolist())
    opciones_comprador = ["Todos los Compradores"] + compradores_disponibles
    
    comprador_seleccionado = st.selectbox(
        "Selecciona un comprador para análisis detallado:",
        options=opciones_comprador,
        index=0,
        help="Selecciona un comprador específico o 'Todos los Compradores' para vista consolidada"
    )
    
    # Filtrar por comprador si se seleccionó uno específico
    if comprador_seleccionado == "Todos los Compradores":
        df_comprador = df_analisis.copy()
        titulo_comprador = "Todos los Compradores"
    else:
        df_comprador = df_analisis[df_analisis["C_Usuario"] == comprador_seleccionado].copy()
        titulo_comprador = comprador_seleccionado
    
    # ==============================================================================
    # KPIs PRINCIPALES
    # ==============================================================================
    
    st.markdown("### 📊 Métricas Clave")
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    carga_ponderada_total = df_comprador["CargaPonderada"].sum()
    licitaciones_en_proceso = len(df_comprador[df_comprador["EstadoClasificado"] == "En Proceso"])
    monto_total = df_comprador["MontoEstimado"].sum()
    monto_en_proceso = df_comprador[df_comprador["EstadoClasificado"] == "En Proceso"]["MontoEstimado"].sum()
    
    with col_kpi1:
        st.metric(
            label="⚖️ Carga Ponderada Total",
            value=f"{carga_ponderada_total:.0f}",
            help="Suma de licitaciones ponderadas según tipo (LR=5, LP=4, LE=3, L1=2)"
        )
    
    with col_kpi2:
        st.metric(
            label="🔄 Licitaciones En Proceso",
            value=f"{licitaciones_en_proceso}",
            delta=f"{licitaciones_en_proceso - len(df_comprador) + licitaciones_en_proceso}" if licitaciones_en_proceso > 0 else None,
            delta_color="inverse",
            help="Licitaciones activas que requieren seguimiento"
        )
    
    with col_kpi3:
        st.metric(
            label="💰 Monto Total",
            value=f"${monto_total:,.0f}",
            help="Monto total estimado de todas las licitaciones"
        )
    
    with col_kpi4:
        st.metric(
            label="⚠️ Monto En Proceso",
            value=f"${monto_en_proceso:,.0f}",
            help="Monto total de licitaciones en proceso activo"
        )
    
    # Alerta si hay alta carga o montos en proceso
    if carga_ponderada_total > 50:
        st.warning(f"⚠️ **Alta Carga Laboral**: {titulo_comprador} tiene una carga ponderada de {carga_ponderada_total:.0f}, considerando redistribución de recursos.")
    
    if monto_en_proceso > monto_total * 0.7:
        st.warning(f"⚠️ **Alto Monto en Proceso**: {monto_en_proceso/monto_total*100:.1f}% del monto total está en proceso activo.")
    
    # ==============================================================================
    # GRÁFICOS Y VISUALIZACIONES
    # ==============================================================================
    
    st.markdown("---")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.markdown("#### 📊 Distribución por Estado")
        
        # Contar estados
        conteo_estados = df_comprador["EstadoClasificado"].value_counts()
        
        # Colores diferenciados: destacar "En Proceso"
        colores_estados = {
            "En Proceso": "#FF6B6B",  # Rojo destacado
            "Publicada": "#4ECDC4",   # Turquesa
            "Cerrada": "#95E1D3",      # Verde claro
            "Adjudicada": "#F38181",   # Rosa
            "Desierta": "#AA96DA",      # Morado
            "Otro": "#C7CEEA"          # Gris claro
        }
        
        colores = [colores_estados.get(estado, "#C7CEEA") for estado in conteo_estados.index]
        
        fig_torta = px.pie(
            values=conteo_estados.values,
            names=conteo_estados.index,
            title=f"Estados de Licitaciones - {titulo_comprador}",
            color_discrete_sequence=colores,
            hole=0.4
        )
        fig_torta.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
        )
        fig_torta.update_layout(
            height=400,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, x=1.15)
        )
        st.plotly_chart(fig_torta, use_container_width=True)
    
    with col_graf2:
        st.markdown("#### 📈 Licitaciones por Tipo")
        
        # Agrupar por Tipo
        if "Tipo" in df_comprador.columns:
            conteo_tipo = df_comprador.groupby("Tipo").agg(
                Cantidad=("CodigoLicitacion", "count"),
                CargaPonderada=("CargaPonderada", "sum"),
                MontoTotal=("MontoEstimado", "sum")
            ).reset_index()
            conteo_tipo = conteo_tipo.sort_values("Cantidad", ascending=True)
            
            # Colores diferenciados por tipo
            colores_tipo = px.colors.qualitative.Set3[:len(conteo_tipo)]
            
            fig_barras = px.bar(
                conteo_tipo,
                x="Cantidad",
                y="Tipo",
                orientation='h',
                title=f"Distribución por Tipo - {titulo_comprador}",
                color="CargaPonderada",
                color_continuous_scale="YlOrRd",
                labels={"Cantidad": "Cantidad de Licitaciones", "Tipo": "Tipo", "CargaPonderada": "Carga Ponderada"},
                hover_data=["MontoTotal"]
            )
            fig_barras.update_layout(
                height=400,
                xaxis_title="Cantidad de Licitaciones",
                yaxis_title="Tipo",
                showlegend=False
            )
            fig_barras.update_traces(
                hovertemplate='<b>%{y}</b><br>Cantidad: %{x}<br>Carga Ponderada: %{customdata[0]:.0f}<br>Monto: $%{customdata[1]:,.0f}<extra></extra>',
                customdata=conteo_tipo[["CargaPonderada", "MontoTotal"]].values
            )
            st.plotly_chart(fig_barras, use_container_width=True)
        else:
            st.info("No hay información de Tipo disponible para este comprador.")
    
    # ==============================================================================
    # TABLA DE RESUMEN POR TIPO
    # ==============================================================================
    
    st.markdown("---")
    st.markdown("### 📋 Resumen Detallado por Tipo")
    
    if "Tipo" in df_comprador.columns:
        resumen_tipo = df_comprador.groupby("Tipo").agg(
            Cantidad=("CodigoLicitacion", "count"),
            MontoTotal=("MontoEstimado", "sum"),
            CargaPonderada=("CargaPonderada", "sum"),
            EnProceso=("EstadoClasificado", lambda x: (x == "En Proceso").sum())
        ).reset_index()
        
        resumen_tipo["PromedioMonto"] = resumen_tipo["MontoTotal"] / resumen_tipo["Cantidad"]
        resumen_tipo = resumen_tipo.sort_values("CargaPonderada", ascending=False)
        
        # Formatear montos
        resumen_tipo["MontoTotal_Fmt"] = resumen_tipo["MontoTotal"].apply(lambda x: f"${x:,.0f}")
        resumen_tipo["PromedioMonto_Fmt"] = resumen_tipo["PromedioMonto"].apply(lambda x: f"${x:,.0f}")
        
        # Preparar para visualización
        resumen_display = resumen_tipo[[
            "Tipo", "Cantidad", "CargaPonderada", "EnProceso",
            "MontoTotal_Fmt", "PromedioMonto_Fmt"
        ]].copy()
        resumen_display.columns = [
            "Tipo", "Cantidad", "⚖️ Carga Ponderada", "🔄 En Proceso",
            "💰 Monto Total", "📊 Promedio Monto"
        ]
        
        st.dataframe(
            resumen_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "⚖️ Carga Ponderada": st.column_config.NumberColumn(
                    "⚖️ Carga Ponderada",
                    format="%.0f",
                    help="Métrica principal de carga laboral"
                ),
                "🔄 En Proceso": st.column_config.NumberColumn(
                    "🔄 En Proceso",
                    format="%d",
                    help="Licitaciones activas en proceso"
                ),
            }
        )
    else:
        st.info("No hay información de Tipo disponible para generar el resumen.")
    
    # ==============================================================================
    # ANÁLISIS DE CARGA LABORAL POR COMPRADOR (Vista Consolidada)
    # ==============================================================================
    
    st.markdown("---")
    st.markdown("### 👥 Análisis de Carga Laboral por Comprador")
    
    if comprador_seleccionado == "Todos los Compradores":
        # Vista consolidada: análisis de todos los compradores
        carga_por_comprador = df_analisis.groupby("C_Usuario").agg(
            CantidadLicitaciones=("CodigoLicitacion", "count"),
            CargaPonderada=("CargaPonderada", "sum"),
            MontoTotal=("MontoEstimado", "sum"),
            EnProceso=("EstadoClasificado", lambda x: (x == "En Proceso").sum()),
            Publicadas=("EstadoClasificado", lambda x: (x == "Publicada").sum()),
            Cerradas=("EstadoClasificado", lambda x: (x == "Cerrada").sum())
        ).reset_index()
        
        carga_por_comprador["PromedioMonto"] = carga_por_comprador["MontoTotal"] / carga_por_comprador["CantidadLicitaciones"]
        carga_por_comprador = carga_por_comprador.sort_values("CargaPonderada", ascending=False)
        
        # Gráfico de barras horizontales
        fig_carga = px.bar(
            carga_por_comprador.head(15),
            x="CargaPonderada",
            y="C_Usuario",
            orientation='h',
            title="Top 15 Compradores por Carga Ponderada",
            color="MontoTotal",
            color_continuous_scale="Viridis",
            labels={"CargaPonderada": "Carga Ponderada", "C_Usuario": "Comprador"},
            hover_data=["CantidadLicitaciones", "EnProceso", "MontoTotal"]
        )
        fig_carga.update_layout(
            height=600,
            xaxis_title="Carga Ponderada (Métrica Principal)",
            yaxis_title="Comprador",
            yaxis={'categoryorder': 'total ascending'}
        )
        fig_carga.update_traces(
            hovertemplate='<b>%{y}</b><br>Carga Ponderada: %{x:.0f}<br>Licitaciones: %{customdata[0]}<br>En Proceso: %{customdata[1]}<br>Monto: $%{customdata[2]:,.0f}<extra></extra>',
            customdata=carga_por_comprador[["CantidadLicitaciones", "EnProceso", "MontoTotal"]].head(15).values
        )
        st.plotly_chart(fig_carga, use_container_width=True)
        
        # Tabla detallada
        carga_display = carga_por_comprador[[
            "C_Usuario", "CantidadLicitaciones", "CargaPonderada",
            "EnProceso", "Publicadas", "Cerradas", "MontoTotal"
        ]].copy()
        carga_display["MontoTotal_Fmt"] = carga_display["MontoTotal"].apply(lambda x: f"${x:,.0f}")
        carga_display = carga_display.drop("MontoTotal", axis=1)
        carga_display.columns = [
            "Comprador", "Cantidad", "⚖️ Carga Ponderada",
            "🔄 En Proceso", "📢 Publicadas", "⏳ Cerradas", "💰 Monto Total"
        ]
        
        st.dataframe(
            carga_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "⚖️ Carga Ponderada": st.column_config.NumberColumn(
                    "⚖️ Carga Ponderada",
                    format="%.0f",
                    help="Métrica principal de carga laboral"
                ),
                "🔄 En Proceso": st.column_config.NumberColumn(
                    "🔄 En Proceso",
                    format="%d"
                ),
            }
        )
    else:
        # Vista individual: mostrar detalle de licitaciones del comprador seleccionado
        st.markdown(f"#### 📋 Licitaciones de {comprador_seleccionado}")
        
        cols_detalle = [
            "CodigoLicitacion", "Nombre", "Tipo", "EstadoClasificado",
            "EstadoFlujo", "MontoEstimado", "FechaClave", "DiasParaProximoHito"
        ]
        cols_detalle = [c for c in cols_detalle if c in df_comprador.columns]
        
        df_detalle = df_comprador[cols_detalle].copy()
        
        # Formatear montos
        if "MontoEstimado" in df_detalle.columns:
            df_detalle["MontoEstimado"] = df_detalle["MontoEstimado"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) and x != 0 else ""
            )
        
        # Resaltar "En Proceso"
        st.dataframe(
            df_detalle.sort_values(
                by=[c for c in ["EstadoClasificado", "FechaClave"] if c in df_detalle.columns],
                ascending=[True, True]
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "EstadoClasificado": st.column_config.TextColumn(
                    "Estado",
                    help="Estado clasificado de la licitación"
                ),
                "MontoEstimado": st.column_config.TextColumn("Monto (CLP)"),
                "FechaClave": st.column_config.DateColumn(format="DD/MM/YYYY"),
            }
        )
    
    # ==============================================================================
    # MÉTRICAS ADICIONALES DE IMPACTO
    # ==============================================================================
    
    st.markdown("---")
    st.markdown("### 🎯 Métricas de Impacto y Seguimiento")
    
    col_met1, col_met2, col_met3 = st.columns(3)
    
    with col_met1:
        # Comprador con mayor carga ponderada
        if comprador_seleccionado == "Todos los Compradores":
            max_carga = df_analisis.groupby("C_Usuario")["CargaPonderada"].sum().idxmax()
            max_carga_valor = df_analisis.groupby("C_Usuario")["CargaPonderada"].sum().max()
            st.metric(
                label="👤 Comprador con Mayor Carga",
                value=max_carga,
                delta=f"{max_carga_valor:.0f} puntos",
                help="Comprador con mayor carga laboral ponderada"
            )
        else:
            st.metric(
                label="📊 Posición en Ranking",
                value=f"#{list(df_analisis.groupby('C_Usuario')['CargaPonderada'].sum().sort_values(ascending=False).index).index(comprador_seleccionado) + 1}",
                help="Posición del comprador en ranking de carga ponderada"
            )
    
    with col_met2:
        # Porcentaje de licitaciones en proceso
        pct_en_proceso = (licitaciones_en_proceso / len(df_comprador) * 100) if len(df_comprador) > 0 else 0
        st.metric(
            label="📈 % En Proceso",
            value=f"{pct_en_proceso:.1f}%",
            help="Porcentaje de licitaciones en proceso activo"
        )
    
    with col_met3:
        # Promedio de monto por licitación
        promedio_monto = monto_total / len(df_comprador) if len(df_comprador) > 0 else 0
        st.metric(
            label="💵 Promedio Monto/Licitación",
            value=f"${promedio_monto:,.0f}",
            help="Monto promedio por licitación"
        )
    
    # ==============================================================================
    # ALERTAS Y RECOMENDACIONES
    # ==============================================================================
    
    if comprador_seleccionado != "Todos los Compradores":
        st.markdown("---")
        st.markdown("### ⚠️ Alertas y Recomendaciones")
        
        alertas = []
        
        if carga_ponderada_total > 50:
            alertas.append(f"🔴 **Alta Carga Laboral**: Carga ponderada de {carga_ponderada_total:.0f} puntos. Considerar redistribución.")
        
        if licitaciones_en_proceso > len(df_comprador) * 0.5:
            alertas.append(f"🟡 **Alto % En Proceso**: {pct_en_proceso:.1f}% de las licitaciones están en proceso activo.")
        
        if monto_en_proceso > monto_total * 0.7:
            alertas.append(f"🟠 **Alto Monto en Riesgo**: ${monto_en_proceso:,.0f} ({monto_en_proceso/monto_total*100:.1f}%) en proceso activo.")
        
        if len(df_comprador[df_comprador["EstadoClasificado"] == "Desierta"]) > len(df_comprador) * 0.2:
            alertas.append(f"⚠️ **Alta Tasa de Desiertas**: {len(df_comprador[df_comprador['EstadoClasificado']=='Desierta'])} licitaciones desiertas.")
        
        if alertas:
            for alerta in alertas:
                st.warning(alerta)
        else:
            st.success("✅ No se detectaron alertas críticas para este comprador.")
    