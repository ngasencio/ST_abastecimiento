import pandas as pd
import pathlib
import datetime as dt


# ======================================================
# CONFIGURACIÓN DE RUTAS (Proporcionadas por el usuario)
# ======================================================

# Obtiene la ubicación del archivo actual (Consolidar_OC.py)
# .parent nos saca de la carpeta 'api' y nos deja en 'ST_abastecimiento'
RUTA_ACTUAL = pathlib.Path(__file__).parent.absolute()

# Definimos las rutas relativas al archivo
CARPETA_ORDENCOMPRA = RUTA_ACTUAL / "OC_DSSO" / "DIARIO"
CARPETA_CONSOLIDADO = CARPETA_ORDENCOMPRA / "CONSOLIDADO"

#ESCRITORIO = pathlib.Path.home() / "Desktop"
#CARPETA_ORDENCOMPRA = ESCRITORIO / "ST_abastecimiento" / "ST_abastecimiento" / "api" / "OC_DSSO" / "DIARIO"
#CARPETA_CONSOLIDADO = CARPETA_ORDENCOMPRA / "CONSOLIDADO"

def limpiar_y_estandarizar_oc(df):
    """Realiza la limpie za profunda de los datos de Órdenes de Compra."""
    if df.empty:
        return df
    
    # 1. Quitar espacios en blanco en columnas de texto
    df_obj = df.select_dtypes(['object'])
    df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip())
    
    # 2. Limpiar caracteres que rompen el CSV (puntos y coma y saltos de línea)
    df = df.replace({'\n': ' ', '\r': ' ', ';': ','}, regex=True)
    
    # 3. Eliminar duplicados (si se descargó la misma OC varias veces)
    df = df.drop_duplicates()
    
    # 4. Formatear todas las columnas que contienen la palabra 'Fecha' al formato dd-mm-yyyy
    columnas_fecha = [c for c in df.columns if 'Fecha' in c]
    for col in columnas_fecha:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d-%m-%Y')
        
    return df

def ejecutar_consolidacion_oc():
    """Une, limpia y guarda los maestros de OC."""
    # Crear carpeta de destino
    CARPETA_CONSOLIDADO.mkdir(parents=True, exist_ok=True)
    
    # Buscar todos los archivos CSV en la carpeta raíz de OC
    # Nota: glob("*") busca archivos en la carpeta principal
    todos_los_archivos = list(CARPETA_ORDENCOMPRA.glob("*.csv"))
    
    grupos = {
        "RESUMEN": [f for f in todos_los_archivos if "RESUMEN" in f.name],
        "DETALLES": [f for f in todos_los_archivos if "DETALLES" in f.name]
    }
    
    bases_listas = {}

    print(f"\n>>> INICIANDO CONSOLIDACIÓN OC ({dt.datetime.now().strftime('%H:%M:%S')})")

    for tipo, lista_rutas in grupos.items():
        if not lista_rutas:
            print(f"   ⚠ No se encontraron archivos de tipo: {tipo}")
            continue
            
        print(f"   Uniendo {len(lista_rutas)} archivos de {tipo}...")
        
        # Leer y concatenar
        lista_df = [pd.read_csv(f, sep=";", encoding="utf-8-sig") for f in lista_rutas]
        df_unido = pd.concat(lista_df, ignore_index=True)
        
        # Limpieza
        df_limpio = limpiar_y_estandarizar_oc(df_unido)
        
        # Guardar Master
        ruta_guardado = CARPETA_CONSOLIDADO / f"MASTER_OC_{tipo}.csv"
        df_limpio.to_csv(ruta_guardado, sep=";", index=False, encoding="utf-8-sig")
        
        bases_listas[tipo] = df_limpio
        print(f"   ✅ Master OC {tipo} creado en: {ruta_guardado.name}")

    print(f"\n>>> PROCESO COMPLETADO. Carpeta: {CARPETA_CONSOLIDADO}")
    return bases_listas

if __name__ == "__main__":
    try:
        ejecutar_consolidacion_oc()
    except Exception as e:
        print(f"❌ Error: {e}")