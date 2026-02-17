import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# Importamos tus cargadores
from data.data_loader import load_pac26_data
import api.OC_data_loader as loader_oc
from style.ui import cargar_css

cargar_css()


# =============================================================================
# 0. FUNCIONES DE APOYO (LÓGICA DE CRUCE Y LINKS)
# =============================================================================

@st.cache_data(ttl=3600)
def load_pac_master():
    """Carga el archivo maestro consolidado generado previamente."""
    file_path = os.path.join("data", "data_pac", "OCPAC_Maestro.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path, dtype={"OC Asociada PAC": str, "ID Proyecto": str})
    return pd.DataFrame(columns=["ID Proyecto", "OC Asociada PAC"])

def enriquecer_datos_con_pac(df_principal, df_maestro):
    """Cruce vectorizado para identificar OCs en el plan."""
    df = df_principal.copy()
    col_oc_compras = "CodigoOC"
    
    # Normalización de llaves
    keys_compras = df[col_oc_compras].astype(str).str.strip().str.upper()
    keys_pac = df_maestro["OC Asociada PAC"].astype(str).str.strip().str.upper()
    
    # Columna indicadora
    df["PAC"] = "No Enlazada"
    mask = keys_compras.isin(keys_pac)
    df.loc[mask, "PAC"] = "Enlazada"
    
    # Traer ID Proyecto
    df_maestro_clean = df_maestro.copy()
    df_maestro_clean["key_tmp"] = keys_pac
    
    df = df.merge(
        df_maestro_clean[["key_tmp", "ID Proyecto"]],
        left_on=keys_compras,
        right_on="key_tmp",
        how="left"
    ).drop(columns=["key_tmp"])
    
    return df

def generar_link_mp(codigo_oc):
    """Genera el link directo a la orden de compra en Mercado Público"""
    base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
    return f"{base_url}{codigo_oc}"


def categorizar_ejecucion(row):
    porcentaje = row["% Ejecución"]
    ejecutado = row["Monto_Ejecutado"]
    
    if ejecutado == 0:
        return "🔴 Sin Compras"
    elif porcentaje < 50:
        return "🟡 Subejecución crítica"
    elif 50 <= porcentaje <= 79:
        return "🟢 Subejecución moderada"
    elif 80 <= porcentaje <= 100:
        return "✅ Ejecución eficiente"
    else: # > 100
        return "💹 Sobreejecución"


# =============================================================================
# 1. CARGA DE DATOS
# =============================================================================
# A. Carga del Plan (Excel Original)
df_planner_pac = load_pac26_data()

# B. Carga de Ejecución (OCs + Maestro)
@st.cache_data(ttl=3600, show_spinner="Cargando Planificación y Ejecución...") 
def obtener_datos_ejecucion():
    df_OCres, df_OCdet = loader_oc.cargar_maestros_oc()
    df_pac_maestro = load_pac_master()
    return df_OCres, df_OCdet, df_pac_maestro

try:
    df_raw_res, df_oc_det, df_pac_maestro = obtener_datos_ejecucion()
    
    # --- PROCESAMIENTO OC ---
    if not df_raw_res.empty:
        # 1. Enriquecer con ID Proyecto
        df_oc_res = enriquecer_datos_con_pac(df_raw_res, df_pac_maestro)
        
        # 2. Generar LINK (Requerimiento 2)
        df_oc_res["Link"] = df_oc_res["CodigoOC"].apply(generar_link_mp)
        
        # 3. Normalización Fechas y Tipos
        cols_fecha = ['FechaCreacion', 'FechaEnvio', 'FechaAceptacion', 'FechaCancelacion']
        for col in cols_fecha:
            df_oc_res[col] = pd.to_datetime(df_oc_res[col], errors='coerce')
            
        df_oc_res['TotalBruto'] = pd.to_numeric(df_oc_res['TotalBruto'], errors='coerce').fillna(0)
    else:
        df_oc_res = pd.DataFrame()

except Exception as e:
    st.error(f"❌ Error crítico en carga de datos: {e}")
    st.stop()

# =============================================================================
# HEADER
# =============================================================================
st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">🚀 Panel de Control: Ejecución PAC 2026</div>
        <div style="font-size: 15px; opacity: 0.9;">Seguimiento Planificado vs. Real (Enlazado por ID Proyecto)</div>
    </div>
    """, unsafe_allow_html=True
)

# =============================================================================
# NORMALIZACIÓN PLANIFICADOR
# =============================================================================
cols_texto = ["Subdirección", "Departamento_SHORT", "Nombre responsable", "ID Proyecto"]
for col in cols_texto:
    df_planner_pac[col] = df_planner_pac[col].astype(str).str.strip()

df_planner_pac["Fecha de Inicio Compra"] = pd.to_datetime(df_planner_pac["Fecha de Inicio Compra"], errors="coerce")
df_planner_pac["Año"] = df_planner_pac["Fecha de Inicio Compra"].dt.year
df_planner_pac["Mes_nombre"] = df_planner_pac["Fecha de Inicio Compra"].dt.strftime("%B")

meses_es = {"January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril", "May": "Mayo", "June": "Junio",
            "July": "Julio", "August": "Agosto", "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"}
df_planner_pac["Mes_nombre"] = df_planner_pac["Mes_nombre"].replace(meses_es)

# --- 🔄 TRADUCCIÓN DE MESES (NUEVO) ---
# Mapeamos manualmente para asegurar español sin depender de la configuración del servidor
meses_es = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}
df_planner_pac["Mes_nombre"] = df_planner_pac["Mes_nombre"].replace(meses_es)


# =============================================================================
# FILTROS (ACTÚAN SOBRE EL PLAN Y REPERCUTEN EN OCS)
# =============================================================================
col1, col2, col3, col4, col5, col6 = st.columns(6)
df_cascada = df_planner_pac.copy()

# Filtros (simplificados para brevedad, lógica idéntica a tu original)
with col1:
    sub_sel = st.multiselect("🏢 Subdirección", sorted(df_cascada["Subdirección"].dropna().unique()),placeholder="Seleccione")
if sub_sel: df_cascada = df_cascada[df_cascada["Subdirección"].isin(sub_sel)]

with col2:
    dep_sel = st.multiselect("📊 Depto.", sorted(df_cascada["Departamento_SHORT"].dropna().unique()),placeholder="Seleccione")
if dep_sel: df_cascada = df_cascada[df_cascada["Departamento_SHORT"].isin(dep_sel)]

with col3:
    resp_sel = st.multiselect("👤 Resp.", sorted(df_cascada["Nombre responsable"].dropna().unique()),placeholder="Seleccione")
if resp_sel: df_cascada = df_cascada[df_cascada["Nombre responsable"].isin(resp_sel)]

with col4:
    proy_sel = st.multiselect("🆔 ID Proy.", sorted(df_cascada["ID Proyecto"].dropna().unique()),placeholder="Seleccione")
if proy_sel: df_cascada = df_cascada[df_cascada["ID Proyecto"].isin(proy_sel)]

with col5:
    mes_sel = st.multiselect("📅 Mes", sorted(df_cascada["Mes_nombre"].dropna().unique()),placeholder="Seleccione")
if mes_sel: df_cascada = df_cascada[df_cascada["Mes_nombre"].isin(mes_sel)]

with col6:
    anio_sel = st.multiselect("📅 Año", sorted(df_cascada["Año"].dropna().unique()),placeholder="Seleccione")
if anio_sel: df_cascada = df_cascada[df_cascada["Año"].isin(anio_sel)]

# DataFrame FINAL del Plan
df_plan_filtrado = df_cascada.copy()

# --- 🔗 FILTRADO RELACIONAL DE OCS ---
# Aquí ocurre la magia: Filtramos las OCs para que coincidan SOLO con los proyectos del Plan filtrado
proyectos_visibles = df_plan_filtrado["ID Proyecto"].unique()
df_oc_filtrado = df_oc_res[df_oc_res["ID Proyecto"].isin(proyectos_visibles)].copy()

# =============================================================================
# 📊 CÁLCULO DE EJECUCIÓN (PLAN vs REAL)
# =============================================================================

# 1. Agrupar Planificación (Meta)
df_kpi_plan = df_plan_filtrado.groupby("ID Proyecto").agg({
    "Nombre Proyecto": "first",
    "Departamento_SHORT": "first",
    "Subdirección": "first",
    "Nombre responsable": "first",
    "Suma de Monto Total Ítem Año 2026": "sum",
}).reset_index().rename(columns={"Suma de Monto Total Ítem Año 2026": "Monto_Plan"})

# 2. Agrupar Ejecución (Realidad)
# Filtramos solo OCs aceptadas o emitidas para no contar canceladas
df_oc_validas = df_oc_filtrado[~df_oc_filtrado["EstadoOC"].str.contains("Cancelada", na=False)]
df_kpi_real = df_oc_validas.groupby("ID Proyecto")["TotalBruto"].sum().reset_index().rename(columns={"TotalBruto": "Monto_Ejecutado"})

# 3. MERGE FINAL (Base para gráficos)
df_comparativo = pd.merge(df_kpi_plan, df_kpi_real, on="ID Proyecto", how="left")
df_comparativo["Monto_Ejecutado"] = df_comparativo["Monto_Ejecutado"].fillna(0)
df_comparativo["% Ejecución"] = (df_comparativo["Monto_Ejecutado"] / df_comparativo["Monto_Plan"] * 100).fillna(0)
df_comparativo["Estado_Ejecucion"] = df_comparativo["Monto_Ejecutado"].apply(lambda x: "🟢 En Ejecución" if x > 0 else "🔴 Sin Compras")
df_comparativo["Comparativa_Visual"] = df_comparativo.apply(
    lambda row: [row["Monto_Plan"], row["Monto_Ejecutado"]], axis=1
)

# Normalizamos: El Plan siempre será 1.0 y el Real será (Real/Plan)
df_comparativo["Comparativa_Normalizada"] = df_comparativo.apply(
    lambda row: [1.0, row["Monto_Ejecutado"] / row["Monto_Plan"] if row["Monto_Plan"] > 0 else 0], 
    axis=1
)

# 1. Calculamos la proporción (Real / Plan)
# Si el Plan es 100 y Real es 120, el ratio es 1.2
df_comparativo["Ratio_Desempeño"] = (df_comparativo["Monto_Ejecutado"] / df_comparativo["Monto_Plan"]).fillna(0)

# 2. Creamos la data del gráfico normalizada: [Meta_Normalizada, Real_Normalizado]
# La Meta siempre será 1.0 (nuestra referencia fija)
df_comparativo["Visual_Normalizado"] = df_comparativo["Ratio_Desempeño"].apply(lambda x: [1.0, x])

# 3. Calculamos el límite superior del gráfico para que nada se corte
# Buscamos el ratio más alto (por ejemplo, si alguien gastó el 200%, el max_ratio será 2.0)
# Le sumamos un 10% de margen para que la barra no toque el borde superior
max_ratio_global = max(1.0, df_comparativo["Ratio_Desempeño"].max()) * 1.1

# 2. Aplicamos la categoría al DataFrame
df_comparativo["Estado_Presupuestario"] = df_comparativo.apply(categorizar_ejecucion, axis=1)

# 3. Mantenemos la lógica de normalización para el gráfico visual (Plan vs Real)
df_comparativo["Ratio_Desempeño"] = (df_comparativo["Monto_Ejecutado"] / df_comparativo["Monto_Plan"]).fillna(0)
df_comparativo["Visual_Normalizado"] = df_comparativo["Ratio_Desempeño"].apply(lambda x: [1.0, x])
max_ratio_global = float(max(1.0, df_comparativo["Ratio_Desempeño"].max()) * 1.1)

# =============================================================================
# NIVEL 1 (RESUMEN EJECUTIVO)
# =============================================================================
st.markdown("## 1) ¿Cómo vamos?")

total_plan = float(df_comparativo["Monto_Plan"].sum())
total_real = float(df_comparativo["Monto_Ejecutado"].sum())
avance_global = (total_real / total_plan * 100) if total_plan > 0 else 0.0
gap = total_real - total_plan

k1, k2, k3, k4 = st.columns([1, 1, 1.2, 1])
with k1:
    st.metric("💰 Presupuesto Total Plan", f"${total_plan:,.0f}")
with k2:
    st.metric("🛒 Ejecutado Total", f"${total_real:,.0f}")
with k3:
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(avance_global),
            number={"suffix": "%"},
            gauge={"axis": {"range": [0, 150]}, "bar": {"color": "#2ECC71"}},
            title={"text": "% Avance Global"},
        )
    )
    fig_gauge.update_layout(height=170, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)
with k4:
    etiqueta_gap = "💹 Superávit" if gap >= 0 else "📉 Déficit"
    st.metric(etiqueta_gap, f"${gap:,.0f}")

st.markdown("---")

# NIVEL 2 (TABLERO POR PROYECTO)
# =============================================================================
st.markdown("## 2) ¿Dónde están los problemas?")
st.caption("Ordenado por % de ejecución (sobregiros primero). Selecciona un proyecto para filtrar el detalle inferior.")

df_tablero = df_comparativo.copy()
df_tablero["% Ejecución"] = df_tablero["% Ejecución"].fillna(0.0)
df_tablero = df_tablero.sort_values("% Ejecución", ascending=False)

cols_tablero = [
    "ID Proyecto",
    "Nombre Proyecto",
    "Departamento_SHORT",
    "Nombre responsable",
    "Monto_Plan",
    "Monto_Ejecutado",
    "Visual_Normalizado",
    "% Ejecución",
    "Estado_Presupuestario",
]
cols_tablero = [c for c in cols_tablero if c in df_tablero.columns]

sel = st.dataframe(
    df_tablero[cols_tablero],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Monto_Plan": st.column_config.NumberColumn("Plan", format="$ %,.0f"),
        "Monto_Ejecutado": st.column_config.NumberColumn("Real", format="$ %,.0f"),
        "Departamento_SHORT": st.column_config.TextColumn("Unidad"),
        "Nombre responsable": st.column_config.TextColumn("Dueño"),
        "Estado_Presupuestario": st.column_config.TextColumn("Semáforo"),
        "Visual_Normalizado": st.column_config.BarChartColumn(
            "Plan vs Real",
            y_min=0,
            y_max=max_ratio_global,
        ),
        "% Ejecución": st.column_config.ProgressColumn(
            "%",
            format="%.1f%%",
            min_value=0.0,
            max_value=150.0,
        ),
    },
)

selected_id = None
try:
    if sel and sel.selection and sel.selection.get("rows"):
        idx = sel.selection["rows"][0]
        selected_id = df_tablero.iloc[idx]["ID Proyecto"]
except Exception:
    selected_id = None

st.markdown("---")

# NIVEL 3 (HERRAMIENTAS DE EXPLORACIÓN)
# =============================================================================
st.markdown("## 3) Exploración")
q = st.text_input("🔎 Buscador (Código OC / Proveedor / Ítem)", value="")

bf1, bf2, bf3 = st.columns(3)
with bf1:
    btn_sobreej = st.button("Ver Solo Sobreejecutados")
with bf2:
    btn_sin_mov = st.button("Ver Solo Sin Movimiento")
with bf3:
    btn_no_plan = st.button("Ver Solo Compras No Planificadas")

if "quick_filter" not in st.session_state:
    st.session_state["quick_filter"] = None
if btn_sobreej:
    st.session_state["quick_filter"] = "sobreej"
if btn_sin_mov:
    st.session_state["quick_filter"] = "sin_mov"
if btn_no_plan:
    st.session_state["quick_filter"] = "no_plan"

st.markdown("---")

# NIVEL 4 (DETALLE TRANSACCIONAL)
# =============================================================================
st.markdown("## 4) Detalle Transaccional (Órdenes de Compra)")

df_oc_work = df_oc_filtrado.copy()
if selected_id is not None and "ID Proyecto" in df_oc_work.columns:
    df_oc_work = df_oc_work[df_oc_work["ID Proyecto"].astype(str) == str(selected_id)]

if st.session_state.get("quick_filter") == "sobreej":
    if selected_id is None:
        df_sobreej = df_tablero[df_tablero["% Ejecución"] > 100]
        sobreej_ids = set(df_sobreej["ID Proyecto"].astype(str).unique())
        df_oc_work = df_oc_work[df_oc_work["ID Proyecto"].astype(str).isin(sobreej_ids)]
elif st.session_state.get("quick_filter") == "sin_mov":
    if selected_id is None:
        df_sin = df_tablero[df_tablero["Monto_Ejecutado"].fillna(0).astype(float) == 0]
        sin_ids = set(df_sin["ID Proyecto"].astype(str).unique())
        df_oc_work = df_oc_work[df_oc_work["ID Proyecto"].astype(str).isin(sin_ids)]
elif st.session_state.get("quick_filter") == "no_plan":
    df_oc_work = df_oc_work[df_oc_work["PAC"].astype(str).str.contains("No", na=False)]

if q:
    q_norm = str(q).strip()
    mask_oc = pd.Series(False, index=df_oc_work.index)
    for col in ["CodigoOC", "P_Nombre", "NombreOC"]:
        if col in df_oc_work.columns:
            mask_oc |= df_oc_work[col].astype(str).str.contains(q_norm, case=False, na=False)

    if not df_oc_det.empty and "Producto" in df_oc_det.columns and "CodigoOC" in df_oc_det.columns:
        oc_match = df_oc_det[df_oc_det["Producto"].astype(str).str.contains(q_norm, case=False, na=False)]["CodigoOC"].astype(str).unique()
        mask_oc |= df_oc_work["CodigoOC"].astype(str).isin(set(oc_match))

    df_oc_work = df_oc_work[mask_oc]

cols_oc = [
    "PAC",
    "CodigoOC",
    "P_Nombre",
    "FechaAceptacion",
    "TotalBruto",
    "Link",
    "EstadoOC",
]
cols_oc = [c for c in cols_oc if c in df_oc_work.columns]

if not df_oc_work.empty and "TotalBruto" in df_oc_work.columns:
    max_m = float(df_oc_work["TotalBruto"].max()) if df_oc_work["TotalBruto"].max() else 0.0
    df_oc_work["Monto_Rel"] = df_oc_work["TotalBruto"].astype(float) / max_m if max_m else 0.0

def _style_pac(row):
    pac = str(row.get("PAC", ""))
    if "Enlazada" in pac:
        return ["background-color: rgba(46, 204, 113, 0.15)"] * len(row)
    return ["background-color: rgba(231, 76, 60, 0.12)"] * len(row)

if df_oc_work.empty:
    st.info("No hay Órdenes de Compra para la selección actual.")
else:
    st.dataframe(
        df_oc_work[cols_oc + (["Monto_Rel"] if "Monto_Rel" in df_oc_work.columns else [])]
        .style.apply(_style_pac, axis=1)
        .format({"TotalBruto": "${:,.0f}"}),
        use_container_width=True,
        hide_index=True,
        column_config={
            "FechaAceptacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Link": st.column_config.LinkColumn("Mercado Público", display_text="🔗"),
            "Monto_Rel": st.column_config.ProgressColumn("Monto (rel)", min_value=0.0, max_value=1.0),
        },
    )

st.markdown("---")

# NIVEL 5 (INSIGHTS / ALERTAS)
# =============================================================================
st.markdown("## 5) Insights y Alertas")

alert1, alert2, alert3 = st.columns(3)

with alert1:
    st.markdown("### 🧯 Alertas de Fuga")
    if not df_oc_work.empty and "TotalBruto" in df_oc_work.columns:
        fuga = df_oc_work[
            df_oc_work["PAC"].astype(str).str.contains("No", na=False)
            & (df_oc_work["TotalBruto"].astype(float) >= 5_000_000)
        ].sort_values("TotalBruto", ascending=False)
        if fuga.empty:
            st.success("Sin fugas relevantes.")
        else:
            st.warning(f"OCs sin enlace al PAC: {len(fuga)}")
            st.dataframe(
                fuga[[c for c in ["CodigoOC", "P_Nombre", "TotalBruto", "Link"] if c in fuga.columns]].head(20),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "TotalBruto": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Link": st.column_config.LinkColumn("MP", display_text="🔗"),
                },
            )

with alert2:
    st.markdown("### 💤 Alertas de Inacción")
    mes_hoy = date.today().month
    if mes_hoy >= 6:
        inaccion = df_tablero[
            (df_tablero["Monto_Plan"].astype(float) >= 10_000_000)
            & (df_tablero["Monto_Ejecutado"].fillna(0).astype(float) == 0)
        ].sort_values("Monto_Plan", ascending=False)
        if inaccion.empty:
            st.success("Sin inacción crítica.")
        else:
            st.error(f"Proyectos sin movimiento: {len(inaccion)}")
            st.dataframe(
                inaccion[[c for c in ["Nombre Proyecto", "Departamento_SHORT", "Nombre responsable", "Monto_Plan"] if c in inaccion.columns]].head(20),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Monto_Plan": st.column_config.NumberColumn(format="$ %,.0f"),
                },
            )
    else:
        st.info("Esta alerta se activa desde mitad de año (junio).")

with alert3:
    st.markdown("### 🧾 Alertas de Proveedores")
    if not df_oc_work.empty and "P_Nombre" in df_oc_work.columns and "TotalBruto" in df_oc_work.columns:
        total_gasto = float(df_oc_work["TotalBruto"].sum())
        if total_gasto > 0:
            prov = (
                df_oc_work.groupby("P_Nombre")["TotalBruto"].sum().sort_values(ascending=False).reset_index()
            )
            prov["Participación"] = prov["TotalBruto"].astype(float) / total_gasto
            concentrados = prov[prov["Participación"] >= 0.30]
            if concentrados.empty:
                st.success("Sin concentración > 30%.")
            else:
                st.warning(f"Proveedores concentrados: {len(concentrados)}")
                st.dataframe(
                    concentrados.head(20),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "TotalBruto": st.column_config.NumberColumn(format="$ %,.0f"),
                        "Participación": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0),
                    },
                )