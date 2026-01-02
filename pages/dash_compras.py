# pages/dash_compras.py

import streamlit as st
import pandas as pd
import numpy as np

# Título y encabezado
st.title("🛒 Gestión de Compras")
st.header("Análisis de Costos y Proveedores")

st.markdown("""
Monitoreo de la eficiencia en la adquisición, el costo promedio por unidad
y la calidad del servicio de los proveedores.
""")

# Simulación de datos de compras
data_compras = {
    'Artículo': ['Materia Prima A', 'Componente B', 'Servicio C'],
    'Costo Promedio Unitario': [15.50, 4.25, 1200.00],
    'Volumen Comprado': [5000, 25000, 12],
    'Proveedor Principal': ['Alpha Corp', 'Beta Tools', 'Gama Tech']
}

df_compras = pd.DataFrame(data_compras)

# Métricas específicas de compras
col1, col2 = st.columns(2)
col1.metric("💸 Ahorro Logrado", "$15,000", "5%")
col2.metric("⏱️ Tiempo Prom. Entrega", "4 días", "-1 día")

st.subheader("Detalle de Compras Recientes")
st.dataframe(df_compras, use_container_width=True)