import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns

# ===== CARGAR CSS =====
def cargar_css():
    with open("style/style.css", encoding="utf-8") as f:
      st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css()


# 1. Importar el módulo completo
from data.data_loader import load_fsc_data
df_fsc = load_fsc_data()


st.set_page_config(
    page_title="Portal DSSO",
    page_icon="logosso.jpg", 
    layout="wide",
    initial_sidebar_state="expanded")

# Importas Datos
def generar_datos_empresa():
    fechas = pd.date_range(start="2024-01-01", end=datetime.today(), freq='D')
    datos = {
        "Fecha": fechas,
        "ingresos_diarios": np.random.normal(50000, 15000, size=len(fechas)),
        "usuarios_activos": np.random.normal(12000, 3000, size=len(fechas)),
        "conversion_rate": np.random.normal(2.5, 0.8, size=len(fechas)),
        "costo_adquisicion": np.random.normal(45, 12, size=len(fechas)),
        "ltv_cliente": np.random.normal(180, 40, size=len(fechas)),
    }
    
    df=pd.DataFrame(datos)
    df["ingresos_diarios"] *= (1+ np.arange(len(df)) * 0.0001) #tendencia creciente
    return df

df = generar_datos_empresa()

#Titulo
st.markdown(
    """
    <div style="
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #0063AE, #0076D1);
        color: white;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 28px; font-weight: 800;">
            📊 Panel Formularios Solicitud de Compra
        </div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">
            Este módulo entrega una visión general de los formularios de solicitud de compra.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
