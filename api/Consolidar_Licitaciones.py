import pandas as pd
import pathlib
import datetime as dt
import os

# ==========================================
# CONFIGURACIÓN DE RUTAS (Ajustadas a tu PC)
# ==========================================
ESCRITORIO = pathlib.Path.home() / "Desktop"
CARPETA_LICITACIONES = ESCRITORIO / "ST_abastecimiento" / "ST_abastecimiento" / "api" / "LI_DSSO"
CARPETA_CONSOLIDADO = ESCRITORIO / "ST_abastecimiento" / "ST_abastecimiento" / "api" / "LI_DSSO" / "CONSOLIDADO"

def limpiar_y_estandarizar(df):
    """Realiza la limpieza profunda de los datos."""
    if df.empty:
        return df
    
    # 1. Quitar espacios en blanco al inicio y final de todos los textos
    df_obj = df.select_dtypes(['object'])
    df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip())
    
    # 2. Reemplazar saltos de línea y puntos y coma que rompen el CSV
    df = df.replace({'\n': ' ', '\r': ' ', ';': ','}, regex=True)
    
    # 3. Eliminar duplicados exactos (muy común si se descarga el mismo día 2 veces)
    df = df.drop_duplicates()
    
    # 4. Formatear todas las columnas que contienen la palabra 'Fecha'
    columnas_fecha = [c for c in df.columns if 'Fecha' in c]
    for col in columnas_fecha:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d-%m-%Y')
        
    return df

def ejecutar_consolidacion_LI():
    # ... (rutas y carpetas igual) ...
    
    todos_los_archivos = list(CARPETA_LICITACIONES.glob("*.csv"))
    
    grupos = {
        "RESUMEN": [f for f in todos_los_archivos if "RESUMEN" in f.name],
        "DETALLES": [f for f in todos_los_archivos if "DETALLES" in f.name]
    }
    
    # IMPORTANTE: Inicializamos con DataFrames vacíos para evitar el KeyError
    bases_listas = {
        "RESUMEN": pd.DataFrame(),
        "DETALLES": pd.DataFrame()
    }

    print(f"\n>>> INICIANDO CONSOLIDACIÓN")

    for tipo, lista_rutas in grupos.items():
        if not lista_rutas:
            print(f"   ⚠ No se encontraron archivos para: {tipo}")
            continue # Aquí es donde antes fallaba porque no agregaba la llave
            
        print(f"   Procesando {len(lista_rutas)} archivos de {tipo}...")
        
        lista_df = [pd.read_csv(f, sep=";", encoding="utf-8-sig") for f in lista_rutas]
        df_unido = pd.concat(lista_df, ignore_index=True)
        
        df_limpio = limpiar_y_estandarizar(df_unido)
        
        ruta_guardado = CARPETA_CONSOLIDADO / f"MASTER_LICITACIONES_{tipo}.csv"
        df_limpio.to_csv(ruta_guardado, sep=";", index=False, encoding="utf-8-sig")
        
        # Guardamos el resultado (sobrescribe el DataFrame vacío inicial)
        bases_listas[tipo] = df_limpio
        print(f"   ✅ Master {tipo} guardado exitosamente.")

    return bases_listas

# Esto permite ejecutar el archivo solo haciendo doble clic
if __name__ == "__main__":
    try:
        ejecutar_consolidacion()
        input("\nPresiona Enter para cerrar...")
    except Exception as e:
        print(f"\n❌ Error en la consolidación: {e}")
        input()