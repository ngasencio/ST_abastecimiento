"""
dashboard_jerarquico.py  v3.0
─────────────────────────────────────────────────────────────────────────────
• Filtros inline (establecimiento, año, rango fechas, niveles, semáforo)
• Treemap corregido: siempre incluye N1 como raíz aunque no esté en niv_sel
• Tab "Semáforos de Control" con tabla detallada + filtro rápido por estado
• 6 pestañas de análisis
Ejecutar:  streamlit run dashboard_jerarquico.py
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    from data.data_anexo1.jerarquia_presupuestaria import (
        enriquecer, filtrar_arbol, filtrar_nivel,
        metricas_arbol, reporte_control, arbol_navegacion, variacion_mom,
    )
except ImportError:
    st.error("No se encontró jerarquia_presupuestaria.py")
    st.stop()

# ── Configuración de página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Jerárquico Presupuestario",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────
def _css():
    try:
        with open("style.css", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    # CSS extra para filtros inline
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Source+Sans+3:wght@400;600;700&display=swap');
    html,body,[class*="css"]{font-family:'Source Sans 3',sans-serif !important;}
    .stApp{background:#F4F6FA !important;}
    [data-testid="stSidebar"]{background:linear-gradient(175deg,#00122C,#001C41,#0a2952) !important;
        border-right:1px solid rgba(255,255,255,.06) !important;}
    [data-testid="stSidebar"],[data-testid="stSidebar"] *{color:rgba(255,255,255,.92) !important;}
    [data-testid="stSidebar"] label{font-size:.72rem !important;font-weight:700 !important;
        letter-spacing:.08em !important;text-transform:uppercase !important;
        color:rgba(255,255,255,.5) !important;}
    /* Filter panel */
    .filter-panel{background:#fff;border:1px solid #E2E8F0;border-radius:12px;
        padding:18px 22px 14px;margin-bottom:20px;
        box-shadow:0 2px 8px rgba(0,0,0,.05);}
    .filter-row-title{font-family:'Plus Jakarta Sans',sans-serif;font-size:.7rem;
        font-weight:700;letter-spacing:.09em;text-transform:uppercase;
        color:#64748B;margin-bottom:10px;display:flex;align-items:center;gap:8px;}
    .filter-row-title::after{content:'';flex:1;height:1px;background:#E2E8F0;}
    .chip{display:inline-flex;align-items:center;gap:4px;background:#EFF6FF;
        border:1px solid #BFDBFE;border-radius:20px;padding:2px 9px;
        font-size:.71rem;font-weight:600;color:#1D4ED8;margin:2px 2px;}
    /* Semáforo tabla */
    .sem-badge{display:inline-block;padding:2px 8px;border-radius:12px;
        font-size:.72rem;font-weight:700;}
    </style>
    """, unsafe_allow_html=True)

_css()

# ════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ════════════════════════════════════════════════════════════════════════════
MESES_ORDEN = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
}
PAL = ["#138AEC","#0D7377","#B45309","#6B3FA0","#1A7A4A",
       "#C0392B","#5C6BC0","#00796B","#E65100","#4527A0"]

SEM_COLOR  = {"Verde":"#16A34A","Amarillo":"#B45309","Rojo":"#C0392B",
               "Excedido":"#7C3AED","Sin Ejecutar":"#0D7377","Sin Presupuesto":"#94A3B8"}
SEM_EMOJI  = {"Verde":"🟢","Amarillo":"🟡","Rojo":"🔴",
               "Excedido":"⛔","Sin Ejecutar":"⬜","Sin Presupuesto":"⚪"}
SEM_BG     = {"Verde":"#F0FDF4","Amarillo":"#FFFBEB","Rojo":"#FEF2F2",
               "Excedido":"#F5F3FF","Sin Ejecutar":"#F0FDFA","Sin Presupuesto":"#F8FAFC"}
SEM_ORDEN  = ["Excedido","Rojo","Amarillo","Sin Ejecutar","Verde","Sin Presupuesto"]

def fmt(v):
    if pd.isna(v): return "—"
    v = float(v)
    if abs(v) >= 1e9: return f"${v/1e9:.2f}MM"
    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"

def pct_fmt(v):
    return "—" if pd.isna(v) else f"{v:.1f}%"

PLOT_BASE = dict(
    paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
    font=dict(family="Source Sans 3, sans-serif", color="#64748B", size=11),
    margin=dict(l=50, r=20, t=50, b=50),
    colorway=PAL,
)

def mkfig(height=340, title="", showlegend=True):
    """Devuelve un dict de layout listo para update_layout."""
    lo = dict(**PLOT_BASE, height=height, showlegend=showlegend)
    lo["xaxis"] = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", showgrid=True)
    lo["yaxis"] = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", showgrid=True)
    if title:
        lo["title"] = dict(text=title,
                           font=dict(family="Plus Jakarta Sans,sans-serif",
                                     size=13, color="#001C41"), x=0.01)
    if showlegend:
        lo["legend"] = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10),
                            orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1)
    return lo

def sec(txt, sub=""):
    s = f"<span style='font-size:.7rem;color:#94A3B8;margin-left:auto'>{sub}</span>" if sub else ""
    st.markdown(
        f"<div style='display:flex;align-items:center;border-bottom:1.5px solid"
        f" #E2E8F0;padding-bottom:8px;margin:22px 0 14px'>"
        f"<p style='font-size:.9rem;font-weight:700;color:#334155;margin:0'>{txt}</p>"
        f"{s}</div>",
        unsafe_allow_html=True,
    )

def kpi_card(col, color, label, value, sub=""):
    col.markdown(
        f"<div style='background:#fff;border:1px solid #E2E8F0;border-top:3px solid {color};"
        f"border-radius:10px;padding:16px 18px 12px'>"
        f"<div style='font-size:.67rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;"
        f"color:#64748B;margin-bottom:8px'>{label}</div>"
        f"<div style='font-family:Plus Jakarta Sans,sans-serif;font-size:1.5rem;font-weight:800;"
        f"color:#001C41;line-height:1;margin-bottom:6px'>{value}</div>"
        + (f"<div style='font-size:.72rem;color:#94A3B8'>{sub}</div>" if sub else "") +
        "</div>",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Cargando y enriqueciendo datos…")
def cargar_datos():
    try:
        from anexo1_loader import cargar_anexo1
        return enriquecer(cargar_anexo1())
    except Exception:
        return enriquecer(_demo())

def _demo():
    rng = np.random.default_rng(42)
    EST = [
        ("21",           "21 GASTOS EN PERSONAL",                    1),
        ("2101",         "2101 Personal de Planta",                  2),
        ("2101001",      "2101001 Sueldos y Sobresueldos",            3),
        ("2101001001",   "2101001001 Sueldo Base",                   4),
        ("210100100101", "210100100101 Sueldo Base Planta L15076",    5),
        ("210100100102", "210100100102 Sueldo Base Planta L18834",    5),
        ("2101001002",   "2101001002 Asignacion Antiguedad",          4),
        ("210100100201", "210100100201 Asig Ant Quinquenios",         5),
        ("2102",         "2102 Personal a Contrata",                  2),
        ("2102001",      "2102001 Sueldos Contrata",                  3),
        ("2102001001",   "2102001001 Sueldo Base Contrata",           4),
        ("210200100101", "210200100101 Sueldo Contrata L15076",       5),
        ("22",           "22 BIENES Y SERVICIOS",                    1),
        ("2201",         "2201 Alimentos y Bebidas",                  2),
        ("2201001",      "2201001 Alimentos para Personas",           3),
        ("2201001001",   "2201001001 Raciones para Personal",         4),
        ("220100100101", "220100100101 Raciones Turno Diurno",        5),
        ("220100100102", "220100100102 Raciones Turno Nocturno",      5),
        ("2202",         "2202 Textiles y Vestuario",                 2),
        ("2202001",      "2202001 Vestuario y Uniformes",             3),
        ("2202001001",   "2202001001 Uniformes Personal",             4),
        ("220200100101", "220200100101 Uniformes Area Clinica",       5),
        ("29",           "29 ADQUISICION DE ACTIVOS",                1),
        ("2901",         "2901 Mobiliario y Equipamiento",            2),
        ("2901001",      "2901001 Equipos Medicos",                   3),
        ("2901001001",   "2901001001 Equipos Diagnostico",            4),
        ("290100100101", "290100100101 Equipos Diagnostico Imagen",   5),
    ]
    bases = {c: rng.integers(500_000_000, 5_000_000_000)//12 for c,_,_ in EST}
    rows = []
    for est in ["DSSO","HBO"]:
        fac = rng.uniform(0.8, 1.2)
        for yr in [2024, 2025]:
            for mes, mn in MESES_ORDEN.items():
                for cod, conc, niv in EST:
                    p = int(bases[cod]*fac)
                    d = int(p*rng.uniform(0.55, 1.22))
                    if rng.random() < 0.06: d = 0
                    rows.append({
                        "Establecimiento": est,
                        "Fecha": f"{mes} {yr}",
                        "Nivel": niv,
                        "Concepto Presupuestario": conc,
                        "Ley de Presupuestos": p,
                        "Devengado": d,
                        "Compromiso": int(d*rng.uniform(0.93, 1.05)),
                        "Saldo por Aplicar": max(0, p-d),
                        "Efectivo": int(d*rng.uniform(0.88, 1.0)),
                    })
    return pd.DataFrame(rows)

df_full = cargar_datos()
arbol   = arbol_navegacion(df_full)

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — árbol de conceptos
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        "<div style='padding:16px 0 8px'>"
        "<p style='font-family:Plus Jakarta Sans,sans-serif;font-size:1rem;"
        "font-weight:800;color:#fff;margin:0 0 2px'>Árbol de Conceptos</p>"
        "<p style='font-size:.7rem;color:rgba(255,255,255,.45);margin:0;"
        "text-transform:uppercase;letter-spacing:.08em'>Navegación Jerárquica</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    raices  = arbol.get("__raices__", [])
    n1_sel  = st.selectbox("Capítulo (N1)", ["— Todos —"] + raices)
    n2_opts = arbol.get(n1_sel, []) if n1_sel != "— Todos —" else []
    n2_sel  = st.selectbox("Subcapítulo (N2)", ["— Todos —"] + n2_opts) if n2_opts else None
    n3_opts = arbol.get(n2_sel, []) if n2_sel and n2_sel != "— Todos —" else []
    n3_sel  = st.selectbox("Partida (N3)", ["— Todos —"] + n3_opts) if n3_opts else None
    st.markdown("---")
    solo_hojas = st.checkbox("Solo nodos hoja (sin doble conteo)", value=True)
    n_reg = len(df_full)
    n_per = df_full["Fecha"].nunique() if "Fecha" in df_full.columns else 0
    st.markdown(
        f"<p style='font-size:.7rem;color:rgba(255,255,255,.35)'>"
        f"{n_reg:,} registros · {n_per} períodos</p>",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
bc = " › ".join(filter(None, [
    n1_sel if n1_sel != "— Todos —" else "Todos los Capítulos",
    n2_sel if n2_sel and n2_sel != "— Todos —" else None,
    n3_sel if n3_sel and n3_sel != "— Todos —" else None,
]))
st.markdown(
    f"<div style='background:linear-gradient(135deg,#001C41 0%,#0D5FA8 100%);"
    f"border-radius:14px;padding:22px 28px;margin-bottom:16px;"
    f"position:relative;overflow:hidden'>"
    f"<div style='position:absolute;top:-40px;right:-40px;width:180px;height:180px;"
    f"background:radial-gradient(circle,rgba(19,138,236,.2) 0%,transparent 70%);"
    f"border-radius:50%'></div>"
    f"<h1 style='font-family:Plus Jakarta Sans,sans-serif;font-size:1.45rem;"
    f"font-weight:800;color:#fff;margin:0 0 4px;position:relative'>"
    f"Análisis Jerárquico Presupuestario</h1>"
    f"<p style='font-size:.8rem;color:rgba(255,255,255,.6);margin:0;position:relative'>{bc}</p>"
    f"</div>",
    unsafe_allow_html=True,
)

# ════════════════════════════════════════════════════════════════════════════
# ██  PANEL DE FILTROS INLINE  ██
# ════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='filter-panel'>", unsafe_allow_html=True)
st.markdown("<div class='filter-row-title'>Filtros de Análisis</div>", unsafe_allow_html=True)

# — Fila 1: Establecimiento | Año | Desde | Hasta | Niveles —
r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([1.4, 0.9, 0.9, 0.9, 1.4])

with r1c1:
    est_opts = sorted(df_full["Establecimiento"].dropna().unique()) \
               if "Establecimiento" in df_full.columns else []
    est_sel  = st.multiselect("🏥 Establecimiento", est_opts, default=est_opts, key="f_est")

with r1c2:
    anios_disp = sorted(df_full["Anio"].dropna().unique().astype(int)) \
                 if "Anio" in df_full.columns else []
    anios_sel  = st.multiselect("📅 Año", anios_disp, default=anios_disp, key="f_anio")

fechas_df   = (df_full.drop_duplicates(["Fecha","Mes_Num","Anio"])
               .sort_values(["Anio","Mes_Num"]))
fechas_list = fechas_df["Fecha"].tolist() if not fechas_df.empty else []

with r1c3:
    f_desde = st.selectbox("📆 Desde", fechas_list, index=0, key="f_desde") \
              if fechas_list else None

with r1c4:
    f_hasta = st.selectbox("📆 Hasta", fechas_list,
                           index=len(fechas_list)-1, key="f_hasta") \
              if fechas_list else None

with r1c5:
    niveles_disp = sorted([int(n) for n in df_full["Nivel"].dropna().unique()])
    NIV_LABEL    = {1:"N1 · Capítulo",2:"N2 · Subcapítulo",3:"N3 · Partida",
                    4:"N4 · Subpartida",5:"N5 · Detalle"}
    niv_opts     = [NIV_LABEL.get(n, f"N{n}") for n in niveles_disp]
    niv_map      = {NIV_LABEL.get(n, f"N{n}"): n for n in niveles_disp}
    niv_sel_lbl  = st.multiselect("🌿 Niveles Jerárquicos", niv_opts,
                                   default=niv_opts, key="f_niv")
    niv_sel      = [niv_map[l] for l in niv_sel_lbl] if niv_sel_lbl else niveles_disp

# — Fila 2: Profundidad | Estado semáforo | chips activos —
r2c1, r2c2, r2c3 = st.columns([0.9, 1.4, 2.2])

with r2c1:
    nivel_rep = st.select_slider(
        "📊 Profundidad del reporte",
        options=[1,2,3,4,5], value=2, key="f_nivel_rep",
    )

with r2c2:
    estados_sel = st.multiselect(
        "🚦 Filtrar por Estado Semáforo",
        SEM_ORDEN, default=SEM_ORDEN, key="f_estado",
    )

with r2c3:
    chips = []
    if est_opts and len(est_sel) < len(est_opts):
        chips += [f"🏥 {e}" for e in est_sel]
    if anios_disp and len(anios_sel) < len(anios_disp):
        chips += [f"📅 {a}" for a in anios_sel]
    if f_desde and fechas_list and \
       (f_desde != fechas_list[0] or f_hasta != fechas_list[-1]):
        chips.append(f"📆 {f_desde} → {f_hasta}")
    if niveles_disp and len(niv_sel) < len(niveles_disp):
        chips += [f"🌿 N{n}" for n in niv_sel]
    if len(estados_sel) < len(SEM_ORDEN):
        chips += [f"🚦 {e}" for e in estados_sel]
    if chips:
        chips_html = "".join(f"<span class='chip'>{c}</span>" for c in chips)
        st.markdown(
            f"<div style='margin-top:26px'>"
            f"<span style='font-size:.68rem;color:#94A3B8;font-weight:600;"
            f"text-transform:uppercase;letter-spacing:.05em'>Filtros activos:</span>"
            f"<div style='margin-top:4px'>{chips_html}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# FILTRADO GLOBAL
# ════════════════════════════════════════════════════════════════════════════
def en_rango(df, desde, hasta, lista):
    if not desde or not hasta or not lista:
        return df
    i0 = lista.index(desde) if desde in lista else 0
    i1 = lista.index(hasta)  if hasta  in lista else len(lista) - 1
    return df[df["Fecha"].isin(lista[i0:i1+1])]

df_work = df_full.copy()
if est_sel and "Establecimiento" in df_work.columns:
    df_work = df_work[df_work["Establecimiento"].isin(est_sel)]
if anios_sel and "Anio" in df_work.columns:
    df_work = df_work[df_work["Anio"].isin(anios_sel)]
df_work = en_rango(df_work, f_desde, f_hasta, fechas_list)
# Nivel: NO filtrar aquí para que el treemap siempre tenga raíces N1
# (se aplica por pestaña donde corresponda)

# Árbol jerárquico
concepto_raiz = None
if n3_sel and n3_sel != "— Todos —":   concepto_raiz = n3_sel
elif n2_sel and n2_sel != "— Todos —": concepto_raiz = n2_sel
elif n1_sel and n1_sel != "— Todos —": concepto_raiz = n1_sel

df_arbol_full = filtrar_arbol(df_work, concepto_raiz) if concepto_raiz else df_work.copy()

# Versión filtrada por niveles y estado para las vistas que lo necesitan
df_arbol = df_arbol_full.copy()
if niv_sel and "Nivel" in df_arbol.columns:
    df_arbol = df_arbol[df_arbol["Nivel"].isin(niv_sel)]
if estados_sel and "Estado_Semaforo" in df_arbol.columns:
    df_arbol = df_arbol[df_arbol["Estado_Semaforo"].isin(estados_sel)]

kpis = metricas_arbol(df_arbol, solo_hojas=solo_hojas)
fecha_orden = []
if "Fecha" in df_arbol_full.columns and "Anio" in df_arbol_full.columns:
    fecha_orden = (df_arbol_full.drop_duplicates("Fecha")
                   .sort_values(["Anio","Mes_Num"])["Fecha"].tolist())

# ════════════════════════════════════════════════════════════════════════════
# KPIs
# ════════════════════════════════════════════════════════════════════════════
pct_ej  = kpis.get("pct_ejecucion")
pct_var = kpis.get("pct_variacion")
c_ej    = "#16A34A" if (pct_ej or 0) <= 80 else \
          ("#B45309" if (pct_ej or 0) <= 100 else "#C0392B")
c_var   = "#C0392B" if (pct_var or 0) > 0 else "#16A34A"

cols_kpi = st.columns(6)
kpi_card(cols_kpi[0], "#138AEC", "Devengado",   fmt(kpis["devengado_total"]),
         f"{kpis['n_periodos']} períodos")
kpi_card(cols_kpi[1], "#0D7377", "Presupuesto", fmt(kpis["presupuesto_total"]),
         "Ley de Presupuestos")
kpi_card(cols_kpi[2], "#B45309", "Disponible",  fmt(kpis["disponible"]),
         "Saldo por ejecutar")
kpi_card(cols_kpi[3], c_ej,      "% Ejecución", pct_fmt(pct_ej),
         "Devengado / Presupuesto")
kpi_card(cols_kpi[4], "#138AEC", "Compromiso",  fmt(kpis["compromiso_total"]),
         "Total comprometido")
kpi_card(cols_kpi[5], c_var,     "Variación",   pct_fmt(pct_var),
         "vs Presupuesto")
st.markdown("<br>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌳  Árbol Jerárquico",
    "🚦  Semáforos de Control",
    "📈  Evolución Temporal",
    "📊  Reporte de Control",
    "🔍  Análisis por Nivel",
    "⚖  Variación MoM",
])

# ╔═══════════════════════════════════════════════════╗
# ║  TAB 1 — ÁRBOL JERÁRQUICO                        ║
# ╚═══════════════════════════════════════════════════╝
with tab1:
    # Usamos df_arbol_full (SIN filtro de nivel) para que el treemap
    # siempre tenga raíces N1 disponibles como padres.
    df_tm = df_arbol_full.copy() if not df_arbol_full.empty else df_arbol.copy()

    if df_tm.empty:
        st.warning("Sin datos para los filtros aplicados.")
    else:
        sec("Estructura Jerárquica · Devengado Acumulado",
            f"Niveles 1 a {min(nivel_rep, 4)}")

        # Construir treemap agrupando por nivel 1 → nivel rep
        depth = min(nivel_rep, 4)
        frames = []
        for nv in range(1, depth + 1):
            sub = df_tm[df_tm["Nivel"] == nv].copy()
            if sub.empty:
                continue
            agg = sub.groupby("Concepto Presupuestario",
                              as_index=False)["Devengado"].sum()
            agg["nv"] = nv
            # Etiqueta del padre (nivel anterior)
            col_p = f"Etiqueta_N{nv-1}" if nv > 1 else None
            if col_p and col_p in sub.columns:
                pm = (sub.drop_duplicates("Concepto Presupuestario")
                      .set_index("Concepto Presupuestario")[col_p].to_dict())
                agg["parent"] = agg["Concepto Presupuestario"].map(pm).fillna("")
            else:
                agg["parent"] = ""
            frames.append(agg)

        if frames:
            tm = (pd.concat(frames, ignore_index=True)
                  .drop_duplicates("Concepto Presupuestario"))
            tm["Devengado"] = tm["Devengado"].clip(lower=0)

            col_tree, col_sun = st.columns([1.5, 1])

            with col_tree:
                fig_tm = go.Figure(go.Treemap(
                    labels  = tm["Concepto Presupuestario"].tolist(),
                    parents = tm["parent"].tolist(),
                    values  = tm["Devengado"].tolist(),
                    textinfo= "label+value+percent parent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Devengado: $%{value:,.0f}<br>"
                        "%{percentParent:.1%} del padre"
                        "<extra></extra>"
                    ),
                    marker=dict(
                        colorscale=[[0,"#DBEAFE"],[0.5,"#138AEC"],[1,"#001C41"]],
                        showscale=True,
                        colorbar=dict(thickness=8, len=0.45,
                                      tickfont=dict(size=9)),
                    ),
                    maxdepth=3,
                    pathbar=dict(visible=True),
                ))
                fig_tm.update_layout(
                    paper_bgcolor="#fff", height=460,
                    margin=dict(l=0, r=0, t=10, b=10),
                )
                st.plotly_chart(fig_tm, use_container_width=True)

            with col_sun:
                # Sunburst N1→N2 con df_arbol_full
                sub_sun = df_tm[df_tm["Nivel"].isin([1, 2])].copy()
                if not sub_sun.empty:
                    sa = sub_sun.groupby(
                        ["Concepto Presupuestario","Nivel"],
                        as_index=False)["Devengado"].sum()
                    sa["Devengado"] = sa["Devengado"].clip(lower=0)
                    if "Etiqueta_N1" in sub_sun.columns:
                        p2 = (sub_sun.drop_duplicates("Concepto Presupuestario")
                              .set_index("Concepto Presupuestario")["Etiqueta_N1"]
                              .to_dict())
                        sa["parent"] = sa.apply(
                            lambda r: p2.get(r["Concepto Presupuestario"], "")
                                      if r["Nivel"] > 1 else "", axis=1)
                    else:
                        sa["parent"] = ""
                    fig_sun = go.Figure(go.Sunburst(
                        labels       = sa["Concepto Presupuestario"].tolist(),
                        parents      = sa["parent"].tolist(),
                        values       = sa["Devengado"].tolist(),
                        branchvalues = "total",
                        hovertemplate= (
                            "<b>%{label}</b><br>"
                            "$%{value:,.0f}<extra></extra>"
                        ),
                        marker=dict(colorscale="Blues"),
                        textfont=dict(size=10),
                    ))
                    fig_sun.update_layout(
                        paper_bgcolor="#fff", height=460,
                        margin=dict(l=0, r=0, t=35, b=10),
                        title=dict(
                            text="N1 → N2 · Proporción",
                            font=dict(family="Plus Jakarta Sans",
                                      size=12, color="#001C41"),
                            x=0.5,
                        ),
                    )
                    st.plotly_chart(fig_sun, use_container_width=True)
        else:
            st.info("Sin datos disponibles para el treemap.")

# ╔═══════════════════════════════════════════════════╗
# ║  TAB 2 — SEMÁFOROS DE CONTROL                    ║
# ╚═══════════════════════════════════════════════════╝
with tab2:
    if df_arbol.empty or "Estado_Semaforo" not in df_arbol.columns:
        st.warning("Sin datos de semáforo disponibles.")
    else:
        # Filtrar al nivel del reporte
        df_ns = filtrar_nivel(df_arbol, nivel_rep)
        if df_ns.empty:
            max_nv = int(df_arbol["Nivel"].max())
            df_ns  = filtrar_nivel(df_arbol, max_nv)

        sem_cnt = df_ns["Estado_Semaforo"].value_counts().to_dict() \
                  if not df_ns.empty else {}

        # ── Contadores globales ──────────────────────────────────
        cnt_cols = st.columns(len(SEM_ORDEN))
        for i, estado in enumerate(SEM_ORDEN):
            cnt   = sem_cnt.get(estado, 0)
            color = SEM_COLOR.get(estado, "#94A3B8")
            emoji = SEM_EMOJI.get(estado, "—")
            bg    = SEM_BG.get(estado, "#F8FAFC")
            with cnt_cols[i]:
                st.markdown(
                    f"<div style='background:{bg};border:1px solid #E2E8F0;"
                    f"border-top:3px solid {color};border-radius:10px;"
                    f"padding:14px 10px;text-align:center'>"
                    f"<div style='font-size:1.3rem'>{emoji}</div>"
                    f"<div style='font-family:Plus Jakarta Sans,sans-serif;"
                    f"font-size:1.5rem;font-weight:800;color:{color};"
                    f"margin:4px 0'>{cnt}</div>"
                    f"<div style='font-size:.65rem;font-weight:700;color:#94A3B8;"
                    f"text-transform:uppercase;letter-spacing:.06em'>{estado}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Tabla detallada ──────────────────────────────────────
        sec("Tabla Detallada por Estado Semáforo",
            f"Nivel {nivel_rep} · ordenado por criticidad")

        if not df_ns.empty:
            grp = ["Concepto Presupuestario", "Estado_Semaforo"]
            if "Establecimiento" in df_ns.columns:
                grp.append("Establecimiento")

            agg_d = {"Devengado": ("Devengado","sum"),
                     "Presupuesto": ("Ley de Presupuestos","sum")}
            if "Compromiso" in df_ns.columns:
                agg_d["Compromiso"] = ("Compromiso","sum")

            tbl = df_ns.groupby(grp, dropna=False).agg(**agg_d).reset_index()
            sp  = tbl["Presupuesto"].replace(0, np.nan)
            tbl["Disponible"]   = tbl["Presupuesto"] - tbl["Devengado"]
            tbl["% Ejecución"]  = (tbl["Devengado"] / sp * 100).round(2)
            tbl["Variación $"]  = tbl["Devengado"] - tbl["Presupuesto"]
            tbl["% Variación"]  = ((tbl["Devengado"]-tbl["Presupuesto"]) / sp * 100).round(2)

            # Orden criticidad
            ord_map = {e: i for i, e in enumerate(SEM_ORDEN)}
            tbl["_ord"] = tbl["Estado_Semaforo"].map(ord_map).fillna(99)
            tbl = tbl.sort_values(["_ord", "% Ejecución"],
                                  ascending=[True, False]).drop(columns=["_ord"])

            # Filtro rápido dentro de la tabla
            est_tab = [e for e in SEM_ORDEN if e in tbl["Estado_Semaforo"].unique()]
            col_ft, _ = st.columns([2, 3])
            with col_ft:
                est_flt = st.multiselect(
                    "Filtrar tabla por estado",
                    est_tab, default=est_tab, key="sem_tbl_flt",
                )
            vis = tbl[tbl["Estado_Semaforo"].isin(est_flt)].copy() if est_flt else tbl.copy()

            # Emoji en la columna Estado
            vis["Estado"] = vis["Estado_Semaforo"].apply(
                lambda e: f"{SEM_EMOJI.get(e,'—')} {e}"
            )

            show_cols = ["Concepto Presupuestario", "Estado"]
            if "Establecimiento" in vis.columns:
                show_cols.append("Establecimiento")
            show_cols += ["Presupuesto","Devengado","Disponible",
                          "% Ejecución","Variación $","% Variación"]
            if "Compromiso" in vis.columns:
                idx = show_cols.index("Disponible") + 1
                show_cols.insert(idx, "Compromiso")

            disp = vis[[c for c in show_cols if c in vis.columns]].copy()
            for mc in ["Presupuesto","Devengado","Disponible","Compromiso","Variación $"]:
                if mc in disp.columns:
                    disp[mc] = disp[mc].apply(fmt)
            for pc in ["% Ejecución","% Variación"]:
                if pc in disp.columns:
                    disp[pc] = disp[pc].apply(pct_fmt)

            st.dataframe(disp, use_container_width=True, hide_index=True,
                         height=min(38*len(disp)+44, 540))

            csv_s = vis.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                "⬇ Descargar tabla semáforo CSV",
                csv_s, f"semaforo_N{nivel_rep}.csv", "text/csv",
            )

        # ── Gráficos distribución ────────────────────────────────
        sec("Distribución del Devengado por Estado")
        cg1, cg2 = st.columns(2)

        with cg1:
            if not df_ns.empty:
                gs = (df_ns.groupby("Estado_Semaforo")["Devengado"]
                      .sum().reset_index()
                      .sort_values("Devengado", ascending=True))
                gs["lbl"] = gs["Estado_Semaforo"].apply(
                    lambda e: f"{SEM_EMOJI.get(e,'')} {e}")
                fgs = go.Figure(go.Bar(
                    y=gs["lbl"], x=gs["Devengado"], orientation="h",
                    marker=dict(color=[SEM_COLOR.get(e,"#94A3B8")
                                       for e in gs["Estado_Semaforo"]]),
                    text=[fmt(v) for v in gs["Devengado"]],
                    textposition="outside", textfont=dict(size=10),
                ))
                lo = mkfig(280, "Devengado Total por Estado", False)
                lo["yaxis"] = dict(showgrid=False, tickfont=dict(size=10))
                lo["bargap"] = 0.35
                fgs.update_layout(**lo)
                st.plotly_chart(fgs, use_container_width=True)

        with cg2:
            if not df_ns.empty:
                gp = (df_ns.groupby("Estado_Semaforo")["Devengado"]
                      .sum().reset_index())
                gp = gp[gp["Devengado"] > 0]
                gp["lbl"] = gp["Estado_Semaforo"].apply(
                    lambda e: f"{SEM_EMOJI.get(e,'')} {e}")
                fgp = go.Figure(go.Pie(
                    labels=gp["lbl"], values=gp["Devengado"], hole=0.5,
                    marker=dict(colors=[SEM_COLOR.get(e,"#94A3B8")
                                        for e in gp["Estado_Semaforo"]]),
                    textfont=dict(size=11),
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "$%{value:,.0f}<br>%{percent}<extra></extra>"
                    ),
                ))
                fgp.update_layout(
                    paper_bgcolor="#fff", height=280,
                    margin=dict(l=8, r=8, t=30, b=8),
                    showlegend=True,
                    legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)",
                                orientation="v", x=1.02, y=0.5),
                )
                st.plotly_chart(fgp, use_container_width=True)

# ╔═══════════════════════════════════════════════════╗
# ║  TAB 3 — EVOLUCIÓN TEMPORAL                      ║
# ╚═══════════════════════════════════════════════════╝
with tab3:
    if df_arbol.empty:
        st.warning("Sin datos para los filtros seleccionados.")
    else:
        pp = kpis.get("por_periodo", pd.DataFrame())
        ca, cb = st.columns(2)
        with ca:
            if not pp.empty:
                fe = go.Figure()
                fe.add_trace(go.Scatter(
                    x=pp["Fecha"], y=pp.get("Presupuesto", []),
                    name="Presupuesto", mode="lines",
                    line=dict(color="#CBD5E1", width=2, dash="dot"),
                ))
                fe.add_trace(go.Scatter(
                    x=pp["Fecha"], y=pp["Devengado"],
                    name="Devengado", fill="tozeroy", mode="lines+markers",
                    line=dict(color="#138AEC", width=2.5),
                    fillcolor="rgba(19,138,236,0.08)",
                    marker=dict(size=5),
                ))
                fe.update_layout(**mkfig(300, "Devengado vs Presupuesto · Total"))
                st.plotly_chart(fe, use_container_width=True)
        with cb:
            if not pp.empty and "Pct_Ejecucion" in pp.columns:
                cb_colors = [
                    "#16A34A" if p <= 80 else ("#B45309" if p <= 100 else "#C0392B")
                    for p in pp["Pct_Ejecucion"].fillna(0)
                ]
                fb = go.Figure(go.Bar(
                    x=pp["Fecha"], y=pp["Pct_Ejecucion"],
                    marker_color=cb_colors,
                    text=[f"{p:.1f}%" for p in pp["Pct_Ejecucion"].fillna(0)],
                    textposition="outside", textfont=dict(size=9),
                ))
                fb.add_hline(y=100, line_color="#001C41",
                             line_dash="dot", line_width=1.5)
                lo_b = mkfig(300, "% Ejecución por Período", False)
                lo_b["yaxis"] = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0",
                                     showgrid=True, ticksuffix="%")
                fb.update_layout(**lo_b)
                st.plotly_chart(fb, use_container_width=True)

        sec("Devengado por Nivel Jerárquico")
        if "Nivel" in df_arbol.columns:
            dnt = (df_arbol.groupby(["Fecha","Nivel","Anio","Mes_Num"])["Devengado"]
                   .sum().reset_index().sort_values(["Anio","Mes_Num"])
                   .astype({"Nivel": str}))
            if not dnt.empty:
                fn = px.line(dnt, x="Fecha", y="Devengado", color="Nivel",
                             markers=True, color_discrete_sequence=PAL,
                             category_orders={"Fecha": fecha_orden},
                             labels={"Devengado":"($)","Fecha":"","Nivel":"Nivel"})
                fn.update_traces(line_width=1.8, marker_size=4)
                fn.update_layout(**mkfig(280, ""))
                st.plotly_chart(fn, use_container_width=True)

        sec("Composición del Devengado por Capítulo")
        if "Etiqueta_N1" in df_arbol.columns:
            sh  = df_arbol[df_arbol["Es_Hoja"]] \
                  if "Es_Hoja" in df_arbol.columns else df_arbol
            d1t = (sh.groupby(["Fecha","Etiqueta_N1","Anio","Mes_Num"])["Devengado"]
                   .sum().reset_index().sort_values(["Anio","Mes_Num"]))
            if not d1t.empty:
                fa = px.area(d1t, x="Fecha", y="Devengado", color="Etiqueta_N1",
                             color_discrete_sequence=PAL,
                             category_orders={"Fecha": fecha_orden},
                             labels={"Devengado":"($)","Fecha":"","Etiqueta_N1":"Capítulo"})
                fa.update_layout(**mkfig(260, ""))
                st.plotly_chart(fa, use_container_width=True)

# ╔═══════════════════════════════════════════════════╗
# ║  TAB 4 — REPORTE DE CONTROL                      ║
# ╚═══════════════════════════════════════════════════╝
with tab4:
    st.markdown(
        f"<div style='background:#EFF6FF;border-left:3px solid #138AEC;"
        f"border-radius:0 8px 8px 0;padding:10px 14px;font-size:.82rem;"
        f"color:#1E40AF;margin-bottom:14px'>"
        f"Nivel {nivel_rep} · Solo hojas: {'Sí' if solo_hojas else 'No'} · "
        f"{len(est_sel)} est. · Años: {', '.join(map(str,anios_sel)) or 'Todos'}"
        f"</div>",
        unsafe_allow_html=True,
    )
    rep = reporte_control(df_arbol, nivel_reporte=nivel_rep,
                          agrupar_por=["Establecimiento","Fecha"])
    if rep.empty:
        st.info(f"Sin datos para Nivel {nivel_rep}.")
    else:
        show = ["Concepto Presupuestario"]
        for lv in range(1, nivel_rep):
            ec = f"Etiqueta_N{lv}"
            if ec in rep.columns: show.append(ec)
        for c in ["Establecimiento","Fecha","Ley de Presupuestos","Devengado",
                  "Compromiso","Disponible","Pct_Ejecucion","Pct_Variacion","Estado"]:
            if c in rep.columns: show.append(c)
        rd = rep[[c for c in show if c in rep.columns]].copy()
        for mc in ["Ley de Presupuestos","Devengado","Compromiso","Disponible"]:
            if mc in rd.columns: rd[mc] = rd[mc].apply(fmt)
        for pc in ["Pct_Ejecucion","Pct_Variacion"]:
            if pc in rd.columns: rd[pc] = rd[pc].apply(pct_fmt)
        st.dataframe(rd, use_container_width=True, hide_index=True)
        csv_r = rep.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇ Descargar Reporte CSV",
                           csv_r, f"reporte_N{nivel_rep}.csv", "text/csv")

# ╔═══════════════════════════════════════════════════╗
# ║  TAB 5 — ANÁLISIS POR NIVEL                      ║
# ╚═══════════════════════════════════════════════════╝
with tab5:
    nd = st.select_slider("Seleccionar nivel de análisis",
                          options=[1,2,3,4,5], value=nivel_rep, key="nd_sl")
    dn = filtrar_nivel(df_arbol, nd) if not df_arbol.empty else pd.DataFrame()

    if dn.empty:
        st.info(f"Sin datos para Nivel {nd}.")
    else:
        agg_d = {"Dev":("Devengado","sum"),
                 "Pres":("Ley de Presupuestos","sum")}
        if "Compromiso" in dn.columns:
            agg_d["Comp"] = ("Compromiso","sum")
        an = dn.groupby("Concepto Presupuestario").agg(**agg_d).reset_index()
        if "Comp" not in an.columns: an["Comp"] = 0
        an["pct"] = (an["Dev"] / an["Pres"].replace(0,np.nan)*100).round(2)
        an["var"] = an["Dev"] - an["Pres"]
        an = an.sort_values("Dev", ascending=False)
        an["cc"] = an["Concepto Presupuestario"].str[:45]

        cc, cd = st.columns(2)
        with cc:
            bc5 = ["#16A34A" if p<=80 else ("#B45309" if p<=100 else "#C0392B")
                   for p in an["pct"].fillna(0)]
            f5 = go.Figure(go.Bar(
                y=an["cc"].head(15), x=an["pct"].head(15),
                orientation="h", marker_color=bc5[:15],
                text=[f"{p:.1f}%" for p in an["pct"].head(15).fillna(0)],
                textposition="outside", textfont=dict(size=9),
            ))
            f5.add_vline(x=100, line_color="#001C41", line_dash="dot", line_width=1.5)
            lo5 = mkfig(400, f"% Ejecución · Nivel {nd}", False)
            pm = float(an["pct"].max()) if not an.empty else 130
            lo5["xaxis"] = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0",
                                showgrid=True, ticksuffix="%",
                                range=[0, max(130, pm+15)])
            lo5["yaxis"] = dict(showgrid=False, tickfont=dict(size=9))
            lo5["bargap"] = 0.3
            f5.update_layout(**lo5)
            st.plotly_chart(f5, use_container_width=True)

        with cd:
            at = an.head(10).copy()
            cv6 = ["#C0392B" if v > 0 else "#16A34A" for v in at["var"]]
            f6 = go.Figure(go.Bar(
                x=at["cc"], y=at["var"],
                marker=dict(color=cv6),
                text=[fmt(v) for v in at["var"]],
                textposition="outside", textfont=dict(size=8),
            ))
            f6.add_hline(y=0, line_color="#001C41",
                         line_dash="dot", line_width=1.5)
            lo6 = mkfig(400, f"Variación Dev−Pres · N{nd}", False)
            lo6["xaxis"] = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0",
                                showgrid=False, tickangle=-35,
                                tickfont=dict(size=8))
            f6.update_layout(**lo6)
            st.plotly_chart(f6, use_container_width=True)

        sec("Dispersión: Presupuesto vs Devengado (tamaño = compromiso)")
        mx = float(max(an[["Pres","Dev"]].max().max(), 1))
        f7 = px.scatter(
            an, x="Pres", y="Dev",
            size=an["Comp"].clip(lower=0)+1,
            color="pct",
            hover_name="Concepto Presupuestario",
            color_continuous_scale=["#16A34A","#B45309","#C0392B"],
            labels={"Pres":"Presupuesto ($)","Dev":"Devengado ($)","pct":"% Ejec."},
            size_max=40,
        )
        f7.add_trace(go.Scatter(
            x=[0,mx], y=[0,mx], mode="lines",
            line=dict(color="#CBD5E1", dash="dot", width=1.5),
            name="100% ejecución", showlegend=True,
        ))
        f7.update_layout(**mkfig(320, ""))
        st.plotly_chart(f7, use_container_width=True)

# ╔═══════════════════════════════════════════════════╗
# ║  TAB 6 — VARIACIÓN MOM                           ║
# ╚═══════════════════════════════════════════════════╝
with tab6:
    st.markdown(
        "<div style='background:#EFF6FF;border-left:3px solid #138AEC;"
        "border-radius:0 8px 8px 0;padding:10px 14px;font-size:.82rem;"
        "color:#1E40AF;margin-bottom:14px'>"
        "Variación mes a mes. Solo nodos hoja para evitar doble conteo.</div>",
        unsafe_allow_html=True,
    )
    sm = variacion_mom(df_arbol)
    cm1, cm2 = st.columns(2)
    with cm1:
        if not sm.empty:
            cma = ["#16A34A" if v >= 0 else "#C0392B"
                   for v in sm["Variacion_Abs"].fillna(0)]
            fm1 = go.Figure()
            fm1.add_trace(go.Bar(
                x=sm["Fecha"], y=sm["Variacion_Abs"],
                marker_color=cma,
                text=[fmt(v) for v in sm["Variacion_Abs"].fillna(0)],
                textposition="outside", textfont=dict(size=8),
            ))
            fm1.add_hline(y=0, line_color="#001C41", line_width=1)
            fm1.update_layout(**mkfig(300, "Variación Absoluta MoM", False))
            st.plotly_chart(fm1, use_container_width=True)
    with cm2:
        if not sm.empty and "Variacion_Pct" in sm.columns:
            cmp = ["#16A34A" if v >= 0 else "#C0392B"
                   for v in sm["Variacion_Pct"].fillna(0)]
            fm2 = go.Figure(go.Bar(
                x=sm["Fecha"], y=sm["Variacion_Pct"],
                marker_color=cmp,
                text=[f"{v:+.1f}%" for v in sm["Variacion_Pct"].fillna(0)],
                textposition="outside", textfont=dict(size=8),
            ))
            fm2.add_hline(y=0, line_color="#001C41", line_width=1)
            lo_m2 = mkfig(300, "Variación Porcentual MoM (%)", False)
            lo_m2["yaxis"] = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0",
                                  showgrid=True, ticksuffix="%")
            fm2.update_layout(**lo_m2)
            st.plotly_chart(fm2, use_container_width=True)

    if not sm.empty:
        sec("Detalle Período a Período")
        mt = sm[["Fecha","Devengado","Dev_Anterior",
                  "Variacion_Abs","Variacion_Pct"]].copy()
        mt["Devengado"]     = mt["Devengado"].apply(fmt)
        mt["Dev_Anterior"]  = mt["Dev_Anterior"].apply(
            lambda v: fmt(v) if pd.notna(v) else "—")
        mt["Variacion_Abs"] = mt["Variacion_Abs"].apply(
            lambda v: fmt(v) if pd.notna(v) else "—")
        mt["Variacion_Pct"] = mt["Variacion_Pct"].apply(
            lambda v: f"{v:+.1f}%" if pd.notna(v) else "—")
        mt.columns = ["Período","Devengado","Período Anterior",
                      "Var. Absoluta","Var. %"]
        st.dataframe(mt, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    "<div style='border-top:1px solid #E2E8F0;margin-top:36px;padding-top:14px;"
    "display:flex;justify-content:space-between'>"
    "<span style='font-size:.72rem;color:#94A3B8'>"
    "Dashboard Jerárquico v3.0 · jerarquia_presupuestaria.py</span>"
    "<span style='font-size:.72rem;color:#94A3B8'>"
    "Solo nodos hoja activo · Sin doble conteo</span>"
    "</div>",
    unsafe_allow_html=True,
)