import pandas as pd
import re

def validate_oc_in_pac(df_oc, df_pac):
    """
    df_oc: Tu DataFrame df_MaestroOC_Resumen
    df_pac: El DataFrame que sale de load_pac_consolidado
    """
    if df_pac is None or df_oc.empty:
        df_oc["En_PAC_2026"] = "No Verificado"
        df_oc["ID_Proyecto_PAC"] = "N/A"
        return df_oc

    # 1. Normalizar la columna 'Codigo' de tus OCs reales para igualar formato
    def normalizar(texto):
        texto = str(texto).strip().upper()
        return re.sub(r'[^A-Z0-9-]', '', texto)
    
    # Creamos columna temporal para el merge
    df_oc["Codigo_Norm_Temp"] = df_oc["Codigo"].apply(normalizar)
    
    # 2. Merge (Left Join) para traer info del PAC
    df_merged = df_oc.merge(
        df_pac[["OC_Normalizada", "ID Proyecto"]],
        left_on="Codigo_Norm_Temp",
        right_on="OC_Normalizada",
        how="left"
    )
    
    # 3. Crear columnas finales
    # Si 'OC_Normalizada' no es nulo, es porque hizo match
    df_merged["En_PAC_2026"] = df_merged["OC_Normalizada"].notna().map({True: "Sí", False: "No"})
    df_merged["ID_Proyecto_PAC"] = df_merged["ID Proyecto"].fillna("No Planificado")
    
    # 4. Limpieza de columnas temporales
    df_merged.drop(columns=["Codigo_Norm_Temp", "OC_Normalizada", "ID Proyecto"], inplace=True)
    
    return df_merged