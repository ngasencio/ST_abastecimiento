import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from utils.pdf_generador_pac import generar_pdf_pac
from data.data_loader import load_pac26_data

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================

def cargar_css():
    try:
        with open("style/style.css") as f:
            css_content = f.read().replace("\n", "").strip()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")
cargar_css()

# =============================================================================
# CARGA DE DATOS
# =============================================================================
df_planner_pac = load_pac26_data()
import api.OC_data_loader as loader_oc

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
        cols_fecha = ['FechaCreacion', 'FechaAceptacion']
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
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #138AEC, #3E9FEF);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            🛒 Planificación 2026
        </div>
        <div style="font-size: 15px; opacity: 0.9;">
            Módulo de seguimiento del Plan Anual de Compras 2026.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =============================================================================
# NORMALIZACIÓN DE DATOS
# =============================================================================
cols_texto = [
    "Subdirección",
    "Departamento_SHORT",
    "Nombre responsable",
    "ID Proyecto"
]

for col in cols_texto:
    df_planner_pac[col] = df_planner_pac[col].astype(str).str.strip()

df_planner_pac["Fecha de Inicio Compra"] = pd.to_datetime(
    df_planner_pac["Fecha de Inicio Compra"], errors="coerce"
)

df_planner_pac["Año"] = df_planner_pac["Fecha de Inicio Compra"].dt.year
df_planner_pac["Mes"] = df_planner_pac["Fecha de Inicio Compra"].dt.month
# Esto genera el nombre en inglés (January, February...)
df_planner_pac["Mes_nombre"] = df_planner_pac["Fecha de Inicio Compra"].dt.strftime("%B") 

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
# FILTROS (6 COLUMNAS)
# =============================================================================
col1, col2, col3, col4, col5, col6 = st.columns(6)

df_cascada = df_planner_pac.copy()

# --- Filtro 1: Subdirección ---
with col1:
    subdireccion_sel = st.multiselect("🏢 Subdirección", sorted(df_cascada["Subdirección"].dropna().unique()), placeholder="Seleccione")

if subdireccion_sel:
    df_cascada = df_cascada[df_cascada["Subdirección"].isin(subdireccion_sel)]

# --- Filtro 2: Departamento ---
with col2:
    depto_sel = st.multiselect("📊 Depto.", sorted(df_cascada["Departamento_SHORT"].dropna().unique()), placeholder="Seleccione")

if depto_sel:
    df_cascada = df_cascada[df_cascada["Departamento_SHORT"].isin(depto_sel)]

# --- Filtro 3: Responsable ---
with col3:
    responsable_sel = st.multiselect("👤 Resp.", sorted(df_cascada["Nombre responsable"].dropna().unique()), placeholder="Seleccione")

if responsable_sel:
    df_cascada = df_cascada[df_cascada["Nombre responsable"].isin(responsable_sel)]

# --- Filtro 4: ID Proyecto ---
with col4:
    proyecto_sel = st.multiselect("🆔 ID Proy.", sorted(df_cascada["ID Proyecto"].dropna().unique()), placeholder="Seleccione")

if proyecto_sel:
    df_cascada = df_cascada[df_cascada["ID Proyecto"].isin(proyecto_sel)]

# --- Filtro 5: Año ---
with col5:
    anio_sel = st.multiselect("📅 Año", sorted(df_cascada["Año"].dropna().unique()), placeholder="Seleccione")

if anio_sel:
    df_cascada = df_cascada[df_cascada["Año"].isin(anio_sel)]

# --- Filtro 6: Mes (Ahora detectará correctamente el Español) ---
with col6:
    # Lista fija para forzar el orden cronológico
    orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    # Obtenemos los meses que realmente existen en los datos filtrados
    meses_disponibles = df_cascada["Mes_nombre"].dropna().unique()
    
    # Intersección: Solo mostramos los meses disponibles pero en el orden correcto
    meses_opciones = [m for m in orden_meses if m in meses_disponibles]

    mes_sel = st.multiselect(
        "🗓️ Mes",
        meses_opciones,
        placeholder="Seleccione"
    )

if mes_sel:
    df_cascada = df_cascada[df_cascada["Mes_nombre"].isin(mes_sel)]

# --- Resultado Final ---
df_filtrado = df_cascada.copy()
# =============================================================================
# DASHBOARD: KPIs + GRÁFICO (2 Columnas)
# =============================================================================
st.markdown("## 📈 Dashboard General PAC26")

# Definimos proporciones: [1, 3] significa que la col_grafico es 3 veces más ancha
col_kpis, col_grafico = st.columns([1, 3])

# --- COLUMNA 1: MÉTRICAS APILADAS ---
with col_kpis:
    # --- Métrica 1: Cantidad de Proyectos ---
    total_proyectos_general = df_planner_pac["ID Proyecto"].nunique()
    total_proyectos_filtrado = df_filtrado["ID Proyecto"].nunique()

    # Cálculo seguro del porcentaje
    porc_proyectos = (total_proyectos_filtrado / total_proyectos_general * 100) if total_proyectos_general > 0 else 0

    st.metric(
        "🗂️ Cantidad de Proyectos",
        total_proyectos_filtrado,
        f"{porc_proyectos:.1f}% del total"
    )
    
    # Espaciador o línea divisoria para separar visualmente la métrica de arriba con la de abajo
    #st.markdown("---") 
    
    # --- Métrica 2: Montos ---
    monto_total_general = df_planner_pac["Suma de Monto Total Ítem Año 2026"].sum()
    monto_total_filtrado = df_filtrado["Suma de Monto Total Ítem Año 2026"].sum()
    
    # Cálculo seguro del porcentaje
    porc_monto = (monto_total_filtrado / monto_total_general * 100) if monto_total_general > 0 else 0

    st.metric(
        "💰 Monto Estimado 2026",
        f"${monto_total_filtrado:,.0f}",
        f"{porc_monto:.1f}% del total"
    )

# --- COLUMNA 2: GRÁFICO ---
with col_grafico:
    
    # Preparación de datos
    df_grafico = df_filtrado.copy()
    
    # Convertimos a formato Periodo para agrupar y luego a String para graficar
    df_grafico["Mes_Año"] = df_grafico["Fecha de Inicio Compra"].dt.to_period("M").astype(str)

    df_mensual = (
        df_grafico
        .groupby("Mes_Año", as_index=False)["ID Proyecto"]
        .nunique()
    )

    # Creación del gráfico
    fig = px.bar(
        df_mensual,
        x="Mes_Año",
        y="ID Proyecto",
        text_auto=True,
        labels={"Mes_Año": "Mes", "ID Proyecto": "Proyectos"},
        title="📊 Cantidad de Proyectos por Mes"
    )
    
    # Ajustes visuales para que se vea bien en el contenedor
    fig.update_layout(
        height=450, # Altura fija para alinear mejor con las 2 métricas
        xaxis_title=None
    )

    st.plotly_chart(fig, use_container_width=True)

# ==============================================================
# ==============================================================
# ==============================================================
st.markdown("### 📊 Planificación vs. Ejecución Mensual")

# 1. PREPARAR DATOS DEL PLAN (Basado en Inicio de Compra)
df_plan_g = df_filtrado.copy()
df_plan_g["Fecha de Inicio Compra"] = pd.to_datetime(df_plan_g["Fecha de Inicio Compra"], errors='coerce')
df_plan_g = df_plan_g.dropna(subset=["Fecha de Inicio Compra"])
df_plan_g["Mes_Año"] = df_plan_g["Fecha de Inicio Compra"].dt.to_period("M").astype(str)

data_plan = (
    df_plan_g
    .groupby("Mes_Año", as_index=False)["ID Proyecto"]
    .nunique()
    .rename(columns={"ID Proyecto": "Cantidad"})
)
data_plan["Tipo"] = "📅 Proyectos Planificados"

# 2. PREPARAR DATOS DE EJECUCIÓN (Basado en FechaEnvio)
if 'df_oc_filtrado' in globals() and not df_oc_filtrado.empty:
    df_exec_g = df_oc_filtrado.copy()
    
    # --- CAMBIO CLAVE: Usamos FechaEnvio ---
    df_exec_g["FechaEnvio"] = pd.to_datetime(df_exec_g["FechaEnvio"], errors='coerce')
    
    # Filtramos filas que no tengan fecha de envío para no ensuciar el gráfico
    df_exec_g = df_exec_g.dropna(subset=["FechaEnvio"])
    
    df_exec_g["Mes_Año"] = df_exec_g["FechaEnvio"].dt.to_period("M").astype(str)
    
    data_exec = (
        df_exec_g
        .groupby("Mes_Año", as_index=False)["CodigoOC"]
        .nunique()
        .rename(columns={"CodigoOC": "Cantidad"})
    )
    data_exec["Tipo"] = "🛒 OCs Enviadas"
else:
    data_exec = pd.DataFrame(columns=["Mes_Año", "Cantidad", "Tipo"])

# 3. UNIFICAR Y ORDENAR
df_grafico_final = pd.concat([data_plan, data_exec], ignore_index=True)
df_grafico_final = df_grafico_final.sort_values("Mes_Año")

# 4. CREACIÓN DEL GRÁFICO
if not df_grafico_final.empty:
    fig = px.bar(
        df_grafico_final,
        x="Mes_Año",
        y="Cantidad",
        color="Tipo",
        barmode="group",
        text_auto=True,
        color_discrete_map={
            "📅 Proyectos Planificados": "#BDC3C7", 
            "🛒 OCs Enviadas": "#3498DB"
        },
        labels={"Mes_Año": "Periodo (Mes)", "Cantidad": "Total de Registros"}
    )
    
    fig.update_layout(
        height=450,
        xaxis_title=None,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1
        ),
        # Añadimos hover para ver detalle
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ Sin datos para el periodo o filtros seleccionados.")



# =============================================================================
# =============================================================================
# --- 🔄 EXPANSIÓN DE ÓRDENES DE COMPRA (RELACIONAL) ---
# Creamos un DataFrame expandido: una fila por cada fecha en 'Meses envío OC'
df_expandido = df_filtrado.copy()

# 1. Convertir la columna a string y separar por comas
df_expandido['Meses envío OC'] = df_expandido['Meses envío OC'].astype(str).str.split(',')

# 2. 'Explode' convierte cada elemento de la lista en una nueva fila
df_expandido = df_expandido.explode('Meses envío OC')

# 3. Limpiar espacios y convertir a fecha
df_expandido['Meses envío OC'] = pd.to_datetime(df_expandido['Meses envío OC'].str.strip(), errors='coerce')
df_expandido = df_expandido.dropna(subset=['Meses envío OC'])

st.markdown("---")
st.markdown("### 📋 Detalle de Compras y Cronograma de OC")

# Pestañas para organizar la visualización
tab1, tab2 = st.tabs(["🔍 Vista por Proyecto", "📅 Cronograma de Órdenes (Expandido)"])

# Configuración común para las tablas (Fechas y Moneda)
config_columnas = {
    "Fecha de Inicio Compra": st.column_config.DateColumn(
        "Fecha Inicio",
        format="DD-MM-YYYY",
    ),
    "Meses envío OC": st.column_config.DateColumn(
        "Fecha de OC",
        format="DD-MM-YYYY",
    ),
    "Suma de Monto Total Ítem Año 2026": st.column_config.NumberColumn(
        "Monto Total ($)",
        format="$ %,.0f",  # El %,.0f agrega el $ y los separadores de miles
    )
}

with tab1:
    st.dataframe(
        df_filtrado[[
            "ID Proyecto", "Nombre Proyecto", "Nombre ítem", 
            "Nombre responsable", "Fecha de Inicio Compra", "Suma de Monto Total Ítem Año 2026"
        ]],
        column_config=config_columnas, # Aplicamos el formato aquí
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.write("Cada fila representa una Orden de Compra individual programada:")
    # Aseguramos que la columna sea datetime para que el config funcione
    df_expandido['Meses envío OC'] = pd.to_datetime(df_expandido['Meses envío OC'])
    
    df_display_oc = df_expandido[[
        "Meses envío OC", "Nombre ítem", "ID Proyecto", "Nombre responsable", "Departamento_SHORT"
    ]].sort_values("Meses envío OC")
    
    st.dataframe(
        df_display_oc, 
        column_config=config_columnas, # Aplicamos el formato aquí también
        use_container_width=True, 
        hide_index=True
    )

# =============================================================================
# BOTÓN EXPORTAR PDF
# =============================================================================
st.markdown("## 📄 Exportar Reporte (Por Crear)")

if st.button("📥 Generar PDF PAC 2026"):
    pdf_path = generar_pdf_pac(
        df_datos=df_filtrado,
        total_proyectos=total_proyectos_filtrado,
        monto_total=monto_total_filtrado,
        fig_plotly=fig
    )

    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇️ Descargar PDF",
            f,
            file_name="Reporte_PAC_2026.pdf",
            mime="application/pdf"
        )
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
    st.markdown("Comparativo consolidado por Proyecto.")
    st.dataframe(
        df_comparativo.sort_values("Monto_Plan", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monto_Plan": st.column_config.NumberColumn("Meta (Plan)", format="$ %,.0f"),
            "Monto_Ejecutado": st.column_config.NumberColumn("Gastado (Real)", format="$ %,.0f"),
            "% Ejecución": st.column_config.ProgressColumn(
                "Avance Presupuestario", 
                format="%.1f%%", 
                min_value=0, 
                max_value=100
            )
        }
    )

# --- COLUMNA 2: GRÁFICO COMPARATIVO MENSUAL (REPARADO) ---

st.markdown("#### 📅 Planificación vs. Ejecución Mensual")

# 1. Agrupamos el PLAN por mes
df_plan_mensual = df_plan_filtrado.copy()
df_plan_mensual["Mes_Año"] = df_plan_mensual["Fecha de Inicio Compra"].dt.to_period("M").astype(str)
resumen_plan = df_plan_mensual.groupby("Mes_Año")["Suma de Monto Total Ítem Año 2026"].sum().reset_index()
resumen_plan.columns = ["Mes_Año", "Monto_Plan"]

# 2. Agrupamos la EJECUCIÓN (OCs) por mes (usando FechaEnvio)
if not df_oc_filtrado.empty:
    df_oc_mensual = df_oc_filtrado.copy()
    df_oc_mensual["FechaEnvio"] = pd.to_datetime(df_oc_mensual["FechaEnvio"], errors='coerce')
    df_oc_mensual = df_oc_mensual.dropna(subset=["FechaEnvio"])
    df_oc_mensual["Mes_Año"] = df_oc_mensual["FechaEnvio"].dt.to_period("M").astype(str)
    resumen_real = df_oc_mensual.groupby("Mes_Año")["TotalBruto"].sum().reset_index()
    resumen_real.columns = ["Mes_Año", "Monto_Real"]
else:
    resumen_real = pd.DataFrame(columns=["Mes_Año", "Monto_Real"])

# 3. EL TRUCO MAESTRO: Unir ambas tablas por Mes
# Usamos 'outer' para no perder meses que tengan plan pero no OCs (o viceversa)
df_mes_comp = pd.merge(resumen_plan, resumen_real, on="Mes_Año", how="outer").fillna(0)
df_mes_comp = df_mes_comp.sort_values("Mes_Año")

# 4. "DERRETIR" (Melt) para Plotly
df_mes_melt = df_mes_comp.melt(
    id_vars="Mes_Año", 
    value_vars=["Monto_Plan", "Monto_Real"], 
    var_name="Tipo", 
    value_name="Monto"
)

# 5. GRAFICAR
if not df_mes_melt.empty:
    fig_mes = px.bar(
        df_mes_melt,
        x="Mes_Año",
        y="Monto",
        color="Tipo",
        barmode="group",
        text_auto=".2s", # Muestra valores compactos (ej: 1.2M)
        color_discrete_map={"Monto_Plan": "#BDC3C7", "Monto_Real": "#3498DB"},
        labels={"Monto": "Monto Total ($)", "Mes_Año": "Mes de Operación"}
    )
    
    fig_mes.update_layout(
        height=450,
        xaxis_title=None,
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_mes, use_container_width=True)
else:
    st.info("No hay datos suficientes para mostrar la comparativa mensual.")
