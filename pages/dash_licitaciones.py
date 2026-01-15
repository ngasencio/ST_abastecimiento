# pages/licitaciones.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Importamos la función desde tu archivo consolidacion.py
from api.Consolidar_Licitaciones import ejecutar_consolidacion_LI

# ... (imports y carga de bases) ...
bases = ejecutar_consolidacion_LI()

df_res = bases.get("RESUMEN", pd.DataFrame())
df_det = bases.get("DETALLES", pd.DataFrame())

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
with st.expander("🔍 Ver Datos Maestros (Resumen)"):
    st.dataframe(df_res.style.format({
        # Formato Moneda
        "MontoEstimado": "${:,.0f}".format,
        # Formato Texto/Categoría (asegurar que se vean como strings)
        "CodigoLicitacion": str,
        "Estado": str,
        "FuenteFinanciamiento": str,
        # Nota: Las fechas ya vienen formateadas como dd-mm-yyyy desde consolidacion.py
        # Si las convertiste a datetime en Streamlit, usa: 
        # "FechaCierre": lambda x: x.strftime("%d-%m-%Y") 
    }), height=400, use_container_width=True)