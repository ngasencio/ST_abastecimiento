import pandas as pd
import pathlib
import datetime as dt
import os

# ==========================================
# CONFIGURACIÓN DE RUTAS CORREGIDA
# ==========================================

# 1. Detectamos dónde está el script actual (debería estar en la carpeta 'api')
RUTA_API = pathlib.Path(__file__).parent.absolute()

# 2. Definimos las rutas basándonos en la estructura de carpetas interna
# Esto busca la carpeta LI_DSSO que está dentro de 'api'
CARPETA_LICITACIONES = RUTA_API / "LI_DSSO" / "DIARIO"
CARPETA_CONSOLIDADO = CARPETA_LICITACIONES / "CONSOLIDADO"

def limpiar_y_estandarizar(df):
    if df.empty: return df
    
    # Limpieza de textos y caracteres especiales
    df_obj = df.select_dtypes(['object'])
    df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip())
    df = df.replace({'\n': ' ', '\r': ' ', ';': ','}, regex=True)
    df = df.drop_duplicates()
    
    # Formateo de fechas
    columnas_fecha = [c for c in df.columns if 'Fecha' in c]
    for col in columnas_fecha:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d-%m-%Y')
        
    return df

def ejecutar_consolidacion_LI():
    CARPETA_CONSOLIDADO.mkdir(parents=True, exist_ok=True)
    
    # CAMBIO CLAVE: rglob busca dentro de LI_DSSO y también dentro de DIARIO
    todos_los_archivos = list(CARPETA_LICITACIONES.rglob("*.csv"))
    
    # Filtrar para no procesar los archivos que ya están en CONSOLIDADO
    todos_los_archivos = [f for f in todos_los_archivos if "CONSOLIDADO" not in str(f)]
    
    grupos = {
        "RESUMEN": [f for f in todos_los_archivos if "RESUMEN" in f.name.upper()],
        "DETALLES": [f for f in todos_los_archivos if "DETALLES" in f.name.upper()]
    }
    
    bases_listas = {
        "RESUMEN": pd.DataFrame(),
        "DETALLES": pd.DataFrame()
    }

    print(f"\n>>> INICIANDO CONSOLIDACIÓN LICITACIONES")

    for tipo, lista_rutas in grupos.items():
        if not lista_rutas:
            print(f"   ⚠ No se encontraron archivos CSV de tipo {tipo} en {CARPETA_LICITACIONES}")
            continue
            
        print(f"   Procesando {len(lista_rutas)} archivos de {tipo}...")
        
        # Cargar archivos ignorando errores de tokens si los hay
        lista_df = []
        for f in lista_rutas:
            try:
                lista_df.append(pd.read_csv(f, sep=";", encoding="utf-8-sig", on_bad_lines='skip'))
            except Exception as e:
                print(f"      Error al leer {f.name}: {e}")

        if lista_df:
            df_unido = pd.concat(lista_df, ignore_index=True)
            df_limpio = limpiar_y_estandarizar(df_unido)
            
            ruta_guardado = CARPETA_CONSOLIDADO / f"MASTER_LICITACIONES_{tipo}.csv"
            df_limpio.to_csv(ruta_guardado, sep=";", index=False, encoding="utf-8-sig")
            
            bases_listas[tipo] = df_limpio
            print(f"   ✅ Master {tipo} guardado exitosamente.")

    return bases_listas

if __name__ == "__main__":
    # Corregido el nombre de la función aquí
    ejecutar_consolidacion_LI()