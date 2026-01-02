# pages/dash_general.py

import streamlit as st
import pandas as pd
import numpy as np

# Título y encabezado
st.title("📊 Dashboard General")
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

# Mostrar métricas en columnas (como un pequeño cuadro de mando)
st.subheader("Indicadores Clave (KPIs)")
col1, col2, col3 = st.columns(3)

col1.metric("💰 Ingresos Totales", "$5.5M", "12%")
col2.metric("👥 Usuarios Activos", "15K", "-3%")
col3.metric("🎯 Tasa Conversión", "2.8%", "0.5%")

st.subheader("Datos de Muestra")
st.dataframe(df_general, use_container_width=True)