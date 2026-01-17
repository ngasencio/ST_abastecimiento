# pages/licitaciones.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Importación Correcta (basada en tu estructura de carpetas)###
from api.Consolidar_Licitaciones import ejecutar_consolidacion_LI

# 2. Llamada segura
# Esto ejecuta la lógica de unión y limpieza
bases = ejecutar_consolidacion_LI()

# 3. Asignación defensiva (evita el KeyError)
df_res = bases.get("RESUMEN", pd.DataFrame())
df_det = bases.get("DETALLES", pd.DataFrame())
# --- INYECCIÓN DE CSS (Tus estilos) ---

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
            📊 Licitaciones DSSO
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega la cantidad y detalle de licitaciones en curso.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("## 📅 Resumen General de Licitaciones")
with st.expander("🔍 Ver Datos Maestros (Resumen)", expanded=True):
        # Aplicamos formato solo a las columnas que existen
        st.dataframe(
            df_res.style.format({
                "MontoEstimado": "${:,.0f}".format,
                "CodigoLicitacion": str,
                "Estado": str
            }, na_rep="-"), 
            height=400, 
            use_container_width=True
        )