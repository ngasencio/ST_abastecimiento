import os
import glob
import pandas as pd
import warnings

def load_anexo1_data() -> pd.DataFrame:
    """
    Busca automáticamente todos los archivos 'maestro_*.csv' en el directorio
    donde se encuentra este script y los consolida en un único DataFrame.


https://app.powerbi.com/view?r=eyJrIjoiMjAxNTRmYmEtMDlkNi00NmZlLWI5Y2YtOWE0ZDJmNGM3NWQyIiwidCI6Ijc0NDRkNTdjLTA0YzgtNDJkZS1hMDgxLWRkODk5YWYyOTIyZSIsImMiOjR9


https://app.powerbi.com/view?r=eyJrIjoiMjAxNTRmYmEtMDlkNi00NmZlLWI5Y2YtOWE0ZDJmNGM3NWQyIiwidCI6Ijc0NDRkNTdjLTA0YzgtNDJkZS1hMDgxLWRkODk5YWYyOTIyZSIsImMiOjR9


    """
    # El base_dir es el directorio donde está este archivo (data/data_anexo1)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Buscar todos los CSVs maestros en la carpeta base
    archivos_maestros = glob.glob(os.path.join(base_dir, "maestro_*.csv"))
    
    if not archivos_maestros:
        warnings.warn(f"No se encontraron archivos 'maestro_*.csv' en {base_dir}.")
        return pd.DataFrame()
    
    frames = []
    for filepath in archivos_maestros:
        try:
            # Leer el CSV asegurando codificación UTF-8
            df = pd.read_csv(filepath, encoding="utf-8-sig", dtype={"Nivel": str})
            # Asegurarse de que el 'Nivel' sea tratado correctamente como numérico/string
            frames.append(df)
        except Exception as e:
            warnings.warn(f"Error al cargar {filepath}: {e}")
            
    if not frames:
        return pd.DataFrame()
        
    df_consolidado = pd.concat(frames, ignore_index=True)
    return df_consolidado

if __name__ == "__main__":
    print("Prueba de carga de consolidado de archivos Anexo 1:")
    df_prueba = load_anexo1_data()
    if not df_prueba.empty:
        print(f"✔ Consolidado cargado exitosamente. Filas totales: {len(df_prueba)}")
        print(f"✔ Establecimientos encontrados: {df_prueba['Establecimiento'].unique()}")
        print(f"✔ Meses encontrados: {df_prueba['Fecha'].unique()}")
        print("\nPrimeras 5 filas:")
        print(df_prueba.head())
    else:
        print("⚠ No se pudo cargar el consolidado porque no hay datos.")
