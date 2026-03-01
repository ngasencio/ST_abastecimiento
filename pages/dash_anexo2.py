"""
dashboard_nivel1.py
Dashboard Ejecutivo · Presupuesto Devengado — Nivel 1
Ejecutar con: streamlit run dashboard_nivel1.py
"""

import warnings
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard Ejecutivo · Nivel 1",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════
# PALETA & TEMA  — Refinado corporativo: crema + slate + acento índigo
# ══════════════════════════════════════════════════════════════════════
C = {
    "bg":       "#F7F6F2",
    "surface":  "#FFFFFF",
    "surface2": "#F0EEE8",
    "border":   "#E2DDD5",
    "text":     "#1A1A2E",
    "muted":    "#7A7A8C",
    "accent":   "#2D4B9C",
    "accent2":  "#4B6FD4",
    "accent3":  "#7B9FF5",
    "green":    "#1A7A4A",
    "amber":    "#B45309",
    "red":      "#C0392B",
    "teal":     "#0D7377",
}

PALETTE_CONCEPTOS = [
    "#2D4B9C","#0D7377","#B45309","#6B3FA0",
    "#1A7A4A","#C0392B","#5C6BC0","#00796B",
    "#E65100","#4527A0",
]

PLOT_BG   = C["surface"]
PAPER_BG  = C["surface"]
GRID_COL  = "#ECEAE3"
TEXT_COL  = C["muted"]
FONT      = "Georgia, serif"

# ══════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Lato:wght@300;400;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Lato', sans-serif;
    background-color: {C['bg']};
    color: {C['text']};
}}
.stApp {{ background: {C['bg']}; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {C['surface']};
    border-right: 1px solid {C['border']};
}}
[data-testid="stSidebar"] * {{ font-family: 'Lato', sans-serif; }}
[data-testid="stSidebar"] label {{ color: {C['muted']}; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }}

/* ── Header ── */
.exec-header {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    border-bottom: 2px solid {C['accent']};
    padding-bottom: 16px;
    margin-bottom: 28px;
}}
.exec-header-left h1 {{
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: {C['text']};
    margin: 0;
    line-height: 1.15;
}}
.exec-header-left p {{
    font-family: 'Lato', sans-serif;
    font-size: 0.82rem;
    color: {C['muted']};
    margin: 4px 0 0 0;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}
.exec-header-badge {{
    background: {C['accent']};
    color: white;
    font-family: 'Lato', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 6px 14px;
    border-radius: 3px;
}}

/* ── KPI Cards ── */
.kpi-wrap {{ display: flex; flex-direction: column; height: 100%; }}
.kpi-card {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-top: 3px solid {C['accent']};
    border-radius: 2px;
    padding: 18px 20px 14px;
    flex: 1;
    position: relative;
}}
.kpi-card.green  {{ border-top-color: {C['green']}; }}
.kpi-card.amber  {{ border-top-color: {C['amber']}; }}
.kpi-card.red    {{ border-top-color: {C['red']}; }}
.kpi-card.teal   {{ border-top-color: {C['teal']}; }}
.kpi-label {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {C['muted']};
    margin-bottom: 10px;
}}
.kpi-value {{
    font-family: 'Playfair Display', serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: {C['text']};
    line-height: 1;
    margin-bottom: 8px;
}}
.kpi-delta {{
    font-size: 0.75rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 2px;
    display: inline-block;
}}
.delta-pos {{ background: #E8F5EE; color: {C['green']}; }}
.delta-neg {{ background: #FDECEA; color: {C['red']}; }}
.delta-neu {{ background: {C['surface2']}; color: {C['muted']}; }}
.kpi-sub {{ font-size: 0.73rem; color: {C['muted']}; margin-top: 6px; }}

/* ── Sección ── */
.section-head {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 28px 0 12px;
    border-bottom: 1px solid {C['border']};
    padding-bottom: 8px;
}}
.section-head h3 {{
    font-family: 'Playfair Display', serif;
    font-size: 1rem;
    font-weight: 600;
    color: {C['text']};
    margin: 0;
}}
.section-head span {{
    font-size: 0.7rem;
    color: {C['muted']};
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-left: auto;
}}

/* ── Alerta ── */
.alert-box {{
    background: #EEF2FF;
    border-left: 3px solid {C['accent']};
    padding: 10px 14px;
    font-size: 0.8rem;
    color: {C['accent']};
    border-radius: 0 3px 3px 0;
    margin-bottom: 16px;
}}

/* ── Tabs ── */
[data-testid="stTabs"] button[role="tab"] {{
    font-family: 'Lato', sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: {C['muted']};
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {C['accent']};
    border-bottom-color: {C['accent']};
}}

/* ── Tabla ── */
[data-testid="stDataFrame"] {{ border: 1px solid {C['border']}; border-radius: 2px; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background:{C['bg']}; }}
::-webkit-scrollbar-thumb {{ background:{C['border']}; border-radius:3px; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# HELPERS PLOTLY
# ══════════════════════════════════════════════════════════════════════
def base_layout(height=360, showlegend=True, title=""):
    return dict(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family=FONT, color=TEXT_COL, size=11),
        height=height,
        title=dict(text=title, font=dict(family="Playfair Display, serif", size=13,
                   color=C["text"]), x=0.01, y=0.97) if title else {},
        showlegend=showlegend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=24, t=44, b=50),
        xaxis=dict(gridcolor=GRID_COL, linecolor=C["border"],
                   tickfont=dict(size=10), showgrid=False),
        yaxis=dict(gridcolor=GRID_COL, linecolor=C["border"],
                   tickfont=dict(size=10), showgrid=True),
        colorway=PALETTE_CONCEPTOS,
    )


def fmt(v):
    if abs(v) >= 1_000_000_000: return f"${v/1e9:.2f}MM"
    if abs(v) >= 1_000_000:     return f"${v/1e6:.1f}M"
    if abs(v) >= 1_000:         return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"


def delta_html(val, pct=None):
    sym = "▲" if val >= 0 else "▼"
    cls = "delta-pos" if val >= 0 else "delta-neg"
    txt = f"{sym} {pct:+.1f}%" if pct is not None else f"{sym} {fmt(val)}"
    return f'<span class="kpi-delta {cls}">{txt}</span>'


# ══════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════
MESES_ORDER = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
}
MESES_INV = {v: k for k, v in MESES_ORDER.items()}


@st.cache_data(show_spinner="Cargando datos…")
def load_data():
    try:
        from anexo1_loader import cargar_anexo1
        df_raw = cargar_anexo1()
    except Exception:
        # ── DATOS DEMO ──────────────────────────────────────────────
        rng = np.random.default_rng(7)
        conceptos_n1 = [
            "21 GASTOS EN PERSONAL",
            "22 BIENES Y SERVICIOS DE CONSUMO",
            "23 PRESTACIONES DE SEGURIDAD SOCIAL",
            "24 TRANSFERENCIAS CORRIENTES",
            "29 ADQUISICIÓN DE ACTIVOS NO FINANCIEROS",
        ]
        establecimientos = ["DSSO", "HBO", "HCUCH", "HNBSJ"]
        rows = []
        bases = {c: rng.integers(800_000_000, 4_000_000_000) for c in conceptos_n1}
        for est in establecimientos:
            factor_est = rng.uniform(0.7, 1.3)
            for year in [2024, 2025]:
                for mes, mnum in MESES_ORDER.items():
                    for c in conceptos_n1:
                        trend = 1 + 0.01 * (mnum + (year - 2024) * 12)
                        noise = rng.uniform(0.85, 1.15)
                        dev = int(bases[c] * factor_est * trend * noise / 12)
                        if rng.random() < 0.04:
                            dev = -abs(dev)
                        rows.append({
                            "Establecimiento": est,
                            "Fecha": f"{mes} {year}",
                            "Nivel": 1,
                            "Concepto Presupuestario": c,
                            "Ruta_Jerarquica": c,
                            "Ley de Presupuestos": int(bases[c] * factor_est / 12 * 1.05),
                            "Devengado": dev,
                        })
        df_raw = pd.DataFrame(rows)

    # ── Normalización ──────────────────────────────────────────────
    df_raw["Nivel"] = pd.to_numeric(df_raw["Nivel"], errors="coerce")
    df_raw["Devengado"] = pd.to_numeric(df_raw.get("Devengado", 0), errors="coerce").fillna(0)
    df_raw["Ley de Presupuestos"] = pd.to_numeric(df_raw.get("Ley de Presupuestos", 0), errors="coerce").fillna(0)

    df1 = df_raw[df_raw["Nivel"] == 1].copy()

    def parse_f(f):
        try:
            p = str(f).strip().lower().split()
            return MESES_ORDER.get(p[0], 0), int(p[1]) if len(p) > 1 else 0
        except Exception:
            return 0, 0

    df1[["mes_num","anio"]] = pd.DataFrame(df1["Fecha"].apply(parse_f).tolist(), index=df1.index)
    df1 = df1.sort_values(["anio","mes_num"]).reset_index(drop=True)
    return df1


df_full = load_data()

# ══════════════════════════════════════════════════════════════════════
# SIDEBAR FILTROS
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="padding:16px 0 20px">
        <p style="font-family:'Playfair Display',serif;font-size:1rem;font-weight:700;
                  color:{C['text']};margin:0 0 4px">Filtros</p>
        <p style="font-size:0.72rem;color:{C['muted']};margin:0;text-transform:uppercase;
                  letter-spacing:0.06em">Panel de control ejecutivo</p>
    </div>
    """, unsafe_allow_html=True)

    est_opts = sorted(df_full["Establecimiento"].dropna().unique())
    est_sel  = st.multiselect("Establecimiento", est_opts, default=est_opts)

    anio_opts = sorted(df_full["anio"].dropna().unique().astype(int))
    anio_sel  = st.multiselect("Año", anio_opts, default=anio_opts)

    fechas_df = (df_full.drop_duplicates(["Fecha","mes_num","anio"])
                  .sort_values(["anio","mes_num"]))
    fechas_list = fechas_df["Fecha"].tolist()

    col_d, col_h = st.columns(2)
    with col_d:
        f_desde = st.selectbox("Desde", fechas_list, index=0)
    with col_h:
        f_hasta = st.selectbox("Hasta", fechas_list, index=len(fechas_list)-1)

    conceptos_opts = sorted(df_full["Concepto Presupuestario"].dropna().unique())
    conc_sel = st.multiselect("Concepto (N1)", conceptos_opts, default=conceptos_opts)

    st.divider()
    st.markdown(f"<p style='font-size:0.7rem;color:{C['muted']}'>Solo Nivel 1 · Datos devengados</p>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# FILTRADO
# ══════════════════════════════════════════════════════════════════════
def en_rango(df, desde, hasta, lista_fechas):
    idx_d = lista_fechas.index(desde) if desde in lista_fechas else 0
    idx_h = lista_fechas.index(hasta) if hasta in lista_fechas else len(lista_fechas)-1
    validas = lista_fechas[idx_d:idx_h+1]
    return df[df["Fecha"].isin(validas)]

df = df_full[
    df_full["Establecimiento"].isin(est_sel) &
    df_full["anio"].isin(anio_sel) &
    df_full["Concepto Presupuestario"].isin(conc_sel)
].copy()
df = en_rango(df, f_desde, f_hasta, fechas_list)

fecha_orden = (df.drop_duplicates("Fecha").sort_values(["anio","mes_num"])["Fecha"].tolist())

# ══════════════════════════════════════════════════════════════════════
# MÉTRICAS GLOBALES
# ══════════════════════════════════════════════════════════════════════
dev_total   = df["Devengado"].sum()
pres_total  = df["Ley de Presupuestos"].sum()
pct_ejec    = dev_total / pres_total * 100 if pres_total else 0
disponible  = pres_total - dev_total
n_periodos  = df["Fecha"].nunique()
n_conceptos = df["Concepto Presupuestario"].nunique()

# Variación vs período anterior
periodos_ord = fecha_orden
if len(periodos_ord) >= 2:
    dev_ult  = df[df["Fecha"] == periodos_ord[-1]]["Devengado"].sum()
    dev_prev = df[df["Fecha"] == periodos_ord[-2]]["Devengado"].sum()
    var_mom  = (dev_ult - dev_prev) / dev_prev * 100 if dev_prev else 0
else:
    dev_ult = dev_total
    var_mom = 0.0

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="exec-header">
    <div class="exec-header-left">
        <h1>Ejecución Presupuestaria · Nivel 1</h1>
        <p>Control y seguimiento del gasto devengado por concepto principal · {n_periodos} período(s) · {len(est_sel)} establecimiento(s)</p>
    </div>
    <div class="exec-header-badge">Nivel 1 · Devengado</div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "Resumen Ejecutivo",
    "Evolución Temporal",
    "Proyecciones 2026",
    "Análisis por Concepto",
])


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — RESUMEN EJECUTIVO                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab1:
    # ── KPIs ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    kpis = [
        (c1, "accent", "Devengado Total",      fmt(dev_total),
         delta_html(var_mom, var_mom), f"Último período: {fmt(dev_ult)}"),
        (c2, "teal",   "Presupuesto Asignado", fmt(pres_total),
         "", f"{n_periodos} períodos acumulados"),
        (c3, "green" if pct_ejec <= 100 else "red",
              "% Ejecución",                   f"{pct_ejec:.1f}%",
         delta_html(pct_ejec - 100, pct_ejec - 100) if abs(pct_ejec-100)>0.1 else "",
         "Devengado / Presupuesto"),
        (c4, "amber",  "Disponible",           fmt(disponible),
         "", "Saldo por ejecutar"),
        (c5, "green" if var_mom >= 0 else "red",
              "Var. Mensual",                  f"{var_mom:+.1f}%",
         delta_html(var_mom, var_mom), f"vs período anterior"),
    ]
    for col, color, label, value, delta_str, sub in kpis:
        color_cls = "green" if color=="green" else ("red" if color=="red" else
                    ("amber" if color=="amber" else ("teal" if color=="teal" else "")))
        with col:
            st.markdown(f"""
            <div class="kpi-card {color_cls}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                {delta_str}
                <div class="kpi-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    # ── Gauge % ejecución global ───────────────────────────────────
    st.markdown("""<div class="section-head"><h3>Estado de Ejecución Global</h3>
    <span>Devengado vs Presupuesto</span></div>""", unsafe_allow_html=True)

    col_g, col_bar = st.columns([1, 2])
    with col_g:
        gauge_color = C["green"] if pct_ejec < 90 else (C["amber"] if pct_ejec <= 100 else C["red"])
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=pct_ejec,
            number=dict(suffix="%", font=dict(family="Playfair Display, serif",
                        size=32, color=C["text"])),
            delta=dict(reference=100, suffix="pp", increasing=dict(color=C["red"]),
                       decreasing=dict(color=C["green"])),
            gauge=dict(
                axis=dict(range=[0, 130], tickwidth=1, tickcolor=C["border"],
                          tickfont=dict(size=9), dtick=25),
                bar=dict(color=gauge_color, thickness=0.6),
                bgcolor=C["surface2"],
                borderwidth=0,
                steps=[
                    dict(range=[0, 80],   color="#E8F5EE"),
                    dict(range=[80, 100], color="#FEF3C7"),
                    dict(range=[100,130], color="#FDECEA"),
                ],
                threshold=dict(line=dict(color=C["accent"], width=2),
                               thickness=0.85, value=100),
            ),
        ))
        fig_gauge.update_layout(
            paper_bgcolor=PAPER_BG, font=dict(family=FONT),
            height=240, margin=dict(l=20, r=20, t=20, b=10),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_bar:
        # Barras horizontales por concepto
        df_conc = (df.groupby("Concepto Presupuestario")
                    .agg(Dev=("Devengado","sum"), Pres=("Ley de Presupuestos","sum"))
                    .reset_index())
        df_conc["pct"] = df_conc.apply(lambda r: r.Dev/r.Pres*100 if r.Pres else 0, axis=1)
        df_conc = df_conc.sort_values("pct", ascending=True)

        bar_cols = [C["green"] if p <= 90 else (C["amber"] if p <= 100 else C["red"])
                    for p in df_conc["pct"]]
        fig_hbar = go.Figure()
        fig_hbar.add_trace(go.Bar(
            y=df_conc["Concepto Presupuestario"],
            x=df_conc["pct"],
            orientation="h",
            marker_color=bar_cols,
            text=[f"{p:.1f}%" for p in df_conc["pct"]],
            textposition="outside",
            textfont=dict(size=10, family=FONT),
        ))
        fig_hbar.add_vline(x=100, line_color=C["accent"], line_dash="dot", line_width=1.5)
        lay_hbar = base_layout(240, False, "% Ejecución por Concepto")
        lay_hbar["xaxis"].update(dict(range=[0, max(135, df_conc["pct"].max()+10)],
                                      showgrid=True, ticksuffix="%"))
        lay_hbar["yaxis"].update(dict(tickfont=dict(size=9), showgrid=False))
        lay_hbar["bargap"] = 0.35
        fig_hbar.update_layout(**lay_hbar)
        st.plotly_chart(fig_hbar, use_container_width=True)

    # ── Tabla resumen ──────────────────────────────────────────────
    st.markdown("""<div class="section-head"><h3>Resumen por Concepto Presupuestario</h3>
    <span>Nivel 1 · Todos los períodos seleccionados</span></div>""", unsafe_allow_html=True)

    tbl = (df.groupby("Concepto Presupuestario")
             .agg(Devengado=("Devengado","sum"),
                  Presupuesto=("Ley de Presupuestos","sum"))
             .reset_index())
    tbl["Disponible"] = tbl["Presupuesto"] - tbl["Devengado"]
    tbl["% Ejecución"] = tbl.apply(lambda r: r.Devengado/r.Presupuesto*100 if r.Presupuesto else 0, axis=1)
    tbl["Desviación"] = tbl["Devengado"] - tbl["Presupuesto"]
    for c in ["Devengado","Presupuesto","Disponible","Desviación"]:
        tbl[c] = tbl[c].apply(fmt)
    tbl["% Ejecución"] = tbl["% Ejecución"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(tbl.rename(columns={"Concepto Presupuestario":"Concepto"}),
                 use_container_width=True, hide_index=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — EVOLUCIÓN TEMPORAL                                     ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab2:
    st.markdown("""<div class="alert-box">
    Series temporales del devengado por concepto de Nivel 1.
    La línea punteada representa la media móvil de 3 períodos.
    </div>""", unsafe_allow_html=True)

    # ── Serie total con media móvil ────────────────────────────────
    serie_tot = (df.groupby("Fecha")["Devengado"].sum()
                  .reindex(fecha_orden).reset_index())
    serie_tot["MA3"] = serie_tot["Devengado"].rolling(3, min_periods=1).mean()

    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        x=serie_tot["Fecha"], y=serie_tot["Devengado"],
        name="Devengado", fill="tozeroy", mode="lines+markers",
        line=dict(color=C["accent"], width=2.5),
        fillcolor=f"rgba(45,75,156,0.07)",
        marker=dict(size=5, color=C["accent"]),
    ))
    fig_area.add_trace(go.Scatter(
        x=serie_tot["Fecha"], y=serie_tot["MA3"],
        name="Media Móvil 3m", mode="lines",
        line=dict(color=C["amber"], width=1.5, dash="dot"),
    ))
    fig_area.update_layout(**base_layout(300, True, "Devengado Total — Evolución Mensual"))
    st.plotly_chart(fig_area, use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        # Líneas por concepto
        df_cp = (df.groupby(["Fecha","Concepto Presupuestario"])["Devengado"].sum()
                  .reset_index())
        fig_lines = px.line(
            df_cp, x="Fecha", y="Devengado",
            color="Concepto Presupuestario",
            markers=True,
            color_discrete_sequence=PALETTE_CONCEPTOS,
            category_orders={"Fecha": fecha_orden},
            labels={"Devengado":"Devengado ($)","Fecha":"","Concepto Presupuestario":""},
        )
        fig_lines.update_traces(line_width=1.8, marker_size=4)
        fig_lines.update_layout(**base_layout(360, True, "Por Concepto Presupuestario"))
        st.plotly_chart(fig_lines, use_container_width=True)

    with col_r:
        # Varianza período a período
        var_df = serie_tot.copy()
        var_df["Varianza"] = var_df["Devengado"].diff()
        var_df = var_df.dropna()
        v_colors = [C["green"] if v >= 0 else C["red"] for v in var_df["Varianza"]]

        fig_var = go.Figure()
        fig_var.add_trace(go.Bar(
            x=var_df["Fecha"], y=var_df["Varianza"],
            marker_color=v_colors,
            text=[fmt(v) for v in var_df["Varianza"]],
            textposition="outside",
            textfont=dict(size=8),
        ))
        fig_var.add_hline(y=0, line_color=C["muted"], line_width=1)
        fig_var.update_layout(**base_layout(360, False, "Variación Mensual del Devengado"))
        st.plotly_chart(fig_var, use_container_width=True)

    # ── Área apilada por concepto ─────────────────────────────────
    st.markdown("""<div class="section-head"><h3>Composición del Devengado por Concepto</h3>
    <span>Área apilada · participación relativa</span></div>""", unsafe_allow_html=True)

    fig_stack = px.area(
        df_cp, x="Fecha", y="Devengado",
        color="Concepto Presupuestario",
        color_discrete_sequence=PALETTE_CONCEPTOS,
        category_orders={"Fecha": fecha_orden},
        labels={"Devengado":"Devengado ($)","Fecha":"","Concepto Presupuestario":""},
    )
    fig_stack.update_layout(**base_layout(300, True, ""))
    st.plotly_chart(fig_stack, use_container_width=True)

    # ── Heatmap por establecimiento ───────────────────────────────
    st.markdown("""<div class="section-head"><h3>Mapa de Calor · Devengado por Establecimiento y Período</h3>
    </div>""", unsafe_allow_html=True)

    pivot = (df.groupby(["Establecimiento","Fecha"])["Devengado"].sum()
              .unstack("Fecha").reindex(columns=fecha_orden).fillna(0))
    if not pivot.empty:
        fig_heat = px.imshow(
            pivot, aspect="auto",
            color_continuous_scale=["#EEF2FF","#A5B4FC","#4B6FD4","#1E3A8A"],
            labels=dict(color="Devengado"),
        )
        lay_heat = base_layout(220, False)
        lay_heat["xaxis"].update(dict(tickfont=dict(size=9), showgrid=False))
        lay_heat["yaxis"].update(dict(tickfont=dict(size=10), showgrid=False))
        fig_heat.update_layout(**lay_heat)
        st.plotly_chart(fig_heat, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — PROYECCIONES 2026                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab3:
    st.markdown("""<div class="alert-box">
    Proyecciones calculadas mediante regresión lineal sobre la serie histórica mensual de cada concepto.
    La banda sombreada representa el intervalo de confianza al 95%. Los resultados son estimaciones estadísticas.
    </div>""", unsafe_allow_html=True)

    # ── Proyección global ──────────────────────────────────────────
    serie_g = (df.groupby(["Fecha","mes_num","anio"])["Devengado"].sum()
                .reset_index().sort_values(["anio","mes_num"]))

    if len(serie_g) < 2:
        st.info("Se necesitan al menos 2 períodos para calcular proyecciones.")
    else:
        serie_g["t"] = range(len(serie_g))
        coef  = np.polyfit(serie_g["t"], serie_g["Devengado"], 1)
        poli  = np.poly1d(coef)
        resid = serie_g["Devengado"] - poli(serie_g["t"])
        std_r = resid.std()

        t_max = serie_g["t"].max()
        t_f   = np.arange(t_max+1, t_max+13)
        m_ini = int(serie_g["mes_num"].iloc[-1])
        a_ini = int(serie_g["anio"].iloc[-1])
        fechas_f = []
        for i in range(1, 13):
            mm = (m_ini - 1 + i) % 12 + 1
            aa = a_ini + (m_ini + i - 1) // 12
            fechas_f.append(f"{MESES_INV.get(mm, mm)} {aa}")

        y_hat = poli(t_f)
        y_up  = y_hat + 1.96 * std_r
        y_dn  = np.maximum(y_hat - 1.96 * std_r, 0)

        fig_proj = go.Figure()
        # Histórico
        fig_proj.add_trace(go.Scatter(
            x=serie_g["Fecha"], y=serie_g["Devengado"],
            name="Histórico", mode="lines+markers",
            line=dict(color=C["accent"], width=2.5),
            marker=dict(size=5),
        ))
        # Tendencia sobre histórico
        fig_proj.add_trace(go.Scatter(
            x=serie_g["Fecha"], y=poli(serie_g["t"]),
            name="Tendencia", mode="lines",
            line=dict(color=C["amber"], width=1.5, dash="dot"),
        ))
        # IC
        fig_proj.add_trace(go.Scatter(
            x=list(fechas_f) + list(fechas_f[::-1]),
            y=list(y_up) + list(y_dn[::-1]),
            fill="toself", fillcolor="rgba(45,75,156,0.08)",
            line=dict(color="rgba(0,0,0,0)"),
            name="IC 95%",
        ))
        # Proyección
        fig_proj.add_trace(go.Scatter(
            x=fechas_f, y=y_hat,
            name="Proyección 2026", mode="lines+markers",
            line=dict(color=C["teal"], width=2, dash="dash"),
            marker=dict(size=7, symbol="diamond", color=C["teal"]),
        ))
        # Línea divisoria histórico/proyección
        if fecha_orden:
            fig_proj.add_vline(
                x=fecha_orden[-1], line_color=C["border"],
                line_dash="dot", line_width=1.5,
                annotation_text="Inicio proyección",
                annotation_font=dict(size=9, color=C["muted"]),
            )
        fig_proj.update_layout(**base_layout(380, True, "Proyección del Devengado Total — 2026"))
        st.plotly_chart(fig_proj, use_container_width=True)

        # ── Tabla de proyección ───────────────────────────────────
        col_t, col_c = st.columns([1.4, 1])
        with col_t:
            st.markdown("""<div class="section-head"><h3>Tabla de Proyecciones Mensuales</h3></div>""",
                        unsafe_allow_html=True)
            proj_tbl = pd.DataFrame({
                "Período":      fechas_f,
                "Proyectado":   [fmt(int(v)) for v in y_hat],
                "IC Inferior":  [fmt(int(v)) for v in y_dn],
                "IC Superior":  [fmt(int(v)) for v in y_up],
                "Tendencia":    ["↑" if coef[0] > 0 else "↓"] * 12,
            })
            st.dataframe(proj_tbl, use_container_width=True, hide_index=True)

        with col_c:
            # ── Proyección por concepto ───────────────────────────
            st.markdown("""<div class="section-head"><h3>Estimación Anual 2026 por Concepto</h3></div>""",
                        unsafe_allow_html=True)
            filas_conc = []
            for conc in df["Concepto Presupuestario"].unique():
                s = (df[df["Concepto Presupuestario"]==conc]
                      .groupby(["Fecha","mes_num","anio"])["Devengado"].sum()
                      .reset_index().sort_values(["anio","mes_num"]))
                if len(s) < 2:
                    continue
                s["t"] = range(len(s))
                c2 = np.polyfit(s["t"], s["Devengado"], 1)
                t_proj = np.arange(len(s), len(s)+12)
                total_proj = int(np.poly1d(c2)(t_proj).sum())
                filas_conc.append({
                    "Concepto": conc[:35] + ("…" if len(conc) > 35 else ""),
                    "Proyectado 2026": fmt(total_proj),
                    "Tendencia": "↑ Alza" if c2[0] > 0 else "↓ Baja",
                })
            if filas_conc:
                st.dataframe(pd.DataFrame(filas_conc), use_container_width=True, hide_index=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 4 — ANÁLISIS POR CONCEPTO                                  ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab4:
    conc_detalle = st.selectbox(
        "Seleccione un Concepto para análisis detallado",
        sorted(df["Concepto Presupuestario"].unique()),
        key="conc_det",
    )
    df_c = df[df["Concepto Presupuestario"] == conc_detalle]

    # KPIs del concepto
    dev_c  = df_c["Devengado"].sum()
    pres_c = df_c["Ley de Presupuestos"].sum()
    pct_c  = dev_c / pres_c * 100 if pres_c else 0
    disp_c = pres_c - dev_c

    k1, k2, k3, k4 = st.columns(4)
    kpis_c = [
        (k1, "",      "Devengado",   fmt(dev_c),  ""),
        (k2, "teal",  "Presupuesto", fmt(pres_c), ""),
        (k3, "amber", "Disponible",  fmt(disp_c), ""),
        (k4, "green" if pct_c <= 100 else "red",
              "% Ejecución",         f"{pct_c:.1f}%", delta_html(pct_c-100, pct_c-100)),
    ]
    for col, color, label, value, extra in kpis_c:
        with col:
            st.markdown(f"""
            <div class="kpi-card {color}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                {extra}
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_e, col_d = st.columns(2)

    with col_e:
        # Serie temporal del concepto
        s_c = (df_c.groupby("Fecha")["Devengado"].sum()
                .reindex(fecha_orden).reset_index())
        s_c["MA3"] = s_c["Devengado"].rolling(3, min_periods=1).mean()
        s_c_pres = (df_c.groupby("Fecha")["Ley de Presupuestos"].sum()
                     .reindex(fecha_orden).reset_index())

        fig_ec = go.Figure()
        fig_ec.add_trace(go.Scatter(
            x=s_c["Fecha"], y=s_c["Devengado"],
            name="Devengado", fill="tozeroy", mode="lines+markers",
            line=dict(color=C["accent"], width=2.5),
            fillcolor="rgba(45,75,156,0.07)",
            marker=dict(size=5),
        ))
        fig_ec.add_trace(go.Scatter(
            x=s_c_pres["Fecha"], y=s_c_pres["Ley de Presupuestos"],
            name="Presupuesto", mode="lines",
            line=dict(color=C["amber"], width=1.5, dash="dot"),
        ))
        fig_ec.add_trace(go.Scatter(
            x=s_c["Fecha"], y=s_c["MA3"],
            name="MA 3m", mode="lines",
            line=dict(color=C["teal"], width=1.2, dash="dash"),
        ))
        fig_ec.update_layout(**base_layout(320, True,
            f"Evolución · {conc_detalle[:40]}"))
        st.plotly_chart(fig_ec, use_container_width=True)

    with col_d:
        # Distribución por establecimiento
        dist_est = (df_c.groupby("Establecimiento")["Devengado"].sum()
                     .reset_index().sort_values("Devengado", ascending=False))
        fig_pie = go.Figure(go.Pie(
            labels=dist_est["Establecimiento"],
            values=dist_est["Devengado"],
            hole=0.5,
            marker=dict(colors=PALETTE_CONCEPTOS),
            textfont=dict(family=FONT, size=11),
            insidetextorientation="radial",
        ))
        lay_pie = base_layout(320, True, "Distribución por Establecimiento")
        lay_pie["legend"] = dict(orientation="v", x=1, y=0.5,
                                 font=dict(size=10), bgcolor="rgba(0,0,0,0)")
        fig_pie.update_layout(**lay_pie)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Comparativa de establecimientos en el tiempo ──────────────
    st.markdown(f"""<div class="section-head">
    <h3>Comparativa entre Establecimientos · {conc_detalle[:50]}</h3>
    </div>""", unsafe_allow_html=True)

    df_c_est = (df_c.groupby(["Fecha","Establecimiento"])["Devengado"].sum()
                 .reset_index())
    fig_comp = px.bar(
        df_c_est, x="Fecha", y="Devengado",
        color="Establecimiento",
        barmode="group",
        color_discrete_sequence=PALETTE_CONCEPTOS,
        category_orders={"Fecha": fecha_orden},
        labels={"Devengado":"Devengado ($)","Fecha":"","Establecimiento":""},
    )
    fig_comp.update_layout(**base_layout(300, True))
    st.plotly_chart(fig_comp, use_container_width=True)

    # ── Análisis de dispersión (box por mes) ──────────────────────
    st.markdown("""<div class="section-head">
    <h3>Dispersión del Devengado por Período</h3>
    <span>Distribución entre establecimientos</span></div>""", unsafe_allow_html=True)

    fig_box = px.box(
        df_c_est, x="Fecha", y="Devengado",
        color_discrete_sequence=[C["accent"]],
        category_orders={"Fecha": fecha_orden},
        labels={"Devengado":"Devengado ($)","Fecha":""},
        points="all",
    )
    fig_box.update_traces(marker_color=C["accent2"], marker_size=5,
                          line_color=C["accent"])
    fig_box.update_layout(**base_layout(280, False))
    st.plotly_chart(fig_box, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="border-top:1px solid {C['border']};margin-top:40px;padding-top:16px;
            display:flex;justify-content:space-between;align-items:center">
    <span style="font-size:0.72rem;color:{C['muted']};font-family:'Lato',sans-serif">
        Dashboard Ejecutivo · Nivel 1 · Presupuesto Devengado
    </span>
    <span style="font-size:0.72rem;color:{C['muted']};font-family:'Lato',sans-serif">
        Fuente: data_anexo1.py · anexo1_loader.py
    </span>
</div>
""", unsafe_allow_html=True)
