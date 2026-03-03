import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from style.ui import cargar_css

cargar_css()
# ==========================================================
# 1. CARGA DE DATOS
# ==========================================================

# ==========================================================
# 3. HEADER
# ==========================================================

st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #138AEC, #3E9FEF);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            🏢 Activos Fijos
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Visión ejecutiva del desempeño de los activos fijos en el periodo.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)