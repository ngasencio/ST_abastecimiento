import pandas as pd
from pathlib import Path
import os

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================
# Detecta la ruta base donde está este archivo
BASE_DIR = Path(__file__).parent.absolute()

# Ruta esperada de los maestros (Ajustada a la estructura de OC)
RUTA_MAESTROS = BASE_DIR / "OC_DSSO" / "MAESTROS"

# Nombres de archivos generados por el script ETL
FILE_RESUMEN = RUTA_MAESTROS / "OC_Maestro_Resumen.csv"
FILE_DETALLE = RUTA_MAESTROS / "OC_Maestro_Detalles.csv"

# ==========================================
# CONFIGURACIÓN DE TIPOS DE DATOS (ESPECÍFICO OC)
# ==========================================
# Columnas de FECHA en Órdenes de Compra
COLS_FECHA = [
    "FechaCreacion", "FechaEnvio", "FechaAceptacion", 
    "FechaCancelacion", "FechaUltimaModificacion"
]

# Columnas NUMÉRICAS en Resumen (Cabecera)
COLS_NUM_RESUMEN = [
    "TotalNeto", "PorcentajeIva", "Impuestos", 
    "TotalBruto", "PromedioCalificacion", "CantidadEvaluacion"
]

# Columnas NUMÉRICAS en Detalle (Items)
COLS_NUM_DETALLE = [
    "Cantidad", "PrecioNeto", "TotalImpuestos", "TotalLinea"
]

def _cargar_csv_seguro(ruta, cols_fecha=None, cols_num=None):
    """
    Función interna genérica para cargar CSVs con manejo de errores y tipos.
    """
    if not ruta.exists():
        print(f"⚠️  Advertencia: No se encontró el archivo maestro en: {ruta}")
        return pd.DataFrame() # Retorna DF vacío para no romper la app

    try:
        # Carga con utf-8-sig para acentos y ; como separador. 
        # dtype=str asegura que no se rompan códigos que empiezan con 0.
        df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig", dtype=str)
        
        # 1. Conversión de Fechas
        if cols_fecha:
            for col in cols_fecha:
                if col in df.columns:
                    # errors='coerce' transforma fechas inválidas en NaT (Not a Time)
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        
        # 2. Conversión de Números
        if cols_num:
            for col in cols_num:
                if col in df.columns:
                    # Reemplazamos comas por puntos y forzamos a numérico
                    df[col] = (
                        df[col]
                        .str.replace(",", ".", regex=False)
                        .apply(pd.to_numeric, errors="coerce")
                        .fillna(0.0)
                    )
        
        return df

    except Exception as e:
        print(f"❌ Error crítico cargando {ruta.name}: {e}")
        return pd.DataFrame()

# ==========================================
# FUNCIONES PÚBLICAS (A importar)
# ==========================================

def cargar_resumen_oc():
    """Carga y procesa el Maestro de Resumen de Órdenes de Compra."""
    print(f"⏳ Cargando Maestro OC Resumen desde {FILE_RESUMEN}...")
    df = _cargar_csv_seguro(
        FILE_RESUMEN, 
        cols_fecha=COLS_FECHA, 
        cols_num=COLS_NUM_RESUMEN
    )
    # Limpieza específica para OC
    if not df.empty:
        df["CodigoOC"] = df["CodigoOC"].astype(str).str.strip()
    
    print(f"   ✅ OC Resumen cargado: {len(df)} registros.")
    return df

def cargar_detalle_oc():
    """Carga y procesa el Maestro de Detalles (Items de OC)."""
    print(f"⏳ Cargando Maestro OC Detalle desde {FILE_DETALLE}...")
    df = _cargar_csv_seguro(
        FILE_DETALLE, 
        cols_fecha=None, 
        cols_num=COLS_NUM_DETALLE
    )
    
    # Limpieza específica
    if not df.empty:
        df["CodigoOC"] = df["CodigoOC"].astype(str).str.strip()
        # El correlativo en OC es importante que sea entero
        df["Correlativo"] = pd.to_numeric(df["Correlativo"], errors="coerce").fillna(0).astype(int)
        
    print(f"   ✅ OC Detalles cargados: {len(df)} registros.")
    return df

def cargar_maestros_oc():
    """
    Función 'One-Stop-Shop': Devuelve ambos DataFrames listos.
    Retorna: (df_resumen, df_detalle)
    """
    df_res = cargar_resumen_oc()
    df_det = cargar_detalle_oc()
    return df_res, df_det

# ==========================================
# BLOQUE DE PRUEBA
# ==========================================
if __name__ == "__main__":
    print("--- INICIANDO PRUEBA DE CARGA OC ---")
    r, d = cargar_maestros_oc()
    
    print("\n--- Vista Previa OC Resumen ---")
    if not r.empty:
        print(r.head(3))
        print(f"Total Bruto Suma: {r['TotalBruto'].sum():,.0f}")
    else:
        print("VACÍO")

    print("\n--- Vista Previa OC Detalle ---")
    if not d.empty:
        print(d.head(3))
    else:
        print("VACÍO")