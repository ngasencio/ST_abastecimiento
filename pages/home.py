import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from style.ui import cargar_css

from data.data_loader import load_pac26_data
from data.data_loader import load_fsc_data
import api.OC_data_loader as loader_oc
from api import LI_data_loader as loader_li

cargar_css()

@st.cache_data(ttl=900, show_spinner=False)
def _load_licitaciones_maestros():
    df_res, df_det = loader_li.cargar_maestros()
    return df_res, df_det

@st.cache_data(ttl=900, show_spinner=False)
def _load_fsc_maestro():
    return load_fsc_data()

# CSS Adicional específico para modificaciones en caliente
st.markdown("""
    <style>
    /* Estilo para el contenedor principal */
    .main {
        background-color: #f8f9fa;
    }
    /* Tarjetas de métricas y contenido */
    .st-emotion-cache-1r6slb0, .css-1r6slb0 { 
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    /* Títulos h1, h2, h3 */
    h1, h2, h3 {
        color: #2c3e50;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Métrica personalizada */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #138AEC;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Botones de enlace */
    .stPageLink {
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 10px;
        transition: all 0.3s;
    }
    .stPageLink:hover {
        border-color: #138AEC;
        background-color: #f0f8ff;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. ENCABEZADO
# =============================================================================
col_logo, col_title, col_user = st.columns([1, 4, 2])

with col_title:
    st.title("Panel de Control de Abastecimiento")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d-%m-%Y')} | **Estado:** Operativo")
st.markdown("---")

# =============================================================================
# 3. RESUMEN EJECUTIVO (KPIs)
# =============================================================================
st.markdown("### 📊 Estado General")

@st.cache_data(ttl=900, show_spinner="Cargando fuentes principales...")
def _load_fuentes_principales():
    df_plan = load_pac26_data()
    df_oc_res, df_oc_det = loader_oc.cargar_maestros_oc()

    file_path = os.path.join("data", "data_pac", "OCPAC_Maestro.csv")
    if os.path.exists(file_path):
        df_pac = pd.read_csv(file_path, dtype={"OC Asociada PAC": str, "ID Proyecto": str})
    else:
        df_pac = pd.DataFrame(columns=["ID Proyecto", "OC Asociada PAC"])

    return df_plan, df_oc_res, df_oc_det, df_pac


def _normalizar_oc_resumen(df_raw_res: pd.DataFrame, df_pac: pd.DataFrame) -> pd.DataFrame:
    if df_raw_res.empty:
        return df_raw_res.copy()

    df = df_raw_res.copy()

    if "CodigoOC" in df.columns:
        df["CodigoOC"] = df["CodigoOC"].astype(str).str.strip()
        base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
        df["Link"] = base_url + df["CodigoOC"]

    for c in ["FechaCreacion", "FechaAceptacion", "FechaEnvio", "FechaCancelacion", "FechaUltimaModificacion"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)

    if "TotalBruto" in df.columns:
        df["TotalBruto"] = pd.to_numeric(df["TotalBruto"], errors="coerce").fillna(0)
    else:
        df["TotalBruto"] = 0

    if "FechaAceptacion" in df.columns and "FechaCreacion" in df.columns:
        df["LeadTime_Dias"] = (df["FechaAceptacion"] - df["FechaCreacion"]).dt.days
        df["LeadTime_Dias"] = df["LeadTime_Dias"].clip(lower=0)
    else:
        df["LeadTime_Dias"] = pd.NA

    if not df_pac.empty and "CodigoOC" in df.columns and "OC Asociada PAC" in df_pac.columns:
        keys_compras = df["CodigoOC"].astype(str).str.strip().str.upper()
        keys_pac = df_pac["OC Asociada PAC"].astype(str).str.strip().str.upper()
        df["PAC"] = "No Enlazada"
        df.loc[keys_compras.isin(set(keys_pac)), "PAC"] = "Enlazada"
    else:
        df["PAC"] = "No Enlazada"

    if "EstadoOC" not in df.columns:
        df["EstadoOC"] = "Desconocido"
    df["EstadoOC"] = df["EstadoOC"].fillna("Desconocido")

    if "FechaCreacion" in df.columns:
        df["Mes"] = df["FechaCreacion"].dt.to_period("M").dt.to_timestamp()

    return df


df_plan, df_oc_res_raw, df_oc_det, df_pac = _load_fuentes_principales()
df_oc_res = _normalizar_oc_resumen(df_oc_res_raw, df_pac)

today = datetime.now().date()
f_fin = datetime.combine(today, datetime.min.time()) + timedelta(days=1) - timedelta(microseconds=1)
f_ini_30 = f_fin - timedelta(days=30)
f_ini_60 = f_fin - timedelta(days=60)
f_ini_prev = f_fin - timedelta(days=30)
f_ini_prev0 = f_fin - timedelta(days=60)

df_30 = df_oc_res[df_oc_res["FechaCreacion"].between(f_ini_30, f_fin)] if "FechaCreacion" in df_oc_res.columns else df_oc_res.copy()
df_prev30 = (
    df_oc_res[df_oc_res["FechaCreacion"].between(f_ini_prev0, f_ini_prev)]
    if "FechaCreacion" in df_oc_res.columns
    else df_oc_res.iloc[0:0].copy()
)

def _delta_pct(actual: float, previo: float) -> str:
    if previo == 0:
        return "0%"
    return f"{((actual - previo) / previo) * 100:+.1f}%"


plan_total = float(df_plan.get("Suma de Monto Total Ítem Año 2026", pd.Series([0])).sum())
real_total = float(df_oc_res.get("TotalBruto", pd.Series([0])).sum())
avance_total = (real_total / plan_total * 100) if plan_total > 0 else 0.0

oc_30_count = int(len(df_30))
oc_prev_count = int(len(df_prev30))

monto_30 = float(df_30.get("TotalBruto", pd.Series([0])).sum())
monto_prev = float(df_prev30.get("TotalBruto", pd.Series([0])).sum())

enl_30 = int((df_30.get("PAC", pd.Series([])) == "Enlazada").sum()) if not df_30.empty else 0
adher_30 = (enl_30 / oc_30_count * 100) if oc_30_count > 0 else 0.0

ef_30 = 0.0
if oc_30_count > 0 and "EstadoOC" in df_30.columns:
    ok_count_30 = int(df_30["EstadoOC"].astype(str).str.contains("Aceptada|Recepcionada", case=False, na=False).sum())
    ef_30 = ok_count_30 / oc_30_count * 100

lt_30 = float(df_30["LeadTime_Dias"].dropna().mean()) if (not df_30.empty and "LeadTime_Dias" in df_30.columns) else float("nan")
lt_prev = float(df_prev30["LeadTime_Dias"].dropna().mean()) if (not df_prev30.empty and "LeadTime_Dias" in df_prev30.columns) else float("nan")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(label="💰 Plan PAC 2026", value=f"${plan_total:,.0f}")
with col2:
    st.metric(label="🛒 Ejecutado (OCs)", value=f"${real_total:,.0f}", delta=f"{avance_total:.1f}%")
with col3:
    st.metric(label="📦 OCs (últimos 30 días)", value=f"{oc_30_count:,}", delta=_delta_pct(oc_30_count, oc_prev_count))
with col4:
    st.metric(label="💳 Monto 30 días", value=f"${monto_30:,.0f}", delta=_delta_pct(monto_30, monto_prev))
with col5:
    st.metric(label="📊 Adherencia PAC (30d)", value=f"{adher_30:.1f}%")
with col6:
    lt_txt = f"{lt_30:.1f} días" if pd.notna(lt_30) else "N/A"
    delta_lt = "" if (pd.isna(lt_30) or pd.isna(lt_prev)) else f"{(lt_30 - lt_prev):+.1f} días"
    st.metric(label="⏱️ Lead Time Prom (30d)", value=lt_txt, delta=delta_lt, delta_color="inverse")

st.write("") # Espacio vertical

# =============================================================================
# 4. CUERPO PRINCIPAL
# =============================================================================
col_main, col_side = st.columns([2.5, 1])

# --- COLUMNA IZQUIERDA: OPERACIÓN CRÍTICA (TABLAS) ---
with col_main:
    st.subheader("🎯 Operación crítica")

    c_op1, c_op2 = st.columns([1.4, 1])

    with c_op1:
        st.markdown("#### 🔴 Licitaciones por cerrar (<= 7 días)")
        df_li_res, _df_li_det = _load_licitaciones_maestros()
        if df_li_res is None or df_li_res.empty:
            st.info("Sin datos de licitaciones para mostrar.")
        else:
            df_li = df_li_res.copy()

            if "FechaCierre" in df_li.columns:
                df_li["FechaCierre"] = pd.to_datetime(df_li["FechaCierre"], errors="coerce", dayfirst=True)
            hoy = pd.Timestamp.now().normalize()

            if "Estado" in df_li.columns and "FechaCierre" in df_li.columns:
                df_li["Dias_a_Cierre"] = (df_li["FechaCierre"] - hoy).dt.days
                df_urg = df_li[
                    (df_li["Estado"].astype(str).str.strip().str.lower() == "publicada")
                    & (df_li["Dias_a_Cierre"].between(0, 7, inclusive="both"))
                ].copy()
                df_urg = df_urg.sort_values("Dias_a_Cierre")
                cols_li = [c for c in ["CodigoLicitacion", "Nombre", "C_Usuario", "FechaCierre", "Dias_a_Cierre", "MontoEstimado"] if c in df_urg.columns]
                st.dataframe(
                    df_urg[cols_li].head(20),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "FechaCierre": st.column_config.DateColumn(format="DD-MM-YYYY"),
                        "MontoEstimado": st.column_config.NumberColumn(format="$ %,.0f"),
                    },
                )
            else:
                st.info("No están disponibles las columnas necesarias (Estado, FechaCierre).")

    with c_op2:
        st.markdown("#### 🟡 FSC pendientes")
        df_fsc = _load_fsc_maestro()
        if df_fsc is None or df_fsc.empty:
            st.info("Sin datos de FSC para mostrar.")
        else:
            df_f = df_fsc.copy()

            if "fecha derivado" in df_f.columns:
                df_f["fecha derivado"] = pd.to_datetime(df_f["fecha derivado"], errors="coerce", dayfirst=True)
                pend = df_f[df_f["fecha derivado"].isna()].copy()
            else:
                pend = pd.DataFrame()

            if pend.empty:
                st.success("Sin formularios pendientes (sin fecha derivado).")
            else:
                cols_p = [c for c in ["newiD", "fecha_solicitud", "usuario requirente", "SUBDIRECCION", "DEPTO", "requerimiento", "monto estimado"] if c in pend.columns]
                if "monto estimado" in pend.columns:
                    pend["monto estimado"] = pd.to_numeric(pend["monto estimado"], errors="coerce").fillna(0)
                st.dataframe(
                    pend[cols_p].head(25),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "monto estimado": st.column_config.NumberColumn(format="$ %,.0f"),
                        "fecha_solicitud": st.column_config.DateColumn(format="DD-MM-YYYY"),
                    },
                )

# --- COLUMNA DERECHA: ACCESOS RÁPIDOS Y ALERTAS ---
with col_side:

    # Navegación Rápida
    with st.container(border=True):
        st.markdown("### 🚀 Accesos Rápidos")
        st.write("Navegue a los módulos principales:")
        
        st.page_link("pages/dash_plan_pac.py", label="Planificación PAC 2026", icon="📅")
        st.page_link("pages/dash_ordencompra.py", label="Seguimiento de Órdenes", icon="🛒")
        st.page_link("pages/dash_documentos.py", label="Repositorio Documental", icon="📚")
        
    st.write("")
    
    # Notificaciones
    with st.container(border=True):
        st.markdown("### 🔔 Avisos Recientes")
        st.info("**Cierre de Mes:** prioriza validar OCs y cruces PAC antes del día 30.")

        if not df_30.empty:
            fuera_plan = df_30[df_30["PAC"].astype(str).str.contains("No", na=False)] if "PAC" in df_30.columns else df_30
            fuera_plan_m = float(fuera_plan["TotalBruto"].sum()) if (not fuera_plan.empty and "TotalBruto" in fuera_plan.columns) else 0.0
            if fuera_plan_m > 0:
                st.warning(f"**Fuera de Plan (30d):** ${fuera_plan_m:,.0f} en OCs sin enlace PAC")
            else:
                st.success("**Adherencia:** sin fugas fuera de plan relevantes en 30 días.")

        if pd.notna(lt_30) and lt_30 >= 15:
            st.warning(f"**Lead Time alto:** {lt_30:.1f} días promedio (30d)")

st.markdown("---")

# =============================================================================
# 5. DETALLE Y ACCIONES PRIORITARIAS
# =============================================================================
st.markdown("### 🚨 Órdenes críticas y acciones recomendadas")

col_det, col_acc = st.columns([2.2, 1])

with col_det:
    df_alert = df_30.copy() if not df_30.empty else df_oc_res.copy()

    if not df_alert.empty:
        crit = df_alert.copy()

        if "PAC" in crit.columns:
            crit["_no_plan"] = crit["PAC"].astype(str).str.contains("No", na=False)
        else:
            crit["_no_plan"] = True

        if "LeadTime_Dias" in crit.columns:
            crit["_lt"] = pd.to_numeric(crit["LeadTime_Dias"], errors="coerce").fillna(0)
        else:
            crit["_lt"] = 0

        crit = crit.sort_values(["_no_plan", "TotalBruto", "_lt"], ascending=[False, False, False])
        cols = [
            "PAC",
            "CodigoOC",
            "EstadoOC",
            "P_Nombre",
            "TotalBruto",
            "FechaCreacion",
            "FechaAceptacion",
            "LeadTime_Dias",
            "Link",
        ]
        cols = [c for c in cols if c in crit.columns]

        st.dataframe(
            crit[cols].head(25),
            use_container_width=True,
            hide_index=True,
            column_config={
                "TotalBruto": st.column_config.NumberColumn(format="$ %,.0f"),
                "FechaCreacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
                "FechaAceptacion": st.column_config.DateColumn(format="DD-MM-YYYY"),
                "Link": st.column_config.LinkColumn("MP", display_text="🔗"),
            },
        )
    else:
        st.info("No hay datos de OCs para mostrar detalle.")

with col_acc:
    with st.container(border=True):
        st.markdown("#### ✅ Acciones recomendadas")

        acciones = []

        if oc_30_count > 0:
            fuera_plan = df_30[df_30["PAC"].astype(str).str.contains("No", na=False)] if "PAC" in df_30.columns else df_30
            fuera_plan_m = float(fuera_plan["TotalBruto"].sum()) if (not fuera_plan.empty and "TotalBruto" in fuera_plan.columns) else 0.0
            if fuera_plan_m >= 5_000_000:
                acciones.append(("Alta", f"Reducir fuga fuera de plan: ${fuera_plan_m:,.0f} sin enlace PAC (30d)."))

        if pd.notna(lt_30) and lt_30 >= 15:
            acciones.append(("Media", f"Revisar cuellos de botella: Lead Time promedio {lt_30:.1f} días (30d)."))

        if ef_30 < 70 and oc_30_count > 10:
            acciones.append(("Media", f"Aumentar tasa de flujo: {ef_30:.1f}% de OCs Aceptada/Recepcionada (30d)."))

        if adher_30 < 80 and oc_30_count > 10:
            acciones.append(("Media", f"Mejorar adherencia PAC: {adher_30:.1f}% enlazadas (30d)."))

        if not acciones:
            st.success("Sin alertas críticas. Mantener monitoreo y cierre de mes.")
        else:
            for sev, msg in acciones[:6]:
                if sev == "Alta":
                    st.error(msg)
                else:
                    st.warning(msg)

# =============================================================================
# 5. PIE DE PÁGINA
# =============================================================================


# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #6c757d; padding: 20px;">
        <p><strong>Dashboard de Licitaciones 2026</strong></p>
        <p>Dirección de Abastecimiento - Red de Salud</p>
        <p style="font-size: 12px;">Desarrollado con Streamlit | Última actualización: {}</p>
    </div>
""".format(pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)


st.markdown("---")
col_footer_l, col_footer_r = st.columns(2)

with col_footer_l:
    st.caption("© 2026 Departamento de Abastecimiento y Operaciones. Todos los derechos reservados.")

with col_footer_r:
    st.caption("Versión 2.1.0 | Última actualización: 30 Ene 2026 | Soporte: nicolas.asencio@redsalud.gob.cl")