import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

import api.LI_data_loader as loader
from style.ui import cargar_css

cargar_css()


@st.cache_data(ttl=1800, show_spinner="Cargando licitaciones...")
def obtener_datos():
    df_res, df_det = loader.cargar_maestros()
    return df_res, df_det


def _to_dt(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce")
    return out


def _norm_user(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    s = s.replace({"nan": "", "None": ""})
    s = s.where(s.ne(""), "SIN ASIGNAR")
    return s.str.upper()


def _estado_flujo(row: pd.Series, now: pd.Timestamp):
    # Flujo: Creación -> Publicación -> Cierre -> Adjudicación -> Inicio Contrato -> Firma
    if pd.notna(row.get("FechaCierre")) and row["FechaCierre"] >= now:
        return row["FechaCierre"], "🔴 Por Cerrar", "FechaCierre"
    if pd.notna(row.get("FechaAdjudicacion")) and row["FechaAdjudicacion"] >= now:
        return row["FechaAdjudicacion"], "🟡 Por Adjudicar", "FechaAdjudicacion"
    if pd.notna(row.get("FechaInicioContrato")) and row["FechaInicioContrato"] >= now:
        return row["FechaInicioContrato"], "🟢 Por Iniciar", "FechaInicioContrato"
    if pd.notna(row.get("FechaEstimadaFirma")) and row["FechaEstimadaFirma"] >= now:
        return row["FechaEstimadaFirma"], "🔵 Por Firmar", "FechaEstimadaFirma"
    return pd.NaT, "⚪ Histórico/Vencido", ""


try:
    df_res_raw, df_det_raw = obtener_datos()
except Exception as e:
    st.error(f"Error cargando maestros de licitaciones: {e}")
    st.stop()

if df_res_raw.empty:
    st.error("No se encontraron datos de licitaciones. Ejecuta el actualizador primero.")
    st.stop()


df_res = df_res_raw.copy()

date_cols = [
    "FechaCreacion",
    "FechaPublicacion",
    "FechaCierre",
    "FechaAdjudicacion",
    "FechaInicioContrato",
    "FechaEstimadaFirma",
]

df_res = _to_dt(df_res, date_cols)

if "CodigoLicitacion" in df_res.columns:
    df_res["CodigoLicitacion"] = df_res["CodigoLicitacion"].astype(str).str.strip()

if "Estado" not in df_res.columns:
    df_res["Estado"] = "Desconocido"
else:
    df_res["Estado"] = df_res["Estado"].astype(str).str.strip()

if "Tipo" not in df_res.columns:
    df_res["Tipo"] = "Desconocido"
else:
    df_res["Tipo"] = df_res["Tipo"].astype(str).str.strip().replace({"": "Desconocido"})

if "C_Usuario" in df_res.columns:
    df_res["C_Usuario"] = _norm_user(df_res["C_Usuario"])
else:
    df_res["C_Usuario"] = "SIN ASIGNAR"

# Lead times (días)
if "FechaCreacion" in df_res.columns and "FechaPublicacion" in df_res.columns:
    df_res["LT_Creacion_Publicacion"] = (df_res["FechaPublicacion"] - df_res["FechaCreacion"]).dt.days
else:
    df_res["LT_Creacion_Publicacion"] = pd.NA

if "FechaPublicacion" in df_res.columns and "FechaCierre" in df_res.columns:
    df_res["LT_Publicacion_Cierre"] = (df_res["FechaCierre"] - df_res["FechaPublicacion"]).dt.days
else:
    df_res["LT_Publicacion_Cierre"] = pd.NA

if "FechaCierre" in df_res.columns and "FechaAdjudicacion" in df_res.columns:
    df_res["LT_Cierre_Adjudicacion"] = (df_res["FechaAdjudicacion"] - df_res["FechaCierre"]).dt.days
else:
    df_res["LT_Cierre_Adjudicacion"] = pd.NA

if "FechaAdjudicacion" in df_res.columns and "FechaInicioContrato" in df_res.columns:
    df_res["LT_Adjudicacion_Inicio"] = (df_res["FechaInicioContrato"] - df_res["FechaAdjudicacion"]).dt.days
else:
    df_res["LT_Adjudicacion_Inicio"] = pd.NA

if "FechaInicioContrato" in df_res.columns and "FechaEstimadaFirma" in df_res.columns:
    df_res["LT_Inicio_Firma"] = (df_res["FechaEstimadaFirma"] - df_res["FechaInicioContrato"]).dt.days
else:
    df_res["LT_Inicio_Firma"] = pd.NA

for c in [
    "LT_Creacion_Publicacion",
    "LT_Publicacion_Cierre",
    "LT_Cierre_Adjudicacion",
    "LT_Adjudicacion_Inicio",
    "LT_Inicio_Firma",
]:
    df_res[c] = pd.to_numeric(df_res[c], errors="coerce")

now = pd.Timestamp.now()

# Próximo hito
estado_tmp = df_res.apply(lambda r: pd.Series(_estado_flujo(r, now)), axis=1)
estado_tmp.columns = ["FechaClave", "EstadoFlujo", "TipoHito"]
df_res = pd.concat([df_res, estado_tmp], axis=1)

# =====================================================================
# HEADER
# =====================================================================
st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.2rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">📄 Tablero Ejecutivo: Licitaciones</div>
        <div style="font-size: 15px; opacity: 0.9;">Seguimiento por etapas y próximos hitos (semana actual y próxima)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# FILTROS
# =====================================================================
st.markdown("### 🔍 Filtros")
colf1, colf2, colf3, colf4 = st.columns(4)

with colf1:
    estado_sel = st.multiselect(
        "Estado",
        sorted(df_res["Estado"].dropna().unique()),
        placeholder="Todos",
    )
with colf2:
    flujo_sel = st.multiselect(
        "Etapa (EstadoFlujo)",
        sorted(df_res["EstadoFlujo"].dropna().unique()),
        placeholder="Todas",
    )
with colf3:
    tipo_sel = st.multiselect(
        "Tipo",
        sorted(df_res["Tipo"].dropna().unique()),
        placeholder="Todos",
    )
with colf4:
    usuario_sel = st.multiselect(
        "Comprador (C_Usuario)",
        sorted(df_res["C_Usuario"].dropna().unique()),
        placeholder="Todos",
    )

mask = pd.Series(True, index=df_res.index)
if estado_sel:
    mask &= df_res["Estado"].isin(estado_sel)
if flujo_sel:
    mask &= df_res["EstadoFlujo"].isin(flujo_sel)
if tipo_sel:
    mask &= df_res["Tipo"].isin(tipo_sel)
if usuario_sel:
    mask &= df_res["C_Usuario"].isin(usuario_sel)

df = df_res.loc[mask].copy()

# =====================================================================
# 1) KPIs EJECUTIVOS
# =====================================================================
st.markdown("## 1) Resumen Ejecutivo")

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric("Licitaciones (filtradas)", f"{len(df):,}")

with k2:
    por_cerrar = int((df["EstadoFlujo"] == "🔴 Por Cerrar").sum())
    st.metric("Cierres próximos", f"{por_cerrar}")

with k3:
    por_adj = int((df["EstadoFlujo"] == "🟡 Por Adjudicar").sum())
    st.metric("Por adjudicar", f"{por_adj}", delta_color="inverse")

with k4:
    avg_res = df["LT_Cierre_Adjudicacion"].dropna().mean()
    st.metric("LT Cierre→Adjud.", f"{avg_res:.1f} días" if pd.notna(avg_res) else "N/A")

with k5:
    avg_mkt = df["LT_Publicacion_Cierre"].dropna().mean()
    st.metric("LT Publicación→Cierre", f"{avg_mkt:.1f} días" if pd.notna(avg_mkt) else "N/A")

with k6:
    total_monto = float(df.get("MontoEstimado", pd.Series([0])).sum())
    st.metric("Monto estimado", f"${total_monto:,.0f}")

# =====================================================================
# 2) VISUALIZACIONES
# =====================================================================
st.markdown("## 2) Tendencias y Comparativas")

c1, c2 = st.columns([1, 1])

with c1:
    df_tipo = df.groupby("Tipo", as_index=False).agg(Cantidad=("CodigoLicitacion", "nunique")) if "CodigoLicitacion" in df.columns else df.groupby("Tipo", as_index=False).size().rename(columns={"size": "Cantidad"})
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
    df_usr = df.groupby("C_Usuario", as_index=False).agg(Cantidad=("CodigoLicitacion", "nunique")) if "CodigoLicitacion" in df.columns else df.groupby("C_Usuario", as_index=False).size().rename(columns={"size": "Cantidad"})
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

with c3:
    df_flujo = df.groupby("EstadoFlujo", as_index=False).size().rename(columns={"size": "Cantidad"})
    fig_flujo = px.pie(
        df_flujo,
        names="EstadoFlujo",
        values="Cantidad",
        title="Segmentación por Etapa (EstadoFlujo)",
        hole=0.4,
    )
    fig_flujo.update_layout(height=360)
    st.plotly_chart(fig_flujo, use_container_width=True)

with c4:
    if "FechaCreacion" in df.columns:
        df_ts = df.dropna(subset=["FechaCreacion"]).copy()
        df_ts = df_ts[df_ts["FechaCreacion"] >= (now - pd.Timedelta(days=180))]
        df_ts["Mes"] = df_ts["FechaCreacion"].dt.to_period("M").dt.to_timestamp()
        df_m = df_ts.groupby("Mes", as_index=False).agg(
            Cantidad=("CodigoLicitacion", "nunique") if "CodigoLicitacion" in df_ts.columns else ("Estado", "size"),
        )
        fig_m = px.line(
            df_m,
            x="Mes",
            y="Cantidad",
            markers=True,
            title="Tendencia: licitaciones creadas por mes (180 días)",
            labels={"Mes": "Mes", "Cantidad": "Licitaciones"},
        )
        fig_m.update_layout(height=360, xaxis_title=None)
        st.plotly_chart(fig_m, use_container_width=True)
    else:
        st.info("No se encontró FechaCreacion para tendencia.")

# =====================================================================
# 3) PRÓXIMOS EVENTOS (ESTA SEMANA Y PRÓXIMA)
# =====================================================================
st.markdown("## 3) Agenda de Próximos Hitos")

hoy = pd.Timestamp.now().normalize()
fin_esta_semana = hoy + pd.Timedelta(days=(6 - hoy.weekday()))
fin_prox_semana = fin_esta_semana + pd.Timedelta(days=7)

value_vars = [c for c in ["FechaCierre", "FechaAdjudicacion", "FechaInicioContrato", "FechaEstimadaFirma"] if c in df.columns]

if value_vars:
    df_eventos = df.melt(
        id_vars=[c for c in ["CodigoLicitacion", "Nombre", "Tipo", "Estado", "C_Usuario"] if c in df.columns],
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
if "FechaCreacion" in df.columns:
    df_recent = df[df["FechaCreacion"] >= cut].copy()
else:
    df_recent = df.copy()

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
# 5) LEAD TIMES DETALLADOS
# =====================================================================
st.markdown("## 5) Indicadores de Lead Time por Etapa")

lt_cols = [
    "LT_Creacion_Publicacion",
    "LT_Publicacion_Cierre",
    "LT_Cierre_Adjudicacion",
    "LT_Adjudicacion_Inicio",
    "LT_Inicio_Firma",
]
lt_cols = [c for c in lt_cols if c in df.columns]

if not lt_cols:
    st.info("No hay columnas suficientes para calcular lead times.")
else:
    df_lt = df[lt_cols].copy()
    resumen = df_lt.agg(["count", "mean", "median", "min", "max"]).T.reset_index().rename(columns={"index": "Etapa"})
    st.dataframe(
        resumen,
        use_container_width=True,
        hide_index=True,
        column_config={
            "mean": st.column_config.NumberColumn(format="%.1f"),
            "median": st.column_config.NumberColumn(format="%.1f"),
            "min": st.column_config.NumberColumn(format="%.0f"),
            "max": st.column_config.NumberColumn(format="%.0f"),
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
    if "Estado" in df.columns and "FechaAdjudicacion" in df.columns:
        cerr = df[df["Estado"].astype(str).str.contains("Cerrad", case=False, na=False)].copy()
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
    top_usr = df.groupby("C_Usuario", as_index=False).size().rename(columns={"size": "Licitaciones"}).sort_values("Licitaciones", ascending=False).head(10)
    st.dataframe(top_usr, use_container_width=True, hide_index=True)
