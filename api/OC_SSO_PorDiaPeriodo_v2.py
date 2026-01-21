import urllib.request
import urllib.parse
import json
import datetime as dt
import pathlib
import csv
import ssl
import time
import os
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

# =========================
# FUNCIONES DE APOYO API
# =========================

def llamada_api(url, params):
    ctx = ssl._create_unverified_context()
    url_completa = url + "?" + urllib.parse.urlencode(params)
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            with urllib.request.urlopen(url_completa, context=ctx, timeout=30) as resp:
                return json.load(resp)
        except:
            time.sleep(ESPERA_ENTRE_INTENTOS)
    return None

def obtener_detalle_oc(codigo_oc):
    params = {"codigo": codigo_oc, "ticket": TICKET}
    url = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
    data = llamada_api(url, params)
    return data["Listado"][0] if data and data.get("Listado") else None

def limpiar(texto):
    if texto is None: return ""
    return str(texto).replace("\n", " ").replace(";", ",").replace("\r", " ").strip()

# =========================
# PROCESAMIENTO DIARIO (EXTRACCIÓN)
# =========================

def procesar_dia(fecha_dt, modo_actualizar=False):
    """
    Descarga las OCs de un día específico y las guarda en la carpeta DIARIO.
    Retorna True si descargó datos, False si no encontró nada.
    """
    fecha_consulta = fecha_dt.strftime("%d/%m/%Y")
    f_str = fecha_dt.strftime("%Y%m%d")
    
    # Definimos las rutas
    ruta_resumen = CARPETA_DIARIO / f"SSO_{f_str}_RESUMEN.csv"
    ruta_detalles = CARPETA_DIARIO / f"SSO_{f_str}_DETALLES.csv"

    # Lógica de Actualización: Borrar previo a la descarga si existe
    if modo_actualizar:
        if ruta_resumen.exists(): ruta_resumen.unlink()
        if ruta_detalles.exists(): ruta_detalles.unlink()

    print(f"\n>>> EXTRACCIÓN SSO: {fecha_consulta}")
    
    params = {"fecha": fecha_dt.strftime("%d%m%Y"), "CodigoOrganismo": CODIGO_ORGANISMO, "ticket": TICKET}
    url_listado = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
    
    data_listado = llamada_api(url_listado, params)
    if not data_listado or not data_listado.get("Listado"):
        print("    ⚠ Sin datos en API para esta fecha.")
        return False

    ocs_basicas = data_listado["Listado"]
    db_resumen = []
    db_detalles = []

    for i, item_b in enumerate(ocs_basicas, 1):
        codigo = item_b.get("Codigo")
        print(f"    [{i}/{len(ocs_basicas)}] Procesando: {codigo}", end="\r")
        
        oc = obtener_detalle_oc(codigo)
        if not oc: continue

        comp = oc.get("Comprador") or {}
        prov = oc.get("Proveedor") or {}
        fech = oc.get("Fechas") or {}

        # 1. TABLA RESUMEN (Estructura completa solicitada)
        db_resumen.append({
            "CodigoOC": codigo,
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
            # Fechas Detalladas
            "FechaCreacion": fech.get("FechaCreacion"),
            "FechaEnvio": fech.get("FechaEnvio"),
            "FechaAceptacion": fech.get("FechaAceptacion"),
            "FechaCancelacion": fech.get("FechaCancelacion"),
            "FechaUltimaModificacion": fech.get("FechaUltimaModificacion"),
            # Métricas y Totales
            "PromedioCalificacion": oc.get("PromedioCalificacion"),
            "CantidadEvaluacion": oc.get("CantidadEvaluacion"),
            "TotalNeto": oc.get("TotalNeto"),
            "PorcentajeIva": oc.get("PorcentajeIva"),
            "Impuestos": oc.get("Impuestos"),
            "TotalBruto": oc.get("Total"),
            # Datos Comprador (SSO)
            "C_CodigoUnidad": comp.get("CodigoUnidad"),
            "C_Unidad": comp.get("NombreUnidad"),
            "C_RutUnidad": comp.get("RutUnidad"),
            "C_Actividad": comp.get("Actividad"),
            "C_Direccion": comp.get("DireccionUnidad"),
            "C_Comuna": comp.get("ComunaUnidad"),
            "C_Region": comp.get("RegionUnidad"),
            "C_Contacto": comp.get("NombreContacto"),
            "C_Cargo": comp.get("CargoContacto"),
            "C_Email": comp.get("MailContacto"),
            # Datos Proveedor
            "P_Codigo": prov.get("Codigo"),
            "P_Nombre": prov.get("Nombre"),
            "P_Rut": prov.get("RutSucursal"),
            "P_Actividad": limpiar(prov.get("Actividad")),
            "P_Direccion": limpiar(prov.get("Direccion")),
            "P_Comuna": prov.get("Comuna"),
            "P_Region": prov.get("Region"),
            "P_Contacto": prov.get("NombreContacto"),
            "P_Cargo": prov.get("CargoContacto"),
            "P_Email": prov.get("MailContacto"),
            # Otros
            "DescripcionOC": limpiar(oc.get("Descripcion"))
        })

        # 2. TABLA DETALLES
        items_list = oc.get("Items", {}).get("Listado", []) if oc.get("Items") else []
        for it in items_list:
            db_detalles.append({
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
                "TotalLinea": it.get("Total")
            })
        time.sleep(0.1) # Breve pausa para no saturar

    # GUARDADO EN CSV
    if db_resumen:
        for nombre_archivo, data_list in [(ruta_resumen, db_resumen), (ruta_detalles, db_detalles)]:
            with open(nombre_archivo, "w", newline="", encoding="utf-8-sig") as csvfile:
                if data_list:
                    w = csv.DictWriter(csvfile, fieldnames=data_list[0].keys(), delimiter=";")
                    w.writeheader()
                    w.writerows(data_list)
        
        print(f"\n✅ Guardado en DIARIO: {f_str}")
        return True
    else:
        return False

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
        # Leemos todos los archivos y los concatenamos. dtype=str protege los códigos con ceros.
        df_res = pd.concat([pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_res], ignore_index=True)
        
        # Deduplicamos por CodigoOC, quedándonos con el último encontrado (asumiendo que fechas posteriores sobreescriben)
        df_res.drop_duplicates(subset=["CodigoOC"], keep="last", inplace=True)
        
        ruta_m_res = CARPETA_MAESTROS / "OC_Maestro_Resumen.csv"
        df_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Resumen creado: {len(df_res)} registros.")
    else:
        print("   ⚠️ No se encontraron archivos de Resumen en DIARIO.")

    # --- PROCESAR DETALLES ---
    print("   -> Buscando archivos de Detalles en DIARIO...")
    archivos_det = list(CARPETA_DIARIO.glob("*_DETALLES.csv"))
    
    if archivos_det:
        df_det = pd.concat([pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_det], ignore_index=True)
        
        # Deduplicamos por OC + Correlativo
        df_det.drop_duplicates(subset=["CodigoOC", "Correlativo"], keep="last", inplace=True)
        
        ruta_m_det = CARPETA_MAESTROS / "OC_Maestro_Detalles.csv"
        df_det.to_csv(ruta_m_det, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Detalles creado: {len(df_det)} registros.")
    else:
        print("   ⚠️ No se encontraron archivos de Detalles en DIARIO.")

def refresh_base_datos(f_ini, f_fin):
    """
    6) Descarga rango, lee Maestros, actualiza (Upsert) y guarda.
    """
    print(f"\n🚀 INICIANDO REFRESH DE BASE DE DATOS ({f_ini} al {f_fin})")
    
    # 1. DESCARGA MASIVA A DIARIO
    d_actual = f_ini
    dias_descargados = []
    
    while d_actual <= f_fin:
        # procesar_dia guarda en DIARIO y devuelve True si hubo datos
        hubo_datos = procesar_dia(d_actual, modo_actualizar=True)
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
    df_nuevos_res = pd.concat([pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_res if f.exists()])

    if not df_nuevos_res.empty:
        # Concatenar y deduplicar (Keep Last asegura que la versión nueva de la OC reemplace a la vieja)
        df_final_res = pd.concat([df_master_res, df_nuevos_res])
        df_final_res.drop_duplicates(subset=["CodigoOC"], keep="last", inplace=True)
        
        df_final_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Resumen actualizado. Total registros: {len(df_final_res)}")

    # --- ACTUALIZAR DETALLES ---
    if ruta_m_det.exists():
        df_master_det = pd.read_csv(ruta_m_det, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_det = pd.DataFrame()

    archivos_nuevos_det = [CARPETA_DIARIO / f"SSO_{d.strftime('%Y%m%d')}_DETALLES.csv" for d in dias_descargados]
    df_nuevos_det = pd.concat([pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_det if f.exists()])

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

        except Exception as e: 
            print(f"\n❌ Error: {e}")