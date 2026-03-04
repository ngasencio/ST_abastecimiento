"""
data_anexo1.py
Procesa todos los archivos Excel mensuales en data/data_anexo1/<subcarpeta>/
y genera un CSV maestro por subcarpeta.

Estructura esperada:
    data/data_anexo1/
        DSSO/
            01-2025.xlsx
            02-2025.xlsx
            ...
        HBO/
            01-2025.xlsx
            ...

Genera:
    data/data_anexo1/maestro_DSSO.csv
    data/data_anexo1/maestro_HBO.csv
    ...
"""

import re
import os
import glob
import warnings
import pandas as pd

# ─────────────────────────── configuración ───────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


MESES = {
    "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
    "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
    "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre",
}

# Columnas numéricas que pueden contener valores entre paréntesis
NUMERIC_COLS_HINT = [
    "Ley de Presupuestos", "Requerimiento", "Saldo por Aplicar",
    "Compromiso", "Saldo por Comprometer", "Devengado",
    "Saldo por Devengar", "Efectivo", "Deuda Flotante",
]


# ─────────────────────────── helpers ────────────────────────────────
def parse_parentheses(value):
    """Convierte '(1000)' → -1000; deja los demás valores sin cambio."""
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("(") and v.endswith(")"):
            inner = v[1:-1].replace(",", "").replace(".", "")
            try:
                return -float(inner)
            except ValueError:
                warnings.warn(f"No se pudo convertir a negativo: '{value}'")
                return value
        # Intenta convertir strings numéricos normales
        try:
            return float(v.replace(",", ""))
        except ValueError:
            return value
    return value


def nombre_mes(filename: str) -> str:
    """'01-2025.xlsx' → 'enero 2025'"""
    m = re.match(r"^(\d{2})-(\d{4})\.xlsx$", os.path.basename(filename), re.IGNORECASE)
    if not m:
        warnings.warn(f"Nombre de archivo no sigue formato MM-YYYY.xlsx: {filename}")
        return "desconocido"
    mm, yyyy = m.group(1), m.group(2)
    return f"{MESES.get(mm, mm)} {yyyy}"


def determinar_nivel(concepto: str) -> int | None:
    """
    Infiere el nivel jerárquico desde el código numérico al inicio de 'concepto'.
    Regla:  2 dígitos → nivel 1, 4 → 2, 7 → 3, 10 → 4, 12 → 5, etc.
    Se prefiere la columna 'Nivel' ya presente; esta función es fallback.
    """
    if not isinstance(concepto, str):
        return None
    m = re.match(r"^(\d+)", concepto.strip())
    if not m:
        return None
    n = len(m.group(1))
    mapping = {2: 1, 4: 2, 7: 3, 10: 4, 12: 5}
    return mapping.get(n)


def construir_ruta_jerarquica(df: pd.DataFrame) -> pd.Series:
    """
    Para cada fila, concatena los conceptos de todos los ancestros (niveles
    superiores) que aparecen antes en el dataframe.
    Retorna una Series con la ruta en formato
    'Nivel1 > Nivel2 > ... > NivelActual'.
    """
    rutas = []
    pila: list[tuple[int, str]] = []   # (nivel, concepto)

    for _, row in df.iterrows():
        nivel = row["Nivel"]
        concepto = str(row["Concepto Presupuestario"]).strip()

        if pd.isna(nivel):
            rutas.append(concepto)
            continue

        nivel = int(nivel)

        # Elimina de la pila todos los niveles >= al actual
        pila = [(n, c) for n, c in pila if n < nivel]
        pila.append((nivel, concepto))

        rutas.append(" > ".join(c for _, c in pila))

    return pd.Series(rutas, index=df.index)


# ─────────────────────────── lectura de un archivo ──────────────────
def extraer_establecimiento(filepath: str, fallback: str) -> str:
    """
    Lee fila 1 del Excel para obtener el nombre real del establecimiento.

    Estructura conocida del archivo:
        Fila 0: 'Estado de Ejecución Presupuestaria'
        Fila 1: '1638001 Direccion del Servicio'   ← nombre real
        Fila 2: '01 enero 2025 al 31 enero 2025'
        ...
        Fila 6: encabezados de columnas

    Si no se puede leer, retorna el fallback (nombre de carpeta).
    """
    try:
        meta = pd.read_excel(filepath, header=None, dtype=str, nrows=4)
        val = str(meta.iloc[1, 0]).strip()
        if val and val.lower() not in ("nan", "none", ""):
            return val
    except Exception:
        pass
    return fallback


def leer_archivo(filepath: str, establecimiento: str, fecha: str) -> pd.DataFrame | None:
    # Extraer nombre real del establecimiento desde las filas de cabecera del Excel
    # (fila 1 contiene el código y nombre del establecimiento)
    establecimiento = extraer_establecimiento(filepath, fallback=establecimiento)

    try:
        # Fila 6 (índice 6) es el encabezado; se saltan las primeras 6 filas
        df = pd.read_excel(filepath, header=6, dtype=str)
    except Exception as e:
        warnings.warn(f"Error leyendo {filepath}: {e}")
        return None

    if df.empty:
        warnings.warn(f"Archivo vacío: {filepath}")
        return None

    # Eliminar columnas totalmente vacías (artefactos de Excel)
    df.dropna(axis=1, how="all", inplace=True)

    # Eliminar filas que contengan "indica 1 de" (paginación)
    mask_pagina = df.apply(
        lambda col: col.astype(str).str.contains("indica 1 de", case=False, na=False)
    ).any(axis=1)
    if mask_pagina.any():
        print(f"  ⚠ Eliminadas {mask_pagina.sum()} fila(s) de paginación en {os.path.basename(filepath)}")
    df = df[~mask_pagina].reset_index(drop=True)

    # Eliminar filas completamente vacías
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Renombrar columnas duplicadas o sin nombre
    cols = []
    seen: dict[str, int] = {}
    for c in df.columns:
        c = str(c).strip()
        if c.startswith("Unnamed"):
            c = f"_col_{len(cols)}"
        if c in seen:
            seen[c] += 1
            c = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
        cols.append(c)
    df.columns = cols

    # Convertir valores entre paréntesis en columnas numéricas
    converted_errors = []
    for col in df.columns:
        if col in NUMERIC_COLS_HINT or any(hint in col for hint in ["Saldo", "Deveng", "Compromi", "Efectivo", "Deuda", "Ley de", "Requerimiento"]):
            before_nulls = df[col].isna().sum()
            df[col] = df[col].apply(parse_parentheses)
            # Detectar celdas que siguen siendo strings después de la conversión
            non_numeric = df[col].apply(lambda x: isinstance(x, str) and x not in ("", "nan"))
            if non_numeric.any():
                converted_errors.append(
                    f"Columna '{col}': {non_numeric.sum()} valor(es) no convertibles"
                )

    if converted_errors:
        print(f"  ⚠ Advertencias en {os.path.basename(filepath)}:")
        for msg in converted_errors:
            print(f"    · {msg}")

    # Columna Nivel: usar la existente o inferirla
    if "Nivel" not in df.columns:
        if "Concepto Presupuestario" in df.columns:
            df["Nivel"] = df["Concepto Presupuestario"].apply(determinar_nivel)
            warnings.warn(f"Columna 'Nivel' no encontrada en {filepath}; inferida desde código.")
        else:
            df["Nivel"] = None

    # Validación de niveles
    niveles_invalidos = df[~df["Nivel"].isna() & ~df["Nivel"].astype(str).str.match(r"^\d+$")]
    if not niveles_invalidos.empty:
        warnings.warn(
            f"{filepath}: {len(niveles_invalidos)} fila(s) con nivel inválido: "
            f"{niveles_invalidos['Nivel'].unique().tolist()}"
        )

    # Columna Ruta_Jerarquica
    if "Concepto Presupuestario" in df.columns:
        df["Ruta_Jerarquica"] = construir_ruta_jerarquica(df)
    else:
        df["Ruta_Jerarquica"] = None
        warnings.warn(f"Columna 'Concepto Presupuestario' no encontrada en {filepath}")

    # Metadatos
    df["Establecimiento"] = establecimiento
    df["Fecha"] = fecha

    # Verificar montos duplicados (misma ruta + fecha → posible doble carga)
    if "Ruta_Jerarquica" in df.columns and "Devengado" in df.columns:
        dupes = df.duplicated(subset=["Ruta_Jerarquica", "Devengado"], keep=False)
        if dupes.any():
            warnings.warn(
                f"{filepath}: {dupes.sum()} fila(s) potencialmente duplicadas "
                f"(misma Ruta_Jerarquica + Devengado)"
            )

    return df


# ─────────────────────────── procesamiento por subcarpeta ───────────
def procesar_subcarpeta(subdir: str) -> None:
    establecimiento = os.path.basename(subdir)
    archivos = sorted(glob.glob(os.path.join(subdir, "*.xlsx")))

    if not archivos:
        warnings.warn(f"No se encontraron archivos .xlsx en: {subdir}")
        return

    print(f"\n📂 Procesando subcarpeta: {establecimiento} ({len(archivos)} archivo(s))")

    frames: list[pd.DataFrame] = []
    for filepath in archivos:
        fecha = nombre_mes(filepath)
        print(f"  → {os.path.basename(filepath)}  [{fecha}]")
        df = leer_archivo(filepath, establecimiento, fecha)
        if df is not None:
            frames.append(df)

    if not frames:
        warnings.warn(f"No se pudo leer ningún archivo en {subdir}")
        return

    maestro = pd.concat(frames, ignore_index=True)

    # Validación final: consistencia jerárquica (nivel padre siempre existe)
    if "Nivel" in maestro.columns and "Fecha" in maestro.columns:
        for fecha in maestro["Fecha"].unique():
            sub = maestro[maestro["Fecha"] == fecha].copy()
            sub["Nivel_int"] = pd.to_numeric(sub["Nivel"], errors="coerce")
            niveles_presentes = set(sub["Nivel_int"].dropna().unique())
            for n in sorted(niveles_presentes):
                if n > 1 and (n - 1) not in niveles_presentes:
                    warnings.warn(
                        f"{establecimiento} / {fecha}: Nivel {n} presente pero no el Nivel {n-1}"
                    )

    output_path = os.path.join(BASE_DIR, f"maestro_{establecimiento}.csv")
    maestro.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✅ Exportado: {output_path}  ({len(maestro)} filas)")


# ─────────────────────────── main ───────────────────────────────────
def main():
    if not os.path.isdir(BASE_DIR):
        raise FileNotFoundError(f"Directorio base no encontrado: {BASE_DIR}")

    subdirs = [
        d for d in glob.glob(os.path.join(BASE_DIR, "*"))
        if os.path.isdir(d)
    ]

    if not subdirs:
        print(f"⚠ No se encontraron subcarpetas en {BASE_DIR}")
        return

    print(f"🔍 Encontradas {len(subdirs)} subcarpeta(s): {[os.path.basename(d) for d in subdirs]}")

    for subdir in sorted(subdirs):
        procesar_subcarpeta(subdir)

    print("\n✔ Proceso completado.")


if __name__ == "__main__":
    main()