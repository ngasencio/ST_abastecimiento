# pages/dash_ventas.py

import streamlit as st
import pandas as pd
import numpy as np

# Título y encabezado
st.title("💰 Análisis de Ventas")
st.header("Rendimiento, Pipeline y Cierre")

st.markdown("""
Aquí se profundiza en las métricas relacionadas con el ciclo de ventas,
el desempeño del equipo y la distribución geográfica.
""")

# Simulación de datos de ventas por región
data_ventas = {
    'Región': ['Norte', 'Sur', 'Este', 'Oeste'],
    'Ventas Mensuales (K)': [250, 180, 120, 300],
    'Meta Cumplida (%)': [95, 110, 85, 125]
}

df_ventas = pd.DataFrame(data_ventas)

# Mostrar una tabla de detalle
st.subheader("Desempeño Regional")
st.dataframe(df_ventas, use_container_width=True)

# Indicador de estado
st.info("🚨 Alerta: La Región Este está por debajo de la meta de ventas.")