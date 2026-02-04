import pandas as pd
import re

def clean_pac_file(df):
    """Limpia el PAC: selecciona columnas, normaliza texto y quita duplicados."""
    # 1. Seleccionar columnas
    cols_necesarias = ["ID Proyecto", "OC Asociada Item 2026"]
    # Verificamos que existan
    if not all(col in df.columns for col in cols_necesarias):
        return None # O lanzar error
        
    df = df[cols_necesarias].copy()
    
    # 2. Eliminar vacíos
    df = df.dropna(subset=["OC Asociada Item 2026"])
    
    # 3. Función de normalización (Regex para dejar solo letras, números y guiones)
    def normalizar(texto):
        texto = str(texto).strip().upper()
        return re.sub(r'[^A-Z0-9-]', '', texto)

    df["OC_Normalizada"] = df["OC Asociada Item 2026"].apply(normalizar)
    
    # 4. Eliminar duplicados (nos interesa saber si la OC existe en el PAC, no cuántas veces)
    df_consolidado = df.drop_duplicates(subset=["OC_Normalizada"]).reset_index(drop=True)
    
    return df_consolidado