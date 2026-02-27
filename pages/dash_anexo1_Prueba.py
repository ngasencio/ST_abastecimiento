import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
from datetime import datetime
from style.ui import cargar_css

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Control Presupuestario",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

cargar_css()

# ══════════════════════════════════════════════════════════════════════
# ESTILOS GLOBALES
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Reset y base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}



[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Syne', sans-serif;
    color: #7eb8f7;
}

/* ── Header ── */
.dashboard-header {
    background: linear-gradient(135deg, #0f1f40 0%, #162545 60%, #0d1a35 100%);
    border: 1px solid #1e3a6e;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.dashboard-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(100,180,255,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.dashboard-header h1 {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
}
.dashboard-header p {
    color: #7a9cc4;
    font-size: 0.9rem;
    margin: 0;
}

/* ── Tarjetas KPI ── */
.kpi-card {
    background: linear-gradient(145deg, #111827, #141d2e);
    border: 1px solid #1e2d47;
    border-radius: 14px;
    padding: 20px 22px;
    height: 100%;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: #3a5a8a; }
.kpi-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 0 0 14px 14px;
}
.kpi-card.blue::after   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.kpi-card.teal::after   { background: linear-gradient(90deg, #0d9488, #2dd4bf); }
.kpi-card.amber::after  { background: linear-gradient(90deg, #d97706, #fbbf24); }
.kpi-card.red::after    { background: linear-gradient(90deg, #dc2626, #f87171); }
.kpi-card.green::after  { background: linear-gradient(90deg, #16a34a, #4ade80); }
.kpi-label {
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #4a6080;
    margin-bottom: 8px;
}
.kpi-value {
    font-family: 'Syne', sans-serif;
    font-size: 1.65rem;
    font-weight: 700;
    color: #e8eaf0;
    line-height: 1;
    margin-bottom: 6px;
}
.kpi-sub {
    font-size: 0.78rem;
    color: #5a7a9a;
}
.kpi-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-ok  { background: rgba(22,163,74,0.15); color: #4ade80; }
.badge-warn{ background: rgba(217,119,6,0.15);  color: #fbbf24; }
.badge-crit{ background: rgba(220,38,38,0.15);  color: #f87171; }

/* ── Semáforo ── */
.semaforo-row {
    display: flex; align-items: center; gap: 12px;
    background: #111827;
    border: 1px solid #1e2d47;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.dot {
    width: 12px; height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 6px currentColor;
}
.dot-green  { background: #4ade80; color: #4ade80; }
.dot-yellow { background: #fbbf24; color: #fbbf24; }
.dot-red    { background: #f87171; color: #f87171; }
.sem-label  { font-size: 0.8rem; color: #94a3b8; flex: 1; }
.sem-value  { font-family: 'Syne', sans-serif; font-size: 0.85rem; color: #e2e8f0; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    gap: 4px;
    border-bottom: 1px solid #1e2d47;
    padding-bottom: 0;
}
[data-testid="stTabs"] button[role="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 500;
    color: #4a6080;
    padding: 8px 18px;
    border-radius: 8px 8px 0 0;
    border: 1px solid transparent;
    background: transparent;
    transition: all 0.15s;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #7eb8f7;
    background: #0f1f40;
    border-color: #1e3a6e;
    border-bottom-color: #0b0f1a;
}

/* ── Sección título ── */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #c8d8f0;
    margin: 0 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2d47;
}

/* ── Alerta info ── */
.info-box {
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.83rem;
    color: #7eb8f7;
    margin-bottom: 16px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0b0f1a; }
::-webkit-scrollbar-thumb { background: #1e3a6e; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════
# CONSTANTES VISUALES
# ══════════════════════════════════════════════════════════════════════
PLOT_BG      = "#0b0f1a"
PAPER_BG     = "#0b0f1a"
GRID_COLOR   = "#1a2540"
TEXT_COLOR   = "#8899b4"
FONT_FAMILY  = "DM Sans, sans-serif"

PALETTE = [
    "#3b82f6", "#0d9488", "#f59e0b", "#8b5cf6",
    "#ec4899", "#10b981", "#f97316", "#6366f1",
    "#14b8a6", "#a855f7",
]

def plotly_layout(title="", height=380, showlegend=True):
    """Layout base para gráficos Plotly con tema oscuro."""
    return dict(
        title=dict(text=title, font=dict(family="Syne, sans-serif", size=14, color="#c8d8f0"), x=0.01),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        height=height,
        showlegend=showlegend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=50, r=20, t=50, b=50),
        xaxis=dict(gridcolor=GRID_COLOR, linecolor="#1e2d47", tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor="#1e2d47", tickfont=dict(size=10)),
        colorway=PALETTE,
    )

def plotly_layout_subplot(title="", height=380, showlegend=True):
    """Layout para subplots sin conflicto de ejes."""
    layout = plotly_layout(title, height, showlegend)
    # Remover xaxis/yaxis para evitar conflicto en subplots
    layout.pop('xaxis', None)
    layout.pop('yaxis', None)
    return layout

# ══════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════
MESES_ORDER = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
}

def fmt_m(v):
    """Formatea en millones con 1 decimal."""
    if abs(v) >= 1_000_000_000:
        return f"${v/1e9:.2f}MM"
    if abs(v) >= 1_000_000:
        return f"${v/1e6:.1f}M"
    if abs(v) >= 1_000:
        return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"

def badge(pct):
    """Genera badge de estado según porcentaje."""
    if pct < 80:
        return '<span class="kpi-badge badge-warn">▼ Bajo</span>'
    if pct <= 100:
        return '<span class="kpi-badge badge-ok">✓ Normal</span>'
    return '<span class="kpi-badge badge-crit">▲ Excedido</span>'

# ══════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Cargando datos presupuestarios…")
def cargar_datos():
    try:
        from anexo1_loader import cargar_anexo1
        df = cargar_anexo1()
    except Exception:
        # ── DATOS DEMO si no existe el loader ──────────────────────
        rng = np.random.default_rng(42)
        conceptos = {
            1: ["21 GASTOS EN PERSONAL", "22 BIENES Y SERVICIOS", "29 ADQUISICION DE ACTIVOS"],
            2: ["2101 Personal de Planta", "2102 Personal a Contrata", "2201 Alimentos", "2202 Textiles"],
            3: ["2101001 Sueldos y Sobresueldos", "2101002 Horas Extra", "2201001 Víveres"],
            4: ["2101001001 Sueldo Base", "2101001002 Asig. Antigüedad"],
            5: ["210100100101 Sueldo Planta L15076", "210100100102 Sueldo Planta L18834"],
        }
        establecimientos = ["DSSO", "HBO", "HCUCH", "HNBSJ"]
        rows = []
        for est in establecimientos:
            presupuesto_base = rng.integers(5_000_000, 20_000_000)
            for year in [2024, 2025]:
                for mes, mnum in MESES_ORDER.items():
                    for nivel, conceptos_n in conceptos.items():
                        for concepto in conceptos_n:
                            dev = int(presupuesto_base * rng.uniform(0.06, 0.12))
                            if rng.random() < 0.05:
                                dev = -abs(dev)
                            rows.append({
                                "Establecimiento": est,
                                "Fecha": f"{mes} {year}",
                                "Nivel": nivel,
                                "Concepto Presupuestario": concepto,
                                "Ruta_Jerarquica": concepto,
                                "Ley de Presupuestos": int(presupuesto_base * 0.1),
                                "Devengado": dev,
                                "Compromiso": int(dev * rng.uniform(0.95, 1.05)),
                                "Saldo por Aplicar": int(presupuesto_base * rng.uniform(0.01, 0.08)),
                            })
        df = pd.DataFrame(rows)

    # ── Normalización ──────────────────────────────────────────────
    df["Nivel"] = pd.to_numeric(df["Nivel"], errors="coerce").astype("Int64")
    df["Devengado"] = pd.to_numeric(df.get("Devengado", 0), errors="coerce").fillna(0)
    df["Ley de Presupuestos"] = pd.to_numeric(df.get("Ley de Presupuestos", 0), errors="coerce").fillna(0)
    df["Compromiso"] = pd.to_numeric(df.get("Compromiso", 0), errors="coerce").fillna(0)

    # Extraer año y número de mes para ordenar
    def parse_fecha(f):
        try:
            parts = str(f).strip().lower().split()
            return MESES_ORDER.get(parts[0], 0), int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            return 0, 0

    df[["mes_num", "anio"]] = pd.DataFrame(df["Fecha"].apply(parse_fecha).tolist(), index=df.index)
    df = df.sort_values(["anio", "mes_num"]).reset_index(drop=True)
    return df

df_full = cargar_datos()

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #138AEC, #3E9FEF);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
           🧮 Anexo N°1
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Visión ejecutiva del desempeño de los compradores en eficiencia,
            cumplimiento y volumen de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ══════════════════════════════════════════════════════════════════════
# SIDEBAR — FILTROS
# ══════════════════════════════════════════════════════════════════════
st.markdown("<h2 style='font-family:Syne;font-size:1.1rem;margin-bottom:20px'>⚙ Filtros</h2>", unsafe_allow_html=True)

# Establecimientos
est_opts = sorted(df_full["Establecimiento"].dropna().unique())
est_sel = st.multiselect("Establecimiento", est_opts, default=est_opts, key="f_est")

# Niveles
niv_opts = sorted([n for n in df_full["Nivel"].dropna().unique()])
niv_sel = st.multiselect("Nivel jerárquico", niv_opts, default=niv_opts, key="f_niv")

# Fechas disponibles
fechas_sorted = df_full.drop_duplicates(["Fecha","mes_num","anio"]).sort_values(["anio","mes_num"])["Fecha"].tolist()
if fechas_sorted:
    idx_desde = st.selectbox("Desde", fechas_sorted, index=0, key="f_desde")
    idx_hasta = st.selectbox("Hasta", fechas_sorted, index=len(fechas_sorted)-1, key="f_hasta")
else:
    idx_desde = idx_hasta = None

# Conceptos (filtrado por los ya seleccionados)
df_temp = df_full[df_full["Establecimiento"].isin(est_sel) & df_full["Nivel"].isin(niv_sel)]
concepto_opts = sorted(df_temp["Concepto Presupuestario"].dropna().unique())
concepto_sel = st.multiselect("Concepto Presupuestario", concepto_opts,
                                default=concepto_opts[:min(8, len(concepto_opts))], key="f_conc")

st.divider()
st.markdown("<p style='font-size:0.72rem;color:#2a3a55'>Los filtros afectan todas las visualizaciones simultáneamente.</p>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# FILTRADO GLOBAL
# ══════════════════════════════════════════════════════════════════════
def fecha_en_rango(df, desde, hasta):
    if not desde or not hasta:
        return df
    orden = df.drop_duplicates("Fecha").set_index("Fecha")[["mes_num","anio"]]
    fechas_validas = []
    for f, row in orden.iterrows():
        f_desde = orden.loc[desde] if desde in orden.index else None
        f_hasta = orden.loc[hasta] if hasta in orden.index else None
        if f_desde is None or f_hasta is None:
            fechas_validas.append(f)
            continue
        clave   = (row["anio"], row["mes_num"])
        c_desde = (f_desde["anio"], f_desde["mes_num"])
        c_hasta = (f_hasta["anio"], f_hasta["mes_num"])
        if c_desde <= clave <= c_hasta:
            fechas_validas.append(f)
    return df[df["Fecha"].isin(fechas_validas)]

df = df_full[
    df_full["Establecimiento"].isin(est_sel) &
    df_full["Nivel"].isin(niv_sel) &
    df_full["Concepto Presupuestario"].isin(concepto_sel)
].copy()
df = fecha_en_rango(df, idx_desde, idx_hasta)

# ══════════════════════════════════════════════════════════════════════
# MÉTRICAS BASE
# ══════════════════════════════════════════════════════════════════════
devengado_total   = df["Devengado"].sum()
presupuesto_total = df["Ley de Presupuestos"].sum()
disponible        = presupuesto_total - devengado_total
pct_ejecucion     = (devengado_total / presupuesto_total * 100) if presupuesto_total else 0
desv_abs          = devengado_total - presupuesto_total
desv_pct          = (desv_abs / presupuesto_total * 100) if presupuesto_total else 0

st.markdown(f"""
<div class="dashboard-header">
    <h1>📊 Control Presupuestario</h1>
    <p>Sistema de análisis y seguimiento de ejecución presupuestaria · {len(est_sel)} establecimiento(s) · {df["Fecha"].nunique()} período(s)</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "📋  Resumen Ejecutivo",
    "📈  Análisis Temporal",
    "🔮  Análisis Predictivo",
    "🏥  Comparativa Establecimientos",
])

# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — RESUMEN EJECUTIVO                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab1:
    # ── KPI Cards ──────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "blue",  "DEVENGADO TOTAL",         fmt_m(devengado_total),   f"{df['Fecha'].nunique()} períodos", badge(pct_ejecucion)),
        (c2, "teal",  "PRESUPUESTO",             fmt_m(presupuesto_total), "Ley de Presupuestos", ""),
        (c3, "amber", "DISPONIBLE",              fmt_m(disponible),        "Saldo sin ejecutar", ""),
        (c4, "green" if pct_ejecucion <= 100 else "red",
              "% EJECUCIÓN",                     f"{pct_ejecucion:.1f}%",  "Devengado / Presupuesto", badge(pct_ejecucion)),
        (c5, "red" if desv_abs > 0 else "green",
              "DESVIACIÓN",                      fmt_m(desv_abs),          f"{desv_pct:+.1f}% vs presupuesto", ""),
    ]
    for col, color, label, value, sub, extra in cards:
        with col:
            st.markdown(f"""
            <div class="kpi-card {color}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub} {extra}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Semáforos por Establecimiento ─────────────────────────────
    col_sem, col_bar = st.columns([1, 2])

    with col_sem:
        st.markdown('<p class="section-title">🚦 Estado por Establecimiento</p>', unsafe_allow_html=True)
        if not df.empty:
            sem_df = df.groupby("Establecimiento").agg(
                Dev=("Devengado", "sum"),
                Pres=("Ley de Presupuestos", "sum")
            ).reset_index()
            sem_df["pct"] = sem_df.apply(lambda r: r.Dev/r.Pres*100 if r.Pres else 0, axis=1)
            sem_df = sem_df.sort_values("pct", ascending=False)
            for _, row in sem_df.iterrows():
                p = row["pct"]
                dot_cls = "dot-green" if p <= 90 else ("dot-yellow" if p <= 100 else "dot-red")
                estado   = "Normal" if p <= 90 else ("Próximo al límite" if p <= 100 else "⚠ Excedido")
                st.markdown(f"""
                <div class="semaforo-row">
                    <div class="dot {dot_cls}"></div>
                    <div class="sem-label">{row['Establecimiento']}</div>
                    <div class="sem-value">{p:.1f}% · {estado}</div>
                </div>""", unsafe_allow_html=True)

    with col_bar:
        st.markdown('<p class="section-title">Ejecución vs Presupuesto por Establecimiento</p>', unsafe_allow_html=True)
        if not df.empty:
            grp = df.groupby("Establecimiento").agg(
                Devengado=("Devengado", "sum"),
                Presupuesto=("Ley de Presupuestos", "sum")
            ).reset_index().sort_values("Devengado", ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Presupuesto", y=grp["Establecimiento"], x=grp["Presupuesto"],
                orientation="h", marker_color="rgba(59,130,246,0.25)",
                marker_line=dict(color="#3b82f6", width=1)
            ))
            fig.add_trace(go.Bar(
                name="Devengado", y=grp["Establecimiento"], x=grp["Devengado"],
                orientation="h", marker_color="#3b82f6"
            ))
            fig.update_layout(
                **plotly_layout("", 300, True),
                barmode="overlay",
                bargap=0.3,
            )
            fig.update_xaxes(tickformat=",.0f", gridcolor=GRID_COLOR)
            st.plotly_chart(fig, use_container_width=True)

    # ── Top Conceptos ─────────────────────────────────────────────
    st.markdown('<p class="section-title">Top 10 Conceptos por Devengado</p>', unsafe_allow_html=True)
    if not df.empty:
        max_nivel = df["Nivel"].max()
        df_det = df[df["Nivel"] == max_nivel] if pd.notna(max_nivel) else df
        top10 = (df_det.groupby("Concepto Presupuestario")["Devengado"]
                 .sum().reset_index()
                 .sort_values("Devengado", ascending=False).head(10))

        fig = px.bar(
            top10, x="Devengado", y="Concepto Presupuestario",
            orientation="h", color="Devengado",
            color_continuous_scale=["#1e3a6e", "#3b82f6", "#7eb8f7"],
            labels={"Devengado": "Devengado ($)", "Concepto Presupuestario": ""},
        )
        fig.update_layout(**plotly_layout("", 380, False))
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — ANÁLISIS TEMPORAL                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab2:
    st.markdown('<div class="info-box">Series temporales del devengado por período. Utilice los filtros laterales para enfocar el análisis por concepto, nivel o establecimiento.</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("Sin datos para los filtros seleccionados.")
    else:
        fecha_orden = (df.drop_duplicates("Fecha")
                        .sort_values(["anio","mes_num"])["Fecha"].tolist())

        # ── Serie temporal total ──────────────────────────────────
        serie_total = (df.groupby("Fecha")["Devengado"].sum()
                        .reindex(fecha_orden).reset_index())

        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=serie_total["Fecha"], y=serie_total["Devengado"],
            fill="tozeroy", mode="lines+markers",
            line=dict(color="#3b82f6", width=2),
            fillcolor="rgba(59,130,246,0.12)",
            marker=dict(size=5, color="#7eb8f7"),
            name="Devengado Total",
        ))
        fig_area.update_layout(**plotly_layout("Evolución Total del Devengado", 280))
        st.plotly_chart(fig_area, use_container_width=True)

        col_l, col_r = st.columns(2)

        with col_l:
            # Serie por Establecimiento
            grp_est = (df.groupby(["Fecha","Establecimiento"])["Devengado"].sum()
                        .reset_index())
            fig_est = px.line(
                grp_est, x="Fecha", y="Devengado",
                color="Establecimiento", markers=True,
                color_discrete_sequence=PALETTE,
                category_orders={"Fecha": fecha_orden},
                labels={"Devengado": "Devengado ($)", "Fecha": ""},
            )
            fig_est.update_layout(**plotly_layout("Por Establecimiento", 340))
            st.plotly_chart(fig_est, use_container_width=True)

        with col_r:
            # Serie por Nivel
            grp_niv = (df.groupby(["Fecha","Nivel"])["Devengado"].sum()
                        .reset_index().astype({"Nivel": str}))
            fig_niv = px.line(
                grp_niv, x="Fecha", y="Devengado",
                color="Nivel", markers=True,
                color_discrete_sequence=PALETTE,
                category_orders={"Fecha": fecha_orden},
                labels={"Devengado": "Devengado ($)", "Fecha": "", "Nivel": "Nivel"},
            )
            fig_niv.update_layout(**plotly_layout("Por Nivel Jerárquico", 340))
            st.plotly_chart(fig_niv, use_container_width=True)

        # ── Gráfico de varianza ───────────────────────────────────
        st.markdown('<p class="section-title">Varianza Presupuestaria por Período</p>', unsafe_allow_html=True)
        var_df = (df.groupby("Fecha")
                    .agg(Dev=("Devengado","sum"), Pres=("Ley de Presupuestos","sum"))
                    .reindex(fecha_orden).reset_index())
        var_df["Varianza"] = var_df["Dev"] - var_df["Pres"]

        colors = ["#f87171" if v > 0 else "#4ade80" for v in var_df["Varianza"]]
        fig_var = go.Figure()
        fig_var.add_trace(go.Bar(
            x=var_df["Fecha"], y=var_df["Varianza"],
            marker_color=colors,
            name="Varianza",
        ))
        fig_var.add_hline(y=0, line_color="#334155", line_width=1)
        fig_var.update_layout(**plotly_layout("Varianza (Devengado − Presupuesto)", 280))
        st.plotly_chart(fig_var, use_container_width=True)

        # ── Heatmap ───────────────────────────────────────────────
        st.markdown('<p class="section-title">Mapa de Calor: Devengado por Establecimiento × Período</p>', unsafe_allow_html=True)
        pivot = (df.groupby(["Establecimiento","Fecha"])["Devengado"].sum()
                  .unstack("Fecha").reindex(columns=fecha_orden).fillna(0))
        if not pivot.empty:
            fig_heat = px.imshow(
                pivot, aspect="auto",
                color_continuous_scale=["#0b1a35","#1e3a6e","#3b82f6","#7eb8f7"],
                labels=dict(color="Devengado"),
            )
            fig_heat.update_layout(**plotly_layout("", 300, False))
            st.plotly_chart(fig_heat, use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — ANÁLISIS PREDICTIVO                                    ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab3:
    st.markdown('<div class="info-box">Proyecciones 2026 calculadas mediante regresión lineal sobre el historial mensual de devengado. Las bandas sombreadas representan el intervalo de confianza al 95%.</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("Sin datos para proyección.")
    else:
        fecha_orden = (df.drop_duplicates("Fecha")
                        .sort_values(["anio","mes_num"])["Fecha"].tolist())

        # Serie total mensual para regresión global
        serie = (df.groupby(["Fecha","mes_num","anio"])["Devengado"].sum()
                  .reset_index()
                  .sort_values(["anio","mes_num"]))
        serie["t"] = range(len(serie))

        if len(serie) >= 2:
            coeffs  = np.polyfit(serie["t"], serie["Devengado"], 1)
            poly    = np.poly1d(coeffs)
            residuals = serie["Devengado"] - poly(serie["t"])
            std_res = residuals.std()

            # Proyección 12 meses
            t_max    = serie["t"].max()
            t_fut    = np.arange(t_max + 1, t_max + 13)
            meses_fut = [(((serie["mes_num"].iloc[-1] - 1 + i) % 12) + 1) for i in range(1, 13)]
            anios_fut = [serie["anio"].iloc[-1] + (serie["mes_num"].iloc[-1] + i - 1) // 12
                         for i in range(1, 13)]
            nombres_mes = {v: k for k, v in MESES_ORDER.items()}
            fechas_fut  = [f"{nombres_mes.get(m, m)} {a}" for m, a in zip(meses_fut, anios_fut)]

            y_pred = poly(t_fut)
            y_upper= y_pred + 1.96 * std_res
            y_lower= y_pred - 1.96 * std_res

            fig_pred = go.Figure()
            # Histórico
            fig_pred.add_trace(go.Scatter(
                x=serie["Fecha"], y=serie["Devengado"],
                mode="lines+markers", name="Histórico",
                line=dict(color="#3b82f6", width=2),
                marker=dict(size=5),
            ))
            # Línea de regresión sobre histórico
            fig_pred.add_trace(go.Scatter(
                x=serie["Fecha"], y=poly(serie["t"]),
                mode="lines", name="Tendencia",
                line=dict(color="#f59e0b", width=1.5, dash="dot"),
            ))
            # Banda confianza
            fig_pred.add_trace(go.Scatter(
                x=fechas_fut + fechas_fut[::-1],
                y=list(y_upper) + list(y_lower[::-1]),
                fill="toself", fillcolor="rgba(139,92,246,0.1)",
                line=dict(color="rgba(0,0,0,0)"),
                name="IC 95%", showlegend=True,
            ))
            # Proyección
            fig_pred.add_trace(go.Scatter(
                x=fechas_fut, y=y_pred,
                mode="lines+markers", name="Proyección 2026",
                line=dict(color="#8b5cf6", width=2, dash="dash"),
                marker=dict(size=6, symbol="diamond"),
            ))
            fig_pred.update_layout(**plotly_layout("Proyección de Devengado 2026", 400))
            st.plotly_chart(fig_pred, use_container_width=True)

            # ── Tabla resumen proyección ──────────────────────────
            proj_df = pd.DataFrame({
                "Período": fechas_fut,
                "Proyectado": y_pred.astype(int),
                "IC Inferior": y_lower.astype(int),
                "IC Superior": y_upper.astype(int),
            })
            proj_df["Proyectado"] = proj_df["Proyectado"].apply(fmt_m)
            proj_df["IC Inferior"] = proj_df["IC Inferior"].apply(fmt_m)
            proj_df["IC Superior"] = proj_df["IC Superior"].apply(fmt_m)

            col_t, col_s = st.columns([1.5, 1])
            with col_t:
                st.markdown('<p class="section-title">Tabla de Proyecciones Mensuales</p>', unsafe_allow_html=True)
                st.dataframe(proj_df, use_container_width=True, hide_index=True)

            with col_s:
                # ── Proyección por Establecimiento ───────────────
                st.markdown('<p class="section-title">Tendencia por Establecimiento</p>', unsafe_allow_html=True)
                proj_est = []
                for est in df["Establecimiento"].unique():
                    s_est = (df[df["Establecimiento"]==est]
                              .groupby(["Fecha","mes_num","anio"])["Devengado"].sum()
                              .reset_index().sort_values(["anio","mes_num"]))
                    if len(s_est) < 2:
                        continue
                    s_est["t"] = range(len(s_est))
                    c = np.polyfit(s_est["t"], s_est["Devengado"], 1)
                    t_f = np.arange(len(s_est), len(s_est)+12)
                    proj_est.append({
                        "Establecimiento": est,
                        "Proyectado Total 2026": int(np.poly1d(c)(t_f).sum()),
                        "Tendencia": "↑ Alza" if c[0] > 0 else "↓ Baja",
                    })
                if proj_est:
                    pe_df = pd.DataFrame(proj_est).sort_values("Proyectado Total 2026", ascending=False)
                    pe_df["Proyectado Total 2026"] = pe_df["Proyectado Total 2026"].apply(fmt_m)
                    st.dataframe(pe_df, use_container_width=True, hide_index=True)
        else:
            st.info("Se necesitan al menos 2 períodos para calcular proyecciones.")

# ╔══════════════════════════════════════════════════════════════════╗
# ║  TAB 4 — COMPARATIVA POR ESTABLECIMIENTO                        ║
# ╚══════════════════════════════════════════════════════════════════╝
with tab4:
    if df.empty:
        st.warning("Sin datos para los filtros seleccionados.")
    else:
        fecha_orden = (df.drop_duplicates("Fecha")
                        .sort_values(["anio","mes_num"])["Fecha"].tolist())

        # ── Selector de establecimiento ───────────────────────────
        est_detail = st.selectbox(
            "Establecimiento en detalle",
            sorted(df["Establecimiento"].unique()),
            key="est_detail",
        )
        df_est = df[df["Establecimiento"] == est_detail]

        # ── KPIs del establecimiento ──────────────────────────────
        d_est = df_est["Devengado"].sum()
        p_est = df_est["Ley de Presupuestos"].sum()
        pct_est = d_est / p_est * 100 if p_est else 0
        disp_est = p_est - d_est

        k1, k2, k3, k4 = st.columns(4)
        kpis_est = [
            (k1, "blue",  "DEVENGADO",   fmt_m(d_est),   ""),
            (k2, "teal",  "PRESUPUESTO", fmt_m(p_est),   ""),
            (k3, "amber", "DISPONIBLE",  fmt_m(disp_est),""),
            (k4, "green" if pct_est <= 100 else "red",
                  "EJECUCIÓN",     f"{pct_est:.1f}%",    badge(pct_est)),
        ]
        for col, color, label, value, extra in kpis_est:
            with col:
                st.markdown(f"""
                <div class="kpi-card {color}">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-sub">{est_detail} {extra}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)

        with col_a:
            # Evolución temporal del establecimiento
            serie_est = (df_est.groupby("Fecha")["Devengado"].sum()
                          .reindex(fecha_orden).reset_index())
            fig_e = go.Figure()
            fig_e.add_trace(go.Scatter(
                x=serie_est["Fecha"], y=serie_est["Devengado"],
                fill="tozeroy", mode="lines+markers",
                line=dict(color="#0d9488", width=2),
                fillcolor="rgba(13,148,136,0.12)",
                name="Devengado",
            ))
            pres_est = (df_est.groupby("Fecha")["Ley de Presupuestos"].sum()
                          .reindex(fecha_orden).reset_index())
            fig_e.add_trace(go.Scatter(
                x=pres_est["Fecha"], y=pres_est["Ley de Presupuestos"],
                mode="lines", name="Presupuesto",
                line=dict(color="#f59e0b", width=1.5, dash="dot"),
            ))
            fig_e.update_layout(**plotly_layout(f"Evolución · {est_detail}", 320))
            st.plotly_chart(fig_e, use_container_width=True)

        with col_b:
            # Distribución por Nivel (treemap)
            grp_niv = (df_est.groupby("Nivel")["Devengado"].sum()
                        .reset_index().astype({"Nivel": str}))
            fig_donut = px.pie(
                grp_niv, values="Devengado", names="Nivel",
                hole=0.55,
                color_discrete_sequence=PALETTE,
            )
            fig_donut.update_layout(**plotly_layout(f"Distribución por Nivel · {est_detail}", 320, True))
            st.plotly_chart(fig_donut, use_container_width=True)

        # ── Comparativa entre todos los establecimientos ──────────
        st.markdown('<p class="section-title">Comparativa Global: Desviación por Establecimiento</p>', unsafe_allow_html=True)

        comp_df = df.groupby("Establecimiento").agg(
            Devengado=("Devengado","sum"),
            Presupuesto=("Ley de Presupuestos","sum"),
        ).reset_index()
        comp_df["Desviacion"] = comp_df["Devengado"] - comp_df["Presupuesto"]
        comp_df["Ejecucion_pct"] = comp_df.apply(
            lambda r: r.Devengado/r.Presupuesto*100 if r.Presupuesto else 0, axis=1)

        fig_comp = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Devengado vs Presupuesto", "% Ejecución"),
            horizontal_spacing=0.08,
        )
        fig_comp.add_trace(go.Bar(
            name="Presupuesto", x=comp_df["Establecimiento"], y=comp_df["Presupuesto"],
            marker_color="rgba(59,130,246,0.3)",
            marker_line=dict(color="#3b82f6", width=1),
        ), row=1, col=1)
        fig_comp.add_trace(go.Bar(
            name="Devengado", x=comp_df["Establecimiento"], y=comp_df["Devengado"],
            marker_color="#3b82f6",
        ), row=1, col=1)

        bar_colors = ["#4ade80" if p <= 100 else "#f87171" for p in comp_df["Ejecucion_pct"]]
        fig_comp.add_trace(go.Bar(
            name="% Ejecución", x=comp_df["Establecimiento"], y=comp_df["Ejecucion_pct"],
            marker_color=bar_colors, showlegend=False,
        ), row=1, col=2)
        fig_comp.add_hline(y=100, line_color="#f59e0b", line_dash="dot", row=1, col=2)

        fig_comp.update_layout(
            **plotly_layout_subplot("", 340, True),
            barmode="overlay",
        )
        # Configurar ejes para subplots
        fig_comp.update_xaxes(gridcolor=GRID_COLOR, linecolor="#1e2d47", row=1, col=1)
        fig_comp.update_xaxes(gridcolor=GRID_COLOR, linecolor="#1e2d47", row=1, col=2)
        fig_comp.update_yaxes(gridcolor=GRID_COLOR, linecolor="#1e2d47", row=1, col=1)
        fig_comp.update_yaxes(gridcolor=GRID_COLOR, linecolor="#1e2d47", row=1, col=2)
        
        st.plotly_chart(fig_comp, use_container_width=True)

        # ── Top conceptos del establecimiento ────────────────────
        st.markdown(f'<p class="section-title">Top Conceptos · {est_detail}</p>', unsafe_allow_html=True)
        max_niv = df_est["Nivel"].max()
        df_det_est = df_est[df_est["Nivel"] == max_niv] if pd.notna(max_niv) else df_est
        top_est = (df_det_est.groupby("Concepto Presupuestario")["Devengado"].sum()
                    .reset_index().sort_values("Devengado", ascending=False).head(12))

        fig_top = px.bar(
            top_est, x="Concepto Presupuestario", y="Devengado",
            color="Devengado",
            color_continuous_scale=["#1e3a6e","#3b82f6","#7eb8f7"],
            labels={"Devengado": "Devengado ($)", "Concepto Presupuestario": ""},
        )
        fig_top.update_layout(**plotly_layout("", 340, False))
        fig_top.update_coloraxes(showscale=False)
        fig_top.update_xaxes(tickangle=-35, tickfont=dict(size=9))
        st.plotly_chart(fig_top, use_container_width=True)

# ── Footer ──────────────────────────────────────────────────────────
st.markdown("""
<div style="border-top:1px solid #1e2d47;margin-top:32px;padding-top:16px;
            text-align:center;color:#2a3a55;font-size:0.73rem;">
    Control Presupuestario · Datos procesados por data_anexo1.py · anexo1_loader.py
</div>
""", unsafe_allow_html=True)
