# pages/dash_general.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()


# Título y encabezado
st.title("📋 Dashboard Comrpadores")
st.header("Vista Ejecutiva de la Organización")

st.markdown("""
Este es un resumen de las métricas clave, incluyendo rendimiento general
y tendencias a nivel macro.
""")

# Simulación de datos clave
data_general = {
    'Métrica': ['Ingresos', 'Usuarios Activos', 'Tasa de Conversión'],
    'Valor Actual': [5500000, 15000, '2.8%'],
    'Variación vs Mes Anterior': ['+12%', '-3%', '+0.5%']
}
df_general = pd.DataFrame(data_general)

# Opciones desde la base
opciones_comprador = (
    df_fsc['comprador']
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)
# (Opcional) agrega opción "Todos"
opciones_comprador = ["Todos"] + sorted(opciones_comprador)

#filtros
col1, col2, col3 = st.columns(3)
with col1:
    comprador = st.selectbox("👥 Compradores", opciones_comprador)
    # ---- Filtro ----
    if comprador == "Todos":
        df_filtrado = df_fsc.copy()
    else:
        df_filtrado = df_fsc[df_fsc['comprador'] == comprador]

with col2:
    categoria = st.selectbox("📊 Categoría",
                    ["General", "Ventas", "Marketing", "Producto"])
with col3:
    comparacion = st.selectbox("📈 Comparar con:",
                    ["Periodo anterior", "Año pasado", "Promedio"])

# Mostrar métricas en columnas (como un pequeño cuadro de mando)
st.subheader("Indicadores Clave (KPIs)")
##### KPIS ####
st.markdown("## 📈 KPIs Principales")
col1, col2, col3, col4 = st.columns(4)
with col1:
    montos_estimados = df_filtrado["monto estimado"].sum()
    st.metric("💰 Montos Estimados", 
            f"${montos_estimados:,.0f}",
            f"{np.random.uniform(5, 15):.1f}%")
    
with col2:
    Total_FSC = df_filtrado["newiD"].count()
    st.metric("📋 Total FSC", 
            f"{Total_FSC:,.0f}",
            f"{np.random.uniform(2, 8):.1f}%")

with col3:
    conversion_prom = df_filtrado["monto estimado"].mean()
    st.metric("🎯 Tasa de Conversión", 
            f"{conversion_prom:.2f}%",
            f"{np.random.uniform(0.5, 2):.1f}%")
    
with col4:
    cac_prom = df_fsc["monto estimado"].mean()
    st.metric("💸Costo de Adquisición", 
            f"${cac_prom:.2f}",
            f"-{np.random.uniform(1, 5):.1f}%")
st.subheader("Datos de Muestra")
st.dataframe(df_general, use_container_width=True)

st.markdown("## 📊 Análisis Detallado")


col1, col2 = st.columns(2)

with col1:

    # --- 1) Convertir fecha desde formato DD-MM-YYYY ---
    df_filtrado["fecha derivado"] = pd.to_datetime(
        df_filtrado["fecha derivado"],
        format="%d-%m-%Y",
        errors="coerce"
    )

    # --- 2) Crear columna de MES (año + mes) ---
    df_filtrado["mes"] = df_filtrado["fecha derivado"].dt.to_period("M").dt.to_timestamp()

    # --- 3) Agrupar por mes y contar formularios ---
    serie = (
        df_filtrado
        .groupby("mes")["newiD"]
        .count()
        .reset_index(name="cantidad")
        .sort_values("mes")
    )

    # --- 4) Gráfico de líneas mensual ---
    fig = px.line(
        serie,
        x="mes",
        y="cantidad",
        markers=True,
        title="Evolución Mensual de Formularios Derivados",
        labels={
            "mes": "Mes",
            "cantidad": "Cantidad de Formularios"
        }
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Mes",
        yaxis_title="Cantidad",
    )

    # --- 5) (Opcional) Mostrar etiquetas sobre cada punto ---
    fig.update_traces(text=serie["cantidad"], textposition="top center")

    st.plotly_chart(fig, use_container_width=True)
with col2:
    etapas = ['Visitantes', 'Leads', 'Oportunidades', 'Clientes']
    valores = [10000, 2500, 625, 156]
    funenel = go.Figure(go.Funnel(y=etapas, x=valores, textinfo="value+percent initial"))
    funenel.update_layout(title="🎯 Embudo de Conversión", height=400, template="plotly_white")
    st.plotly_chart(funenel, use_container_width=True)    












# --- 1. Conteo ---
conteo = (
    df_filtrado
    .groupby(["comprador","ProcesoCompra"])["newiD"]
    .count()
    .reset_index(name="formularios")
)

# --- 2. Orden por total de formularios ---
orden = (
    conteo
    .groupby("comprador")["formularios"]
    .sum()
    .sort_values(ascending=False)   # 👈 mayor → menor
    .index
)

# --- 3. Convertir a categoría ordenada ---
conteo["comprador"] = pd.Categorical(
    conteo["comprador"],
    categories=orden,
    ordered=True
)

# --- 4. ORDENAR explícitamente el dataframe ---
conteo = conteo.sort_values("comprador")   # 👈 clave

# --- 5. Gráfico ---
fig = px.bar(
    conteo,
    x="comprador",
    y="formularios",
    color="ProcesoCompra",
    text="formularios",
    title="Cantidad de Formularios por Comprador",
)

fig.update_layout(
    barmode="stack",
    xaxis_tickangle=-30,
    template="plotly_white"
)

fig.update_traces(textposition="inside")

st.plotly_chart(fig, use_container_width=True)