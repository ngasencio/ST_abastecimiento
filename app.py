import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()

st.set_page_config(
    page_title="Dashboard DSSO",
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
        background: linear-gradient(90deg, #1748EB, #3f6ef2);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            📊 Panel General
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega una visión ejecutiva del desempeño de los compradores de la organización, 
permitiendo analizar su gestión en términos de eficiencia, cumplimiento y volumen de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
st.write("""
Este informe presenta una visión ejecutiva del desempeño operacional y financiero,
considerando los principales indicadores de la organización.
""")
# =============================== FILTRO ================================================================

# --- Normalizar texto (recomendado) ---
df_fsc["SUBDIRECCION"] = df_fsc["SUBDIRECCION"].astype(str).str.strip()
df_fsc["DEPTO"] = df_fsc["DEPTO"].astype(str).str.strip()

# ========= OPCIONES =========
opciones_subdireccion = sorted(
    df_fsc["SUBDIRECCION"].dropna().unique()
)

opciones_depto = sorted(
    df_fsc["DEPTO"].dropna().unique()
)

# ========= SELECT MULTI =========
col1, col2 = st.columns(2)

# ---- Subdirección (nivel 1) ----
with col1:
    subdireccion_sel = st.multiselect(
        "🏢 Subdirección",
        opciones_subdireccion,
        placeholder="Seleccione"
    )

# DataFrame base para cascada
df_cascada = df_fsc.copy()

if subdireccion_sel:
    df_cascada = df_cascada[
        df_cascada["SUBDIRECCION"].isin(subdireccion_sel)
    ]

# ---- Departamento (nivel 2) ----
opciones_depto = sorted(
    df_cascada["DEPTO"].dropna().unique()
)

with col2:
    depto_sel = st.multiselect(
        "📊 Departamento",
        opciones_depto,
        placeholder="Seleccione"
    )

# ========= APLICAR FILTROS =========
df_filtrado = df_fsc.copy()

if subdireccion_sel:
    df_filtrado = df_filtrado[
        df_filtrado["SUBDIRECCION"].isin(subdireccion_sel)
    ]

if depto_sel:
    df_filtrado = df_filtrado[
        df_filtrado["DEPTO"].isin(depto_sel)
    ]

# =========================================================================


##### KPIS ####
st.markdown("## 📈 Datos Generales")
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_fsc_general = df_fsc["newiD"].count()
    total_fsc_filtrado = df_filtrado["newiD"].count()

    porcentaje_fsc = (
        (total_fsc_filtrado / total_fsc_general) * 100
        if total_fsc_general > 0 else 0
    )

    st.metric(
        "📋 Total FSC",
        f"{total_fsc_filtrado:,}",
        f"{porcentaje_fsc:.1f}% del total"
    )   
    
with col2:
    monto_total_general = df_fsc["monto estimado"].sum()
    monto_filtrado = df_filtrado["monto estimado"].sum()

    porcentaje_monto = (
        (monto_filtrado / monto_total_general) * 100
        if monto_total_general > 0 else 0
    )

    st.metric(
        "💰 Montos FSC",
        f"${monto_filtrado:,.0f}",
        f"{porcentaje_monto:.1f}% del monto total"
    )

with col3:
    conversion_prom = df["conversion_rate"].mean()
    st.metric("🎯 Tasa de Conversión", 
            f"{conversion_prom:.2f}%",
            f"{np.random.uniform(0.5, 2):.1f}%")
    
with col4:
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

col1, col2 = st.columns(2)

# ======================================
# 📊 FSC por Mes (Cantidad)
# ======================================
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
        template="plotly_white"
    )

    st.plotly_chart(fig_q, use_container_width=True)

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
        yaxis_tickformat=",.0f"
    )

    st.plotly_chart(fig_m, use_container_width=True)


st.markdown("## 🚦 Centro de Alertas Inteligentes ")
alertas = []

if df["ingresos_diarios"].tail(7).mean() < df["ingresos_diarios"].head(-7).mean():
    alertas.append({'tipo': "⚠️ Alerta: Ingresos diarios por debajo del promedio en 7 dias.", 'color': "orange"})

if df["conversion_rate"].tail(1).iloc[0] < 2.0:
    alertas.append({'tipo': "❗ Alerta: Tasa de conversión ha caído por debajo del 2% en la última semana.", 'color': "red"})

if df["usuarios_activos"].tail(1).iloc[0] > df["usuarios_activos"].quantile(0.9):
    alertas.append({'tipo': "✅ Notificación: Usuarios activos han superado el 90 percentil.", 'color': "green"})
    
for alerta in alertas:
    st.markdown(f"""<div style="padding: 1rem; margin:0.5rem 0; background-color: {alerta['color']}; color: white; border-radius: 10px; font-weight: bold;">{alerta['tipo']}:{alerta['tipo']}</div>""", unsafe_allow_html=True)
    
    
st.markdown("## 📅 Tabla de Datos")
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
    }), height=400)