import pandas as pd
import glob
import os
import streamlit as st

# Obtiene la ruta absoluta de la carpeta donde vive ESTE script (data_pac_manager.py)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Como los excel están en la misma carpeta, la ruta de datos es la misma
DATA_PATH = CURRENT_DIR

def _normalizar_oc(serie):
    """Función auxiliar para limpiar códigos de OC. Convierte a string, mayúsculas, quita espacios y caracteres extraños."""
    return serie.astype(str).str.strip().str.upper().str.replace(r'[^A-Z0-9-]', '', regex=True)

def _detectar_columna_oc(df):
    """
    Busca dinámicamente la columna que contiene la OC, 
    ya que en PAC22 puede llamarse diferente a PAC26.
    """
    # Buscamos columnas que contengan "OC Asociada" o "Orden de Compra"
    posibles = [c for c in df.columns if "OC Asociada" in c or "Orden de Compra" in c]
    if posibles:
        return posibles[0] # Devolvemos la primera coincidencia
    return None

@st.cache_data(ttl=3600, show_spinner="Consolidando Planes Anuales (2022-2026)...")
def load_maestro_pac_consolidado():
    """
    Carga todos los excels de PAC, estandariza columnas y consolida en un solo DF.
    """
    # 1. Buscar todos los archivos Excel en la ruta (PAC*.xls*)
    patron = os.path.join(DATA_PATH, "PAC*.xls*")
    archivos = glob.glob(patron)
    
    if not archivos:
        st.error(f"No se encontraron archivos PAC en {DATA_PATH}")
        return pd.DataFrame(columns=["ID Proyecto", "OC_Normalizada"])

    lista_dfs = []

    for archivo in archivos:
        try:
            # Leemos el archivo
            df_temp = pd.read_excel(archivo)
            
            # 2. Detectar columnas dinámicamente
            col_oc = _detectar_columna_oc(df_temp)
            col_id = "ID Proyecto" # Asumimos que esta se mantiene constante
            
            if col_oc and col_id in df_temp.columns:
                # Seleccionamos solo lo necesario
                df_clean = df_temp[[col_id, col_oc]].copy()
                
                # Renombramos para estandarizar el maestro final
                df_clean.rename(columns={col_oc: "OC_Normalizada"}, inplace=True)
                
                # Limpiamos vacíos clave
                df_clean.dropna(subset=["OC_Normalizada"], inplace=True)
                
                # Normalizamos el texto de la OC inmediatamente
                df_clean["OC_Normalizada"] = _normalizar_oc(df_clean["OC_Normalizada"])
                
                lista_dfs.append(df_clean)
                
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")
            continue

    if not lista_dfs:
        return pd.DataFrame()

    # 3. Consolidar (Concatenar)
    MAESTRO_PAC_MP = pd.concat(lista_dfs, ignore_index=True)

    # 4. Deduplicación inteligente (Objetivo 2)
    # Eliminamos si el par (Proyecto, OC) es idéntico.
    MAESTRO_PAC_MP = MAESTRO_PAC_MP.drop_duplicates(subset=["ID Proyecto", "OC_Normalizada"])

    return MAESTRO_PAC_MP

def enriquecer_con_pac(df_filtrado, maestro_pac):
    """
    Cruza el dataframe de OCs del dashboard con el Maestro PAC.
    """
    if df_filtrado.empty or maestro_pac.empty:
        df_filtrado["PAC"] = "No Enlazada"
        return df_filtrado

    # Aseguramos que la columna de enlace en df_filtrado esté normalizada igual
    # Asumimos que la columna en df_filtrado se llama 'Codigo' o 'CodigoOC'
    col_key = "Codigo" if "Codigo" in df_filtrado.columns else "CodigoOC"
    
    # Creamos una serie temporal para comparar (no sobreescribimos la original visual)
    oc_keys = _normalizar_oc(df_filtrado[col_key])
    
    # 5. Clasificación Vectorizada (Objetivo 3)
    # Usamos .isin() que es ultra rápido
    mask_encontrada = oc_keys.isin(maestro_pac["OC_Normalizada"])
    
    df_filtrado["PAC"] = "No Enlazada"
    df_filtrado.loc[mask_encontrada, "PAC"] = "Enlazada"
    
    # Opcional: Si quieres traer el ID del Proyecto al dashboard
    # Hacemos un merge rápido solo para traer el ID Proyecto
    # (Esto es un paso extra que añade valor visual)
    df_merge = df_filtrado.merge(
        maestro_pac, 
        left_on=oc_keys, 
        right_on="OC_Normalizada", 
        how="left"
    )
    # Si hubo duplicados en PAC (misma OC en 2 proyectos), drop_duplicates lo maneja
    df_merge = df_merge.drop_duplicates(subset=[col_key])
    
    return df_merge