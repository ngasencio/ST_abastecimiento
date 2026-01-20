import urllib.request
import urllib.parse
import json
import datetime as dt
import pathlib
import csv
import ssl
import time
import os
import pandas as pd  # Importante para la gestión de bases de datos

# =========================
# CONFIGURACIÓN FIJA SSO
# =========================
CODIGO_ORGANISMO = "7296"
TICKET = "2798F2D3-0AC5-4323-9BB9-5E90618194BA"

# Rutas de carpetas
RUTA_API = pathlib.Path(__file__).parent.absolute()
CARPETA_DIARIO = RUTA_API / "OC_DSSO" / "DIARIO"
CARPETA_MAESTROS = RUTA_API / "OC_DSSO" / "MAESTROS" # Carpeta para los consolidados

# Asegurar existencia de directorios
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
# PROCESAMIENTO DIARIO
# =========================

def procesar_dia(fecha_dt, modo_actualizar=False):
    """Descarga OCs de un día y las guarda en DIARIO"""
    fecha_consulta = fecha_dt.strftime("%d/%m/%Y")
    f_str = fecha_dt.strftime("%Y%m%d")
    
    ruta_resumen = CARPETA_DIARIO / f"SSO_{f_str}_RESUMEN.csv"
    ruta_detalles = CARPETA_DIARIO / f"SSO_{f_str}_DETALLES.csv"

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
        print(f"    [{i}/{len(ocs_basicas)}] Procesando OC: {codigo}", end="\r")
        
        oc = obtener_detalle_oc(codigo)
        if not oc: continue

        comp = oc.get("Comprador") or {}
        prov = oc.get("Proveedor") or {}
        fech = oc.get("Fechas") or {}

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

        items_list = oc.get("Items", {}).get("Listado", []) if oc.get("Items") else []
        for it in items_list:
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
        time.sleep(0.1)

    if db_resumen:
        for f_path, data in {ruta_resumen: db_resumen, ruta_detalles: db_detalles}.items():
            with open(f_path, "w", newline="", encoding="utf-8-sig") as csvfile:
                w = csv.DictWriter(csvfile, fieldnames=data[0].keys(), delimiter=";")
                w.writeheader()
                w.writerows(data)
        print(f"\n✅ Guardado en DIARIO: {f_str}")
        return True
    return False

# =======================================================
# NUEVAS FUNCIONES: UNIFICACIÓN Y REFRESH (MAESTROS)
# =======================================================

def unificar_base_datos():
    """Lee carpeta DIARIO y crea Maestros desde cero"""
    print("\n🔄 UNIFICANDO MAESTROS DE ORDENES DE COMPRA...")
    
    for tipo in ["RESUMEN", "DETALLES"]:
        archivos = list(CARPETA_DIARIO.glob(f"*_{tipo}.csv"))
        if not archivos: continue
        
        print(f"   Procesando {len(archivos)} archivos de {tipo}...")
        df_total = pd.concat([pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos])
        
        # Deduplicar
        id_col = ["CodigoOC"] if tipo == "RESUMEN" else ["CodigoOC", "Correlativo"]
        df_total.drop_duplicates(subset=id_col, keep="last", inplace=True)
        
        nombre_maestro = f"OC_Maestro_{tipo.capitalize()}.csv"
        df_total.to_csv(CARPETA_MAESTROS / nombre_maestro, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ {nombre_maestro} creado con {len(df_total)} registros.")

def refresh_base_datos(f_ini, f_fin):
    """Descarga rango y actualiza Maestros (Upsert)"""
    print(f"\n🚀 REFRESH OC: {f_ini} al {f_fin}")
    
    # 1. Descarga
    d_act = f_ini
    descargados = []
    while d_act <= f_fin:
        if procesar_dia(d_act, modo_actualizar=True):
            descargados.append(d_act.strftime("%Y%m%d"))
        d_act += dt.timedelta(days=1)
    
    if not descargados:
        print("⚠ No hay datos nuevos para integrar.")
        return

    # 2. Actualizar Maestro Resumen
    ruta_m_res = CARPETA_MAESTROS / "OC_Maestro_Resumen.csv"
    df_m_res = pd.read_csv(ruta_m_res, sep=";", encoding="utf-8-sig", dtype=str) if ruta_m_res.exists() else pd.DataFrame()
    
    nuevos_res = pd.concat([pd.read_csv(CARPETA_DIARIO / f"SSO_{d}_RESUMEN.csv", sep=";", dtype=str) for d in descargados])
    
    df_final_res = pd.concat([df_m_res, nuevos_res]).drop_duplicates(subset=["CodigoOC"], keep="last")
    df_final_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
    
    # 3. Actualizar Maestro Detalle (Borrado de items antiguos de OCs modificadas)
    ruta_m_det = CARPETA_MAESTROS / "OC_Maestro_Detalles.csv"
    df_m_det = pd.read_csv(ruta_m_det, sep=";", encoding="utf-8-sig", dtype=str) if ruta_m_det.exists() else pd.DataFrame()
    
    nuevos_det = pd.concat([pd.read_csv(CARPETA_DIARIO / f"SSO_{d}_DETALLES.csv", sep=";", dtype=str) for d in descargados])
    
    # Limpiamos el maestro de las OCs que estamos actualizando para evitar duplicados de items
    ocs_actualizadas = nuevos_det["CodigoOC"].unique()
    df_m_det = df_m_det[~df_m_det["CodigoOC"].isin(ocs_actualizadas)]
    
    df_final_det = pd.concat([df_m_det, nuevos_det])
    df_final_det.to_csv(ruta_m_det, sep=";", index=False, encoding="utf-8-sig")
    
    print(f"\n✅ PROCESO COMPLETADO.")
    print(f"   Total OCs en Maestro: {len(df_final_res)}")

# =========================
# MENÚ PRINCIPAL
# =========================

if __name__ == "__main__":
    while True:
        print("\n=========================================")
        print("   GESTOR ORDENES DE COMPRA SSO (7296)")
        print("=========================================")
        print("1) Descargar HOY (Solo DIARIO)")
        print("2) Manual (Un día - Solo DIARIO)")
        print("3) Rango de fechas (Solo nuevas)")
        print("4) ACTUALIZAR Rango (BORRA y descarga)")
        print("-" * 30)
        print("5) UNIFICAR BASE DATOS (Maestros desde DIARIO)")
        print("6) REFRESH BASE DATOS (Descarga + Upsert Maestro)")
        print("0) Salir")
        
        op = input("\nSeleccione opción: ")
        
        try:
            if op == "0": break
            elif op == "1": procesar_dia(dt.date.today())
            elif op == "2":
                f = input("Fecha (dd-mm-aaaa): ")
                procesar_dia(dt.datetime.strptime(f, "%d-%m-%Y").date())
            elif op in ["3", "4"]:
                ini = dt.datetime.strptime(input("Desde: "), "%d-%m-%Y").date()
                fin = dt.datetime.strptime(input("Hasta: "), "%d-%m-%Y").date()
                d = ini
                while d <= fin:
                    procesar_dia(d, modo_actualizar=(op=="4"))
                    d += dt.timedelta(days=1)
            elif op == "5":
                unificar_base_datos()
            elif op == "6":
                ini = dt.datetime.strptime(input("Desde: "), "%d-%m-%Y").date()
                fin = dt.datetime.strptime(input("Hasta: "), "%d-%m-%Y").date()
                refresh_base_datos(ini, fin)
        except Exception as e:
            print(f"❌ Error: {e}")