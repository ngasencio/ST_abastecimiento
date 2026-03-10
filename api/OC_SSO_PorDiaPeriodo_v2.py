import csv
import datetime as dt
import json
import os
import pathlib
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd  # Necesario para la unificación y refresco

# =========================
# CONFIGURACIÓN FIJA SSO
# =========================
CODIGO_ORGANISMO = "7296"
TICKET = "2798F2D3-0AC5-4323-9BB9-5E90618194BA"

# 1. Obtenemos la ruta donde está este archivo
RUTA_API = pathlib.Path(__file__).parent.absolute()

# 2. Definimos las carpetas de trabajo
CARPETA_BASE = RUTA_API / "OC_DSSO"
CARPETA_DIARIO = CARPETA_BASE / "DIARIO"
CARPETA_MAESTROS = CARPETA_BASE / "MAESTROS"  # Nueva carpeta para consolidados

# Asegurar que existan los directorios
CARPETA_DIARIO.mkdir(parents=True, exist_ok=True)
CARPETA_MAESTROS.mkdir(parents=True, exist_ok=True)

MAX_REINTENTOS = 5
ESPERA_ENTRE_INTENTOS = 4.0

# Límite de concurrencia: demasiados hilos puede gatillar rate-limit en la API.
MAX_WORKERS_DETALLE = 6

# Throttle suave entre peticiones de detalle (en segundos). Se aplica por tarea/hilo.
ESPERA_ENTRE_DETALLES = 0.05

URL_OC = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"

@dataclass(frozen=True)
class ApiConfig:
    """Configuración de acceso a API y resiliencia."""

    codigo_organismo: str
    ticket: str
    max_reintentos: int = MAX_REINTENTOS
    espera_base: float = ESPERA_ENTRE_INTENTOS
    timeout: int = 30
    url_oc: str = URL_OC

class MercadoPublicoClient:
    """Cliente mínimo para la API (urllib) con backoff y manejo de errores."""

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._ctx = ssl._create_unverified_context()

    def get_json(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url_completa = self.cfg.url_oc + "?" + urllib.parse.urlencode(params)
        last_err: Optional[Exception] = None

        for intento in range(1, self.cfg.max_reintentos + 1):
            try:
                with urllib.request.urlopen(url_completa, context=self._ctx, timeout=self.cfg.timeout) as resp:
                    return json.load(resp)
            except Exception as e:
                last_err = e
                # Backoff lineal (simple y predecible). Si necesitas más agresividad: exponencial.
                time.sleep(self.cfg.espera_base * intento)

        print(f"⚠️  API sin respuesta tras {self.cfg.max_reintentos} intentos: {last_err}")
        return None

    def obtener_listado_dia(self, fecha_dt: dt.date) -> List[Dict[str, Any]]:
        params = {
            "fecha": fecha_dt.strftime("%d%m%Y"),
            "CodigoOrganismo": self.cfg.codigo_organismo,
            "ticket": self.cfg.ticket,
        }
        data = self.get_json(params)
        if not data or not data.get("Listado"):
            return []
        return data["Listado"]

    def obtener_detalle_oc(self, codigo_oc: str) -> Optional[Dict[str, Any]]:
        params = {"codigo": codigo_oc, "ticket": self.cfg.ticket}
        data = self.get_json(params)
        return data["Listado"][0] if data and data.get("Listado") else None

def limpiar(texto):
    if texto is None: return ""
    return str(texto).replace("\n", " ").replace(";", ",").replace("\r", " ").strip()

def generar_link_mp(codigo_oc):
    """Genera el link directo a la orden de compra en Mercado Público"""
    if not codigo_oc or str(codigo_oc).strip() == "" or str(codigo_oc).lower() == "nan":
        return ""
    base_url = "http://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC="
    return f"{base_url}{codigo_oc}"

def _write_csv_dicts(path: pathlib.Path, rows: List[Dict[str, Any]], delimiter: str = ";") -> None:
    """Escritura CSV consistente y relativamente rápida para lista de dicts."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as csvfile:
        w = csv.DictWriter(csvfile, fieldnames=rows[0].keys(), delimiter=delimiter)
        w.writeheader()
        w.writerows(rows)

def _extraer_resumen_y_detalles(codigo: str, oc: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normaliza un JSON de OC en fila resumen + filas detalle."""
    comp = oc.get("Comprador") or {}
    prov = oc.get("Proveedor") or {}
    fech = oc.get("Fechas") or {}

    resumen = {
        "CodigoOC": codigo,
        "LinkMP": generar_link_mp(codigo),
        "NombreOC": limpiar(oc.get("Nombre")),
        "CodigoEstado": oc.get("CodigoEstado"),
        "EstadoOC": oc.get("Estado"),
        "CodigoLicitacion": oc.get("CodigoLicitacion"),
        "TipoOC": oc.get("Tipo"),
        "TipoMoneda": oc.get("TipoMoneda"),
        "Financiamiento": oc.get("Financiamiento"),
        "FormaPago": oc.get("FormaPago"),
        "TipoDespacho": oc.get("TipoDespacho"),
        "Pais": oc.get("Pais"),
        "FechaCreacion": fech.get("FechaCreacion"),
        "FechaEnvio": fech.get("FechaEnvio"),
        "FechaAceptacion": fech.get("FechaAceptacion"),
        "FechaCancelacion": fech.get("FechaCancelacion"),
        "FechaUltimaModificacion": fech.get("FechaUltimaModificacion"),
        "PromedioCalificacion": oc.get("PromedioCalificacion"),
        "CantidadEvaluacion": oc.get("CantidadEvaluacion"),
        "TotalNeto": oc.get("TotalNeto"),
        "PorcentajeIva": oc.get("PorcentajeIva"),
        "Impuestos": oc.get("Impuestos"),
        "TotalBruto": oc.get("Total"),
        "C_CodigoUnidad": comp.get("CodigoUnidad"),
        "C_Unidad": comp.get("NombreUnidad"),
        "C_RutUnidad": comp.get("RutUnidad"),
        "C_Actividad": comp.get("Actividad"),
        "C_Direccion": comp.get("DireccionUnidad"),
        "C_Comuna": comp.get("ComunaUnidad"),
        "C_Region": comp.get("RegionUnidad"),
        "C_Contacto": comp.get("NombreContacto"),
        "C_Cargo": comp.get("CargoContacto"),
        "C_Email": comp.get("MailContacto"), #Duplicado
        "P_Codigo": prov.get("Codigo"),
        "P_Nombre": prov.get("Nombre"),
        "P_Rut": prov.get("RutSucursal"),
        "P_Actividad": limpiar(prov.get("Actividad")),
        "P_Direccion": limpiar(prov.get("Direccion")),
        "P_Comuna": prov.get("Comuna"),
        "P_Region": prov.get("Region"),
        "P_Contacto": prov.get("NombreContacto"),
        "P_Cargo": prov.get("CargoContacto"),
        "P_Email": prov.get("MailContacto"), #Duplicado
        "DescripcionOC": limpiar(oc.get("Descripcion")),
    }

    detalles: List[Dict[str, Any]] = []
    items_list = oc.get("Items", {}).get("Listado", []) if oc.get("Items") else []
    for it in items_list:
        detalles.append(
            {
                "CodigoOC": codigo,
                "Correlativo": it.get("Correlativo"),
                "CodigoCategoria": it.get("CodigoCategoria"),
                "Categoria": limpiar(it.get("Categoria")),
                "CodigoProducto": it.get("CodigoProducto"),
                "Producto": limpiar(it.get("Producto")),
                "EspecificacionComprador": limpiar(it.get("EspecificacionComprador")),
                "EspecificacionProveedor": limpiar(it.get("EspecificacionProveedor")),
                "Cantidad": it.get("Cantidad"),
                "Unidad": it.get("Unidad"),
                "PrecioNeto": it.get("PrecioNeto"),
                "TotalImpuestos": it.get("TotalImpuestos"),
                "TotalLinea": it.get("Total"),
            }
        )

    return resumen, detalles

# =========================
# PROCESAMIENTO DIARIO (EXTRACCIÓN)
# =========================

def procesar_dia(
    fecha_dt,
    modo_actualizar=False,
    codigo_organismo: str = CODIGO_ORGANISMO,
    ticket: str = TICKET,
    max_workers_detalle: int = MAX_WORKERS_DETALLE,
    espera_entre_detalles: float = ESPERA_ENTRE_DETALLES,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
):
    """
    Descarga las OCs de un día específico y las guarda en la carpeta DIARIO.
    Retorna True si descargó datos, False si no encontró nada.
    """
    fecha_consulta = fecha_dt.strftime("%d/%m/%Y")
    f_str = fecha_dt.strftime("%Y%m%d")
    
    # Definimos las rutas
    ruta_resumen = CARPETA_DIARIO / f"SSO_{f_str}_RESUMEN.csv"
    ruta_detalles = CARPETA_DIARIO / f"SSO_{f_str}_DETALLES.csv"

    # Cache en disco: si ya existen ambos archivos y no se fuerza actualización, se evita trabajo.
    if (not modo_actualizar) and ruta_resumen.exists() and ruta_detalles.exists():
        print("    ✅ Ya existe en DIARIO (cache).")
        return True

    # Lógica de Actualización: Borrar previo a la descarga si existe
    if modo_actualizar:
        if ruta_resumen.exists():
            ruta_resumen.unlink()
        if ruta_detalles.exists():
            ruta_detalles.unlink()

    print(f"\n>>> EXTRACCIÓN SSO: {fecha_consulta}")
    
    client = MercadoPublicoClient(ApiConfig(codigo_organismo=codigo_organismo, ticket=ticket))
    ocs_basicas = client.obtener_listado_dia(fecha_dt)
    if not ocs_basicas:
        print("    ⚠ Sin datos en API para esta fecha.")
        return False

    db_resumen: List[Dict[str, Any]] = []
    db_detalles: List[Dict[str, Any]] = []

    codigos: List[str] = [str(item.get("Codigo")) for item in ocs_basicas if item.get("Codigo")]
    total = len(codigos)

    def _fetch_one(idx_codigo: Tuple[int, str]) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        idx, codigo = idx_codigo
        oc = client.obtener_detalle_oc(codigo)
        time.sleep(espera_entre_detalles)
        if not oc:
            return None
        return _extraer_resumen_y_detalles(codigo, oc)

    # Concurrencia controlada: acelera drásticamente cuando hay muchas OCs por día.
    with ThreadPoolExecutor(max_workers=max_workers_detalle) as ex:
        future_to_codigo = {ex.submit(_fetch_one, (i, c)): c for i, c in enumerate(codigos, 1)}

        for done_count, fut in enumerate(as_completed(future_to_codigo), 1):
            codigo = future_to_codigo[fut]

            if progress_callback:
                try:
                    progress_callback(codigo, done_count, total)
                except Exception:
                    pass

            if done_count % 10 == 0 or done_count == total:
                print(f"    Procesadas {done_count}/{total} OCs", end="\r")

            res = fut.result()
            if not res:
                continue
            resumen, detalles = res
            db_resumen.append(resumen)
            db_detalles.extend(detalles)

    # GUARDADO EN CSV
    if not db_resumen:
        return False

    _write_csv_dicts(ruta_resumen, db_resumen)
    _write_csv_dicts(ruta_detalles, db_detalles)

    print(f"\n✅ Guardado en DIARIO: {f_str}")
    return True

# =======================================================
# NUEVAS FUNCIONES: UNIFICACIÓN Y REFRESH (PANDAS)
# =======================================================

def unificar_base_datos():
    """
    5) Lee todos los CSVs de la carpeta DIARIO y crea/sobreescribe 
    los archivos Maestros en la carpeta MAESTROS.
    """
    print("\n🔄 INICIANDO UNIFICACIÓN DE BASE DE DATOS...")
    
    # --- PROCESAR RESUMEN ---
    print("   -> Buscando archivos de Resumen en DIARIO...")
    archivos_res = list(CARPETA_DIARIO.glob("*_RESUMEN.csv"))
    
    if archivos_res:
        # Nota: si la carpeta DIARIO crece mucho, esta concatenación puede consumir RAM.
        # Para grandes volúmenes, conviene migrar a un almacenamiento incremental (SQLite/Parquet).
        df_res = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_res],
            ignore_index=True,
        )

        df_res.drop_duplicates(subset=["CodigoOC"], keep="last", inplace=True)
        
        df_res["LinkMP"] = df_res["CodigoOC"].apply(generar_link_mp)

        ruta_m_res = CARPETA_MAESTROS / "OC_Maestro_Resumen.csv"
        df_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Resumen creado: {len(df_res)} registros.")

    else:
        print("   ⚠️ No se encontraron archivos de Resumen en DIARIO.")

    # --- PROCESAR DETALLES ---
    print("   -> Buscando archivos de Detalles en DIARIO...")
    archivos_det = list(CARPETA_DIARIO.glob("*_DETALLES.csv"))
    
    if archivos_det:
        df_det = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_det],
            ignore_index=True,
        )

        df_det.drop_duplicates(subset=["CodigoOC", "Correlativo"], keep="last", inplace=True)

        ruta_m_det = CARPETA_MAESTROS / "OC_Maestro_Detalles.csv"
        df_det.to_csv(ruta_m_det, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Detalles creado: {len(df_det)} registros.")

    else:
        print("   ⚠️ No se encontraron archivos de Detalles en DIARIO.")

def refresh_base_datos(
    f_ini,
    f_fin,
    codigo_organismo: str = CODIGO_ORGANISMO,
    ticket: str = TICKET,
    max_workers_detalle: int = MAX_WORKERS_DETALLE,
    espera_entre_detalles: float = ESPERA_ENTRE_DETALLES,
    progress_callback: Optional[Callable[[dt.date, str, int, int], None]] = None,
):
    """
    6) Descarga rango, lee Maestros, actualiza (Upsert) y guarda.
    """
    print(f"\n🚀 INICIANDO REFRESH DE BASE DE DATOS ({f_ini} al {f_fin})")
    
    # 1. DESCARGA MASIVA A DIARIO
    d_actual = f_ini
    dias_descargados = []
    
    while d_actual <= f_fin:
        # Callback de OC para este día (se propaga desde Streamlit)
        def _cb_oc(codigo: str, done: int, total: int) -> None:
            if progress_callback:
                progress_callback(d_actual, codigo, done, total)

        hubo_datos = procesar_dia(
            d_actual,
            modo_actualizar=True,
            codigo_organismo=codigo_organismo,
            ticket=ticket,
            max_workers_detalle=max_workers_detalle,
            espera_entre_detalles=espera_entre_detalles,
            progress_callback=_cb_oc,
        )
        if hubo_datos:
            dias_descargados.append(d_actual)
        d_actual += dt.timedelta(days=1)
    
    if not dias_descargados:
        print("\n⚠️ No se encontraron nuevos datos en el rango seleccionado. Los Maestros no se tocarán.")
        return

    print("\n🔄 INTEGRANDO NUEVOS DATOS A LOS MAESTROS (UPSERT)...")

    # Rutas Maestros
    ruta_m_res = CARPETA_MAESTROS / "OC_Maestro_Resumen.csv"
    ruta_m_det = CARPETA_MAESTROS / "OC_Maestro_Detalles.csv"

    # --- ACTUALIZAR RESUMEN ---
    # Cargar Maestro existente o crear vacío
    if ruta_m_res.exists():
        df_master_res = pd.read_csv(ruta_m_res, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_res = pd.DataFrame()

    # Cargar Nuevos Archivos Diarios
    archivos_nuevos_res = [CARPETA_DIARIO / f"SSO_{d.strftime('%Y%m%d')}_RESUMEN.csv" for d in dias_descargados]
    df_nuevos_res = pd.concat(
        [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_res if f.exists()],
        ignore_index=True,
    )

    if not df_nuevos_res.empty:
        # Concatenar y deduplicar (Keep Last asegura que la versión nueva de la OC reemplace a la vieja)
        df_final_res = pd.concat([df_master_res, df_nuevos_res])
        df_final_res.drop_duplicates(subset=["CodigoOC"], keep="last", inplace=True)
        
        df_final_res["LinkMP"] = df_final_res["CodigoOC"].apply(generar_link_mp)
        
        df_final_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Resumen actualizado. Total registros: {len(df_final_res)}")

    # --- ACTUALIZAR DETALLES ---
    if ruta_m_det.exists():
        df_master_det = pd.read_csv(ruta_m_det, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_det = pd.DataFrame()

    archivos_nuevos_det = [CARPETA_DIARIO / f"SSO_{d.strftime('%Y%m%d')}_DETALLES.csv" for d in dias_descargados]
    df_nuevos_det = pd.concat(
        [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_det if f.exists()],
        ignore_index=True,
    )

    if not df_nuevos_det.empty:
        # ESTRATEGIA SEGURA: 
        # Si una OC se modificó, sus items pueden haber cambiado (cantidad, borrado, agregado).
        # Identificamos las OCs que vinieron en la nueva carga.
        ocs_actualizadas = df_nuevos_det["CodigoOC"].unique()
        
        # Borramos del Maestro antiguo TODOS los items de esas OCs
        if not df_master_det.empty:
            df_master_det = df_master_det[~df_master_det["CodigoOC"].isin(ocs_actualizadas)]
        
        # Agregamos los items nuevos (que son la versión "foto" actual completa de esa OC)
        df_final_det = pd.concat([df_master_det, df_nuevos_det])
        
        df_final_det.to_csv(ruta_m_det, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Detalles actualizado. Total registros: {len(df_final_det)}")

    print("\n✨ PROCESO DE REFRESH COMPLETADO EXITOSAMENTE.")

def enlazar_con_pac():
    """
    7) Lee OC_Maestro_Resumen.csv y OCPAC_Maestro.csv.
    Añade columnas EnlacePAC e ID Proyecto guiándose por OC Asociada PAC.
    """
    print("\n🔗 INICIANDO ENLACE CON PLAN ANUAL DE COMPRAS (PAC)...")
    ruta_m_res = CARPETA_MAESTROS / "OC_Maestro_Resumen.csv"
    ruta_pac = RUTA_API.parent / "data" / "data_pac" / "OCPAC_Maestro.csv"

    if not ruta_m_res.exists():
        print("   ⚠️ No se encontró OC_Maestro_Resumen.csv en MAESTROS.")
        return
    
    if not ruta_pac.exists():
        print("   ⚠️ No se encontró OCPAC_Maestro.csv en data/data_pac.")
        return

    print("   -> Cargando OC_Maestro_Resumen.csv...")
    df_res = pd.read_csv(ruta_m_res, sep=";", encoding="utf-8-sig", dtype=str)
    
    print("   -> Cargando OCPAC_Maestro.csv...")
    try:
        # Se asume delimitador coma, típico de CSV, con fallback por defecto en pandas en caso de errores en la forma
        df_pac = pd.read_csv(ruta_pac, sep=",", encoding="utf-8-sig", dtype=str)
    except Exception as e:
        print(f"   ⚠️ Error al leer OCPAC_Maestro.csv: {e}")
        return

    # Verificar si el archivo pudiera estar separado por punto y coma si no encuentra las columnas
    if "OC Asociada PAC" not in df_pac.columns or "ID Proyecto" not in df_pac.columns:
        df_pac = pd.read_csv(ruta_pac, sep=";", encoding="utf-8-sig", dtype=str)
        if "OC Asociada PAC" not in df_pac.columns or "ID Proyecto" not in df_pac.columns:
            print(f"   ⚠️ OCPAC_Maestro.csv no tiene las columnas 'ID Proyecto' o 'OC Asociada PAC'.")
            return

    # Limpiar columnas previas si existían en el Maestro para que no haya duplicación (Ej: ID Proyecto_x, _y)
    if "EnlacePAC" in df_res.columns:
        df_res.drop(columns=["EnlacePAC"], inplace=True)
    if "ID Proyecto" in df_res.columns:
        df_res.drop(columns=["ID Proyecto"], inplace=True)

    # Dejamos solo valores únicos de OC en PAC para evitar multiplicar filas en Resumen
    df_pac_reducido = df_pac[["OC Asociada PAC", "ID Proyecto"]].drop_duplicates(subset=["OC Asociada PAC"], keep="first")
    
    print("   -> Cruzando datos...")
    df_merged = df_res.merge(
        df_pac_reducido,
        left_on="CodigoOC",
        right_on="OC Asociada PAC",
        how="left"
    )

    # Si hay coincidencias, el campo 'OC Asociada PAC' tendrá valor
    df_merged["EnlacePAC"] = df_merged["OC Asociada PAC"].apply(lambda x: "Enlazada" if pd.notnull(x) and str(x).strip() != "" else "No Enlazada")
    
    # Eliminamos la columna transitoria del join
    df_merged.drop(columns=["OC Asociada PAC"], inplace=True)

    df_merged["LinkMP"] = df_merged["CodigoOC"].apply(generar_link_mp)

    print("   -> Guardando OC_Maestro_Resumen.csv...")
    df_merged.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
    print(f"   ✅ Archivo actualizado exitosamente con {len(df_merged)} registros.")
    print(f"   📊 Resumen Enlace PAC:\n{df_merged['EnlacePAC'].value_counts().to_string()}")


# =========================
# MENÚ PRINCIPAL
# =========================

if __name__ == "__main__":
    while True:
        print("\n=========================================")
        print("   EXTRACTOR SSO ULTRA - GESTIÓN TOTAL")
        print("=========================================")
        print("1) Hoy (Descarga a DIARIO)")
        print("2) Manual (Un día a DIARIO)")
        print("3) Rango de fechas (Solo descarga lo nuevo a DIARIO)")
        print("-" * 40)
        print("5) UNIFICAR BASE DATOS (Crea Maestros desde DIARIO)")
        print("6) REFRESH BASE DATOS (Descarga Rango + Actualiza Maestros)")
        print("7) ENLACE PAC (Añade ID Proyecto a OC_Maestro_Resumen)")
        print("0) Salir")
        
        op = input("\nSeleccione opción: ")
        
        try:
            if op == "0": 
                break
            
            elif op == "1": 
                procesar_dia(dt.date.today())
            
            elif op == "2":
                f_in = input("Fecha (dd-mm-aaaa): ")
                procesar_dia(dt.datetime.strptime(f_in, "%d-%m-%Y").date())
            
            elif op == "3":
                ini = input("Desde (dd-mm-aaaa): ")
                fin = input("Hasta (dd-mm-aaaa): ")
                d1 = dt.datetime.strptime(ini, "%d-%m-%Y").date()
                d2 = dt.datetime.strptime(fin, "%d-%m-%Y").date()
                while d1 <= d2:
                    procesar_dia(d1, modo_actualizar=False)
                    d1 += dt.timedelta(days=1)
            
            elif op == "5":
                unificar_base_datos()
                
            elif op == "6":
                ini = input("Desde (dd-mm-aaaa): ")
                fin = input("Hasta (dd-mm-aaaa): ")
                d_ini = dt.datetime.strptime(ini, "%d-%m-%Y").date()
                d_fin = dt.datetime.strptime(fin, "%d-%m-%Y").date()
                refresh_base_datos(d_ini, d_fin)

            elif op == "7":
                enlazar_con_pac()

        except Exception as e: 
            print(f"\n❌ Error: {e}")