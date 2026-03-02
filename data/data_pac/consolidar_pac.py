import pandas as pd
import glob
import os

#https://www.mercadopublico.cl/PlanDeComprasII/Proyecto/Index?agno=2022


def consolidar_excels_a_maestro():
    # 1. Identificar la carpeta del script
    folder_path = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(folder_path, "PAC*.xls*")
    archivos = glob.glob(pattern)
    
    print(f"🔍 Buscando en: {folder_path}")
    
    if not archivos:
        print(f"❌ No se encontraron archivos 'PAC*.xls*'.")
        return

    print(f"📂 Archivos encontrados: {len(archivos)}")
    
    lista_dfs = []
    COL_ID = "ID Proyecto"
    # Nombre que le daremos a la columna unificada en el CSV final
    COL_OC_ESTANDAR = "OC Asociada PAC"

    for archivo in archivos:
        try:
            # Determinar motor según extensión
            ext = os.path.splitext(archivo)[1].lower()
            motor = 'xlrd' if ext == '.xls' else 'openpyxl'
            
            df_temp = pd.read_excel(archivo, engine=motor)
            df_temp.columns = df_temp.columns.str.strip() # Limpiar espacios en nombres
            
            # --- BÚSQUEDA DINÁMICA DE LA COLUMNA OC ---
            # Buscamos una columna que empiece con "OC Asociada Item"
            col_oc_encontrada = [c for c in df_temp.columns if c.startswith("OC Asociada Item")]
            
            if COL_ID in df_temp.columns and col_oc_encontrada:
                nombre_col_original = col_oc_encontrada[0] # Tomamos la primera coincidencia
                
                # Seleccionar solo las dos columnas
                df_filtrado = df_temp[[COL_ID, nombre_col_original]].copy()
                
                # Renombrar la columna del año (2022, 2023...) a un nombre común
                df_filtrado.rename(columns={nombre_col_original: COL_OC_ESTANDAR}, inplace=True)
                
                # --- LIMPIEZA DE VACÍOS ---
                # 1. Eliminar filas donde la OC sea realmente Nula (NaN)
                df_filtrado.dropna(subset=[COL_OC_ESTANDAR], inplace=True)
                
                # 2. Convertir a string y limpiar espacios
                df_filtrado[COL_OC_ESTANDAR] = df_filtrado[COL_OC_ESTANDAR].astype(str).str.strip()
                
                # 3. Eliminar filas que quedaron como texto vacío "" o palabras como "nan" o "None"
                invalidos = ["", "nan", "None", "nan", "0", "0.0"]
                df_filtrado = df_filtrado[~df_filtrado[COL_OC_ESTANDAR].isin(invalidos)]
                
                lista_dfs.append(df_filtrado)
                print(f"✅ Procesado: {os.path.basename(archivo)} (Columna detectada: {nombre_col_original})")
            else:
                print(f"⚠️ Saltado: {os.path.basename(archivo)} (No se encontró la columna ID o OC)")
                
        except Exception as e:
            print(f"❌ Error en {os.path.basename(archivo)}: {e}")

    if not lista_dfs:
        print("🚫 No hay datos válidos para consolidar.")
        return

    # Unificar todos los dataframes
    df_maestro = pd.concat(lista_dfs, ignore_index=True)
    
    # Eliminar duplicados considerando ambas columnas (ID Proyecto + OC)
    total_antes = len(df_maestro)
    df_maestro = df_maestro.drop_duplicates(subset=[COL_ID, COL_OC_ESTANDAR])
    
    # Guardar maestro
    output_path = os.path.join(folder_path, "OCPAC_Maestro.csv")
    df_maestro.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print("-" * 50)
    print(f"💾 MAESTRO CREADO: {output_path}")
    print(f"📊 Registros finales: {len(df_maestro)}")
    print(f"✨ Se limpiaron {total_antes - len(df_maestro)} duplicados.")

if __name__ == "__main__":
    consolidar_excels_a_maestro()