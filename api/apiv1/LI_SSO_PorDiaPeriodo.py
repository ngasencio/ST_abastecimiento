import urllib.request
import urllib.parse
import json
import datetime as dt
import pathlib
import csv
import ssl
import time
import os

# =========================
# CONFIGURACIÓN FIJA SSO (LICITACIONES)
# =========================
CODIGO_ORGANISMO = "7296"
TICKET = "2798F2D3-0AC5-4323-9BB9-5E90618194BA"

# 1. Detectamos la ubicación del archivo actual (que debe estar en la carpeta 'api')
RUTA_API = pathlib.Path(__file__).parent.absolute()

# 2. Construimos las rutas desde esa posición
# Esto entra a la carpeta LI_DSSO y luego a DIARIO sin importar dónde esté la raíz
CARPETA_BASE = RUTA_API / "LI_DSSO"
CARPETA_SALIDA = CARPETA_BASE / "DIARIO"

MAX_REINTENTOS = 5
ESPERA_ENTRE_INTENTOS = 4.0

# =========================
# FUNCIONES DE CONEXIÓN
# =========================

def llamada_api(params):
    """Función genérica para llamar a la API de Licitaciones"""
    url_base = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
    ctx = ssl._create_unverified_context()
    url_completa = url_base + "?" + urllib.parse.urlencode(params)
    
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            with urllib.request.urlopen(url_completa, context=ctx, timeout=30) as resp:
                return json.load(resp)
        except Exception as e:
            if intento < MAX_REINTENTOS:
                time.sleep(ESPERA_ENTRE_INTENTOS)
            else:
                return None
    return None

def obtener_detalle_licitacion(codigo_externo):
    """Obtiene el JSON completo de una licitación específica"""
    params = {"codigo": codigo_externo, "ticket": TICKET}
    data = llamada_api(params)
    return data["Listado"][0] if data and data.get("Listado") else None

def limpiar(texto):
    if texto is None: return ""
    return str(texto).replace("\n", " ").replace(";", ",").replace("\r", " ").strip()

def to_float(val):
    try: return float(val)
    except: return 0.0

# =========================
# PROCESAMIENTO
# =========================

def procesar_dia(fecha_dt, modo_actualizar=False):
    fecha_consulta = fecha_dt.strftime("%d/%m/%Y")
    f_str = fecha_dt.strftime("%Y%m%d")
    
    # Rutas de archivos
    ruta_res = CARPETA_SALIDA / f"LICITACION_SSO_{f_str}_RESUMEN.csv"
    ruta_det = CARPETA_SALIDA / f"LICITACION_SSO_{f_str}_DETALLES.csv"

    # 1. Lógica de Actualización (Borrado previo)
    if modo_actualizar:
        print(f"\n>>> ACTUALIZANDO: Verificando archivos del {fecha_consulta}...")
        borrados = 0
        if ruta_res.exists():
            ruta_res.unlink()
            borrados += 1
        if ruta_det.exists():
            ruta_det.unlink()
            borrados += 1
        if borrados > 0: print(f"    [i] Se eliminaron {borrados} archivos antiguos.")

    print(f"\n>>> LICITACIONES SSO: {fecha_consulta}")
    
    params = {
        "fecha": fecha_dt.strftime("%d%m%Y"),
        "CodigoOrganismo": CODIGO_ORGANISMO,
        "ticket": TICKET
    }
    
    data_listado = llamada_api(params)
    
    if not data_listado or not data_listado.get("Listado"):
        print("    ⚠ Sin licitaciones publicadas/modificadas este día.")
        return

    licitaciones_basicas = data_listado["Listado"]
    db_resumen = []
    db_detalles = []

    print(f"    Se encontraron {len(licitaciones_basicas)} licitaciones. Descargando detalles...")

    for i, item_b in enumerate(licitaciones_basicas, 1):
        codigo = item_b.get("CodigoExterno")
        print(f"    [{i}/{len(licitaciones_basicas)}] Procesando: {codigo}", end="\r")
        
        lic = obtener_detalle_licitacion(codigo)
        if not lic: continue

        # --- CORRECCIÓN CLAVE: Protección contra Null (or {}) ---
        # Si la API devuelve null en estos campos, forzamos un diccionario vacío {}
        comp = lic.get("Comprador") or {}
        fech = lic.get("Fechas") or {}
        
        # --- TABLA 1: RESUMEN (CABECERA) ---
        db_resumen.append({
            "CodigoLicitacion": codigo,
            "Nombre": limpiar(lic.get("Nombre")),
            "Estado": lic.get("Estado"),
            "Descripcion": limpiar(lic.get("Descripcion")),
            "Tipo": lic.get("Tipo"),
            "Moneda": lic.get("Moneda"),
            "MontoEstimado": to_float(lic.get("MontoEstimado")),
            "FuenteFinanciamiento": lic.get("FuenteFinanciamiento"),
            "VisibilidadMonto": lic.get("VisibilidadMonto"),
            "JustificacionMonto": limpiar(lic.get("JustificacionMontoEstimado")),
            # Fechas
            "FechaCreacion": fech.get("FechaCreacion"),
            "FechaPublicacion": fech.get("FechaPublicacion"),
            "FechaCierre": fech.get("FechaCierre"),
            "FechaAdjudicacion": fech.get("FechaAdjudicacion"),
            "FechaEstimadaFirma": fech.get("FechaEstimadaFirma"),
            "FechaInicioContrato": fech.get("FechaInicio"),
            # Comprador
            "C_Unidad": comp.get("NombreUnidad"),
            "C_RutUnidad": comp.get("RutUnidad"),
            "C_Usuario": comp.get("NombreUsuario"),
            "C_Cargo": comp.get("CargoUsuario"),
            # Responsables
            "Resp_Contrato": lic.get("NombreResponsableContrato"),
            "Resp_Email": lic.get("EmailResponsableContrato"),
            "Resp_Pago": lic.get("NombreResponsablePago"),
            # Tiempos
            "TiempoDuracionContrato": lic.get("TiempoDuracionContrato"),
            "UnidadTiempoDuracion": lic.get("UnidadTiempoDuracionContrato"),
            "EsRenovable": lic.get("EsRenovable")
        })

        # --- TABLA 2: DETALLES ---
        # Protección extra también aquí:
        obj_items = lic.get("Items") or {}
        items_list = obj_items.get("Listado") or []
        
        # Si items_list es None (aunque raro si Items existe), lo forzamos a lista vacía
        if not isinstance(items_list, list): items_list = []

        for it in items_list:
            # Protección contra adjudicación nula
            adj = it.get("Adjudicacion") or {}
            
            db_detalles.append({
                "CodigoLicitacion": codigo,
                "Correlativo": it.get("Correlativo"),
                "Categoria": it.get("Categoria"),
                "CodigoProducto": it.get("CodigoProducto"),
                "NombreProducto": limpiar(it.get("NombreProducto")),
                "DescripcionItem": limpiar(it.get("Descripcion")),
                "UnidadMedida": it.get("UnidadMedida"),
                "Cantidad": it.get("Cantidad"),
                # Datos de Adjudicación
                "RutGanador": adj.get("RutProveedor", ""),
                "NombreGanador": adj.get("NombreProveedor", ""),
                "MontoUnitarioGanador": to_float(adj.get("MontoUnitario")),
                "CantidadAdjudicada": to_float(adj.get("Cantidad"))
            })
        
        time.sleep(0.2)

    # GUARDADO
    if db_resumen:
        CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
        
        for nombre, data in {ruta_res: db_resumen, ruta_det: db_detalles}.items():
            with open(nombre, "w", newline="", encoding="utf-8-sig") as csvfile:
                if data:
                    w = csv.DictWriter(csvfile, fieldnames=data[0].keys(), delimiter=";")
                    w.writeheader()
                    w.writerows(data)
        
        print(f"\n✅ Archivos guardados en: {CARPETA_SALIDA}")
    else:
        print("\n   [i] No se generaron archivos (posiblemente datos incompletos).")

if __name__ == "__main__":
    print("=========================================")
    print("   GESTOR DE LICITACIONES SSO (7296)")
    print("=========================================")
    print("1) Descargar HOY")
    print("2) Manual (Un día)")
    print("3) Rango de fechas (Solo nuevas)")
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
                print("\n⚠ SE BORRARÁN LOS ARCHIVOS EXISTENTES EN EL RANGO.")
            
            ini = input("Desde (dd-mm-aaaa): ")
            fin = input("Hasta (dd-mm-aaaa): ")
            d1 = dt.datetime.strptime(ini, "%d-%m-%Y").date()
            d2 = dt.datetime.strptime(fin, "%d-%m-%Y").date()
            
            while d1 <= d2:
                procesar_dia(d1, modo_actualizar=es_actualizacion)
                d1 += dt.timedelta(days=1)

    except Exception as e: 
        print(f"\n❌ Error Fatal: {e}")