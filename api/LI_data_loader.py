import pandas as pd
from pathlib import Path
import os

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================
# Detecta la ruta base donde está este archivo
BASE_DIR = Path(__file__).parent.absolute()

# Ruta esperada de los maestros (Ajustada a tu estructura anterior)
RUTA_MAESTROS = BASE_DIR / "LI_DSSO" / "MAESTROS"

FILE_RESUMEN = RUTA_MAESTROS / "Maestro_Resumen.csv"
FILE_DETALLE = RUTA_MAESTROS / "Maestro_Detalle.csv"

# ==========================================
# CONFIGURACIÓN DE TIPOS DE DATOS
# ==========================================
# Definimos qué columnas son fechas para convertirlas automáticamente
COLS_FECHA = [
    "FechaCreacion", "FechaPublicacion", "FechaInicio", # Etapa 1
    "FechaVisitaTerreno", "FechaEntregaAntecedentes", "FechaPubRespuestas", # Etapa 2
    "FechaCierre", # Etapa 3
    "FechaActoAperturaTecnica", "FechaActoAperturaEconomica", # Etapa 4
    "FechaTiempoEvaluacion", # Etapa 5
    "FechaEstimadaAdjudicacion", "FechaAdjudicacion", # Etapa 6
    "FechaEstimadaFirma", # Etapa 7
    "FechaInicioContrato", "FechaFinal" # Etapa 8
]

# Definimos columnas numéricas clave para evitar errores de cálculo
COLS_NUM_RESUMEN = ["MontoEstimado"]
COLS_NUM_DETALLE = ["Cantidad", "MontoUnitarioGanador", "CantidadAdjudicada"]

def _cargar_csv_seguro(ruta, cols_fecha=None, cols_num=None):
    """
    Función interna genérica para cargar CSVs con manejo de errores y tipos.
    """
    if not ruta.exists():
        print(f"⚠️  Advertencia: No se encontró el archivo maestro en: {ruta}")
        return pd.DataFrame() # Retorna DF vacío para no romper la app

    try:
        # Carga con utf-8-sig para acentos y ; como separador
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
                    # Reemplazamos comas por puntos si quedaron residuos y convertimos
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

def cargar_resumen():
    """Carga y procesa el Maestro de Resumen de Licitaciones."""
    print(f"⏳ Cargando Maestro Resumen desde {FILE_RESUMEN}...")
    df = _cargar_csv_seguro(
        FILE_RESUMEN, 
        cols_fecha=COLS_FECHA, 
        cols_num=COLS_NUM_RESUMEN
    )
    # Limpieza extra específica si es necesaria
    if not df.empty:
        df["CodigoLicitacion"] = df["CodigoLicitacion"].astype(str).str.strip()
    
    print(f"   ✅ Resumen cargado: {len(df)} registros.")
    return df

def cargar_detalle():
    """Carga y procesa el Maestro de Detalles (Items)."""
    print(f"⏳ Cargando Maestro Detalle desde {FILE_DETALLE}...")
    df = _cargar_csv_seguro(
        FILE_DETALLE, 
        cols_fecha=None, 
        cols_num=COLS_NUM_DETALLE
    )
    
    # Limpieza extra
    if not df.empty:
        df["CodigoLicitacion"] = df["CodigoLicitacion"].astype(str).str.strip()
        df["Correlativo"] = pd.to_numeric(df["Correlativo"], errors="coerce").fillna(0).astype(int)
        
    print(f"   ✅ Detalles cargados: {len(df)} registros.")
    return df

def cargar_maestros():
    """
    Función 'One-Stop-Shop': Devuelve ambos DataFrames listos.
    Retorna: (df_resumen, df_detalle)
    """
    df_res = cargar_resumen()
    df_det = cargar_detalle()
    return df_res, df_det

# Bloque de prueba (solo se ejecuta si corres este archivo directamente)
if __name__ == "__main__":
    r, d = cargar_maestros()
    print("\n--- Vista Previa Resumen ---")
    print(r.head(3))
    print("\n--- Vista Previa Detalle ---")
    print(d.head(3))
    print("\n--- Tipos de Datos Resumen ---")
    print(r.dtypes)