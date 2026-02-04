import pandas as pd
from data_clean_pac import normalizar_texto

def validate_oc_in_pac(df_ordenes_compra, df_pac_consolidado):
    """
    Cruza el DF de OCs con el DF del PAC y añade columna de validación.
    """
    if df_pac_consolidado is None or df_pac_consolidado.empty:
        df_ordenes_compra["En_PAC_2026"] = "No Verificado"
        df_ordenes_compra["ID_Proyecto_PAC"] = "N/A"
        return df_ordenes_compra

    # 1. Crear llave temporal normalizada en las OCs (usando la misma lógica)
    # Asumimos que la columna en tus OCs se llama 'Codigo' o 'CodigoOC'
    col_oc = "Codigo" if "Codigo" in df_ordenes_compra.columns else "CodigoOC"
    
    df_ordenes_compra["OC_KEY_TEMP"] = df_ordenes_compra[col_oc].apply(normalizar_texto)
    
    # 2. Merge (Left Join)
    # Traemos 'ID Proyecto' del PAC para tener contexto
    df_merged = df_ordenes_compra.merge(
        df_pac_consolidado[["OC_KEY_PAC", "ID Proyecto"]],
        left_on="OC_KEY_TEMP",
        right_on="OC_KEY_PAC",
        how="left"
    )
    
    # 3. Crear columna booleana visual ("Sí" / "No")
    # Si 'OC_KEY_PAC' no es nulo, hubo coincidencia
    df_merged["En_PAC_2026"] = df_merged["OC_KEY_PAC"].notna().apply(lambda x: "Sí" if x else "No")
    df_merged["ID_Proyecto_PAC"] = df_merged["ID Proyecto"].fillna("No Planificado")
    
    # 4. Limpieza de columnas auxiliares
    df_merged.drop(columns=["OC_KEY_TEMP", "OC_KEY_PAC", "ID Proyecto"], inplace=True)
    
    return df_merged