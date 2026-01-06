# pages/dash_general.py

import streamlit as st
import pandas as pd
import numpy as np

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