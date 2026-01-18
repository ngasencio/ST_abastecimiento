import urllib.request
import urllib.parse
import json
import datetime as dt
import pathlib
import csv
import ssl
import time

# =========================
# CONFIGURACIÓN FIJA SSO
# =========================
CODIGO_ORGANISMO = "7296"
TICKET = "2798F2D3-0AC5-4323-9BB9-5E90618194BA"


# 1. Obtenemos la ruta donde está este archivo (api/)
RUTA_API = pathlib.Path(__file__).parent.absolute()

# 2. Definimos las carpetas de trabajo basándonos en esa posición
CARPETA_ORDENCOMPRA = RUTA_API / "OC_DSSO" / "DIARIO"
CARPETA_SALIDA = CARPETA_ORDENCOMPRA / "CONSOLIDADO"


#ESCRITORIO = pathlib.Path.home() / "Desktop"
#CARPETA_BASE = ESCRITORIO / "ST_abastecimiento" / "ST_abastecimiento" / "api" / "OC_DSSO"
#CARPETA_SALIDA = CARPETA_BASE / "DIARIO"

MAX_REINTENTOS = 5
ESPERA_ENTRE_INTENTOS = 4.0

# =========================
# FUNCIONES DE APOYO
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
# PROCESAMIENTO
# =========================

def procesar_dia(fecha_dt, modo_actualizar=False):
    fecha_consulta = fecha_dt.strftime("%d/%m/%Y")
    f_str = fecha_dt.strftime("%Y%m%d")
    
    # Definimos las rutas antes para poder borrarlas si es necesario
    ruta_resumen = CARPETA_SALIDA / f"SSO_{f_str}_RESUMEN.csv"
    ruta_detalles = CARPETA_SALIDA / f"SSO_{f_str}_DETALLES.csv"

    # Lógica de Actualización: Borrar previo a la descarga
    if modo_actualizar:
        print(f"\n>>> MODO ACTUALIZAR: Verificando archivos del {fecha_consulta}...")
        borrados = 0
        if ruta_resumen.exists():
            ruta_resumen.unlink()
            print(f"    [X] Eliminado antiguo: {ruta_resumen.name}")
            borrados += 1
        if ruta_detalles.exists():
            ruta_detalles.unlink()
            print(f"    [X] Eliminado antiguo: {ruta_detalles.name}")
            borrados += 1
        if borrados == 0:
            print("    [i] No existían archivos previos para este día.")

    print(f"\n>>> EXTRACCIÓN ULTRA SSO: {fecha_consulta}")
    
    params = {"fecha": fecha_dt.strftime("%d%m%Y"), "CodigoOrganismo": CODIGO_ORGANISMO, "ticket": TICKET}
    url_listado = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
    
    data_listado = llamada_api(url_listado, params)
    if not data_listado or not data_listado.get("Listado"):
        print("    ⚠ Sin datos en API para esta fecha.")
        return

    ocs_basicas = data_listado["Listado"]
    db_resumen = []
    db_detalles = []

    for i, item_b in enumerate(ocs_basicas, 1):
        codigo = item_b.get("Codigo")
        print(f"    [{i}/{len(ocs_basicas)}] Procesando: {codigo}", end="\r")
        
        oc = obtener_detalle_oc(codigo)
        if not oc: continue

        comp = oc.get("Comprador", {})
        prov = oc.get("Proveedor", {})
        fech = oc.get("Fechas", {})

        # 1. TABLA RESUMEN ULTRA (Todos los campos solicitados)
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
        time.sleep(0.2)

    # GUARDADO
    if db_resumen:
        CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        
        for nombre, data in {f"SSO_{f_str}_RESUMEN.csv": db_resumen, f"SSO_{f_str}_DETALLES.csv": db_detalles}.items():
            ruta_completa = CARPETA_SALIDA / nombre
            with open(ruta_completa, "w", newline="", encoding="utf-8-sig") as csvfile:
                w = csv.DictWriter(csvfile, fieldnames=data[0].keys(), delimiter=";")
                w.writeheader()
                w.writerows(data)
        
        print(f"\n✅ Archivos guardados en: {CARPETA_SALIDA}")

if __name__ == "__main__":
    print("=========================================")
    print("   EXTRACTOR SSO ULTRA - GESTIÓN TOTAL")
    print("=========================================")
    print("1) Hoy")
    print("2) Manual (Un día)")
    print("3) Rango de fechas (Solo descarga lo nuevo)")
    print("4) ACTUALIZAR Rango (BORRA y descarga de nuevo)")
    
    op = input("\nSeleccione opción: ")
    
    try:
        if op == "1": 
            procesar_dia(dt.date.today())
        
        elif op == "2":
            f_in = input("Fecha (dd-mm-aaaa): ")
            procesar_dia(dt.datetime.strptime(f_in, "%d-%m-%Y").date())
        
        elif op == "3" or op == "4":
            es_actualizacion = (op == "4")
            if es_actualizacion:
                print("\n⚠ ATENCIÓN: Esta opción BORRARÁ los archivos CSV existentes en el rango para descargarlos de nuevo.")
            
            ini = input("Desde (dd-mm-aaaa): ")
            fin = input("Hasta (dd-mm-aaaa): ")
            d1 = dt.datetime.strptime(ini, "%d-%m-%Y").date()
            d2 = dt.datetime.strptime(fin, "%d-%m-%Y").date()
            
            while d1 <= d2:
                procesar_dia(d1, modo_actualizar=es_actualizacion)
                d1 += dt.timedelta(days=1)

    except Exception as e: 
        print(f"\n❌ Error: {e}")