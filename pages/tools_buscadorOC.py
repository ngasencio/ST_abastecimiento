import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os
from style.ui import cargar_css

cargar_css()

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================
st.set_page_config(page_title="Dashboard Orden de Compra", layout="wide")

# Aumentar el límite de celdas para el Styler
pd.set_option("styler.render.max_elements", 500000)

import api.OC_data_loader as loader_oc

# ==========================================
# 0. FUNCIONES DE APOYO (LOGICA PAC)
# ==========================================

@st.cache_data(ttl=3600)
def load_pac_master():
    """Carga el archivo maestro consolidado generado previamente."""
    file_path = os.path.join("data", "data_pac", "OCPAC_Maestro.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path, dtype={"OC Asociada PAC": str, "ID Proyecto": str})
    return pd.DataFrame(columns=["ID Proyecto", "OC Asociada PAC"])

def enriquecer_datos_con_pac(df_principal, df_maestro):
    """Cruce vectorizado Paso A y B para identificar OCs en el plan."""
    df = df_principal.copy()

    col_oc_compras = "CodigoOC"
    keys_compras = df[col_oc_compras].astype(str).str.strip().str.upper()

    if df_maestro.empty or "OC Asociada PAC" not in df_maestro.columns:
        df["PAC"] = "No Enlazada"
        return df

    maestro = df_maestro[["OC Asociada PAC", "ID Proyecto"]].copy()
    maestro["key_tmp"] = maestro["OC Asociada PAC"].astype(str).str.strip().str.upper()
    maestro = maestro.drop_duplicates(subset=["key_tmp"], keep="last")

    pac_set = set(maestro["key_tmp"].dropna().unique())
    df["PAC"] = np.where(keys_compras.isin(pac_set), "Enlazada", "No Enlazada")

    df = df.merge(
        maestro[["key_tmp", "ID Proyecto"]],
        left_on=keys_compras,
        right_on="key_tmp",
        how="left",
    ).drop(columns=["key_tmp"])

    return df

def generar_link_mp(codigo_oc):
    """Genera el link directo a la orden de compra en Mercado Público"""
    base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
    return f"{base_url}{codigo_oc}"

# ==========================================
# 1. CARGA DE DATOS (CACHÉ)
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Cargando Bases de Datos...") 
def obtener_todo():
    df_OCres, df_OCdet = loader_oc.cargar_maestros_oc()
    df_pac = load_pac_master()
    return df_OCres, df_OCdet, df_pac

@st.cache_data(ttl=3600, show_spinner=False)
def preprocesar_oc_resumen(df_raw_res: pd.DataFrame, df_pac_maestro: pd.DataFrame) -> pd.DataFrame:
    df = enriquecer_datos_con_pac(df_raw_res, df_pac_maestro)

    if "CodigoOC" in df.columns:
        df["CodigoOC"] = df["CodigoOC"].astype(str).str.strip()
        base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
        df["Link"] = base_url + df["CodigoOC"]

    cols_fecha = ["FechaCreacion", "FechaEnvio", "FechaAceptacion", "FechaCancelacion", "FechaUltimaModificacion"]
    for col in cols_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    if "FechaAceptacion" in df.columns and "FechaCreacion" in df.columns:
        df["LeadTime_Dias"] = (df["FechaAceptacion"] - df["FechaCreacion"]).dt.days
        df["LeadTime_Dias"] = df["LeadTime_Dias"].clip(lower=0)

    if "TipoOC" not in df.columns:
        df["TipoOC"] = "Desconocido"
    else:
        df["TipoOC"] = df["TipoOC"].fillna("Desconocido")

    if "FechaCreacion" in df.columns:
        df["Año"] = df["FechaCreacion"].dt.year
        df["Mes"] = df["FechaCreacion"].dt.to_period("M").dt.to_timestamp()

    return df

def aplicar_filtros(df: pd.DataFrame, pac_sel, estado_oc_sel, unidad_sel, contacto_sel, fechas_sel, anio_sel) -> pd.DataFrame:
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if pac_sel:
        mask &= df["PAC"].isin(pac_sel)
    if estado_oc_sel:
        mask &= df["EstadoOC"].isin(estado_oc_sel)
    if unidad_sel:
        mask &= df["C_Unidad"].isin(unidad_sel)
    if contacto_sel:
        mask &= df["C_Contacto"].isin(contacto_sel)
    if anio_sel:
        mask &= df["Año"].isin(anio_sel)
    if fechas_sel and len(fechas_sel) == 2 and "FechaCreacion" in df.columns:
        f0 = pd.to_datetime(fechas_sel[0])
        f1 = pd.to_datetime(fechas_sel[1]) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        mask &= df["FechaCreacion"].between(f0, f1)

    return df.loc[mask]

@st.cache_data(ttl=1, show_spinner=False)
def agregar_productos_por_oc(df_oc_det: pd.DataFrame, ids_filtrados: tuple) -> pd.DataFrame:
    if df_oc_det.empty or not ids_filtrados:
        return pd.DataFrame()

    df_productos_filtrados = df_oc_det[df_oc_det["CodigoOC"].isin(ids_filtrados)]
    if df_productos_filtrados.empty:
        return pd.DataFrame()

    prod_agg = (
        df_productos_filtrados.groupby("Producto", dropna=False)
        .agg({
            "Cantidad": "sum",
            "PrecioNeto": "mean",
            "CodigoOC": "nunique",
        })
        .reset_index()
        .rename(columns={"CodigoOC": "Frecuencia_OC"})
    )

    prod_agg["Monto_Estimado"] = prod_agg["Cantidad"] * prod_agg["PrecioNeto"]
    prod_agg = prod_agg.sort_values("Monto_Estimado", ascending=False)
    return prod_agg

# Ejecución de carga
try:
    df_raw_res, df_oc_det, df_pac_maestro = obtener_todo()
    
    if df_raw_res.empty:
        st.warning("⚠️ No se encontraron datos de Órdenes de Compra.")
        st.stop()

    # --- PROCESAMIENTO INICIAL ---
    df_oc_res = preprocesar_oc_resumen(df_raw_res, df_pac_maestro)

except Exception as e:
    st.error(f"❌ Error al cargar datos: {e}")
    st.stop()




# ==========================================================
# 4. PREPARACIÓN DE DATOS
# ==========================================================
opciones_anio = sorted(df_oc_res["Año"].dropna().unique()) if "Año" in df_oc_res.columns else []
# ==========================================================
# 3. FILTROS EN CASCADA
# ==========================================================
# 1. Creamos una copia para la lógica de cascada (opciones dinámicas)
df_cascada = df_oc_res

# Creamos 5 columnas para que quepa todo el flujo
c1, c2, c3, c4, c5, c6 = st.columns(6)

# --- FILTRO 1: ESTADO PAC (PRIORITARIO) ---
with c1:
    opciones_pac = ["Enlazada", "No Enlazada"]
    pac_sel = st.multiselect("📌 Filtro PAC", opciones_pac, placeholder="Todos")

if pac_sel:
    df_cascada = df_cascada[df_cascada["PAC"].isin(pac_sel)]

# --- FILTRO 2: ESTADO OC ---
opciones_estado = sorted(df_cascada["EstadoOC"].dropna().unique())
with c2:
    estado_oc_sel = st.multiselect("📝 Estado OC", opciones_estado, placeholder="Todos")

if estado_oc_sel:
    df_cascada = df_cascada[df_cascada["EstadoOC"].isin(estado_oc_sel)]

# --- FILTRO 3: UNIDAD ---
opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
with c3:
    unidad_sel = st.multiselect("🏢 Unidad de Compra", opciones_unidad, placeholder="Todas")

if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# --- FILTRO 4: CONTACTO ---
opciones_contacto = sorted(df_cascada["C_Contacto"].dropna().unique())
with c4:
    contacto_sel = st.multiselect("👤 Contacto", opciones_contacto, placeholder="Todos")

if contacto_sel:
    df_cascada = df_cascada[df_cascada["C_Contacto"].isin(contacto_sel)]

# --- FILTRO 5: FECHA ---
with c5:
    f_min = df_oc_res['FechaCreacion'].min()
    f_max = df_oc_res['FechaCreacion'].max()
    fechas_sel = st.date_input("📅 Periodo", [f_min, f_max])

# ---- Filtro de Año ----
with c6:
    anio_sel = st.multiselect("📆 Año", opciones_anio, placeholder="Seleccione")
    if anio_sel:
        df_cascada = df_cascada[df_cascada["Año"].isin(anio_sel)]
    
# ==========================================================
# APLICACIÓN FINAL AL DATAFRAME DE TRABAJO
# ==========================================================
df_filtrado = aplicar_filtros(
    df_oc_res,
    pac_sel,
    estado_oc_sel,
    unidad_sel,
    contacto_sel,
    fechas_sel,
    anio_sel,
)
# =============================================================================
    # 5. TABLA MAESTRA CON FORMATO CONDICIONAL
    # =============================================================================
def style_pac_rows(row):
    # Aplicamos verde si está enlazado, rojo si no.
    color = 'background-color: rgba(46, 204, 113, 0.2)' if row['PAC'] == 'Enlazada' else 'background-color: rgba(231, 76, 60, 0.2)'
    return [color] * len(row)

st.markdown("### 🛒 Órdenes de Compra Consolidadas")
st.markdown("Listado de Órdenes de Compra filtradas por los proyectos seleccionados arriba.")

# 1. Input de búsqueda
texto_busqueda = st.text_input(
    "🔍 Buscar en Órdenes de Compra:", 
    placeholder="Escribe código, nombre, proyecto o estado...",
    help="Filtra automáticamente las filas que coincidan con el texto en cualquier columna."
)

cols_oc_view = ["Link", "PAC", "CodigoOC", "EstadoOC", "NombreOC","FechaCreacion","FechaEnvio", "FechaAceptacion", "TotalBruto", "ID Proyecto","CodigoLicitacion"]
    # Verificamos que existan las columnas antes de mostrar
cols_existentes = [c for c in cols_oc_view if c in df_filtrado.columns]
# Creamos una copia para no alterar el dataframe original
df_display = df_filtrado[cols_existentes].copy()

# =============================================================================
# Agregar íconos a EstadoOC
# =============================================================================
iconos_estado = {
    "Enviada a proveedor": "📤 Enviada a proveedor",
    "Aceptada": "🤝 Aceptada",
    "Recepción Conforme": "✅ Recepción Conforme",
    "Cancelada": "❌ Cancelada"
}

if "EstadoOC" in df_display.columns:
    df_display["EstadoOC"] = df_display["EstadoOC"].map(iconos_estado).fillna(df_display["EstadoOC"])


# 3. Lógica del Filtro
if texto_busqueda:
    cols_busqueda = [c for c in df_display.columns if c != "Link"]
    search_blob = df_display[cols_busqueda].astype(str).agg(" | ".join, axis=1)
    df_display = df_display[search_blob.str.contains(texto_busqueda, case=False, na=False, regex=False)]

# 4. Mostrar Tabla (Solo si hay datos tras la búsqueda) 
if df_display.empty:
    st.warning(f"No se encontraron resultados para '{texto_busqueda}'")
else:
    st.markdown(f"Mostrando **{len(df_display)}** registros encontrados.")
    df_display = df_display.sort_values(by="FechaCreacion", ascending=False)
    st.dataframe(
        df_display.style.apply(style_pac_rows, axis=1).format({
                "TotalBruto": "${:,.0f}",
            }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "FechaCreacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "FechaEnvio": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "FechaAceptacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Link": st.column_config.LinkColumn(
                "Link MercadoPúblico", 
                display_text="🔗 Abrir OC"
            )
        }
    )
st.divider()