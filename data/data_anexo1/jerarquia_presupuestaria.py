"""
jerarquia_presupuestaria.py  v2.0
═══════════════════════════════════════════════════════════════════════════════
CAMBIOS v2.0 — 4 bugs corregidos

BUG 1  filtrar_arbol(): acepta df_referencia para resolver codigo_raiz
       cuando el concepto padre no existe en el df ya filtrado por fecha.

BUG 2  metricas_arbol() + variacion_mom(): Es_Hoja se recalcula DENTRO
       del subconjunto filtrado, no hereda el valor global.

BUG 3  metricas_arbol() → por_periodo: dict de agg construido
       correctamente, sin evaluación condicional inline en el dict.

BUG 4  recalcular_metricas(): nueva función que recomputa Pct_Ejecucion,
       Estado_Semaforo y variaciones sobre el df ya filtrado.
"""

from __future__ import annotations
import re, warnings
import numpy as np
import pandas as pd

LONGITUD_A_NIVEL: dict[int, int] = {2: 1, 4: 2, 7: 3, 10: 4, 12: 5}

COLS_MONETARIAS = [
    "Ley de Presupuestos", "Requerimiento", "Saldo por Aplicar",
    "Compromiso", "Saldo por Comprometer", "Devengado",
    "Saldo por Devengar", "Efectivo", "Deuda Flotante",
]

MESES_ORDEN = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _extraer_codigo(concepto: str) -> str | None:
    if not isinstance(concepto, str):
        return None
    m = re.match(r"^(\d+)", concepto.strip())
    return m.group(1) if m else None

def _nivel_desde_codigo(codigo: str | None) -> int | None:
    if codigo is None:
        return None
    return LONGITUD_A_NIVEL.get(len(codigo))

def _codigo_padre(codigo: str | None) -> str | None:
    if codigo is None:
        return None
    nivel = _nivel_desde_codigo(codigo)
    if nivel is None or nivel <= 1:
        return None
    niveles_long = sorted(LONGITUD_A_NIVEL.keys())
    idx = niveles_long.index(len(codigo))
    if idx == 0:
        return None
    return codigo[:niveles_long[idx - 1]]

def _parse_fecha(fecha_str: str) -> tuple[int, int]:
    try:
        partes = str(fecha_str).strip().lower().split()
        mes  = MESES_ORDEN.get(partes[0], 0)
        anio = int(partes[1]) if len(partes) > 1 else 0
        return anio, mes
    except Exception:
        return 0, 0

def _semaforo(pct) -> str:
    if pd.isna(pct):   return "Sin Presupuesto"
    if pct <= 0:       return "Sin Ejecutar"
    if pct <= 80:      return "Verde"
    if pct <= 100:     return "Amarillo"
    if pct <= 110:     return "Rojo"
    return "Excedido"

def _es_hoja_local(df: pd.DataFrame) -> pd.Series:
    """Calcula Es_Hoja dentro del subconjunto df (no globalmente)."""
    codigos_padre = set(df["Padre_Codigo"].dropna().unique()) \
                    if "Padre_Codigo" in df.columns else set()
    return ~df["Codigo"].isin(codigos_padre)


# ══════════════════════════════════════════════════════════════════════════════
# enriquecer()
# ══════════════════════════════════════════════════════════════════════════════
def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columnas de navegación y análisis jerárquico al DataFrame plano.

    Columnas añadidas: Codigo, Nivel, Padre_Codigo, Es_Hoja, Nivel_Max_Arbol,
    Codigo_N1..N5, Etiqueta_N1..N5, Pct_Ejecucion, Variacion_Devengado,
    Pct_Variacion, Pct_Compromiso, Estado_Semaforo, Anio, Mes_Num.
    """
    df = df.copy()

    # 1. Normalizar monetarias
    for col in COLS_MONETARIAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 2. Codigo y Nivel
    if "Concepto Presupuestario" in df.columns:
        df["Codigo"] = df["Concepto Presupuestario"].apply(_extraer_codigo)
    else:
        df["Codigo"] = None
        warnings.warn("Columna 'Concepto Presupuestario' no encontrada.")

    if "Nivel" not in df.columns:
        df["Nivel"] = df["Codigo"].apply(_nivel_desde_codigo)
    else:
        # Convertir a nullable Int64 PRIMERO para evitar crash en pandas 2.x
        # cuando la columna ya existe como int64 y se intenta asignar None/NaN
        df["Nivel"] = pd.to_numeric(df["Nivel"], errors="coerce").astype("Int64")
        mask_sin = df["Nivel"].isna()
        if mask_sin.any():
            inferidos = df.loc[mask_sin, "Codigo"].apply(_nivel_desde_codigo)
            df["Nivel"] = df["Nivel"].astype(object)
            df.loc[mask_sin, "Nivel"] = inferidos
    df["Nivel"] = pd.array(df["Nivel"].tolist(), dtype="Int64")

    # 3. Padre
    df["Padre_Codigo"] = df["Codigo"].apply(_codigo_padre)

    # 4. Anclas por nivel
    mapa: dict[str, str] = {}
    if "Concepto Presupuestario" in df.columns and "Codigo" in df.columns:
        mapa = (df.dropna(subset=["Codigo"])
                  .drop_duplicates("Codigo")
                  .set_index("Codigo")["Concepto Presupuestario"]
                  .to_dict())

    def _anclas(codigo):
        res = {f"Codigo_N{n}": None for n in range(1, 6)}
        res.update({f"Etiqueta_N{n}": None for n in range(1, 6)})
        if codigo is None:
            return res
        niveles_long = sorted(LONGITUD_A_NIVEL.keys())
        if len(codigo) not in niveles_long:
            return res
        idx = niveles_long.index(len(codigo))
        for long in niveles_long[:idx + 1]:
            cod_anc = codigo[:long]
            nv      = LONGITUD_A_NIVEL[long]
            res[f"Codigo_N{nv}"]   = cod_anc
            res[f"Etiqueta_N{nv}"] = mapa.get(cod_anc)
        return res

    anclas_df = pd.DataFrame(df["Codigo"].apply(_anclas).tolist(), index=df.index)
    df = pd.concat([df, anclas_df], axis=1)

    # 5. Es_Hoja y Nivel_Max_Arbol (global — solo referencia)
    df["Es_Hoja"] = _es_hoja_local(df)

    group_cols = [c for c in ["Establecimiento", "Fecha"] if c in df.columns]
    if group_cols:
        df["Nivel_Max_Arbol"] = df.groupby(group_cols)["Nivel"].transform("max")
    else:
        df["Nivel_Max_Arbol"] = df["Nivel"].max()

    # 6. Métricas (sobre dataset completo — usar recalcular_metricas() tras filtrar)
    pres_col, dev_col, com_col = "Ley de Presupuestos", "Devengado", "Compromiso"
    if pres_col in df.columns and dev_col in df.columns:
        safe_p = df[pres_col].replace(0, np.nan)
        df["Pct_Ejecucion"]       = (df[dev_col] / safe_p * 100).round(2)
        df["Variacion_Devengado"] = df[dev_col] - df[pres_col]
        df["Pct_Variacion"]       = (df["Variacion_Devengado"] / safe_p * 100).round(2)
        if com_col in df.columns:
            df["Pct_Compromiso"]  = (df[com_col] / safe_p * 100).round(2)
        df["Estado_Semaforo"] = df["Pct_Ejecucion"].apply(_semaforo)

    # 7. Tiempo
    if "Fecha" in df.columns:
        tiempo    = df["Fecha"].apply(_parse_fecha)
        df["Anio"]    = tiempo.apply(lambda x: x[0]).astype("Int64")
        df["Mes_Num"] = tiempo.apply(lambda x: x[1]).astype("Int64")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# recalcular_metricas()  — NUEVA  (FIX BUG 4 + BUG 2)
# ══════════════════════════════════════════════════════════════════════════════
def recalcular_metricas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalcula Pct_Ejecucion, Estado_Semaforo, variaciones y Es_Hoja
    sobre el subconjunto ya filtrado (fecha, establecimiento, nivel, etc.).

    Llamar después de cada filtro antes de mostrar datos o calcular KPIs.
    """
    df = df.copy()

    # Recalcular Es_Hoja local (FIX BUG 2)
    df["Es_Hoja"] = _es_hoja_local(df)

    pres_col, dev_col, com_col = "Ley de Presupuestos", "Devengado", "Compromiso"
    if pres_col not in df.columns or dev_col not in df.columns:
        return df

    safe_p = df[pres_col].replace(0, np.nan)
    df["Pct_Ejecucion"]       = (df[dev_col] / safe_p * 100).round(2)
    df["Variacion_Devengado"] = df[dev_col] - df[pres_col]
    df["Pct_Variacion"]       = (df["Variacion_Devengado"] / safe_p * 100).round(2)
    if com_col in df.columns:
        df["Pct_Compromiso"]  = (df[com_col] / safe_p * 100).round(2)
    df["Estado_Semaforo"] = df["Pct_Ejecucion"].apply(_semaforo)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# filtrar_arbol()  — FIX BUG 1
# ══════════════════════════════════════════════════════════════════════════════
def filtrar_arbol(
    df: pd.DataFrame,
    concepto: str,
    incluir_padre: bool = True,
    max_nivel: int | None = None,
    df_referencia: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Retorna el subárbol completo de un concepto y todos sus descendientes.

    df_referencia: dataset global sin filtrar (necesario para resolver el
    codigo_raiz cuando el concepto padre no tiene filas en el período
    filtrado pero sus hijos sí). Se pasa como df_full desde el dashboard.
    """
    if "Codigo" not in df.columns:
        raise ValueError("DataFrame no enriquecido.")

    # Resolver código raíz: buscar primero en df, luego en df_referencia
    codigo_raiz = None
    for fuente in ([df, df_referencia] if df_referencia is not None else [df]):
        if fuente is None or fuente.empty:
            continue
        if "Concepto Presupuestario" in fuente.columns:
            mask = fuente["Concepto Presupuestario"].astype(str).str.strip() \
                   == str(concepto).strip()
            if mask.any():
                codigo_raiz = fuente.loc[mask.idxmax(), "Codigo"]
                break
        mask_cod = fuente["Codigo"].astype(str).str.strip() == str(concepto).strip()
        if mask_cod.any():
            codigo_raiz = str(concepto).strip()
            break

    if codigo_raiz is None:
        warnings.warn(f"Concepto '{concepto}' no encontrado.")
        return pd.DataFrame(columns=df.columns)

    nivel_raiz = _nivel_desde_codigo(codigo_raiz)
    if nivel_raiz is None:
        warnings.warn(f"No se pudo determinar nivel del código '{codigo_raiz}'.")
        return pd.DataFrame(columns=df.columns)

    col_ancla = f"Codigo_N{nivel_raiz}"
    if col_ancla not in df.columns:
        warnings.warn(f"Columna '{col_ancla}' no encontrada.")
        return df[df["Codigo"] == codigo_raiz].copy()

    mask = df[col_ancla] == codigo_raiz
    if not incluir_padre:
        mask = mask & (df["Codigo"] != codigo_raiz)
    if max_nivel is not None:
        mask = mask & (df["Nivel"] <= max_nivel)

    return df[mask].copy()


def filtrar_nivel(
    df: pd.DataFrame,
    nivel: int,
    concepto_n1: str | None = None,
) -> pd.DataFrame:
    """Retorna solo las filas del nivel indicado."""
    mask = df["Nivel"] == nivel
    if concepto_n1 and "Codigo_N1" in df.columns:
        mask_n1 = df["Concepto Presupuestario"].astype(str).str.strip() \
                  == str(concepto_n1).strip()
        if mask_n1.any():
            cod_n1 = df.loc[mask_n1.idxmax(), "Codigo_N1"]
            mask   = mask & (df["Codigo_N1"] == cod_n1)
    return df[mask].copy()


# ══════════════════════════════════════════════════════════════════════════════
# metricas_arbol()  — FIX BUG 2 + BUG 3
# ══════════════════════════════════════════════════════════════════════════════
def metricas_arbol(df: pd.DataFrame, solo_hojas: bool = True) -> dict:
    """
    Calcula KPIs de control presupuestario para el subárbol/subconjunto.
    Llamar DESPUÉS de recalcular_metricas() para valores correctos.
    """
    # FIX BUG 2: recalcular Es_Hoja dentro del subconjunto
    if solo_hojas:
        hoja_mask = _es_hoja_local(df)
        sub = df[hoja_mask].copy()
    else:
        sub = df.copy()

    def _s(col):
        return float(sub[col].sum()) if col in sub.columns else 0.0

    pres = _s("Ley de Presupuestos")
    dev  = _s("Devengado")
    comp = _s("Compromiso")
    disp = pres - dev
    pct_ej  = round(dev / pres * 100, 2) if pres else None
    pct_var = round((dev - pres) / pres * 100, 2) if pres else None

    # FIX BUG 3: dict de agg construido antes del groupby, no inline
    por_periodo = pd.DataFrame()
    if "Fecha" in sub.columns and "Anio" in sub.columns and "Mes_Num" in sub.columns:
        agg_p: dict[str, tuple] = {"Devengado": ("Devengado", "sum")}
        if "Ley de Presupuestos" in sub.columns:
            agg_p["Presupuesto"] = ("Ley de Presupuestos", "sum")
        if "Compromiso" in sub.columns:
            agg_p["Compromiso"]  = ("Compromiso", "sum")

        por_periodo = (sub.groupby(["Fecha", "Anio", "Mes_Num"])
                         .agg(**agg_p).reset_index()
                         .sort_values(["Anio", "Mes_Num"]))
        if "Presupuesto" in por_periodo.columns:
            sp = por_periodo["Presupuesto"].replace(0, np.nan)
            por_periodo["Pct_Ejecucion"] = (por_periodo["Devengado"] / sp * 100).round(2)
            por_periodo["Variacion"]     = por_periodo["Devengado"] - por_periodo["Presupuesto"]

    por_nivel = pd.DataFrame()
    if "Nivel" in sub.columns:
        agg_n: dict[str, tuple] = {"Devengado": ("Devengado", "sum")}
        if "Ley de Presupuestos" in sub.columns:
            agg_n["Ley de Presupuestos"] = ("Ley de Presupuestos", "sum")
        if "Compromiso" in sub.columns:
            agg_n["Compromiso"] = ("Compromiso", "sum")
        por_nivel = sub.groupby("Nivel").agg(**agg_n).reset_index()
        if "Ley de Presupuestos" in por_nivel.columns:
            por_nivel["Pct_Ejecucion"] = (
                por_nivel["Devengado"]
                / por_nivel["Ley de Presupuestos"].replace(0, np.nan) * 100
            ).round(2)

    semaforos: dict = {}
    if "Estado_Semaforo" in sub.columns:
        semaforos = sub["Estado_Semaforo"].value_counts().to_dict()

    def _eg(pct) -> str:
        if pct is None: return "Sin datos"
        if pct <= 0:    return "Sin Ejecutar"
        if pct <= 80:   return "Verde"
        if pct <= 100:  return "Amarillo"
        if pct <= 110:  return "Rojo"
        return "Excedido"

    return {
        "presupuesto_total": pres,
        "devengado_total":   dev,
        "compromiso_total":  comp,
        "disponible":        disp,
        "pct_ejecucion":     pct_ej,
        "pct_variacion":     pct_var,
        "n_conceptos":       sub["Concepto Presupuestario"].nunique()
                             if "Concepto Presupuestario" in sub.columns else 0,
        "n_periodos":        sub["Fecha"].nunique() if "Fecha" in sub.columns else 0,
        "estado_global":     _eg(pct_ej),
        "por_periodo":       por_periodo,
        "por_nivel":         por_nivel,
        "semaforos":         semaforos,
    }


# ══════════════════════════════════════════════════════════════════════════════
# reporte_control()
# ══════════════════════════════════════════════════════════════════════════════
def reporte_control(
    df: pd.DataFrame,
    nivel_reporte: int = 2,
    agrupar_por: list[str] | None = None,
    exportar_csv: str | None = None,
) -> pd.DataFrame:
    """
    Reporte de control agrupado por nivel.
    df debe haber pasado por recalcular_metricas() para semáforos correctos.
    """
    sub = df[df["Nivel"] == nivel_reporte].copy()
    if sub.empty:
        warnings.warn(f"Sin datos para Nivel {nivel_reporte}.")
        return pd.DataFrame()

    id_cols = ["Concepto Presupuestario", "Codigo"]
    if nivel_reporte > 1:
        id_cols += [f"Etiqueta_N{n}" for n in range(1, nivel_reporte)
                    if f"Etiqueta_N{n}" in sub.columns]

    group_cols = id_cols.copy()
    if agrupar_por:
        group_cols += [c for c in agrupar_por if c in sub.columns]

    agg_d: dict[str, tuple] = {}
    for col in COLS_MONETARIAS:
        if col in sub.columns:
            agg_d[col] = (col, "sum")
    if not agg_d:
        return sub

    rep = sub.groupby(group_cols, dropna=False).agg(**agg_d).reset_index()

    pres_r = rep.get("Ley de Presupuestos", pd.Series(dtype=float))
    dev_r  = rep.get("Devengado",           pd.Series(dtype=float))
    if len(pres_r) and len(dev_r):
        sp = pres_r.replace(0, np.nan)
        rep["Pct_Ejecucion"]       = (dev_r / sp * 100).round(2)
        rep["Variacion_Devengado"] = dev_r - pres_r
        rep["Pct_Variacion"]       = ((dev_r - pres_r) / sp * 100).round(2)
        rep["Disponible"]          = pres_r - dev_r
        rep["Estado"] = rep["Pct_Ejecucion"].apply(
            lambda p: "🟢 Verde"    if not pd.isna(p) and p <= 80  else
                      "🟡 Amarillo" if not pd.isna(p) and p <= 100 else
                      "🔴 Rojo"     if not pd.isna(p) and p <= 110 else
                      "⛔ Excedido" if not pd.isna(p) else "—"
        )

    sort_cols = [c for c in ["Codigo_N1","Codigo","Anio","Mes_Num","Fecha"]
                 if c in rep.columns]
    rep = rep.sort_values(sort_cols)

    if exportar_csv:
        rep.to_csv(exportar_csv, index=False, encoding="utf-8-sig")
        print(f"Reporte exportado: {exportar_csv}")

    return rep


# ══════════════════════════════════════════════════════════════════════════════
# arbol_navegacion()
# ══════════════════════════════════════════════════════════════════════════════
def arbol_navegacion(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Mapa jerárquico para selectores Streamlit.
    Llamar siempre sobre el dataset GLOBAL sin filtrar.
    """
    if "Concepto Presupuestario" not in df.columns or "Nivel" not in df.columns:
        return {}

    arbol: dict[str, list[str]] = {
        "__raices__": (df[df["Nivel"] == 1]["Concepto Presupuestario"]
                       .drop_duplicates().sort_values().tolist())
    }
    # drop_duplicates por Codigo para no iterar la misma estructura N veces
    # (un concepto aparece una vez por cada establecimiento × período)
    df_uniq = df.dropna(subset=["Codigo"]).drop_duplicates("Codigo")
    for _, row in df_uniq.iterrows():
        cod  = row["Codigo"]
        conc = str(row["Concepto Presupuestario"]).strip()
        hijos = (df[df["Padre_Codigo"] == cod]["Concepto Presupuestario"]
                 .drop_duplicates().sort_values().tolist())
        if hijos:
            arbol[conc] = hijos
    return arbol


# ══════════════════════════════════════════════════════════════════════════════
# variacion_mom()  — FIX BUG 2
# ══════════════════════════════════════════════════════════════════════════════
def variacion_mom(
    df: pd.DataFrame,
    concepto: str | None = None,
    establecimiento: str | None = None,
) -> pd.DataFrame:
    """Variación Devengado mes a mes. Usa hojas recalculadas en el subconjunto."""
    # FIX BUG 2: Es_Hoja recalculado localmente
    hoja_mask = _es_hoja_local(df)
    sub = df[hoja_mask].copy()

    if concepto and "Etiqueta_N1" in sub.columns:
        sub = sub[sub["Etiqueta_N1"].astype(str).str.strip() == str(concepto).strip()]
    if establecimiento and "Establecimiento" in sub.columns:
        sub = sub[sub["Establecimiento"] == establecimiento]

    if sub.empty:
        return pd.DataFrame()

    group = ["Fecha","Anio","Mes_Num"] if "Anio" in sub.columns else ["Fecha"]
    serie = (sub.groupby(group)["Devengado"].sum().reset_index()
              .sort_values(["Anio","Mes_Num"] if "Anio" in sub.columns else ["Fecha"]))

    serie["Dev_Anterior"]  = serie["Devengado"].shift(1)
    serie["Variacion_Abs"] = serie["Devengado"] - serie["Dev_Anterior"]
    serie["Variacion_Pct"] = (
        serie["Variacion_Abs"] / serie["Dev_Anterior"].replace(0, np.nan) * 100
    ).round(2)

    return serie