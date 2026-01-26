import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns

# ===== CARGAR CSS =====
def cargar_css():
    with open("style/style.css", encoding="utf-8") as f:
      st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css()


# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()


st.set_page_config(
    page_title="Portal DSSO",
    page_icon="logosso.jpg", 
    layout="wide",
    initial_sidebar_state="expanded")

# Importas Datos
def generar_datos_empresa():
    fechas = pd.date_range(start="2024-01-01", end=datetime.today(), freq='D')
    datos = {
        "Fecha": fechas,
        "ingresos_diarios": np.random.normal(50000, 15000, size=len(fechas)),
        "usuarios_activos": np.random.normal(12000, 3000, size=len(fechas)),
        "conversion_rate": np.random.normal(2.5, 0.8, size=len(fechas)),
        "costo_adquisicion": np.random.normal(45, 12, size=len(fechas)),
        "ltv_cliente": np.random.normal(180, 40, size=len(fechas)),
    }
    
    df=pd.DataFrame(datos)
    df["ingresos_diarios"] *= (1+ np.arange(len(df)) * 0.0001) #tendencia creciente
    return df

df = generar_datos_empresa()

#Titulo
st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #0063AE, #0076D1);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            📊 Panel General
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega una visión general de los formularios de solicitud de compra.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =============================== FILTRO ================================================================

# --- 0. Preparación de Fechas (Extracción de Año) ---
# Convertimos a datetime para extraer el año correctamente
df_fsc["fecha_dt_temp"] = pd.to_datetime(
    df_fsc["fecha derivado"], 
    format="%d-%m-%Y", 
    errors="coerce"
)
# Creamos la columna de año (eliminamos nulos para el filtro)
df_fsc["Año"] = df_fsc["fecha_dt_temp"].dt.year.fillna(0).astype(int)

# --- Normalizar texto ---
df_fsc["SUBDIRECCION"] = df_fsc["SUBDIRECCION"].astype(str).str.strip()
df_fsc["DEPTO"] = df_fsc["DEPTO"].astype(str).str.strip()

# ========= OPCIONES INICIALES =========
# Filtramos el año 0 (errores de fecha) de las opciones
opciones_anio = sorted([a for a in df_fsc["Año"].unique() if a > 0], reverse=True)

# ========= SELECTORES EN COLUMNAS =========
col0, col1, col2 = st.columns([2, 5, 5])

# ---- 📅 Filtro de Año (Nuevo) ----
with col0:
    anio_sel = st.multiselect(
        "📅 Año",
        opciones_anio,
        placeholder="Todos"
    )

# DataFrame base para la cascada (Subdirección depende del Año)
df_cascada_sub = df_fsc.copy()
if anio_sel:
    df_cascada_sub = df_cascada_sub[df_cascada_sub["Año"].isin(anio_sel)]

# ---- 🏢 Subdirección (nivel 1) ----
opciones_subdireccion = sorted(df_cascada_sub["SUBDIRECCION"].dropna().unique())

with col1:
    subdireccion_sel = st.multiselect(
        "🏢 Subdirección",
        opciones_subdireccion,
        placeholder="Seleccione"
    )

# DataFrame base para el Departamento (depende de Año y Subdirección)
df_cascada_depto = df_cascada_sub.copy()
if subdireccion_sel:
    df_cascada_depto = df_cascada_depto[df_cascada_depto["SUBDIRECCION"].isin(subdireccion_sel)]

# ---- 📊 Departamento (nivel 2) ----
opciones_depto = sorted(df_cascada_depto["DEPTO"].dropna().unique())

with col2:
    depto_sel = st.multiselect(
        "📊 Departamento",
        opciones_depto,
        placeholder="Seleccione"
    )

# ========= APLICAR FILTROS FINALES A DF_FILTRADO =========
# Usamos df_filtrado como trabajas habitualmente
df_filtrado = df_fsc.copy()

if anio_sel:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(anio_sel)]

if subdireccion_sel:
    df_filtrado = df_filtrado[df_filtrado["SUBDIRECCION"].isin(subdireccion_sel)]

if depto_sel:
    df_filtrado = df_filtrado[df_filtrado["DEPTO"].isin(depto_sel)]

# Limpieza: eliminamos la columna temporal si no se requiere más adelante
# df_filtrado = df_filtrado.drop(columns=["fecha_dt_temp"])

# ===========================================

# =========================================================================

##### KPIS ####
st.markdown("## 📈 Datos Generales")

# Definimos las proporciones: col1(1) + col2(1) = col3(2)
# Esto hace que col3 ocupe exactamente el 50% del ancho total
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # Usamos df_fsc para el total y df_filtrado para lo seleccionado
    total_fsc_general = df_fsc["newiD"].count()
    total_fsc_filtrado = df_filtrado["newiD"].count()

    porcentaje_fsc = (
        (total_fsc_filtrado / total_fsc_general) * 100
        if total_fsc_general > 0 else 0
    )

    st.metric(
        label="📋 Total FSC",
        value=f"{total_fsc_filtrado:,}",
        delta=f"{porcentaje_fsc:.1f}% del total",
        delta_color="normal"
    )   
    
with col2:
    # Aseguramos conversión a número por si hay errores en el origen
    monto_gen = pd.to_numeric(df_fsc["monto estimado"], errors='coerce').sum()
    monto_filt = pd.to_numeric(df_filtrado["monto estimado"], errors='coerce').sum()

    porcentaje_monto = (
        (monto_filt / monto_gen) * 100
        if monto_gen > 0 else 0
    )

    st.metric(
        label="💰 Montos FSC",
        value=f"${monto_filt:,.0f}",
        delta=f"{porcentaje_monto:.1f}% del monto total",
        delta_color="normal"
    )

with col3:
    # Este espacio ahora ocupa el 50% de la fila
    pass

##### GRAFICOS ####
st.markdown("## 📊 Análisis Grafico")

# Asegurar fecha en datetime
df_filtrado["fecha derivado"] = pd.to_datetime(
    df_filtrado["fecha derivado"],
    errors="coerce"
)

# Crear columna mensual
df_filtrado["Mes"] = df_filtrado["fecha derivado"].dt.to_period("M").dt.to_timestamp()

col1, col2, col3 = st.columns([2, 2, 1])

# ======================================
# 📊 FSC por Mes (Cantidad)
# ======================================

conteo_mes = (
    df_filtrado
    .groupby(["Mes", "DENTRO/FUERA"], as_index=False)
    .agg({"newiD": "count"})
    .rename(columns={"newiD": "Cantidad FSC"})
)

print("COLUMNAS:", conteo_mes.columns.tolist())
print(conteo_mes.head(10))
print("DUPLICADOS:", conteo_mes.duplicated(["Mes","DENTRO/FUERA"]).sum())


with col1:
    conteo_mes = (
        df_filtrado
        .groupby(["Mes", "DENTRO/FUERA"])["newiD"]
        .count()
        .reset_index(name="Cantidad FSC")
    )

    fig_q = px.bar(
        conteo_mes,
        x="Mes",
        y="Cantidad FSC",
        color="DENTRO/FUERA",
        title="📊 Cantidad de FSC por Mes (Dentro / Fuera PAC)",
        labels={
            "Mes": "Mes",
            "Cantidad FSC": "Cantidad de FSC",
            "DENTRO/FUERA": "Estado PAC"
        },
        color_discrete_map={
            "Dentro PAC": "#36e93f",   # verde
            "Fuera PAC": "#ec4545"     # rojo
        }
    )

    fig_q.update_layout(
        barmode="stack",
        height=400,
        template="plotly_white",
        font=dict(family="Segoe UI")
    )

    st.plotly_chart(fig_q, use_container_width=True)

print(
conteo_mes.duplicated(["Mes","DENTRO/FUERA"]).sum()
)
# ======================================
# 💰 FSC por Mes (Monto)
# ======================================
with col2:
    monto_mes = (
        df_filtrado
        .groupby(["Mes", "DENTRO/FUERA"])["monto estimado"]
        .sum()
        .reset_index(name="Monto Estimado")
    )

    fig_m = px.bar(
        monto_mes,
        x="Mes",
        y="Monto Estimado",
        color="DENTRO/FUERA",
        title="💰 Monto Estimado FSC por Mes (Dentro / Fuera PAC)",
        labels={
            "Mes": "Mes",
            "Monto Estimado": "Monto Estimado (CLP)",
            "DENTRO/FUERA": "Estado PAC"
        },
        color_discrete_map={
            "Dentro PAC": "#36e93f",   # verde
            "Fuera PAC": "#ec4545"     # rojo
        }
    )

    fig_m.update_layout(
        barmode="stack",
        height=400,
        template="plotly_white",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
font=dict(family="Segoe UI")
    )

    st.plotly_chart(fig_m, use_container_width=True)

with col3:
    # --- Lógica Métrica 1 (Cantidad) ---
    serie_pac = df_filtrado["DENTRO/FUERA"].astype(str).str.strip().str.upper()
    total_f = len(df_filtrado)
    
    if total_f > 0:
        dentro_pac_q = serie_pac.str.contains("DENTRO", na=False).sum()
        porc_q = (dentro_pac_q / total_f) * 100
    else:
        dentro_pac_q, porc_q = 0, 0.0

    st.metric(
        label="✅ FSC Dentro PAC (%)", 
        value=f"{porc_q:.1f}%", 
        delta=f"{dentro_pac_q} Unds",
        help="Porcentaje basado en la cantidad de formularios."
    )

    # Espaciador pequeño entre métricas
    st.write("") 

    # --- Lógica Métrica 2 (Monto) ---
    monto_total_g = df_filtrado["monto estimado"].sum()
    
    if monto_total_g > 0:
        mask_d = serie_pac.str.contains("DENTRO", na=False)
        monto_d = df_filtrado.loc[mask_d, "monto estimado"].sum()
        porc_m = (monto_d / monto_total_g) * 100
    else:
        monto_d, porc_m = 0, 0.0

    st.metric(
        label="💰 Monto Dentro PAC (%)", 
        value=f"{porc_m:.1f}%", 
        delta=f"$ {monto_d:,.0f}",
        help="Porcentaje basado en el valor monetario total."
    )



st.markdown("## 📈 Tabla Dinámica: Análisis por Departamento y PAC")

# Aseguramos que el monto sea numérico para los cálculos
df_filtrado["monto estimado"] = pd.to_numeric(df_filtrado["monto estimado"], errors="coerce").fillna(0)

# Definimos las columnas
col1, col2 = st.columns(2)

with col1:
    # --- 1. Creación de la Tabla Dinámica ---
    # Usamos pivot_table para cruzar Departamentos con el estado DENTRO/FUERA
    tabla_dinamica = df_filtrado.pivot_table(
        index="DEPTO_unido",
        columns="DENTRO/FUERA",
        values=["newiD", "monto estimado"],
        aggfunc={
            "newiD": "count",          # Recuento de registros (FSC)
            "monto estimado": "sum"    # Suma de montos estimados
        },
        fill_value=0,
        margins=True,                  # Totales por fila y columna
        margins_name="TOTAL GENERAL"
    )

    # --- 2. Aplanar niveles de columnas para visualización limpia ---
    tabla_dinamica.columns = [f"{col[0]} ({col[1]})" for col in tabla_dinamica.columns]
    tabla_dinamica = tabla_dinamica.reset_index()

    # --- 3. Ordenar por cantidad total de registros ---
    col_orden = [c for c in tabla_dinamica.columns if "newiD (TOTAL GENERAL)" in c]
    if col_orden:
        tabla_dinamica = tabla_dinamica.sort_values(by=col_orden[0], ascending=False)

    # --- 4. Renderizado con Estilos ---
    st.dataframe(
        tabla_dinamica.style.format({
            col: "$ {:,.0f}" for col in tabla_dinamica.columns if "monto" in col
        }).background_gradient(
            subset=[c for c in tabla_dinamica.columns if "newiD" in c], 
            cmap="Blues"
        ),
        use_container_width=True,
        hide_index=True
    )
    # --- 6. Resumen rápido en texto ---
total_monto_dinamico = df_filtrado["monto estimado"].sum()
st.caption(f"💰 **Monto Total Filtrado:** $ {total_monto_dinamico:,.0f} | 📋 **Total Registros:** {len(df_filtrado)}")
with col2:
    pass


st.markdown("## 🚦 Centro de Alertas")

# --- 1. Cálculo de métricas para alertas ---
total_f = len(df_filtrado)
if total_f > 0:
    # Porcentaje de cumplimiento PAC
    dentro_pac_count = df_filtrado["DENTRO/FUERA"].astype(str).str.upper().str.contains("DENTRO").sum()
    porcentaje_pac = (dentro_pac_count / total_f) * 100
    
    # --- 2. Lógica de Alertas con componentes nativos ---

    # Alerta de Error (Crítico): Cumplimiento PAC muy bajo
    if porcentaje_pac < 50:
        st.error(f"**Crítico:** El cumplimiento de PAC está en un **{porcentaje_pac:.1f}%**. "
                 f"Hay {total_f - dentro_pac_count} formularios fuera de planificación.")

    # Alerta de Advertencia: Tasa de conversión o caída de registros
    # Ejemplo: Si hay más de 10 formularios "FUERA" de PAC
    fuera_pac_count = total_f - dentro_pac_count
    if fuera_pac_count > 10:
        st.warning(f"**Advertencia:** Se detectaron **{fuera_pac_count}** formularios fuera de PAC en el filtro actual.")

    # Notificación de Éxito: Buen desempeño
    if porcentaje_pac >= 85:
        st.success(f"**Excelente:** El nivel de cumplimiento PAC es del **{porcentaje_pac:.1f}%**. "
                   "La gestión se mantiene dentro de los márgenes planificados.")
                   
else:
    st.info("No hay datos disponibles para generar alertas con los filtros seleccionados.")




st.markdown("##  📅 Tabla de Datos")
with st.expander(" 📅Ver Datos Completos"):
    st.dataframe(df.style.format({
        # --- CAMBIO AQUÍ: Eliminar .dt ---
        "Fecha": lambda x: x.strftime("%Y-%m-%d"), 
        # -----------------------------------
        "ingresos_diarios": "${:,.2f}".format,
        "usuarios_activos": "{:,.0f}".format,
        "conversion_rate": "{:.2f}%".format,
        "costo_adquisicion": "${:.2f}".format,
        "ltv_cliente": "${:.2f}".format,
    }), height=400, )
