"""
dash_devengo.py
Dashboard de Control y Gestión Presupuestaria — Servicio de Salud Osorno
Ejecutar: streamlit run dash_devengo.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import io

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gestión Presupuestaria | Salud Osorno",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .stMetric label { font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
    div[data-testid="metric-container"] { background: white; border-radius: 12px; padding: 14px 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .alerta-critica { background:#fef2f2; border-left:4px solid #ef4444; padding:10px 14px; border-radius:6px; color:#991b1b; margin:6px 0; }
    .alerta-warning { background:#fffbeb; border-left:4px solid #f59e0b; padding:10px 14px; border-radius:6px; color:#92400e; margin:6px 0; }
    .header-box { background: linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%); padding:20px 28px; border-radius:12px; color:white; margin-bottom:20px; }
    h1,h2,h3 { color:#1e293b; }
</style>
""", unsafe_allow_html=True)

CSV_PATH    = "data/data_devengo/devengo_consolidado.csv"
XLSX_PRUEBA = "devengoprueba2.xlsx"
HEADER_ROW  = 5
ENTIDAD     = "1638 Servicio de Salud Osorno"

# ── Carga de datos ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos presupuestarios…")
def cargar_datos():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=",", dtype=str)
    elif os.path.exists(XLSX_PRUEBA):
        df = pd.read_excel(XLSX_PRUEBA, header=HEADER_ROW)
        # Limpiar filas de paginación (solo necesario con xlsx)
        mask = df.apply(lambda r: r.astype(str).str.contains(r"Página\s+\d+\s+de", na=False, regex=True).any(), axis=1)
        df = df[~mask].copy()
    else:
        st.error("No se encontró ningún archivo de datos. Ejecute primero `consolidar_devengo.py`.")
        st.stop()

    # Normalizar montos
    for c in ["Monto Vigente", "Monto Disponible", "Monto Consumido"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Fechas
    for c in ["Fecha Documento", "Fecha Conforme", "Fecha Ingreso / Fecha Recepción "]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Extraer código numérico de Unidad Ejecutora para legibilidad
    if "Código Unidad Ejecutora" in df.columns:
        df["Unidad Ejecutora"] = df["Código Unidad Ejecutora"].astype(str)

    # Bandera Mercado Público
    if "Id Chile Compra" in df.columns:
        df["es_mercado_publico"] = df["Id Chile Compra"].notna() & (df["Id Chile Compra"].astype(str).str.strip() != "")
    else:
        df["es_mercado_publico"] = False

    # % ejecución a nivel de fila
    df["pct_ejecucion"] = np.where(
        df["Monto Vigente"] > 0,
        df["Monto Consumido"] / df["Monto Vigente"] * 100,
        0,
    )

    # Mes de la fecha documento
    if "Fecha Documento" in df.columns:
        df["Mes"] = df["Fecha Documento"].dt.to_period("M").astype(str)

    return df

df_raw = cargar_datos()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-box">
  <h2 style="margin:0;color:white;">🏥 Dashboard de Gestión Presupuestaria</h2>
  <p style="margin:4px 0 0;opacity:.85;font-size:14px;">{ENTIDAD} — Disponibilidad de Devengos 2026</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Escudo_de_Chile.svg/200px-Escudo_de_Chile.svg.png", width=60)
st.sidebar.markdown("## ⚙️ Filtros")

# Unidad ejecutora
unidades = sorted(df_raw["Unidad Ejecutora"].dropna().unique().tolist())
sel_unidades = st.sidebar.multiselect("Unidad Ejecutora", unidades, placeholder="Todos (Servicio Osorno)")

# Tipo Documento
tipos_doc = sorted(df_raw["Tipo Documento"].dropna().unique().tolist()) if "Tipo Documento" in df_raw.columns else []
sel_tipos = st.sidebar.multiselect("Tipo Documento", tipos_doc, placeholder="Todos")

# Concepto Presupuestario
conceptos = sorted(df_raw["Concepto Presupuestario"].dropna().unique().tolist()) if "Concepto Presupuestario" in df_raw.columns else []
sel_conceptos = st.sidebar.multiselect("Concepto Presupuestario", conceptos, placeholder="Todos")

# Rango de fechas
if "Fecha Documento" in df_raw.columns:
    fecha_min = df_raw["Fecha Documento"].dropna().min().date()
    fecha_max = df_raw["Fecha Documento"].dropna().max().date()
    rango_fechas = st.sidebar.date_input("Rango Fecha Documento", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
else:
    rango_fechas = None

st.sidebar.markdown("---")
st.sidebar.markdown(f"*Registros totales: **{len(df_raw):,}***")

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_raw.copy()

if sel_unidades:
    df = df[df["Unidad Ejecutora"].isin(sel_unidades)]
if sel_tipos:
    df = df[df["Tipo Documento"].isin(sel_tipos)]
if sel_conceptos:
    df = df[df["Concepto Presupuestario"].isin(sel_conceptos)]
if rango_fechas and len(rango_fechas) == 2 and "Fecha Documento" in df.columns:
    df = df[
        (df["Fecha Documento"].dt.date >= rango_fechas[0]) &
        (df["Fecha Documento"].dt.date <= rango_fechas[1])
    ]

entidad_label = ", ".join(sel_unidades) if sel_unidades else ENTIDAD

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_clp(valor):
    if valor >= 1e9:
        return f"${valor/1e9:.2f} MM"
    elif valor >= 1e6:
        return f"${valor/1e6:.1f} M"
    return f"${valor:,.0f}"

def color_ejecucion(pct):
    if pct >= 100: return "#ef4444"
    if pct >= 90:  return "#f59e0b"
    return "#22c55e"

# ── KPIs ───────────────────────────────────────────────────────────────────────
v_vigente   = df["Monto Vigente"].sum()
v_consumido = df["Monto Consumido"].sum()
v_disponible = v_vigente - v_consumido
pct_global  = (v_consumido / v_vigente * 100) if v_vigente > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Presupuesto Vigente",   fmt_clp(v_vigente))
col2.metric("📤 Monto Consumido",        fmt_clp(v_consumido))
col3.metric("🏦 Saldo Disponible",       fmt_clp(v_disponible))
col4.metric("📊 % Ejecución Global",     f"{pct_global:.1f}%",
            delta=f"{'⚠️ Sobre límite' if pct_global>100 else ''}",
            delta_color="inverse" if pct_global > 90 else "off")

# Alertas globales
if pct_global > 100:
    st.markdown(f'<div class="alerta-critica">🚨 <b>ALERTA CRÍTICA:</b> La ejecución supera el 100% del presupuesto vigente ({pct_global:.1f}%). Revisar urgentemente.</div>', unsafe_allow_html=True)
elif pct_global > 90:
    st.markdown(f'<div class="alerta-warning">⚠️ <b>ADVERTENCIA:</b> Ejecución por encima del 90% ({pct_global:.1f}%). Fondos próximos a agotarse.</div>', unsafe_allow_html=True)

st.markdown(f"**Entidad:** {entidad_label} &nbsp;|&nbsp; **Registros filtrados:** {len(df):,}")
st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_ts, tab_ue, tab_cp, tab_td, tab_mp, tab_det = st.tabs([
    "📈 Serie de Tiempo",
    "🏢 Unidad Ejecutora",
    "📂 Concepto Presupuestario",
    "📄 Tipo Documento",
    "🛒 Mercado Público",
    "📋 Detalle",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — SERIE DE TIEMPO
# ════════════════════════════════════════════════════════════════════════════════
with tab_ts:
    st.subheader("Evolución Temporal del Gasto")

    if "Fecha Documento" not in df.columns or df["Fecha Documento"].isna().all():
        st.info("No hay columna de fecha disponible para análisis temporal.")
    else:
        df_ts = df.dropna(subset=["Fecha Documento"]).copy()
        df_ts["Año-Mes"] = df_ts["Fecha Documento"].dt.to_period("M")
        ts = df_ts.groupby("Año-Mes").agg(
            Consumido=("Monto Consumido","sum"),
            Vigente=("Monto Vigente","sum"),
        ).reset_index()
        ts["Año-Mes_str"] = ts["Año-Mes"].astype(str)
        ts = ts.sort_values("Año-Mes_str")
        ts["Consumido_Acum"] = ts["Consumido"].cumsum()

        # Proyección lineal simple
        if len(ts) >= 2:
            x = np.arange(len(ts))
            coef = np.polyfit(x, ts["Consumido"].values, 1)
            meses_extra = 3
            x_proj = np.arange(len(ts), len(ts) + meses_extra)
            y_proj = np.polyval(coef, x_proj)
            future_labels = [f"Proy. +{i+1}m" for i in range(meses_extra)]
        else:
            x_proj = y_proj = future_labels = []

        fig_ts = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ts.add_trace(go.Bar(name="Consumido Mensual", x=ts["Año-Mes_str"], y=ts["Consumido"],
                                marker_color="#2563eb", opacity=0.75,
                                hovertemplate="<b>%{x}</b><br>Consumido: $%{y:,.0f}<extra></extra>"), secondary_y=False)
        fig_ts.add_trace(go.Scatter(name="Acumulado", x=ts["Año-Mes_str"], y=ts["Consumido_Acum"],
                                    mode="lines+markers", line=dict(color="#f59e0b", width=3),
                                    hovertemplate="<b>%{x}</b><br>Acumulado: $%{y:,.0f}<extra></extra>"), secondary_y=True)
        if len(future_labels):
            fig_ts.add_trace(go.Scatter(name="Proyección", x=future_labels, y=y_proj,
                                        mode="lines+markers", line=dict(color="#ef4444", dash="dash", width=2),
                                        hovertemplate="<b>%{x}</b><br>Proyección: $%{y:,.0f}<extra></extra>"), secondary_y=False)
        fig_ts.update_layout(title="Consumo Mensual y Acumulado", height=420,
                             xaxis_title="Mes", legend=dict(orientation="h", y=1.1),
                             plot_bgcolor="white", paper_bgcolor="white")
        fig_ts.update_yaxes(title_text="Consumido Mensual (CLP)", secondary_y=False)
        fig_ts.update_yaxes(title_text="Consumido Acumulado (CLP)", secondary_y=True)
        st.plotly_chart(fig_ts, use_container_width=True)

        # Peak de gasto
        if not ts.empty:
            peak = ts.loc[ts["Consumido"].idxmax()]
            st.info(f"📌 **Peak de gasto:** {peak['Año-Mes_str']} — ${peak['Consumido']:,.0f}")

        # Top conceptos por mes (heatmap)
        if "Concepto Presupuestario" in df_ts.columns:
            hm = df_ts.groupby(["Año-Mes_str","Concepto Presupuestario"])["Monto Consumido"].sum().reset_index()
            top_c = hm.groupby("Concepto Presupuestario")["Monto Consumido"].sum().nlargest(8).index
            hm2 = hm[hm["Concepto Presupuestario"].isin(top_c)].pivot(index="Concepto Presupuestario", columns="Año-Mes_str", values="Monto Consumido").fillna(0)
            fig_hm = px.imshow(hm2, text_auto=False, color_continuous_scale="Blues",
                               title="Distribución Mensual por Concepto (Top 8)", aspect="auto",
                               labels={"color":"Consumido"})
            fig_hm.update_layout(height=350, plot_bgcolor="white")
            st.plotly_chart(fig_hm, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — UNIDAD EJECUTORA
# ════════════════════════════════════════════════════════════════════════════════
with tab_ue:
    st.subheader("Análisis por Unidad Ejecutora")

    df_ue = df.groupby("Unidad Ejecutora").agg(
        Vigente=("Monto Vigente","sum"),
        Consumido=("Monto Consumido","sum"),
        Registros=("Monto Consumido","count"),
    ).reset_index()
    df_ue["Disponible"] = df_ue["Vigente"] - df_ue["Consumido"]
    df_ue["% Ejecución"] = np.where(df_ue["Vigente"]>0, df_ue["Consumido"]/df_ue["Vigente"]*100, 0)
    df_ue = df_ue.sort_values("% Ejecución", ascending=False)

    # Alertas por unidad
    criticas = df_ue[df_ue["% Ejecución"] > 100]
    advertencias = df_ue[(df_ue["% Ejecución"] > 90) & (df_ue["% Ejecución"] <= 100)]
    if not criticas.empty:
        for _, r in criticas.iterrows():
            st.markdown(f'<div class="alerta-critica">🚨 <b>{r["Unidad Ejecutora"]}</b>: ejecución {r["% Ejecución"]:.1f}%</div>', unsafe_allow_html=True)
    if not advertencias.empty:
        for _, r in advertencias.iterrows():
            st.markdown(f'<div class="alerta-warning">⚠️ <b>{r["Unidad Ejecutora"]}</b>: ejecución {r["% Ejecución"]:.1f}%</div>', unsafe_allow_html=True)

    # Gráfico ranking
    colores = [color_ejecucion(p) for p in df_ue["% Ejecución"]]
    fig_ue = go.Figure(go.Bar(
        y=df_ue["Unidad Ejecutora"],
        x=df_ue["% Ejecución"],
        orientation="h",
        marker_color=colores,
        hovertemplate="<b>%{y}</b><br>Ejecución: %{x:.1f}%<br><extra></extra>",
        text=[f"{p:.1f}%" for p in df_ue["% Ejecución"]],
        textposition="outside",
    ))
    fig_ue.add_vline(x=90, line_dash="dash", line_color="#f59e0b", annotation_text="90%")
    fig_ue.add_vline(x=100, line_dash="dash", line_color="#ef4444", annotation_text="100%")
    fig_ue.update_layout(title="Ranking de Ejecución por Unidad Ejecutora", height=max(350, len(df_ue)*45),
                         xaxis_title="% Ejecución", plot_bgcolor="white", paper_bgcolor="white",
                         xaxis=dict(range=[0, max(df_ue["% Ejecución"].max()*1.15, 110)]))
    st.plotly_chart(fig_ue, use_container_width=True)

    # Gráfico barras apiladas monto
    fig_stk = go.Figure()
    fig_stk.add_trace(go.Bar(name="Consumido", y=df_ue["Unidad Ejecutora"], x=df_ue["Consumido"],
                              orientation="h", marker_color="#2563eb",
                              hovertemplate="<b>%{y}</b><br>Consumido: $%{x:,.0f}<extra></extra>"))
    fig_stk.add_trace(go.Bar(name="Disponible", y=df_ue["Unidad Ejecutora"], x=df_ue["Disponible"].clip(lower=0),
                              orientation="h", marker_color="#e2e8f0",
                              hovertemplate="<b>%{y}</b><br>Disponible: $%{x:,.0f}<extra></extra>"))
    fig_stk.update_layout(barmode="stack", title="Monto Vigente: Consumido vs Disponible",
                           height=max(350, len(df_ue)*45), plot_bgcolor="white", paper_bgcolor="white",
                           xaxis_title="Monto (CLP)", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_stk, use_container_width=True)

    # Tabla detallada
    st.markdown("#### Tabla Resumen por Unidad Ejecutora")
    df_ue_show = df_ue.copy()
    for c in ["Vigente","Consumido","Disponible"]:
        df_ue_show[c] = df_ue_show[c].apply(lambda v: f"${v:,.0f}")
    df_ue_show["% Ejecución"] = df_ue_show["% Ejecución"].apply(lambda v: f"{v:.1f}%")
    st.dataframe(df_ue_show.reset_index(drop=True), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — CONCEPTO PRESUPUESTARIO
# ════════════════════════════════════════════════════════════════════════════════
with tab_cp:
    st.subheader("Análisis por Concepto Presupuestario")

    if "Concepto Presupuestario" not in df.columns:
        st.info("Columna 'Concepto Presupuestario' no disponible.")
    else:
        df_cp = df.groupby("Concepto Presupuestario").agg(
            Vigente=("Monto Vigente","sum"),
            Consumido=("Monto Consumido","sum"),
            Registros=("Monto Consumido","count"),
        ).reset_index()
        df_cp["% Ejecución"] = np.where(df_cp["Vigente"]>0, df_cp["Consumido"]/df_cp["Vigente"]*100, 0)
        df_cp = df_cp.sort_values("Consumido", ascending=False)
        top15 = df_cp.head(15)

        # Treemap Vigente
        fig_tree = px.treemap(df_cp, path=["Concepto Presupuestario"], values="Vigente",
                               color="% Ejecución", color_continuous_scale=["#22c55e","#f59e0b","#ef4444"],
                               range_color=[0, 110],
                               title="Presupuesto Vigente por Concepto (tamaño=monto, color=% ejecución)",
                               hover_data={"Consumido":True, "% Ejecución":":.1f"})
        fig_tree.update_layout(height=450, margin=dict(t=50,l=10,r=10,b=10))
        st.plotly_chart(fig_tree, use_container_width=True)

        # Top 15 consumido
        fig_cp = go.Figure(go.Bar(
            y=top15["Concepto Presupuestario"],
            x=top15["Consumido"],
            orientation="h",
            marker_color="#2563eb",
            hovertemplate="<b>%{y}</b><br>Consumido: $%{x:,.0f}<extra></extra>",
        ))
        fig_cp.update_layout(title="Top 15 Conceptos por Monto Consumido", height=520,
                              xaxis_title="Monto Consumido (CLP)", plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_cp, use_container_width=True)

        # Donut vigente vs consumido total
        fig_pie = go.Figure(go.Pie(
            labels=["Consumido","Disponible"],
            values=[v_consumido, max(v_vigente - v_consumido, 0)],
            hole=.55,
            marker_colors=["#2563eb","#e2e8f0"],
            textinfo="label+percent",
        ))
        fig_pie.update_layout(title="Proporción Global Consumido vs Disponible", height=360)
        st.plotly_chart(fig_pie, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — TIPO DOCUMENTO
# ════════════════════════════════════════════════════════════════════════════════
with tab_td:
    st.subheader("Análisis por Tipo de Documento")

    if "Tipo Documento" not in df.columns:
        st.info("Columna 'Tipo Documento' no disponible.")
    else:
        df_td = df.groupby("Tipo Documento").agg(
            Vigente=("Monto Vigente","sum"),
            Consumido=("Monto Consumido","sum"),
            Volumen=("Monto Consumido","count"),
        ).reset_index()
        df_td["% Ejecución"] = np.where(df_td["Vigente"]>0, df_td["Consumido"]/df_td["Vigente"]*100, 0)
        df_td["Ticket Promedio"] = df_td["Consumido"] / df_td["Volumen"]

        c1, c2 = st.columns(2)
        with c1:
            fig_vol = px.bar(df_td, x="Tipo Documento", y="Volumen", color="Tipo Documento",
                              title="Volumen de Transacciones por Tipo",
                              labels={"Volumen":"N° Registros"},
                              color_discrete_sequence=px.colors.qualitative.Set2)
            fig_vol.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_vol, use_container_width=True)
        with c2:
            fig_mnt = px.bar(df_td, x="Tipo Documento", y="Consumido", color="Tipo Documento",
                              title="Monto Consumido por Tipo de Documento",
                              labels={"Consumido":"Monto (CLP)"},
                              color_discrete_sequence=px.colors.qualitative.Set2)
            fig_mnt.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_mnt, use_container_width=True)

        # Tabla
        df_td_show = df_td.copy()
        df_td_show["Consumido"] = df_td_show["Consumido"].apply(lambda v: f"${v:,.0f}")
        df_td_show["Ticket Promedio"] = df_td_show["Ticket Promedio"].apply(lambda v: f"${v:,.0f}")
        df_td_show["% Ejecución"] = df_td_show["% Ejecución"].apply(lambda v: f"{v:.1f}%")
        st.dataframe(df_td_show.reset_index(drop=True), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — MERCADO PÚBLICO
# ════════════════════════════════════════════════════════════════════════════════
with tab_mp:
    st.subheader("🛒 Análisis — Mercado Público (Chile Compra)")

    df_mp = df[df["es_mercado_publico"]].copy()
    df_no_mp = df[~df["es_mercado_publico"]].copy()

    tot_mp  = df_mp["Monto Consumido"].sum()
    tot_gen = df["Monto Consumido"].sum()
    pct_mp  = (tot_mp / tot_gen * 100) if tot_gen > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Órdenes de Compra",      f"{len(df_mp):,}")
    m2.metric("💵 Monto Mercado Público",   fmt_clp(tot_mp))
    m3.metric("📊 % del Gasto Total",       f"{pct_mp:.1f}%")

    # Donut MP vs otros
    fig_mp_pie = go.Figure(go.Pie(
        labels=["Mercado Público","Otros mecanismos"],
        values=[tot_mp, max(tot_gen - tot_mp, 0)],
        hole=.55,
        marker_colors=["#7c3aed","#e2e8f0"],
        textinfo="label+percent",
    ))
    fig_mp_pie.update_layout(title="Proporción Mercado Público vs Otros", height=340)
    st.plotly_chart(fig_mp_pie, use_container_width=True)

    if df_mp.empty:
        st.info("No hay registros de Mercado Público con los filtros actuales.")
    else:
        col_a, col_b = st.columns(2)

        # Por concepto
        with col_a:
            if "Concepto Presupuestario" in df_mp.columns:
                mp_cp = df_mp.groupby("Concepto Presupuestario")["Monto Consumido"].sum().reset_index().sort_values("Monto Consumido", ascending=False).head(10)
                fig_mpc = px.bar(mp_cp, y="Concepto Presupuestario", x="Monto Consumido", orientation="h",
                                  title="Top 10 Conceptos — Mercado Público",
                                  color_discrete_sequence=["#7c3aed"],
                                  labels={"Monto Consumido":"Monto (CLP)"})
                fig_mpc.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_mpc, use_container_width=True)

        # Por unidad ejecutora
        with col_b:
            mp_ue = df_mp.groupby("Unidad Ejecutora")["Monto Consumido"].sum().reset_index().sort_values("Monto Consumido", ascending=False)
            fig_mpu = px.bar(mp_ue, y="Unidad Ejecutora", x="Monto Consumido", orientation="h",
                              title="Gasto Mercado Público por Unidad Ejecutora",
                              color_discrete_sequence=["#7c3aed"],
                              labels={"Monto Consumido":"Monto (CLP)"})
            fig_mpu.update_layout(plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_mpu, use_container_width=True)

        # Evolución temporal
        if "Fecha Documento" in df_mp.columns:
            mp_ts = df_mp.dropna(subset=["Fecha Documento"]).copy()
            mp_ts["Año-Mes"] = mp_ts["Fecha Documento"].dt.to_period("M").astype(str)
            mp_ts_g = mp_ts.groupby("Año-Mes").agg(Consumido=("Monto Consumido","sum"), Ordenes=("Monto Consumido","count")).reset_index()
            fig_mpts = make_subplots(specs=[[{"secondary_y": True}]])
            fig_mpts.add_trace(go.Bar(name="Monto", x=mp_ts_g["Año-Mes"], y=mp_ts_g["Consumido"],
                                       marker_color="#7c3aed",
                                       hovertemplate="<b>%{x}</b><br>Monto: $%{y:,.0f}<extra></extra>"), secondary_y=False)
            fig_mpts.add_trace(go.Scatter(name="N° Órdenes", x=mp_ts_g["Año-Mes"], y=mp_ts_g["Ordenes"],
                                           mode="lines+markers", line=dict(color="#f59e0b", width=2),
                                           hovertemplate="<b>%{x}</b><br>Órdenes: %{y}<extra></extra>"), secondary_y=True)
            fig_mpts.update_layout(title="Evolución Temporal — Mercado Público", height=360,
                                    plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_mpts, use_container_width=True)

        # Tabla OC
        st.markdown("#### Detalle Órdenes de Compra")
        cols_show = [c for c in ["Unidad Ejecutora","Id Chile Compra","Titulo","Concepto Presupuestario",
                                   "Tipo Documento","Fecha Documento","Monto Consumido"] if c in df_mp.columns]
        st.dataframe(df_mp[cols_show].reset_index(drop=True), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 6 — DETALLE
# ════════════════════════════════════════════════════════════════════════════════
with tab_det:
    st.subheader("Tabla de Detalle Filtrable")
    st.markdown(f"**{len(df):,} registros** con los filtros seleccionados")

    # Búsqueda de texto libre
    texto_busqueda = st.text_input("🔍 Buscar en cualquier columna", placeholder="Ej: UNIVERSIDAD, factura, …")
    df_show = df.copy()
    if texto_busqueda:
        mask = df_show.apply(lambda col: col.astype(str).str.contains(texto_busqueda, case=False, na=False)).any(axis=1)
        df_show = df_show[mask]
        st.caption(f"Resultados de búsqueda: {len(df_show):,} registros")

    # Columnas a mostrar
    cols_default = [c for c in ["Unidad Ejecutora","Folio","Tipo Documento","Concepto Presupuestario",
                                  "Fecha Documento","Id Chile Compra","Monto Vigente","Monto Consumido",
                                  "Monto Disponible","pct_ejecucion"] if c in df_show.columns]
    st.dataframe(df_show[cols_default].rename(columns={"pct_ejecucion":"% Ejec."}).reset_index(drop=True),
                 use_container_width=True, hide_index=True)

    # Exportación
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        csv_data = df_show.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", data=csv_data, file_name="devengo_detalle.csv",
                           mime="text/csv", use_container_width=True)
    with col_ex2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_show.to_excel(writer, index=False, sheet_name="Devengo")
        st.download_button("⬇️ Exportar Excel", data=buf.getvalue(), file_name="devengo_detalle.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#94a3b8;font-size:12px;'>"
    "🏥 Servicio de Salud Osorno · Sistema de Gestión Presupuestaria · 2026"
    "</p>", unsafe_allow_html=True
)