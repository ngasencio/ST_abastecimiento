"""
dashboard_jerarquico.py
═══════════════════════════════════════════════════════════════════════════════
Dashboard interactivo de análisis jerárquico presupuestario.
Permite navegar el árbol de conceptos, ver subconjuntos y métricas de control.

Ejecutar con:  streamlit run dashboard_jerarquico.py
Dependencias:  pip install streamlit plotly pandas numpy
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ── Módulos propios ───────────────────────────────────────────────────────────
try:
    from data.data_anexo1.jerarquia_presupuestaria import (
        enriquecer, filtrar_arbol, filtrar_nivel,
        metricas_arbol, reporte_control, arbol_navegacion, variacion_mom,
    )
except ImportError:
    st.error("No se encontró jerarquia_presupuestaria.py en el directorio.")
    st.stop()

# ── CSS ───────────────────────────────────────────────────────────────────────
def _css():
    try:
        with open("style.css", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # CSS embebido mínimo si no existe el archivo
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Source+Sans+3:wght@400;600;700&display=swap');
        :root {
            --brand-dark:#001C41; --brand-primary:#138AEC;
            --gray-100:#F1F5F9; --gray-200:#E2E8F0;
            --gray-500:#64748B; --gray-700:#334155; --gray-800:#1E293B;
        }
        html,body,[class*="css"]{font-family:'Source Sans 3',sans-serif;}
        .stApp{background:#F4F6FA;}
        [data-testid="stSidebar"]{background:linear-gradient(175deg,#00122C,#001C41,#0a2952)!important;}
        [data-testid="stSidebar"],[data-testid="stSidebar"] *{color:rgba(255,255,255,0.92)!important;}
        [data-testid="stSidebar"] label{font-size:.72rem!important;font-weight:700!important;letter-spacing:.08em!important;text-transform:uppercase!important;color:rgba(255,255,255,.5)!important;}
        </style>""", unsafe_allow_html=True)

_css()

# ════════════════════════════════════════════════════════════════════════════
# CONSTANTES VISUALES
# ════════════════════════════════════════════════════════════════════════════
MESES_ORDEN = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
}

PAL = ["#138AEC","#0D7377","#B45309","#6B3FA0","#1A7A4A",
       "#C0392B","#5C6BC0","#00796B","#E65100","#4527A0"]

SEM_COLOR = {"Verde":"#16A34A","Amarillo":"#B45309","Rojo":"#C0392B","Excedido":"#7C3AED","Sin Presupuesto":"#94A3B8","Sin datos":"#CBD5E1"}
SEM_EMOJI = {"Verde":"🟢","Amarillo":"🟡","Rojo":"🔴","Excedido":"⛔","Sin Presupuesto":"⚪","Sin datos":"—"}

def fmt(v):
    if pd.isna(v): return "—"
    v = float(v)
    if abs(v)>=1e9: return f"${v/1e9:.2f}MM"
    if abs(v)>=1e6: return f"${v/1e6:.1f}M"
    if abs(v)>=1e3: return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"

def pct_fmt(v):
    return "—" if pd.isna(v) else f"{v:.1f}%"

PLOT_CFG = dict(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font=dict(family="Source Sans 3, sans-serif", color="#64748B", size=11),
                margin=dict(l=48,r=16,t=48,b=48),
                xaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", showgrid=True),
                yaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", showgrid=True),
                colorway=PAL)

def apply_plot(fig, height=340, title="", showlegend=True):
    fig.update_layout(**PLOT_CFG, height=height,
                      title=dict(text=title, font=dict(family="Plus Jakarta Sans,sans-serif",
                                 size=13, color="#001C41"), x=0.01),
                      showlegend=showlegend,
                      legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10),
                                  orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ════════════════════════════════════════════════════════════════════════════
# CARGA Y ENRIQUECIMIENTO DE DATOS
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Cargando y enriqueciendo datos jerárquicos…")
def cargar_datos() -> pd.DataFrame:
    """Carga datos reales o genera demo enriquecido."""
    try:
        from anexo1_loader import cargar_anexo1
        df_raw = cargar_anexo1()
    except Exception:
        df_raw = _datos_demo()

    return enriquecer(df_raw)


def _datos_demo() -> pd.DataFrame:
    """Genera datos demo con estructura jerárquica real de 5 niveles."""
    rng = np.random.default_rng(42)
    estructura = [
        # (codigo, concepto, nivel)
        ("21", "21 GASTOS EN PERSONAL", 1),
        ("2101", "2101 Personal de Planta", 2),
        ("2101001", "2101001 Sueldos y Sobresueldos", 3),
        ("2101001001", "2101001001 Sueldo Base", 4),
        ("210100100101", "210100100101 Sueldo Base Planta L15076", 5),
        ("210100100102", "210100100102 Sueldo Base Planta L18834", 5),
        ("2101001002", "2101001002 Asignación Antigüedad", 4),
        ("210100100201", "210100100201 Asig Ant Quinquenios Planta", 5),
        ("2102", "2102 Personal a Contrata", 2),
        ("2102001", "2102001 Sueldos Contrata", 3),
        ("2102001001", "2102001001 Sueldo Base Contrata", 4),
        ("210200100101", "210200100101 Sueldo Contrata L15076", 5),
        ("22", "22 BIENES Y SERVICIOS", 1),
        ("2201", "2201 Alimentos y Bebidas", 2),
        ("2201001", "2201001 Alimentos para Personas", 3),
        ("2201001001", "2201001001 Raciones para Personal", 4),
        ("220100100101", "220100100101 Raciones Turno Diurno", 5),
        ("220100100102", "220100100102 Raciones Turno Nocturno", 5),
        ("2202", "2202 Textiles y Vestuario", 2),
        ("2202001", "2202001 Vestuario y Uniformes", 3),
        ("2202001001", "2202001001 Uniformes Personal", 4),
        ("220200100101", "220200100101 Uniformes Área Clínica", 5),
        ("29", "29 ADQUISICIÓN DE ACTIVOS", 1),
        ("2901", "2901 Mobiliario y Equipamiento", 2),
        ("2901001", "2901001 Equipos Médicos", 3),
        ("2901001001", "2901001001 Equipos Diagnóstico", 4),
        ("290100100101", "290100100101 Equipos Diagnóstico Imagenología", 5),
    ]
    establecimientos = ["DSSO", "HBO", "HCUCH"]
    rows = []
    bases = {cod: rng.integers(500_000_000, 5_000_000_000) // 12 for cod, _, _ in estructura}

    for est in establecimientos:
        factor = rng.uniform(0.8, 1.2)
        for year in [2024, 2025]:
            for mes, mnum in MESES_ORDEN.items():
                for cod, concepto, nivel in estructura:
                    pres = int(bases[cod] * factor)
                    dev = int(pres * rng.uniform(0.70, 1.15))
                    if rng.random() < 0.03:
                        dev = -abs(dev)
                    rows.append({
                        "Establecimiento": est,
                        "Fecha": f"{mes} {year}",
                        "Nivel": nivel,
                        "Concepto Presupuestario": concepto,
                        "Ley de Presupuestos": pres,
                        "Devengado": dev,
                        "Compromiso": int(dev * rng.uniform(0.95, 1.05)),
                        "Saldo por Aplicar": int(pres - dev),
                        "Efectivo": int(dev * rng.uniform(0.90, 1.00)),
                    })
    return pd.DataFrame(rows)


df_full = cargar_datos()
arbol   = arbol_navegacion(df_full)

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — NAVEGADOR JERÁRQUICO
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px">
        <p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:1rem;
                  font-weight:800;color:#fff;margin:0 0 2px">Navegador Jerárquico</p>
        <p style="font-size:.7rem;color:rgba(255,255,255,.45);margin:0;
                  text-transform:uppercase;letter-spacing:.08em">Control Presupuestario</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Establecimientos ──────────────────────────────────────────
    est_opts = sorted(df_full["Establecimiento"].dropna().unique()) if "Establecimiento" in df_full.columns else []
    est_sel  = st.multiselect("Establecimiento", est_opts, default=est_opts)

    # ── Años ──────────────────────────────────────────────────────
    anios = sorted(df_full["Anio"].dropna().unique().astype(int)) if "Anio" in df_full.columns else []
    anios_sel = st.multiselect("Año", anios, default=anios)

    st.markdown("---")

    # ── Navegador N1 → N2 → N3 ───────────────────────────────────
    st.markdown("<p style='font-size:.72rem;font-weight:700;color:rgba(255,255,255,.5);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px'>Árbol de Conceptos</p>", unsafe_allow_html=True)

    raices = arbol.get("__raices__", [])
    n1_sel = st.selectbox("Capítulo (N1)", ["— Todos —"] + raices)

    n2_opts = arbol.get(n1_sel, []) if n1_sel != "— Todos —" else []
    n2_sel  = st.selectbox("Subcapítulo (N2)", ["— Todos —"] + n2_opts) if n2_opts else None

    n3_opts = arbol.get(n2_sel, []) if n2_sel and n2_sel != "— Todos —" else []
    n3_sel  = st.selectbox("Partida (N3)", ["— Todos —"] + n3_opts) if n3_opts else None

    st.markdown("---")

    # ── Profundidad del reporte ───────────────────────────────────
    nivel_rep = st.select_slider("Profundidad del reporte",
                                 options=[1, 2, 3, 4, 5], value=2)
    solo_hojas = st.checkbox("Solo nodos hoja (evitar doble conteo)", value=True)

    st.markdown("---")
    st.markdown(f"<p style='font-size:.7rem;color:rgba(255,255,255,.35)'>{len(df_full):,} registros · {df_full['Fecha'].nunique() if 'Fecha' in df_full.columns else 0} períodos</p>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# FILTRADO ACTIVO
# ════════════════════════════════════════════════════════════════════════════
df_work = df_full.copy()
if est_sel and "Establecimiento" in df_work.columns:
    df_work = df_work[df_work["Establecimiento"].isin(est_sel)]
if anios_sel and "Anio" in df_work.columns:
    df_work = df_work[df_work["Anio"].isin(anios_sel)]

# Determinar concepto raíz del árbol seleccionado
concepto_raiz = None
if n3_sel and n3_sel != "— Todos —":
    concepto_raiz = n3_sel
elif n2_sel and n2_sel != "— Todos —":
    concepto_raiz = n2_sel
elif n1_sel and n1_sel != "— Todos —":
    concepto_raiz = n1_sel

if concepto_raiz:
    df_arbol = filtrar_arbol(df_work, concepto_raiz)
else:
    df_arbol = df_work.copy()

# Métricas del árbol seleccionado
kpis = metricas_arbol(df_arbol, solo_hojas=solo_hojas)

# Ordenar fechas
fecha_orden = []
if "Fecha" in df_arbol.columns and "Anio" in df_arbol.columns:
    fecha_orden = (
        df_arbol.drop_duplicates("Fecha")
        .sort_values(["Anio","Mes_Num"])["Fecha"]
        .tolist()
    )


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
breadcrumb = " › ".join(filter(None, [
    n1_sel if n1_sel != "— Todos —" else "Todos los Capítulos",
    n2_sel if n2_sel and n2_sel != "— Todos —" else None,
    n3_sel if n3_sel and n3_sel != "— Todos —" else None,
]))

estado_global = kpis.get("estado_global", "Sin datos")
est_color = SEM_COLOR.get(estado_global, "#94A3B8")

st.markdown(f"""
<div style="background:linear-gradient(135deg,#001C41 0%,#0D5FA8 100%);
            border-radius:14px;padding:24px 28px;margin-bottom:20px;position:relative;overflow:hidden">
    <div style="position:absolute;top:-40px;right:-40px;width:180px;height:180px;
                background:radial-gradient(circle,rgba(19,138,236,.2) 0%,transparent 70%);border-radius:50%"></div>
    <div style="display:flex;align-items:flex-start;justify-content:space-between;position:relative">
        <div>
            <h1 style="font-family:'Plus Jakarta Sans',sans-serif;font-size:1.5rem;
                       font-weight:800;color:#fff;margin:0 0 4px;line-height:1.2">
                Análisis Jerárquico Presupuestario
            </h1>
            <p style="font-size:.82rem;color:rgba(255,255,255,.6);margin:0;letter-spacing:.02em">
                {breadcrumb}
            </p>
        </div>
        <div style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);
                    border-radius:8px;padding:8px 14px;text-align:center;min-width:120px">
            <div style="font-size:.65rem;color:rgba(255,255,255,.5);letter-spacing:.08em;text-transform:uppercase">Estado</div>
            <div style="font-size:1.1rem;font-weight:800;color:{est_color};margin-top:2px">
                {SEM_EMOJI.get(estado_global,"—")} {estado_global}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ════════════════════════════════════════════════════════════════════════════
def kpi(col, color, label, value, sub=""):
    col.markdown(f"""
    <div style="background:#fff;border:1px solid #E2E8F0;border-top:3px solid {color};
                border-radius:10px;padding:16px 18px 12px;height:100%">
        <div style="font-size:.67rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
                    color:#64748B;margin-bottom:8px">{label}</div>
        <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:1.55rem;font-weight:800;
                    color:#001C41;line-height:1;margin-bottom:6px">{value}</div>
        {'<div style="font-size:.72rem;color:#94A3B8">'+sub+'</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

pct_ej  = kpis.get("pct_ejecucion")
pct_var = kpis.get("pct_variacion")
color_ej = "#16A34A" if pct_ej and pct_ej<=80 else ("#B45309" if pct_ej and pct_ej<=100 else "#C0392B")

c1,c2,c3,c4,c5,c6 = st.columns(6)
kpi(c1,"#138AEC","Devengado",          fmt(kpis["devengado_total"]),     f"{kpis['n_periodos']} períodos")
kpi(c2,"#0D7377","Presupuesto",         fmt(kpis["presupuesto_total"]),   "Ley de Presupuestos")
kpi(c3,"#B45309","Disponible",          fmt(kpis["disponible"]),          "Saldo por ejecutar")
kpi(c4, color_ej,"% Ejecución",         pct_fmt(pct_ej),                  "Devengado / Presupuesto")
kpi(c5,"#138AEC","Compromiso",          fmt(kpis["compromiso_total"]),    "Comprometido")
kpi(c6,"#C0392B" if pct_var and pct_var>0 else "#16A34A",
        "Variación",                    pct_fmt(pct_var),                 "vs Presupuesto")

st.markdown("<br>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌳 Árbol Jerárquico",
    "📈 Evolución Temporal",
    "📊 Reporte de Control",
    "🔍 Análisis por Nivel",
    "⚖ Variación MoM",
])


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 — ÁRBOL JERÁRQUICO                                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab1:
    col_l, col_r = st.columns([1.1, 1])

    with col_l:
        st.markdown("<p style='font-size:.9rem;font-weight:700;color:#334155;border-bottom:1.5px solid #E2E8F0;padding-bottom:8px;margin-bottom:14px'>Estructura Jerárquica · Devengado Acumulado</p>", unsafe_allow_html=True)

        # Treemap
        if not df_arbol.empty and "Nivel" in df_arbol.columns:
            # Para el treemap usamos nodos con padre
            tm = df_arbol[df_arbol["Nivel"] <= min(nivel_rep, 4)].copy()
            tm = tm.dropna(subset=["Concepto Presupuestario","Padre_Codigo"])
            tm_agg = (tm.groupby(["Concepto Presupuestario","Padre_Codigo","Nivel"])
                      ["Devengado"].sum().reset_index())

            # Raíces necesitan padre vacío
            tm_agg.loc[tm_agg["Nivel"]==1, "Padre_Codigo"] = ""

            if not tm_agg.empty:
                fig_tree = go.Figure(go.Treemap(
                    labels=tm_agg["Concepto Presupuestario"],
                    parents=tm_agg["Padre_Codigo"].fillna(""),
                    values=tm_agg["Devengado"].clip(lower=0),
                    textinfo="label+percent parent",
                    hovertemplate="<b>%{label}</b><br>Devengado: $%{value:,.0f}<br>%{percentParent} del padre<extra></extra>",
                    marker=dict(
                        colorscale=[[0,"#E8F4FD"],[0.5,"#138AEC"],[1,"#001C41"]],
                        colorbar=dict(thickness=8, len=0.6),
                    ),
                    maxdepth=3,
                ))
                fig_tree.update_layout(paper_bgcolor="#fff", plot_bgcolor="#fff",
                                       height=420, margin=dict(l=8,r=8,t=8,b=8))
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Sin datos para treemap con los filtros actuales.")

    with col_r:
        st.markdown("<p style='font-size:.9rem;font-weight:700;color:#334155;border-bottom:1.5px solid #E2E8F0;padding-bottom:8px;margin-bottom:14px'>Semáforos de Ejecución</p>", unsafe_allow_html=True)

        # Semáforos por concepto del nivel seleccionado
        df_sem = filtrar_nivel(df_arbol, nivel_rep) if not df_arbol.empty else pd.DataFrame()
        if not df_sem.empty and "Estado_Semaforo" in df_sem.columns:
            sem_agg = (
                df_sem.groupby(["Concepto Presupuestario","Estado_Semaforo"])
                .agg(Dev=("Devengado","sum"), Pres=("Ley de Presupuestos","sum"))
                .reset_index()
            )
            sem_agg["pct"] = (sem_agg["Dev"] / sem_agg["Pres"].replace(0,np.nan)*100).round(1)
            sem_agg["Concepto_Corto"] = sem_agg["Concepto Presupuestario"].str[:50]

            for _, row in sem_agg.sort_values("pct", ascending=False).head(15).iterrows():
                e = row["Estado_Semaforo"]
                col_sem = SEM_COLOR.get(e,"#94A3B8")
                emoji   = SEM_EMOJI.get(e,"—")
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;background:#F8FAFC;
                            border:1px solid #E2E8F0;border-radius:8px;padding:8px 12px;
                            margin-bottom:5px">
                    <div style="font-size:1rem">{emoji}</div>
                    <div style="flex:1;font-size:.78rem;color:#334155;font-weight:500;
                                overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                        {row['Concepto_Corto']}
                    </div>
                    <div style="font-size:.82rem;font-weight:700;color:{col_sem};
                                white-space:nowrap">{row['pct']:.1f}%</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Sin datos de semáforo para el nivel seleccionado.")

    # Distribución de semáforos
    sem_counts = kpis.get("semaforos", {})
    if sem_counts:
        st.markdown("<br>", unsafe_allow_html=True)
        cols_s = st.columns(len(sem_counts))
        for i, (estado, cnt) in enumerate(sorted(sem_counts.items())):
            color = SEM_COLOR.get(estado, "#94A3B8")
            emoji = SEM_EMOJI.get(estado, "—")
            with cols_s[i]:
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #E2E8F0;border-radius:8px;
                            padding:12px;text-align:center">
                    <div style="font-size:1.4rem">{emoji}</div>
                    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:1.3rem;
                                font-weight:800;color:{color};margin:4px 0">{cnt}</div>
                    <div style="font-size:.7rem;font-weight:700;color:#94A3B8;
                                text-transform:uppercase;letter-spacing:.06em">{estado}</div>
                </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ TAB 2 — EVOLUCIÓN TEMPORAL                                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab2:
    if df_arbol.empty:
        st.warning("Sin datos para los filtros seleccionados.")
    else:
        por_periodo = kpis.get("por_periodo", pd.DataFrame())

        col_a, col_b = st.columns(2)

        with col_a:
            # Serie total con presupuesto
            if not por_periodo.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=por_periodo["Fecha"], y=por_periodo.get("Presupuesto", []),
                    name="Presupuesto", mode="lines",
                    line=dict(color="#CBD5E1", width=2, dash="dot"),
                ))
                fig.add_trace(go.Scatter(
                    x=por_periodo["Fecha"], y=por_periodo["Devengado"],
                    name="Devengado", fill="tozeroy", mode="lines+markers",
                    line=dict(color="#138AEC", width=2.5),
                    fillcolor="rgba(19,138,236,0.08)",
                    marker=dict(size=5),
                ))
                fig = apply_plot(fig, 300, "Devengado vs Presupuesto · Total")
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            # % Ejecución temporal
            if not por_periodo.empty and "Pct_Ejecucion" in por_periodo.columns:
                colors_bar = [
                    "#16A34A" if p<=80 else ("#B45309" if p<=100 else "#C0392B")
                    for p in por_periodo["Pct_Ejecucion"].fillna(0)
                ]
                fig2 = go.Figure(go.Bar(
                    x=por_periodo["Fecha"],
                    y=por_periodo["Pct_Ejecucion"],
                    marker_color=colors_bar,
                    text=[f"{p:.1f}%" for p in por_periodo["Pct_Ejecucion"].fillna(0)],
                    textposition="outside", textfont=dict(size=9),
                ))
                fig2.add_hline(y=100, line_color="#001C41", line_dash="dot", line_width=1.5)
                fig2 = apply_plot(fig2, 300, "% Ejecución por Período", False)
                fig2.update_layout(yaxis=dict(ticksuffix="%"))
                st.plotly_chart(fig2, use_container_width=True)

        # Serie por nivel
        st.markdown("<p style='font-size:.9rem;font-weight:700;color:#334155;border-bottom:1.5px solid #E2E8F0;padding-bottom:8px;margin-bottom:14px'>Devengado por Nivel Jerárquico · Evolución</p>", unsafe_allow_html=True)

        if "Nivel" in df_arbol.columns and "Fecha" in df_arbol.columns:
            df_niv_t = (
                df_arbol.groupby(["Fecha","Nivel","Anio","Mes_Num"])["Devengado"]
                .sum().reset_index()
                .sort_values(["Anio","Mes_Num"])
                .astype({"Nivel":str})
            )
            if not df_niv_t.empty:
                fig3 = px.line(df_niv_t, x="Fecha", y="Devengado", color="Nivel",
                               markers=True, color_discrete_sequence=PAL,
                               category_orders={"Fecha": fecha_orden},
                               labels={"Devengado":"Devengado ($)","Fecha":"","Nivel":"Nivel"})
                fig3.update_traces(line_width=1.8, marker_size=4)
                fig3 = apply_plot(fig3, 300, "")
                st.plotly_chart(fig3, use_container_width=True)

        # Área apilada por concepto (N1 del árbol)
        if "Etiqueta_N1" in df_arbol.columns and "Fecha" in df_arbol.columns:
            sub_hojas = df_arbol[df_arbol["Es_Hoja"]] if "Es_Hoja" in df_arbol.columns else df_arbol
            df_n1_t = (
                sub_hojas.groupby(["Fecha","Etiqueta_N1","Anio","Mes_Num"])["Devengado"]
                .sum().reset_index().sort_values(["Anio","Mes_Num"])
            )
            if not df_n1_t.empty:
                fig4 = px.area(df_n1_t, x="Fecha", y="Devengado", color="Etiqueta_N1",
                               color_discrete_sequence=PAL,
                               category_orders={"Fecha": fecha_orden},
                               labels={"Devengado":"Devengado ($)","Fecha":"","Etiqueta_N1":"Capítulo"})
                fig4 = apply_plot(fig4, 280, "Composición del Devengado por Capítulo")
                st.plotly_chart(fig4, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ TAB 3 — REPORTE DE CONTROL                                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab3:
    st.markdown(f"<div style='background:#EFF6FF;border-left:3px solid #138AEC;border-radius:0 8px 8px 0;padding:10px 14px;font-size:.82rem;color:#1E40AF;margin-bottom:14px'>Reporte en Nivel {nivel_rep} · Solo nodos hoja: {'Sí' if solo_hojas else 'No'} · Agrupado por Establecimiento y Fecha</div>", unsafe_allow_html=True)

    reporte = reporte_control(
        df_arbol,
        nivel_reporte=nivel_rep,
        agrupar_por=["Establecimiento","Fecha"],
    )

    if reporte.empty:
        st.info(f"No hay datos para Nivel {nivel_rep} con los filtros actuales.")
    else:
        # Columnas a mostrar
        cols_show = ["Concepto Presupuestario"]
        for lv in range(1, nivel_rep):
            col_et = f"Etiqueta_N{lv}"
            if col_et in reporte.columns:
                cols_show.append(col_et)
        for c in ["Establecimiento","Fecha","Ley de Presupuestos","Devengado",
                  "Compromiso","Disponible","Pct_Ejecucion","Pct_Variacion","Estado"]:
            if c in reporte.columns:
                cols_show.append(c)

        reporte_disp = reporte[[c for c in cols_show if c in reporte.columns]].copy()

        # Formatear para display
        reporte_fmt = reporte_disp.copy()
        for col in ["Ley de Presupuestos","Devengado","Compromiso","Disponible"]:
            if col in reporte_fmt.columns:
                reporte_fmt[col] = reporte_fmt[col].apply(fmt)
        for col in ["Pct_Ejecucion","Pct_Variacion"]:
            if col in reporte_fmt.columns:
                reporte_fmt[col] = reporte_fmt[col].apply(pct_fmt)

        st.dataframe(reporte_fmt, use_container_width=True, hide_index=True)

        # Botón de descarga
        csv_bytes = reporte.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇ Descargar Reporte CSV",
            data=csv_bytes,
            file_name=f"reporte_control_N{nivel_rep}.csv",
            mime="text/csv",
        )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ TAB 4 — ANÁLISIS POR NIVEL                                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab4:
    nivel_detalle = st.select_slider(
        "Seleccionar nivel de análisis",
        options=[1,2,3,4,5], value=nivel_rep,
        key="nivel_det_slider",
    )

    df_niv = filtrar_nivel(df_arbol, nivel_detalle) if not df_arbol.empty else pd.DataFrame()

    if df_niv.empty:
        st.info(f"No hay datos para Nivel {nivel_detalle}.")
    else:
        agg_niv = (
            df_niv.groupby("Concepto Presupuestario")
            .agg(Dev=("Devengado","sum"), Pres=("Ley de Presupuestos","sum"),
                 Comp=("Compromiso","sum"))
            .reset_index()
        )
        agg_niv["pct"] = (agg_niv["Dev"] / agg_niv["Pres"].replace(0,np.nan)*100).round(2)
        agg_niv["var"] = agg_niv["Dev"] - agg_niv["Pres"]
        agg_niv = agg_niv.sort_values("Dev", ascending=False)
        agg_niv["Concepto_Corto"] = agg_niv["Concepto Presupuestario"].str[:45]

        col_c, col_d = st.columns(2)

        with col_c:
            # Barras horizontales de ejecución
            bar_colors = [
                "#16A34A" if p<=80 else ("#B45309" if p<=100 else "#C0392B")
                for p in agg_niv["pct"].fillna(0)
            ]
            fig5 = go.Figure(go.Bar(
                y=agg_niv["Concepto_Corto"].head(15),
                x=agg_niv["pct"].head(15),
                orientation="h",
                marker_color=bar_colors[:15],
                text=[f"{p:.1f}%" for p in agg_niv["pct"].head(15).fillna(0)],
                textposition="outside", textfont=dict(size=9),
            ))
            fig5.add_vline(x=100, line_color="#001C41", line_dash="dot", line_width=1.5)
            fig5 = apply_plot(fig5, 380, f"% Ejecución · Nivel {nivel_detalle}", False)
            fig5.update_layout(
                xaxis=dict(ticksuffix="%", range=[0, max(130, agg_niv["pct"].max()+15 if not agg_niv.empty else 130)]),
                yaxis=dict(tickfont=dict(size=9), showgrid=False),
                bargap=0.3,
            )
            st.plotly_chart(fig5, use_container_width=True)

        with col_d:
            # Waterfall de variación
            agg_top = agg_niv.head(10).copy()
            measure = ["relative"] * len(agg_top)
            colors_wf = ["#C0392B" if v>0 else "#16A34A" for v in agg_top["var"]]
            fig6 = go.Figure(go.Waterfall(
                x=agg_top["Concepto_Corto"],
                y=agg_top["var"],
                measure=measure,
                marker_color=colors_wf,
                connector=dict(line=dict(color="#E2E8F0")),
                text=[fmt(v) for v in agg_top["var"]],
                textposition="outside",
            ))
            fig6.add_hline(y=0, line_color="#001C41", line_dash="dot", line_width=1)
            fig6 = apply_plot(fig6, 380, f"Variación Devengado−Presupuesto · Nivel {nivel_detalle}", False)
            fig6.update_layout(xaxis=dict(tickangle=-35, tickfont=dict(size=8)))
            st.plotly_chart(fig6, use_container_width=True)

        # Bubble chart: Presupuesto vs Devengado
        st.markdown("<p style='font-size:.9rem;font-weight:700;color:#334155;border-bottom:1.5px solid #E2E8F0;padding-bottom:8px;margin-bottom:14px'>Dispersión: Presupuesto vs Devengado (tamaño = compromiso)</p>", unsafe_allow_html=True)

        fig7 = px.scatter(
            agg_niv, x="Pres", y="Dev",
            size=agg_niv["Comp"].clip(lower=0) + 1,
            color="pct",
            hover_name="Concepto Presupuestario",
            color_continuous_scale=["#16A34A","#B45309","#C0392B"],
            labels={"Pres":"Presupuesto ($)","Dev":"Devengado ($)","pct":"% Ejec."},
            size_max=40,
        )
        # Línea identidad
        mx = max(agg_niv[["Pres","Dev"]].max()) if not agg_niv.empty else 1
        fig7.add_trace(go.Scatter(
            x=[0,mx], y=[0,mx], mode="lines",
            line=dict(color="#CBD5E1", dash="dot", width=1.5),
            name="100% ejecución", showlegend=True,
        ))
        fig7 = apply_plot(fig7, 320, "")
        st.plotly_chart(fig7, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ TAB 5 — VARIACIÓN MES A MES                                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab5:
    st.markdown("<div style='background:#EFF6FF;border-left:3px solid #138AEC;border-radius:0 8px 8px 0;padding:10px 14px;font-size:.82rem;color:#1E40AF;margin-bottom:14px'>Variación del Devengado mes a mes (MoM) para el subárbol seleccionado. Solo nodos hoja para evitar doble conteo.</div>", unsafe_allow_html=True)

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        serie_mom = variacion_mom(df_arbol)
        if not serie_mom.empty:
            colors_mom = ["#16A34A" if v>=0 else "#C0392B" for v in serie_mom["Variacion_Abs"].fillna(0)]
            fig_mom = go.Figure()
            fig_mom.add_trace(go.Bar(
                x=serie_mom["Fecha"],
                y=serie_mom["Variacion_Abs"],
                marker_color=colors_mom,
                name="Variación Absoluta",
                text=[fmt(v) for v in serie_mom["Variacion_Abs"].fillna(0)],
                textposition="outside", textfont=dict(size=8),
            ))
            fig_mom.add_hline(y=0, line_color="#001C41", line_width=1)
            fig_mom = apply_plot(fig_mom, 300, "Variación Absoluta MoM", False)
            st.plotly_chart(fig_mom, use_container_width=True)

    with col_m2:
        if not serie_mom.empty and "Variacion_Pct" in serie_mom.columns:
            colors_pct = ["#16A34A" if v>=0 else "#C0392B" for v in serie_mom["Variacion_Pct"].fillna(0)]
            fig_mom2 = go.Figure(go.Bar(
                x=serie_mom["Fecha"],
                y=serie_mom["Variacion_Pct"],
                marker_color=colors_pct,
                text=[f"{v:+.1f}%" for v in serie_mom["Variacion_Pct"].fillna(0)],
                textposition="outside", textfont=dict(size=8),
            ))
            fig_mom2.add_hline(y=0, line_color="#001C41", line_width=1)
            fig_mom2 = apply_plot(fig_mom2, 300, "Variación Porcentual MoM (%)", False)
            fig_mom2.update_layout(yaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig_mom2, use_container_width=True)

    # Tabla de variación
    if not serie_mom.empty:
        st.markdown("<p style='font-size:.9rem;font-weight:700;color:#334155;border-bottom:1.5px solid #E2E8F0;padding-bottom:8px;margin-bottom:14px'>Detalle Período a Período</p>", unsafe_allow_html=True)
        tbl_mom = serie_mom[["Fecha","Devengado","Dev_Anterior","Variacion_Abs","Variacion_Pct"]].copy()
        tbl_mom["Devengado"]     = tbl_mom["Devengado"].apply(fmt)
        tbl_mom["Dev_Anterior"]  = tbl_mom["Dev_Anterior"].apply(lambda v: fmt(v) if pd.notna(v) else "—")
        tbl_mom["Variacion_Abs"] = tbl_mom["Variacion_Abs"].apply(lambda v: fmt(v) if pd.notna(v) else "—")
        tbl_mom["Variacion_Pct"] = tbl_mom["Variacion_Pct"].apply(lambda v: f"{v:+.1f}%" if pd.notna(v) else "—")
        tbl_mom.columns = ["Período","Devengado","Período Anterior","Var. Absoluta","Var. %"]
        st.dataframe(tbl_mom, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="border-top:1px solid #E2E8F0;margin-top:36px;padding-top:14px;
            display:flex;justify-content:space-between">
    <span style="font-size:.72rem;color:#94A3B8">
        Dashboard Jerárquico · jerarquia_presupuestaria.py · data_anexo1.py
    </span>
    <span style="font-size:.72rem;color:#94A3B8">
        Solo nodos hoja activo para evitar doble conteo
    </span>
</div>
""", unsafe_allow_html=True)