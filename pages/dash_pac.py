# pages/dash_compras.py

import streamlit as st
import pandas as pd
import numpy as np

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
            📊 Plan Anual de Compras 2026
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega la planificación del PAC 2026 buscando su cumplimiento de adquisiciones.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

#st.markdown("""Sub""")

# Simulación de datos de compras


#df_compras = pd.DataFrame(data_compras)

# Métricas específicas de compras
#col1, col2 = st.columns(2)
#col1.metric("💸 Ahorro Logrado", "$15,000", "5%")
#col2.metric("⏱️ Tiempo Prom. Entrega", "4 días", "-1 día")

