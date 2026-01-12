import streamlit as st
import pandas as pd
import os

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
CARPETA_DATOS = "data"

# ===============================
# FSC 2025
# ===============================
NOMBRE_ARCHIVO_FSC = "FSC 2025.xlsx"
HOJA_FSC = "FSC 2025"

RUTA_FSC = os.path.join(CARPETA_DATOS, NOMBRE_ARCHIVO_FSC)

@st.cache_data
def load_fsc_data():
    """Carga datos del archivo FSC 2025.xlsx"""
    if not os.path.exists(RUTA_FSC):
        st.error(f"No se encontró el archivo: {RUTA_FSC}")
        return None

    try:
        return pd.read_excel(RUTA_FSC, sheet_name=HOJA_FSC)
    except ValueError:
        st.error(f"No existe la hoja '{HOJA_FSC}' en {NOMBRE_ARCHIVO_FSC}")
        return None
    except Exception as e:
        st.error(f"Error al leer FSC: {e}")
        return None


# ===============================
# PAC26
# ===============================
NOMBRE_ARCHIVO_PAC = "PAC26.xlsx"
HOJA_PAC = "OficialReal"

RUTA_PAC = os.path.join(CARPETA_DATOS, NOMBRE_ARCHIVO_PAC)

@st.cache_data
def load_pac26_data():
    """Carga datos del archivo PAC26.xlsx (hoja OficialReal)"""
    if not os.path.exists(RUTA_PAC):
        st.error(f"No se encontró el archivo: {RUTA_PAC}")
        return None

    try:
        return pd.read_excel(RUTA_PAC, sheet_name=HOJA_PAC)
    except ValueError:
        st.error(f"No existe la hoja '{HOJA_PAC}' en {NOMBRE_ARCHIVO_PAC}")
        return None
    except Exception as e:
        st.error(f"Error al leer PAC26: {e}")
        return None
