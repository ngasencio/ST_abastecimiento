import streamlit as st
import pandas as pd
import os

# Importa la función de limpieza anterior (ajusta la ruta según donde guardes el archivo)
from data_cleaning import clean_pac_file 

RUTA_PAC = os.path.join("data", "data_pac", "PAC_2026.xlsx")

@st.cache_data(ttl=3600)
def load_pac_consolidado():
    if not os.path.exists(RUTA_PAC):
        return None
    try:
        df = pd.read_excel(RUTA_PAC)
        return clean_pac_file(df)
    except Exception as e:
        st.error(f"Error cargando PAC: {e}")
        return None