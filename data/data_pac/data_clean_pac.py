import pandas as pd
import re

def normalizar_texto(texto):
    """
    Estandariza un string: Mayúsculas, sin espacios, solo alfanumérico.
    Ejemplo: ' oc-123 ' -> 'OC123'
    """
    if pd.isna(texto):
        return ""
    # Convertir a string, mayúsculas y quitar espacios extremos
    texto = str(texto).strip().upper()
    # Regex: Mantener solo letras y números (eliminamos guiones para evitar errores de tipeo)
    # Si tus OCs estrictamente usan guiones, cambia a r'[^A-Z0-9-]'
    texto = re.sub(r'[^A-Z0-9]', '', texto) 
    return texto

def clean_pac_file(df):
    """
    Limpia el DataFrame del PAC, selecciona columnas y quita duplicados.
    """
    # 1. Validar columnas requeridas
    cols_req = ["ID Proyecto", "OC Asociada Item 2026"]
    if not all(col in df.columns for col in cols_req):
        return pd.DataFrame() # Retorna vacío si falla
        
    df = df[cols_req].copy()
    
    # 2. Eliminar filas sin OC
    df = df.dropna(subset=["OC Asociada Item 2026"])
    
    # 3. Normalizar la columna clave (Creamos columna interna para el cruce)
    df["OC_KEY_PAC"] = df["OC Asociada Item 2026"].apply(normalizar_texto)
    
    # 4. Deduplicar por OC (Una OC solo puede estar una vez en el listado maestro para el cruce)
    # Mantenemos el primer ID Proyecto que aparezca
    df_consolidado = df.drop_duplicates(subset=["OC_KEY_PAC"], keep='first')
    
    return df_consolidado