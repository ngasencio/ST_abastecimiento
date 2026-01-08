
import streamlit as st
import pandas as pd
import os

# --- Configuración de Archivo y Ruta ---
CARPETA_DATOS = "data"
NOMBRE_ARCHIVO = "FSC 2025.xlsx"
# Usaremos el nombre que especificaste para la hoja:
NOMBRE_HOJA = "FSC 2025" 

RUTA_COMPLETA_ARCHIVO = os.path.join(CARPETA_DATOS, NOMBRE_ARCHIVO)

# --- FUNCIÓN PÚBLICA PARA CARGAR DATOS ---
@st.cache_data
def load_fsc_data():
    """
    Carga los datos del archivo FSC 2025.xlsx (hoja 'FSC 2025') en un DataFrame.
    Usa st.cache_data para asegurar que la lectura del archivo sea rápida y única.
    """
    if not os.path.exists(RUTA_COMPLETA_ARCHIVO):
        st.error(f"Error: El archivo '{NOMBRE_ARCHIVO}' no se encontró en la ruta '{RUTA_COMPLETA_ARCHIVO}'.")
        return None

    try:
        # Lee el archivo y la hoja específica
        df = pd.read_excel(RUTA_COMPLETA_ARCHIVO, sheet_name=NOMBRE_HOJA)
        
        # Opcional: Mostrar éxito solo una vez, no en cada página
        # st.success("Datos FSC 2025 cargados exitosamente.") 
        
        return df
    
    except ValueError:
        st.error(f"Error: No se encontró la hoja '{NOMBRE_HOJA}' dentro del archivo '{NOMBRE_ARCHIVO}'.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al leer el archivo: {e}")
        return None