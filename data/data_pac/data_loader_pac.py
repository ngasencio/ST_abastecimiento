import streamlit as st
import pandas as pd
import os

# Importa la función de limpieza anterior (ajusta la ruta según donde guardes el archivo)
from data_clean_pac import clean_pac_file 

# Ajusta esta ruta si tu carpeta data está en otro nivel
RUTA_PAC = os.path.join("data", "data_pac", "PAC_2026.xlsx")

@st.cache_data(ttl=3600, show_spinner=False)
def load_pac_oc_consolidado():
    """Carga el Excel PAC y retorna el DF limpio y normalizado."""
    if not os.path.exists(RUTA_PAC):
        st.warning(f"No se encontró el archivo PAC en: {RUTA_PAC}")
        return None
        
    try:
        df_raw = pd.read_excel(RUTA_PAC)
        return clean_pac_file(df_raw)
    except Exception as e:
        st.error(f"Error leyendo PAC: {e}")
        return None