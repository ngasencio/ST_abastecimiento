import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# --- EN TU ARCHIVO DE STREAMLIT ---
from api.Consolidar_OC import ejecutar_consolidacion_oc
# Cargar las bases
bases_oc = ejecutar_consolidacion_oc()
df_oc_res = bases_oc["RESUMEN"]

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
            📊 Ordenes de Compra DSSO
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega la planificación del PAC 2026 buscando su cumplimiento de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown("## 🛒 Órdenes de Compra Consolidadas")

with st.expander("📅 Ver Tabla Maestra de OCs"):
    st.dataframe(df_oc_res.style.format({
        # Formatos de Dinero
        "TotalNeto": "${:,.0f}".format,
        "Total": "${:,.0f}".format,
        "Impuestos": "${:,.0f}".format,
        # Formatos de Texto/ID
        "Codigo": str,
        "CodigoLicitacion": str,
        "Estado": str,
        # Formato de Porcentajes
        "PorcentajeIva": "{:.1f}%".format,
    }), height=400, use_container_width=True)