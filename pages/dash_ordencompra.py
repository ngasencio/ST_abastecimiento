import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime


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