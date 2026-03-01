"""
jerarquia_presupuestaria.py
═══════════════════════════════════════════════════════════════════════════════
Módulo de enriquecimiento jerárquico para datos presupuestarios.

Transforma el DataFrame plano producido por data_anexo1.py / anexo1_loader.py
en una estructura analítica completa con:

  · Códigos y etiquetas de cada ancestro (N1 … N5)
  · Claves de navegación (Codigo_N1, Padre_Codigo, Es_Hoja)
  · Métricas de rendimiento presupuestario (ejecución, variación, absorción)
  · Función de filtrado jerárquico que devuelve un concepto + todos sus hijos

USO RÁPIDO
----------
    from jerarquia_presupuestaria import enriquecer, filtrar_arbol, metricas_arbol

    df_rico = enriquecer(df_plano)          # agrega todas las columnas auxiliares
    sub     = filtrar_arbol(df_rico, "21 GASTOS EN PERSONAL")   # concepto + hijos
    kpis    = metricas_arbol(sub)           # dict con métricas de control
"""

from __future__ import annotations

import re
import warnings
import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
# Mapeo: longitud del código numérico → nivel jerárquico
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
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════
def _extraer_codigo(concepto: str) -> str | None:
    """Extrae el código numérico inicial de un concepto presupuestario."""
    if not isinstance(concepto, str):
        return None
    m = re.match(r"^(\d+)", concepto.strip())
    return m.group(1) if m else None


def _nivel_desde_codigo(codigo: str | None) -> int | None:
    """Infiere nivel desde longitud del código."""
    if codigo is None:
        return None
    return LONGITUD_A_NIVEL.get(len(codigo))


def _codigo_padre(codigo: str | None) -> str | None:
    """
    Devuelve el código del padre inmediato según la estructura numérica.
    Ej: "2101001" (N3, 7 dígitos) → "2101" (N2, 4 dígitos)
    """
    if codigo is None:
        return None
    nivel = _nivel_desde_codigo(codigo)
    if nivel is None or nivel <= 1:
        return None
    # Longitud del padre
    niveles_long = sorted(LONGITUD_A_NIVEL.keys())
    idx = niveles_long.index(len(codigo))
    if idx == 0:
        return None
    long_padre = niveles_long[idx - 1]
    return codigo[:long_padre]


def _parse_fecha(fecha_str: str) -> tuple[int, int]:
    """'enero 2025' → (2025, 1)"""
    try:
        partes = str(fecha_str).strip().lower().split()
        mes = MESES_ORDEN.get(partes[0], 0)
        anio = int(partes[1]) if len(partes) > 1 else 0
        return anio, mes
    except Exception:
        return 0, 0


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL: enriquecer()
# ══════════════════════════════════════════════════════════════════════════════
def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columnas de navegación y análisis jerárquico al DataFrame plano.

    Columnas añadidas
    -----------------
    Codigo              : código numérico extraído del concepto
    Nivel               : nivel jerárquico (1-5), corregido/inferido
    Padre_Codigo        : código del concepto padre inmediato
    Es_Hoja             : True si no tiene hijos en el mismo período/establecimiento
    Nivel_Max_Arbol     : nivel máximo presente en el árbol del mismo período/est.

    # Ancla de cada nivel (para filtrado rápido)
    Codigo_N1 … Codigo_N5       : código del ancestro en ese nivel
    Etiqueta_N1 … Etiqueta_N5   : concepto completo del ancestro en ese nivel

    # Métricas de rendimiento (cuando existen las columnas base)
    Pct_Ejecucion       : Devengado / Ley_de_Presupuestos × 100
    Pct_Compromiso      : Compromiso / Ley_de_Presupuestos × 100
    Variacion_Devengado : Devengado − Ley_de_Presupuestos
    Pct_Variacion       : Variacion_Devengado / Ley_de_Presupuestos × 100
    Estado_Semaforo     : 'Verde' / 'Amarillo' / 'Rojo' / 'Excedido'
    Anio, Mes_Num       : para ordenamiento cronológico
    """
    df = df.copy()

    # ── 1. Normalizar columnas monetarias ────────────────────────────
    for col in COLS_MONETARIAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── 2. Código y nivel ────────────────────────────────────────────
    if "Concepto Presupuestario" in df.columns:
        df["Codigo"] = df["Concepto Presupuestario"].apply(_extraer_codigo)
    else:
        df["Codigo"] = None
        warnings.warn("Columna 'Concepto Presupuestario' no encontrada.")

    # Nivel: respetar el existente, inferir donde falte
    if "Nivel" not in df.columns:
        df["Nivel"] = df["Codigo"].apply(_nivel_desde_codigo)
    else:
        df["Nivel"] = pd.to_numeric(df["Nivel"], errors="coerce")
        mask_sin_nivel = df["Nivel"].isna()
        df.loc[mask_sin_nivel, "Nivel"] = df.loc[mask_sin_nivel, "Codigo"].apply(
            _nivel_desde_codigo
        )
    df["Nivel"] = df["Nivel"].astype("Int64")

    # ── 3. Padre ─────────────────────────────────────────────────────
    df["Padre_Codigo"] = df["Codigo"].apply(_codigo_padre)

    # ── 4. Anclas por nivel (Codigo_N1…N5, Etiqueta_N1…N5) ──────────
    # Construimos un mapa codigo → concepto para lookup rápido
    mapa_concepto: dict[str, str] = {}
    if "Concepto Presupuestario" in df.columns and "Codigo" in df.columns:
        mapa_concepto = (
            df.dropna(subset=["Codigo"])
            .drop_duplicates("Codigo")
            .set_index("Codigo")["Concepto Presupuestario"]
            .to_dict()
        )

    def _anclas(codigo: str | None) -> dict:
        """Devuelve dict con Codigo_N1…N5 y Etiqueta_N1…N5 para un código dado."""
        resultado: dict[str, str | None] = {}
        for nivel in range(1, 6):
            resultado[f"Codigo_N{nivel}"] = None
            resultado[f"Etiqueta_N{nivel}"] = None

        if codigo is None:
            return resultado

        # Reconstruir ancestros desde el código
        niveles_long = sorted(LONGITUD_A_NIVEL.keys())  # [2, 4, 7, 10, 12]
        long_actual = len(codigo)
        if long_actual not in niveles_long:
            return resultado

        idx_actual = niveles_long.index(long_actual)
        for i, long in enumerate(niveles_long[: idx_actual + 1]):
            cod_anc = codigo[:long]
            nivel_anc = LONGITUD_A_NIVEL[long]
            resultado[f"Codigo_N{nivel_anc}"] = cod_anc
            resultado[f"Etiqueta_N{nivel_anc}"] = mapa_concepto.get(cod_anc)

        return resultado

    anclas_df = pd.DataFrame(df["Codigo"].apply(_anclas).tolist(), index=df.index)
    df = pd.concat([df, anclas_df], axis=1)

    # ── 5. Es_Hoja y Nivel_Max_Arbol ─────────────────────────────────
    # Un nodo es hoja si ningún otro nodo tiene como padre_codigo su código
    codigos_padre = set(df["Padre_Codigo"].dropna().unique())
    df["Es_Hoja"] = ~df["Codigo"].isin(codigos_padre)

    # Nivel máximo del árbol (por período y establecimiento)
    group_cols = [c for c in ["Establecimiento", "Fecha"] if c in df.columns]
    if group_cols:
        df["Nivel_Max_Arbol"] = df.groupby(group_cols)["Nivel"].transform("max")
    else:
        df["Nivel_Max_Arbol"] = df["Nivel"].max()

    # ── 6. Métricas de rendimiento ───────────────────────────────────
    pres_col = "Ley de Presupuestos"
    dev_col  = "Devengado"
    com_col  = "Compromiso"

    if pres_col in df.columns and dev_col in df.columns:
        safe_pres = df[pres_col].replace(0, np.nan)

        df["Pct_Ejecucion"]   = (df[dev_col] / safe_pres * 100).round(2)
        df["Variacion_Devengado"] = df[dev_col] - df[pres_col]
        df["Pct_Variacion"]   = (df["Variacion_Devengado"] / safe_pres * 100).round(2)

        if com_col in df.columns:
            df["Pct_Compromiso"] = (df[com_col] / safe_pres * 100).round(2)

        # Semáforo
        def _semaforo(pct):
            if pd.isna(pct):
                return "Sin Presupuesto"
            if pct < 0:
                return "Sin Ejecutar"
            if pct <= 80:
                return "Verde"
            if pct <= 100:
                return "Amarillo"
            if pct <= 110:
                return "Rojo"
            return "Excedido"

        df["Estado_Semaforo"] = df["Pct_Ejecucion"].apply(_semaforo)

    # ── 7. Columnas de tiempo ────────────────────────────────────────
    if "Fecha" in df.columns:
        tiempo = df["Fecha"].apply(_parse_fecha)
        df["Anio"]    = tiempo.apply(lambda x: x[0]).astype("Int64")
        df["Mes_Num"] = tiempo.apply(lambda x: x[1]).astype("Int64")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# FILTRADO JERÁRQUICO
# ══════════════════════════════════════════════════════════════════════════════
def filtrar_arbol(
    df: pd.DataFrame,
    concepto: str,
    incluir_padre: bool = True,
    max_nivel: int | None = None,
) -> pd.DataFrame:
    """
    Filtra el DataFrame para obtener un concepto y TODOS sus descendientes.

    Parámetros
    ----------
    df            : DataFrame enriquecido (salida de enriquecer())
    concepto      : concepto raíz (puede ser código o texto completo)
    incluir_padre : si True incluye la fila del propio concepto raíz
    max_nivel     : limita profundidad (ej: max_nivel=3 → solo N1, N2, N3)

    Retorna
    -------
    DataFrame filtrado con el subárbol completo.
    """
    if "Codigo" not in df.columns:
        raise ValueError("DataFrame no enriquecido. Ejecutar enriquecer() primero.")

    # Resolver el código raíz (acepta código o texto completo)
    codigo_raiz = None
    if "Concepto Presupuestario" in df.columns:
        mask_texto = df["Concepto Presupuestario"].astype(str).str.strip() == str(concepto).strip()
        if mask_texto.any():
            codigo_raiz = df.loc[mask_texto.idxmax(), "Codigo"]

    if codigo_raiz is None:
        # Intentar como código directo
        mask_cod = df["Codigo"].astype(str).str.strip() == str(concepto).strip()
        if mask_cod.any():
            codigo_raiz = str(concepto).strip()

    if codigo_raiz is None:
        warnings.warn(f"Concepto '{concepto}' no encontrado en el DataFrame.")
        return pd.DataFrame(columns=df.columns)

    nivel_raiz = _nivel_desde_codigo(codigo_raiz)
    if nivel_raiz is None:
        warnings.warn(f"No se pudo determinar nivel del código '{codigo_raiz}'.")
        return pd.DataFrame(columns=df.columns)

    col_ancla = f"Codigo_N{nivel_raiz}"
    if col_ancla not in df.columns:
        warnings.warn(f"Columna '{col_ancla}' no encontrada. ¿DataFrame enriquecido?")
        return df[df["Codigo"] == codigo_raiz].copy()

    # Todos los nodos que tengan este código en su ancestro del nivel raíz
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
    """
    Filtra el DataFrame para obtener solo filas de un nivel específico,
    opcionalmente dentro de un subárbol N1.

    Parámetros
    ----------
    df           : DataFrame enriquecido
    nivel        : nivel jerárquico a filtrar (1-5)
    concepto_n1  : si se indica, filtra también por árbol N1
    """
    mask = df["Nivel"] == nivel
    if concepto_n1 and "Codigo_N1" in df.columns:
        # Obtener código N1
        mask_n1 = df["Concepto Presupuestario"].astype(str).str.strip() == str(concepto_n1).strip()
        if mask_n1.any():
            cod_n1 = df.loc[mask_n1.idxmax(), "Codigo_N1"]
            mask = mask & (df["Codigo_N1"] == cod_n1)
    return df[mask].copy()


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS DE ÁRBOL
# ══════════════════════════════════════════════════════════════════════════════
def metricas_arbol(
    df: pd.DataFrame,
    solo_hojas: bool = True,
) -> dict:
    """
    Calcula métricas de control presupuestario para un subárbol.

    Parámetros
    ----------
    df         : DataFrame (idealmente salida de filtrar_arbol())
    solo_hojas : si True, suma solo nodos hoja para evitar doble conteo

    Retorna
    -------
    dict con:
        presupuesto_total, devengado_total, compromiso_total,
        disponible, pct_ejecucion, pct_variacion,
        n_conceptos, n_periodos, estado_global,
        por_periodo (DataFrame con evolución temporal),
        por_nivel   (DataFrame con resumen por nivel),
        semaforos   (dict con conteo por estado)
    """
    sub = df[df["Es_Hoja"]].copy() if solo_hojas and "Es_Hoja" in df.columns else df.copy()

    def _sum(col):
        return sub[col].sum() if col in sub.columns else 0.0

    pres    = _sum("Ley de Presupuestos")
    dev     = _sum("Devengado")
    comp    = _sum("Compromiso")
    disp    = pres - dev
    pct_ej  = round(dev / pres * 100, 2) if pres else None
    pct_var = round((dev - pres) / pres * 100, 2) if pres else None

    # Evolución por período
    por_periodo = pd.DataFrame()
    if "Fecha" in sub.columns and "Mes_Num" in sub.columns and "Anio" in sub.columns:
        por_periodo = (
            sub.groupby(["Fecha", "Anio", "Mes_Num"])
            .agg(
                Presupuesto=("Ley de Presupuestos", "sum") if "Ley de Presupuestos" in sub.columns else ("Devengado", "count"),
                Devengado=("Devengado", "sum"),
                Compromiso=("Compromiso", "sum") if "Compromiso" in sub.columns else ("Devengado", "count"),
            )
            .reset_index()
            .sort_values(["Anio", "Mes_Num"])
        )
        if "Presupuesto" in por_periodo.columns and "Devengado" in por_periodo.columns:
            por_periodo["Pct_Ejecucion"] = (
                por_periodo["Devengado"] / por_periodo["Presupuesto"].replace(0, np.nan) * 100
            ).round(2)
            por_periodo["Variacion"] = por_periodo["Devengado"] - por_periodo["Presupuesto"]

    # Resumen por nivel
    por_nivel = pd.DataFrame()
    if "Nivel" in sub.columns:
        agg_cols = {"Devengado": "sum"}
        if "Ley de Presupuestos" in sub.columns:
            agg_cols["Ley de Presupuestos"] = "sum"
        if "Compromiso" in sub.columns:
            agg_cols["Compromiso"] = "sum"
        por_nivel = (
            sub.groupby("Nivel")
            .agg(**{k: (k, v) for k, v in agg_cols.items()})
            .reset_index()
        )
        if "Ley de Presupuestos" in por_nivel.columns:
            por_nivel["Pct_Ejecucion"] = (
                por_nivel["Devengado"]
                / por_nivel["Ley de Presupuestos"].replace(0, np.nan)
                * 100
            ).round(2)

    # Semáforos
    semaforos = {}
    if "Estado_Semaforo" in sub.columns:
        semaforos = sub["Estado_Semaforo"].value_counts().to_dict()

    # Estado global
    def _estado(pct):
        if pct is None:  return "Sin datos"
        if pct <= 80:    return "Verde"
        if pct <= 100:   return "Amarillo"
        if pct <= 110:   return "Rojo"
        return "Excedido"

    return {
        "presupuesto_total":  pres,
        "devengado_total":    dev,
        "compromiso_total":   comp,
        "disponible":         disp,
        "pct_ejecucion":      pct_ej,
        "pct_variacion":      pct_var,
        "n_conceptos":        sub["Concepto Presupuestario"].nunique() if "Concepto Presupuestario" in sub.columns else 0,
        "n_periodos":         sub["Fecha"].nunique() if "Fecha" in sub.columns else 0,
        "estado_global":      _estado(pct_ej),
        "por_periodo":        por_periodo,
        "por_nivel":          por_nivel,
        "semaforos":          semaforos,
    }


# ══════════════════════════════════════════════════════════════════════════════
# REPORTE TABULAR CONSOLIDADO
# ══════════════════════════════════════════════════════════════════════════════
def reporte_control(
    df: pd.DataFrame,
    nivel_reporte: int = 2,
    agrupar_por: list[str] | None = None,
    exportar_csv: str | None = None,
) -> pd.DataFrame:
    """
    Genera un reporte de control presupuestario agrupado por nivel y/o
    columnas adicionales (Establecimiento, Fecha, etc.).

    Parámetros
    ----------
    df             : DataFrame enriquecido
    nivel_reporte  : nivel a reportar (ej: 2 → subtítulos principales)
    agrupar_por    : columnas extra para agrupar (ej: ['Establecimiento','Fecha'])
    exportar_csv   : ruta para exportar el reporte (None = no exportar)

    Retorna
    -------
    DataFrame con el reporte consolidado + columnas de control.
    """
    # Filtrar el nivel solicitado (para no sumar padre + hijo)
    sub = df[df["Nivel"] == nivel_reporte].copy()

    if sub.empty:
        warnings.warn(f"No hay datos para Nivel {nivel_reporte}.")
        return pd.DataFrame()

    # Columnas identificadoras
    id_cols = ["Concepto Presupuestario", "Codigo"]
    if nivel_reporte > 1:
        id_cols += [f"Etiqueta_N{n}" for n in range(1, nivel_reporte)
                    if f"Etiqueta_N{n}" in sub.columns]

    # Columnas de agrupación
    group_cols = id_cols.copy()
    if agrupar_por:
        group_cols += [c for c in agrupar_por if c in sub.columns]

    # Columnas a agregar
    agg_dict: dict[str, tuple] = {}
    for col in COLS_MONETARIAS:
        if col in sub.columns:
            agg_dict[col] = (col, "sum")

    if not agg_dict:
        warnings.warn("No se encontraron columnas monetarias para agregar.")
        return sub

    reporte = (
        sub.groupby(group_cols, dropna=False)
        .agg(**agg_dict)
        .reset_index()
    )

    # Recalcular métricas en el reporte agregado
    pres = reporte.get("Ley de Presupuestos", pd.Series(dtype=float))
    dev  = reporte.get("Devengado",           pd.Series(dtype=float))

    if len(pres) and len(dev):
        safe_pres = pres.replace(0, np.nan)
        reporte["Pct_Ejecucion"]       = (dev / safe_pres * 100).round(2)
        reporte["Variacion_Devengado"] = dev - pres
        reporte["Pct_Variacion"]       = ((dev - pres) / safe_pres * 100).round(2)
        reporte["Disponible"]          = pres - dev

        def _sem(pct):
            if pd.isna(pct):     return "—"
            if pct <= 80:        return "🟢 Verde"
            if pct <= 100:       return "🟡 Amarillo"
            if pct <= 110:       return "🔴 Rojo"
            return "⛔ Excedido"

        reporte["Estado"] = reporte["Pct_Ejecucion"].apply(_sem)

    # Ordenar
    sort_cols = []
    if "Codigo_N1" in reporte.columns:
        sort_cols.append("Codigo_N1")
    sort_cols.append("Codigo")
    if "Fecha" in reporte.columns and "Mes_Num" not in reporte.columns:
        sort_cols.append("Fecha")
    if "Anio" in reporte.columns:
        sort_cols += ["Anio", "Mes_Num"] if "Mes_Num" in reporte.columns else ["Anio"]

    reporte = reporte.sort_values([c for c in sort_cols if c in reporte.columns])

    if exportar_csv:
        reporte.to_csv(exportar_csv, index=False, encoding="utf-8-sig")
        print(f"✅ Reporte exportado: {exportar_csv}")

    return reporte


# ══════════════════════════════════════════════════════════════════════════════
# ÁRBOL DE NAVEGACIÓN (para selectores en Streamlit)
# ══════════════════════════════════════════════════════════════════════════════
def arbol_navegacion(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Construye un mapa jerárquico para poblar selectores anidados en Streamlit.

    Retorna
    -------
    dict donde la clave es el concepto padre y el valor es la lista de hijos
    directos. La clave especial '__raices__' contiene los conceptos de Nivel 1.

    Ejemplo de uso en Streamlit:
        arbol = arbol_navegacion(df_rico)
        n1_sel = st.selectbox("Capítulo", arbol['__raices__'])
        n2_sel = st.selectbox("Subcapítulo", arbol.get(n1_sel, []))
    """
    if "Concepto Presupuestario" not in df.columns or "Nivel" not in df.columns:
        return {}

    arbol: dict[str, list[str]] = {"__raices__": []}

    # Raíces = Nivel 1
    raices = (
        df[df["Nivel"] == 1]["Concepto Presupuestario"]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    arbol["__raices__"] = raices

    # Para cada nodo, encontrar sus hijos directos
    for _, row in df.dropna(subset=["Codigo"]).iterrows():
        codigo  = row["Codigo"]
        concepto = str(row["Concepto Presupuestario"]).strip()

        # Hijos directos: nodos cuyo padre_codigo == este código
        hijos = (
            df[df["Padre_Codigo"] == codigo]["Concepto Presupuestario"]
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        if hijos:
            arbol[concepto] = hijos

    return arbol


# ══════════════════════════════════════════════════════════════════════════════
# VARIACIÓN PERÍODO A PERÍODO
# ══════════════════════════════════════════════════════════════════════════════
def variacion_mom(
    df: pd.DataFrame,
    concepto: str | None = None,
    establecimiento: str | None = None,
) -> pd.DataFrame:
    """
    Calcula la variación del Devengado mes a mes (Month-over-Month).

    Parámetros
    ----------
    df              : DataFrame enriquecido (solo hojas recomendado)
    concepto        : filtrar por concepto N1 (None = todos)
    establecimiento : filtrar por establecimiento (None = todos)

    Retorna
    -------
    DataFrame con columnas: Fecha, Devengado, Dev_Anterior, Variacion_Abs, Variacion_Pct
    """
    sub = df[df.get("Es_Hoja", pd.Series(True, index=df.index))].copy() if "Es_Hoja" in df.columns else df.copy()

    if concepto and "Etiqueta_N1" in sub.columns:
        sub = sub[sub["Etiqueta_N1"].astype(str).str.strip() == str(concepto).strip()]
    if establecimiento and "Establecimiento" in sub.columns:
        sub = sub[sub["Establecimiento"] == establecimiento]

    if sub.empty:
        return pd.DataFrame()

    group = ["Fecha", "Anio", "Mes_Num"] if "Anio" in sub.columns else ["Fecha"]
    serie = (
        sub.groupby(group)["Devengado"]
        .sum()
        .reset_index()
        .sort_values(["Anio", "Mes_Num"] if "Anio" in sub.columns else ["Fecha"])
    )

    serie["Dev_Anterior"]   = serie["Devengado"].shift(1)
    serie["Variacion_Abs"]  = serie["Devengado"] - serie["Dev_Anterior"]
    serie["Variacion_Pct"]  = (serie["Variacion_Abs"] / serie["Dev_Anterior"].replace(0, np.nan) * 100).round(2)

    return serie