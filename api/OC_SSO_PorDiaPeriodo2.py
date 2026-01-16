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

ESCRITORIO = pathlib.Path.home() / "Desktop"
CARPETA_BASE = ESCRITORIO / "ST_abastecimiento" / "ST_abastecimiento" / "api" / "OC_DSSO"
CARPETA_SALIDA = CARPETA_BASE / "DIARIO"

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
    
    # Solo definimos UNA ruta de salida
    ruta_resumen = CARPETA_SALIDA / f"SSO_{f_str}_RESUMEN.csv"

    # Lógica de Actualización: Borrar previo
    if modo_actualizar:
        print(f"\n>>> MODO ACTUALIZAR: Verificando archivos del {fecha_consulta}...")
        if ruta_resumen.exists():
            ruta_resumen.unlink()
            print(f"    [X] Eliminado antiguo: {ruta_resumen.name}")
        else:
            print("    [i] No existía archivo previo.")

    print(f"\n>>> EXTRACCIÓN UNIFICADA SSO: {fecha_consulta}")
    
    params = {"fecha": fecha_dt.strftime("%d%m%Y"), "CodigoOrganismo": CODIGO_ORGANISMO, "ticket": TICKET}
    url_listado = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
    
    data_listado = llamada_api(url_listado, params)
    if not data_listado or not data_listado.get("Listado"):
        print("    ⚠ Sin datos en API para esta fecha.")
        return

    ocs_basicas = data_listado["Listado"]
    db_consolidada = []

    for i, item_b in enumerate(ocs_basicas, 1):
        codigo = item_b.get("Codigo")
        print(f"    [{i}/{len(ocs_basicas)}] Procesando: {codigo}", end="\r")
        
        oc = obtener_detalle_oc(codigo)
        if not oc: continue

        comp = oc.get("Comprador", {})
        prov = oc.get("Proveedor", {})
        fech = oc.get("Fechas", {})
        
        # Obtenemos la lista de items (productos)
        items_list = oc.get("Items", {}).get("Listado", []) if oc.get("Items") else []

        # Si la OC no tiene items (raro, pero posible), creamos una lista con un elemento vacío
        # para que al menos se guarde la cabecera de la OC
        if not items_list:
            items_list = [{}]

        # --- AQUÍ OCURRE LA MAGIA ---
        # Iteramos por cada producto y le pegamos toda la info de la cabecera
        for it in items_list:
            fila = {
                # === DATOS DE CABECERA (Se repiten por cada producto) ===
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
                # Fechas
                "FechaCreacion": fech.get("FechaCreacion"),
                "FechaEnvio": fech.get("FechaEnvio"),
                "FechaAceptacion": fech.get("FechaAceptacion"),
                "FechaCancelacion": fech.get("FechaCancelacion"),
                "FechaUltimaModificacion": fech.get("FechaUltimaModificacion"),
                # Totales Generales de la OC
                "TotalNetoOC": oc.get("TotalNeto"),
                "PorcentajeIvaOC": oc.get("PorcentajeIva"),
                "ImpuestosOC": oc.get("Impuestos"),
                "TotalBrutoOC": oc.get("Total"),
                # Comprador
                "C_Unidad": comp.get("NombreUnidad"),
                "C_RutUnidad": comp.get("RutUnidad"),
                "C_Actividad": comp.get("Actividad"),
                "C_Direccion": comp.get("DireccionUnidad"),
                "C_Comuna": comp.get("ComunaUnidad"),
                "C_Region": comp.get("RegionUnidad"),
                "C_Contacto": comp.get("NombreContacto"),
                "C_Email": comp.get("MailContacto"),
                # Proveedor
                "P_Nombre": prov.get("Nombre"),
                "P_Rut": prov.get("RutSucursal"),
                "P_Actividad": limpiar(prov.get("Actividad")),
                "P_Direccion": limpiar(prov.get("Direccion")),
                "P_Comuna": prov.get("Comuna"),
                "P_Contacto": prov.get("NombreContacto"),
                "P_Email": prov.get("MailContacto"),
                "DescripcionOC": limpiar(oc.get("Descripcion")),

                # === DATOS DEL ITEM (Específicos de esta línea) ===
                "Correlativo": it.get("Correlativo", ""),
                "CodigoCategoria": it.get("CodigoCategoria", ""),
                "Categoria": limpiar(it.get("Categoria", "")),
                "CodigoProducto": it.get("CodigoProducto", ""),
                "Producto": limpiar(it.get("Producto", "")),
                "EspecificacionComprador": limpiar(it.get("EspecificacionComprador", "")),
                "EspecificacionProveedor": limpiar(it.get("EspecificacionProveedor", "")),
                "Cantidad": it.get("Cantidad", ""),
                "Unidad": it.get("Unidad", ""),
                "PrecioNetoUnitario": it.get("PrecioNeto", ""),
                "TotalImpuestosLinea": it.get("TotalImpuestos", ""),
                "TotalLinea": it.get("Total", "")
            }
            db_consolidada.append(fila)
        
        time.sleep(0.2) # Pausa para no saturar

    # GUARDADO EN UN SOLO ARCHIVO
    if db_consolidada:
        CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        
        with open(ruta_resumen, "w", newline="", encoding="utf-8-sig") as csvfile:
            # Usamos las llaves del primer elemento como encabezados
            w = csv.DictWriter(csvfile, fieldnames=db_consolidada[0].keys(), delimiter=";")
            w.writeheader()
            w.writerows(db_consolidada)
        
        print(f"\n✅ Archivo UNIFICADO guardado: {ruta_resumen.name}")

if __name__ == "__main__":
    print("=========================================")
    print("   EXTRACTOR SSO - TABLA UNICA")
    print("=========================================")
    print("1) Hoy")
    print("2) Manual (Un día)")
    print("3) Rango de fechas")
    print("4) ACTUALIZAR Rango (Borrar y re-descargar)")
    
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
                print("\n⚠ ATENCIÓN: Se BORRARÁN los archivos existentes en el rango.")
            
            ini = input("Desde (dd-mm-aaaa): ")
            fin = input("Hasta (dd-mm-aaaa): ")
            d1 = dt.datetime.strptime(ini, "%d-%m-%Y").date()
            d2 = dt.datetime.strptime(fin, "%d-%m-%Y").date()
            
            while d1 <= d2:
                procesar_dia(d1, modo_actualizar=es_actualizacion)
                d1 += dt.timedelta(days=1)

    except Exception as e: 
        print(f"\n❌ Error: {e}")