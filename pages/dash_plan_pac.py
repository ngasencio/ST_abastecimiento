import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import plotly.io as pio
from jinja2 import Environment, FileSystemLoader
import os
import base64
import pdfkit 
from pyhtml2pdf import converter


# =============================================================================
# CARGA DE DATOS
# =============================================================================

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
# DASHBOARD
# =============================================================================
st.markdown("## 📈 Dashboard General PAC26")
col_kpis, col_grafico = st.columns([1, 3])

with col_kpis:
    total_proyectos_general = df_planner_pac["ID Proyecto"].nunique()
    total_proyectos_filtrado = df_filtrado["ID Proyecto"].nunique()
    porc_proyectos = (total_proyectos_filtrado / total_proyectos_general * 100) if total_proyectos_general > 0 else 0
    
    st.metric("🗂️ Cantidad de Proyectos", total_proyectos_filtrado, f"{porc_proyectos:.1f}% del total")
    
    monto_total_general = df_planner_pac["Suma de Monto Total Ítem Año 2026"].sum()
    monto_total_filtrado = df_filtrado["Suma de Monto Total Ítem Año 2026"].sum()
    porc_monto = (monto_total_filtrado / monto_total_general * 100) if monto_total_general > 0 else 0

    st.metric("💰 Monto Estimado 2026", f"${monto_total_filtrado:,.0f}", f"{porc_monto:.1f}% del total")

with col_grafico:
    df_grafico = df_filtrado.copy()
    df_grafico["Mes_Año"] = df_grafico["Fecha de Inicio Compra"].dt.to_period("M").astype(str)
    df_mensual = df_grafico.groupby("Mes_Año", as_index=False)["ID Proyecto"].nunique()

    fig_PAC = px.bar(
        df_mensual, x="Mes_Año", y="ID Proyecto", text_auto=True,
        labels={"Mes_Año": "Mes", "ID Proyecto": "Proyectos"},
        title="📊 Cantidad de Proyectos por Mes"
    )
    fig_PAC.update_layout(height=450, xaxis_title=None)
    st.plotly_chart(fig_PAC, use_container_width=True)

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
    st.write("Cada fila representa un Proyectoy su fecha de compra programada:")
    st.dataframe(
        df_filtrado[[
            "ID Proyecto", "Nombre Proyecto",  
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
    
    df_display_oc = df_expandido[["ID Proyecto",
        "Meses envío OC", "Nombre ítem", "Nombre responsable", "Departamento_SHORT"
    ]].sort_values("Meses envío OC")
    
    st.dataframe(
        df_display_oc, 
        column_config=config_columnas, # Aplicamos el formato aquí también
        use_container_width=True, 
        hide_index=True
    )

# =============================================================================
# 🔄 LÓGICA DE EXPORTACIÓN (USANDO pyhtml2pdf - EL QUE TE FUNCIONA)
# =============================================================================
st.divider()
st.subheader("📄 Exportar Reporte")

# 1. Definir función para cargar plantilla
def cargar_plantilla(nombre_archivo):
    current_dir = os.getcwd()
    # Busca en la misma carpeta o ajusta la ruta si está en subcarpeta
    templates_dir = os.path.join(current_dir, "pages", "streamlitFacturaPDF", "plantillas")
    
    # Si no la encuentra ahí, busca en la carpeta actual (fallback)
    if not os.path.exists(templates_dir):
        templates_dir = current_dir
        
    env = Environment(loader=FileSystemLoader(templates_dir))
    try:
        return env.get_template(nombre_archivo)
    except Exception as e:
        return None

# 2. Función auxiliar para generar el PDF usando Chrome (pyhtml2pdf)
def generar_pdf_con_chrome(html_str, nombre_salida):
    # Guardamos el HTML temporalmente
    tmp_html = f"temp_{nombre_salida}.html"
    tmp_pdf = f"temp_{nombre_salida}.pdf"
    
    try:
        # Escribir HTML en disco con utf-8
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_str)
        
        # Convertir usando la ruta absoluta del archivo
        path_absoluto = os.path.abspath(tmp_html)
        converter.convert(f'file:///{path_absoluto}', tmp_pdf)
        
        # Leer el PDF generado a memoria
        with open(tmp_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        return pdf_bytes
    
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None
    finally:
        # Limpieza de archivos temporales
        if os.path.exists(tmp_html): os.remove(tmp_html)
        if os.path.exists(tmp_pdf): os.remove(tmp_pdf)

# 3. Preparar datos y Botón
items_para_pdf = []
# Mapeo simple: Proyecto -> Actividad, Monto -> Tarifa
for index, row in df_filtrado.iterrows():
    items_para_pdf.append({
        "date": row["Fecha de Inicio Compra"].strftime("%d-%m-%Y") if pd.notnull(row["Fecha de Inicio Compra"]) else "-",
        "task_executed": f"{row['Nombre Proyecto']} ({row['ID Proyecto']})",
        "hours": 1,
        "rate": row["Suma de Monto Total Ítem Año 2026"]
    })

if st.button("📥 Generar PDF (Versión Chrome)", type="primary"):
    with st.spinner("Generando PDF con los filtros actuales..."):
        template = cargar_plantilla("Plantilla_Plan_PAC.html")
        
        if template:
            # Renderizamos HTML
            html_renderizado = template.render(
                TituloReporte="Reporte Planificación PAC 2026",
                SubtituloReporte= "Informe busca mostrar la programción infromada en Mercado Público",
                SubtituloReporte2= "Generado desde ST Abastecimiento",
                reporte_date=pd.Timestamp.now().strftime("%d-%m-%Y"),
                responsable=f"Responsable: {', '.join(responsable_sel) if responsable_sel else 'General'}",
                deptoResponsable=f"Departamento: {', '.join(depto_sel) if depto_sel else 'General'}",
                currency="$",

                # NUEVAS VARIABLES PARA KPIs Y GRÁFICO
                total_proyectos=total_proyectos_filtrado,
                total_monto=monto_total_filtrado,
                chart_base64=fig_PAC,

                items=items_para_pdf,
                subtotal=f"{monto_total_filtrado:,.0f}",
                taxes=None,
                total=f"{monto_total_filtrado:,.0f}",
                invoice_notes="Este reporte refleja la vista actual del Dashboard."
            )
            
            # Generamos el PDF
            pdf_bytes = generar_pdf_con_chrome(html_renderizado, "reporte_pac")
            
            if pdf_bytes:
                st.success("✅ PDF Generado correctamente")
                st.download_button(
                    label="⬇️ Descargar Reporte PDF",
                    data=pdf_bytes,
                    file_name="Reporte_PAC_2026.pdf",
                    mime="application/pdf"
                )
        else:
            st.error("No se encontró la plantilla 'invoice_blue.html'. Verifica que esté en la carpeta correcta.")