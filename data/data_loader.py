import streamlit as st
import pandas as pd
import os
import glob

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
CARPETA_DATOS = "data"
# ===============================
# FSC 2025
# ===============================
CARPETA_FSC = "data_fsc"
NOMBRE_ARCHIVO_FSC = "FSC 2025.xlsx"
HOJA_FSC = "FSC 2025"

RUTA_FSC = os.path.join(CARPETA_DATOS,CARPETA_FSC, NOMBRE_ARCHIVO_FSC)

@st.cache_data
def load_fsc_data():
    """Carga datos del archivo FSC 2025.xlsx"""
    if not os.path.exists(RUTA_FSC):
        st.error(f"No se encontró el archivo: {RUTA_FSC}",encoding="utf-8")
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
CARPETA_PLANIFICACION_PAC = "data_planificacionPac"
NOMBRE_ARCHIVO_PAC = "PlanificacionPAC26.xlsx"
HOJA_PAC = "OficialReal"

RUTA_PAC = os.path.join(CARPETA_DATOS,CARPETA_PLANIFICACION_PAC, NOMBRE_ARCHIVO_PAC)

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

# =============================================================================
# PAC26 - PIPELINE DE NORMALIZACIÓN
# =============================================================================

@st.cache_data
def load_ocpac_master():
    df_OCPAC_Maestro = pd.read_csv(os.path.join(CARPETA_DATOS, "data_pac/OCPAC_Maestro.csv"), dtype={"OC Asociada PAC": str})
    return df_OCPAC_Maestro

# =============================================================================
# FACTURAS - PIPELINE DE NORMALIZACIÓN
# =============================================================================
CARPETA_FACTURAS = os.path.join("data", "Data_Facturas")

@st.cache_data
def load_facturas_data():
    """
    Consolida, limpia y normaliza archivos Excel de facturas desde data/Data_Facturas/
    """
    # 1. Identificar archivos Excel en la ruta
    patron = os.path.join(CARPETA_FACTURAS, "*.xls")
    archivos = glob.glob(patron)
    
    if not archivos:
        st.error(f"No se encontraron archivos Excel en {CARPETA_FACTURAS}")
        return None

    lista_df = []
    
    for archivo in archivos:
        try:
            df_temp = pd.read_excel(archivo)
            # Añadimos columna de origen para trazabilidad
            df_temp['origen_archivo'] = os.path.basename(archivo)
            lista_df.append(df_temp)
        except Exception as e:
            st.warning(f"Error al leer {archivo}: {e}")

    if not lista_df:
        return None

    # 2. Combinar archivos
    df = pd.concat(lista_df, ignore_index=True)

    # 3. NORMALIZACIÓN Y LIMPIEZA
    try:
        # --- Fechas ---
        # Convertimos a datetime, los errores se vuelven NaT (Not a Time)
        for col_fecha in ['fecha_ingreso', 'fecha_aceptacion']:
            if col_fecha in df.columns:
                df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')

        # --- Montos ---
        # Quitamos caracteres especiales si existen y convertimos a numérico
        if 'monto_total' in df.columns:
            df['monto_total'] = pd.to_numeric(df['monto_total'], errors='coerce').fillna(0)

        # --- Texto / Categorías ---
        # Normalizamos a mayúsculas y quitamos espacios extra
        cols_texto = ['tipo_documento', 'estado_acepta', 'estado_sii']
        for col in cols_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                # Reemplazar valores nulos representados como texto
                df[col] = df[col].replace(['NAN', 'NONE', ''], 'SIN INFORMACIÓN')

        # --- Folio OC ---
        # Aseguramos que sea string para cruces con la base de órdenes de compra
        if 'folio_oc' in df.columns:
            df['folio_oc'] = df['folio_oc'].astype(str).str.strip()

        # --- Validación de URI ---
        # Marcamos como inválidas las URIs que no empiecen con http
        if 'uri' in df.columns:
            df['uri_valida'] = df['uri'].apply(lambda x: str(x).startswith('http'))

        return df

    except Exception as e:
        st.error(f"Error crítico en el pipeline de normalización: {e}")
        return None