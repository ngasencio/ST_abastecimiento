"""
consolidar_devengo.py
Script para consolidar archivos de devengo presupuestario del Servicio de Salud Osorno.
Lee todos los .xlsx de data/data_devengo/2026_gasto/, limpia y concatena en un solo CSV.
"""

import pandas as pd
import glob
import os
import sys

DATA_PATH   = "2026_gasto/"
OUTPUT_FILE = "devengo_consolidado.csv"
HEADER_ROW  = 5   # Fila 5 (0-indexed) contiene los encabezados reales

# Columnas que deben aparecer primero en el output (si existen)
COLS_PRIMERAS = ["Código Unidad Ejecutora", "Folio", "Titulo", "Tipo Presupuesto"]


def limpiar_dataframe(df: pd.DataFrame, filepath: str) -> pd.DataFrame:
    """Limpia un DataFrame individual: paginación, tipos y fechas."""

    # Eliminar filas que contengan "Página X de" en cualquier celda
    mask_pagina = df.apply(
        lambda row: row.astype(str).str.contains(r"Página\s+\d+\s+de", na=False, regex=True).any(),
        axis=1,
    )
    n_eliminadas = mask_pagina.sum()
    if n_eliminadas:
        print(f"  ↳ Eliminadas {n_eliminadas} filas de paginación")
    df = df[~mask_pagina].copy()

    # Normalizar montos
    for col in ["Monto Vigente", "Monto Disponible", "Monto Consumido"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalizar fechas
    for col in ["Fecha Documento", "Fecha Conforme", "Fecha Ingreso / Fecha Recepción "]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Columna de trazabilidad
    df["archivo_origen"] = os.path.basename(filepath)

    return df


def reordenar_columnas(df: pd.DataFrame):
    """Pone COLS_PRIMERAS al inicio y elimina columnas completamente vacías."""

    # 1. Eliminar columnas completamente vacías (ningún valor en ninguna fila)
    cols_vacias = [c for c in df.columns if df[c].isna().all()]
    if cols_vacias:
        print(f"\nColumnas vacías eliminadas ({len(cols_vacias)}): {cols_vacias}")
    df = df.dropna(axis=1, how="all")

    # 2. Reordenar: primeras columnas requeridas, luego el resto
    presentes = [c for c in COLS_PRIMERAS if c in df.columns]
    resto = [c for c in df.columns if c not in presentes]
    df = df[presentes + resto]

    return df, cols_vacias


def consolidar():
    archivos = sorted(glob.glob(os.path.join(DATA_PATH, "*.xlsx")))

    if not archivos:
        print(f"[ERROR] No se encontraron archivos .xlsx en: {DATA_PATH}")
        sys.exit(1)

    print(f"Archivos encontrados: {len(archivos)}")
    frames = []

    for filepath in archivos:
        print(f"\nProcesando: {os.path.basename(filepath)}")
        try:
            df_raw = pd.read_excel(filepath, header=HEADER_ROW)
            df_clean = limpiar_dataframe(df_raw, filepath)
            frames.append(df_clean)
            print(f"  ✓ {len(df_clean)} filas cargadas")
        except Exception as e:
            print(f"  [ADVERTENCIA] No se pudo procesar {filepath}: {e}")

    if not frames:
        print("[ERROR] Ningún archivo pudo ser procesado.")
        sys.exit(1)

    # Concatenar todo
    consolidado = pd.concat(frames, ignore_index=True)

    # Reordenar columnas y eliminar vacías
    consolidado, cols_vacias = reordenar_columnas(consolidado)

    # Exportar CSV UTF-8 con BOM (compatible con Excel en español)
    consolidado.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig", sep=",")

    # ── Resumen final ──────────────────────────────────────────────────────────
    print("\n" + "═" * 55)
    print("RESUMEN CONSOLIDACIÓN")
    print("═" * 55)
    print(f"  Archivos procesados  : {len(frames)}")
    print(f"  Filas totales        : {len(consolidado):,}")
    print(f"  Columnas vacías elim.: {len(cols_vacias)}")
    print(f"  Columnas finales     : {len(consolidado.columns)}")
    print(f"  Primeras columnas    : {list(consolidado.columns[:4])}")
    print(f"  Archivo exportado    : {OUTPUT_FILE}")
    print("═" * 55)

    return consolidado


if __name__ == "__main__":
    consolidar()