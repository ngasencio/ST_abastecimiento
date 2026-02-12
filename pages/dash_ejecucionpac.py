import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Importamos tus cargadores
from data.data_loader import load_pac26_data
import api.OC_data_loader as loader_oc

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================
st.set_page_config(page_title="Dashboard PAC vs Ejecución", layout="wide")

def cargar_css():
    try:
        with open("style/style.css") as f:
            css_content = f.read().replace("\n", "").strip()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass # Si no hay CSS, no falla
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
@st.cache_data(ttl=3600, show_spinner="Cargando Compras y Planificación...") 
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

# =============================================================================
# FILTROS (ACTÚAN SOBRE EL PLAN Y REPERCUTEN EN OCS)
# =============================================================================
col1, col2, col3, col4, col5, col6 = st.columns(6)
df_cascada = df_planner_pac.copy()

# Filtros (simplificados para brevedad, lógica idéntica a tu original)
with col1:
    sub_sel = st.multiselect("🏢 Subdirección", sorted(df_cascada["Subdirección"].dropna().unique()))
if sub_sel: df_cascada = df_cascada[df_cascada["Subdirección"].isin(sub_sel)]

with col2:
    dep_sel = st.multiselect("📊 Depto.", sorted(df_cascada["Departamento_SHORT"].dropna().unique()))
if dep_sel: df_cascada = df_cascada[df_cascada["Departamento_SHORT"].isin(dep_sel)]

with col3:
    resp_sel = st.multiselect("👤 Resp.", sorted(df_cascada["Nombre responsable"].dropna().unique()))
if resp_sel: df_cascada = df_cascada[df_cascada["Nombre responsable"].isin(resp_sel)]

with col4:
    proy_sel = st.multiselect("🆔 ID Proy.", sorted(df_cascada["ID Proyecto"].dropna().unique()))
if proy_sel: df_cascada = df_cascada[df_cascada["ID Proyecto"].isin(proy_sel)]

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
    "Suma de Monto Total Ítem Año 2026": "sum",
    "Departamento_SHORT": "first"
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
# VISUALIZACIÓN DE KPIs
# =============================================================================
st.markdown("### 🎯 Indicadores de Desempeño (Real vs Planificado)")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_plan = df_comparativo["Monto_Plan"].sum()
total_real = df_comparativo["Monto_Ejecutado"].sum()
avance_global = (total_real / total_plan * 100) if total_plan > 0 else 0

with kpi1:
    st.metric("💰 Presupuesto Planificado (Filtrado)", f"${total_plan:,.0f}")

with kpi2:
    st.metric("🛒 Ejecución Real (Enlazada)", f"${total_real:,.0f}", delta=f"{avance_global:.1f}% Avance")

with kpi3:
    proyectos_con_compra = df_comparativo[df_comparativo["Monto_Ejecutado"] > 0].shape[0]
    total_proy = df_comparativo.shape[0]
    st.metric("🗂️ Proyectos Iniciados", f"{proyectos_con_compra} / {total_proy}", 
              help="Proyectos del plan que tienen al menos una OC enlazada.")

with kpi4:
    gap = total_plan - total_real
    st.metric("📉 Saldo por Ejecutar", f"${gap:,.0f}", delta_color="inverse")

# =============================================================================
# GRÁFICOS COMPARATIVOS
# =============================================================================
col_g1, col_g2 = st.columns([2, 1])

with col_g1:
    st.markdown("#### 📊 Ejecución por Departamento")
    # Agrupamos por departamento para ver quién ejecuta mejor
    df_depto = df_comparativo.groupby("Departamento_SHORT")[["Monto_Plan", "Monto_Ejecutado"]].sum().reset_index()
    
    # Derretimos el DF para formato largo (Plotly friendly)
    df_melt = df_depto.melt(id_vars="Departamento_SHORT", value_vars=["Monto_Plan", "Monto_Ejecutado"], var_name="Tipo", value_name="Monto")
    
    fig_bar = px.bar(
        df_melt, 
        x="Departamento_SHORT", 
        y="Monto", 
        color="Tipo", 
        barmode="group",
        title="Planificado vs Real por Departamento",
        color_discrete_map={"Monto_Plan": "#BDC3C7", "Monto_Ejecutado": "#2ECC71"},
        labels={"Monto": "Monto ($)", "Departamento_SHORT": "Departamento"}
    )
    fig_bar.update_layout(yaxis_tickformat="$,.0f", legend_title_text="")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_g2:
    st.markdown("#### 🥧 Estado de Proyectos")
    fig_pie = px.pie(
        df_comparativo, 
        names="Estado_Ejecucion", 
        title="Proyectos con vs sin ejecución",
        color="Estado_Ejecucion",
        color_discrete_map={"🟢 En Ejecución": "#2ECC71", "🔴 Sin Compras": "#E74C3C"},
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# =============================================================================
# TABLAS DE DETALLE
# =============================================================================
st.markdown("---")
tab_plan, tab_oc, tab_match = st.tabs(["📅 Planificación Original", "🛒 Órdenes de Compra (Detalle)", "🔗 Cruce Proyecto a Proyecto"])

# TAB 1: EL PLAN (Lo que ya tenías)
with tab_plan:
    st.dataframe(
        df_plan_filtrado[[
            "ID Proyecto", "Nombre Proyecto", "Nombre ítem", 
            "Nombre responsable", "Fecha de Inicio Compra", "Suma de Monto Total Ítem Año 2026"
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={"Suma de Monto Total Ítem Año 2026": st.column_config.NumberColumn(format="$ %,.0f")}
    )

# TAB 2: LAS OCS (Con Link)
with tab_oc:
    st.markdown("Listado de Órdenes de Compra filtradas por los proyectos seleccionados arriba.")
    cols_oc_view = ["CodigoOC", "EstadoOC", "TotalBruto", "NombreOC", "FechaAceptacion", "ID Proyecto", "Link"]
    
    # Verificamos que existan las columnas antes de mostrar
    cols_existentes = [c for c in cols_oc_view if c in df_oc_filtrado.columns]
    
    st.dataframe(
        df_oc_filtrado[cols_existentes],
        use_container_width=True,
        hide_index=True,
        column_config={
            "TotalBruto": st.column_config.NumberColumn(format="$ %,.0f"),
            "FechaAceptacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Link": st.column_config.LinkColumn(
                "Ver en MercadoPúblico", 
                display_text="🔗 Abrir OC"
            )
        }
    )

# TAB 3: RESUMEN MATCH

with tab_match:
    st.markdown("### 📊 Tablero de Control Presupuestario")
    
    # Resumen de reglas en un info box para el usuario
    st.caption("Leyenda: 🔴 0% | 🟡 <50% | 🟢 50-79% | ✅ 80-100% | 💹 >100%")

    st.dataframe(
        df_comparativo.sort_values("Monto_Plan", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID Proyecto": "Proyecto",
            "Monto_Plan": st.column_config.NumberColumn("Meta (Plan)", format="$ %,.0f"),
            "Monto_Ejecutado": st.column_config.NumberColumn("Gastado (Real)", format="$ %,.0f"),
            "Estado_Presupuestario": st.column_config.TextColumn("Estatus de Ejecución"),
            "Visual_Normalizado": st.column_config.BarChartColumn(
                "Plan vs Real",
                help="Barra 1: Meta (100%). Barra 2: Gasto Real proporcional.",
                y_min=0,
                y_max=max_ratio_global
            ),
            "% Ejecución": st.column_config.ProgressColumn(
                "Avance %", 
                format="%.1f%%", 
                min_value=0.0,
                max_value=100.0
            ),
        }
    )