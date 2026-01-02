import urllib.request
import urllib.parse
import json
import datetime as dt
import pathlib
import csv
import ssl
import time
import sys

# =========================
# CONFIGURACIÓN BÁSICA
# =========================

# Código del HOSPITAL BASE OSORNO
CODIGO_ORGANISMO = "7393"

# Ticket REAL de ChileCompra
TICKET = "F7E99CCB-CA92-4921-AD23-ED76F06F940C"

# Carpeta base general
CARPETA_BASE = pathlib.Path("/Users/migueldumenes/Documents/OC_HBSJO2")

# Carpeta específica para los archivos de ESTE script (diario)
CARPETA_SALIDA = CARPETA_BASE / "DIARIO"

# Estados de la Orden de Compra
ESTADOS_OC = {
    "4": "Enviada a Proveedor",
    "5": "En proceso",
    "6": "Aceptada",
    "9": "Cancelada",
    "12": "Recepción Conforme",
    "13": "Pendiente de Recepcionar",
    "14": "Recepcionada Parcialmente",
    "15": "Recepción Conforme Incompleta",
}

# Reintentos
MAX_REINTENTOS_DETALLE = 3
MAX_REINTENTOS_LISTADO = 3
ESPERA_LISTADO = 2.0
ESPERA_DETALLE = 1.0
ESPERA_ENTRE_OC = 0.2


# =========================
# FUNCIONES BASE
# =========================

def crear_contexto_ssl():
    """Crea un contexto SSL sin validación de certificado (para evitar error SSL)."""
    return ssl._create_unverified_context()


def llamada_api(url, params):
    """
    Llama a la API con urllib y devuelve el JSON ya cargado
    o None si hay error.
    """
    ctx = crear_contexto_ssl()
    url_completa = url + "?" + urllib.parse.urlencode(params)
    print("      Consultando URL:", url_completa)

    try:
        with urllib.request.urlopen(url_completa, context=ctx) as resp:
            return json.load(resp)
    except Exception as e:
        print("      Error al conectarse a la API:", e)
        return None


def to_int_or_none(value):
    """Convierte montos/cantidades a entero sin decimales. Devuelve None si no se puede."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return None
        v = v.replace(".", "").replace(",", ".")
    else:
        v = value
    try:
        numero = float(v)
        return int(round(numero))
    except Exception:
        return None


def formatear_fecha_ddmmaaaa(fecha_str):
    """
    Intenta convertir una fecha que viene en formatos tipo:
    - '2025-12-15'
    - '2025-12-15T10:23:00'
    - '15/12/2025'
    y devolver 'dd/mm/aaaa'.
    Si no se puede, devuelve la cadena original.
    """
    if not fecha_str:
        return None

    txt = str(fecha_str).strip()
    formatos = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
    ]
    for fmt in formatos:
        try:
            d = dt.datetime.strptime(txt, fmt).date()
            return d.strftime("%d/%m/%Y")
        except Exception:
            continue
    # Si no se pudo parsear, devolvemos tal cual
    return txt


# =========================
# LISTADO BÁSICO POR FECHA
# =========================

def obtener_ocs_basicas_por_fecha(fecha: dt.date):
    """
    Usa ordenesdecompra.json?fecha=ddmmaaaa&CodigoOrganismo=...
    para obtener la lista básica de OCs del día.

    Devuelve:
      - lista (posiblemente vacía) si la API respondió bien
      - None si la API NO respondió después de reintentos
    """
    fecha_api = fecha.strftime("%d%m%Y")
    base_url = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
    params = {
        "fecha": fecha_api,
        "CodigoOrganismo": CODIGO_ORGANISMO,
        "ticket": TICKET,
    }

    for intento in range(1, MAX_REINTENTOS_LISTADO + 1):
        print(f"    [Listado] Intento {intento} de {MAX_REINTENTOS_LISTADO}...")
        data = llamada_api(base_url, params)
        if data is not None:
            listado = data.get("Listado", [])
            return listado
        time.sleep(ESPERA_LISTADO)

    print("    ⚠ No fue posible obtener el listado desde la API (se agotaron los intentos).")
    return None


# =========================
# DETALLE COMPLETO DE UNA OC
# =========================

def obtener_detalle_oc(codigo_oc: str):
    """
    Intenta primero con ordenesdecompra.json (que es el que te ha funcionado mejor).
    Si falla, usa OrdenCompra.json como respaldo.
    """
    params = {"codigo": codigo_oc, "ticket": TICKET}

    # 1) Intento principal: ordenesdecompra.json
    base_ocs = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
    data = llamada_api(base_ocs, params)
    if data and data.get("Listado"):
        return data["Listado"][0]

    # 2) Respaldo: OrdenCompra.json
    base_ordencompra = "https://api.mercadopublico.cl/servicios/v1/publico/OrdenCompra.json"
    data = llamada_api(base_ordencompra, params)
    if data and data.get("Listado"):
        return data["Listado"][0]

    return None


# =========================
# CONSTRUCCIÓN DE FILAS (OC + ÍTEMS)
# =========================

def construir_filas_items(oc: dict, fecha_consultada_str: str, es_farmacos: bool):
    """
    Construye filas con la estructura:

    - FechaConsulta
    - FechaCreacionOC
    - FechaEnvioOC
    - FechaEnvioProveedorOC
    - FechaAceptacionOC
    - CodigoOC
    - CodigoLicitacion
    - TipoOrdenCompra
    - EsFarmacos (SI/NO)
    - EstadoOC
    - NombreComprador
    - NombreUnidad
    - NombreOrganizacion
    - RutProveedor
    - NombreProveedor
    - EspecificacionComprador
    - Cantidad
    - ValorUnitario
    - TotalNetoItem
    - ImpuestosItem
    - TotalBrutoItem
    - TotalNetoOC
    - ImpuestosOC
    - TotalBrutoOC
    """
    filas = []

    comprador = oc.get("Comprador") or {}
    proveedor = oc.get("Proveedor") or {}
    items = oc.get("Items") or {}
    listado_items = items.get("Listado") if isinstance(items, dict) else None

    codigo_estado = str(oc.get("CodigoEstado") or "")
    estado_mapeado = ESTADOS_OC.get(codigo_estado, codigo_estado)

    # Bloque de fechas desde la API
    fechas = oc.get("Fechas") or {}

    raw_fecha_creacion = (
        fechas.get("FechaCreacion")
        or oc.get("FechaCreacion")
    )

    raw_fecha_envio = (
        fechas.get("FechaEnvio")
        or fechas.get("FechaEnvioOC")
        or oc.get("FechaEnvio")
    )

    raw_fecha_envio_proveedor = (
        fechas.get("FechaEnvioProveedor")
        or fechas.get("FechaEnvioProveedorOC")
        or oc.get("FechaEnvioProveedor")
        or raw_fecha_envio
    )

    raw_fecha_aceptacion = (
        fechas.get("FechaAceptacion")
        or oc.get("FechaAceptacion")
    )

    fecha_creacion_str = formatear_fecha_ddmmaaaa(raw_fecha_creacion)
    fecha_envio_str = formatear_fecha_ddmmaaaa(raw_fecha_envio)
    fecha_envio_prov_str = formatear_fecha_ddmmaaaa(raw_fecha_envio_proveedor)
    fecha_aceptacion_str = formatear_fecha_ddmmaaaa(raw_fecha_aceptacion)

    # Totales de la OC (cabecera)
    total_bruto_oc = to_int_or_none(oc.get("Total"))       # Total con impuestos
    total_neto_oc = to_int_or_none(oc.get("TotalNeto"))    # Total neto (si lo entrega)
    impuestos_oc = to_int_or_none(oc.get("Impuestos"))     # Impuestos totales de la OC

    tipo_oc = oc.get("Tipo")  # SE, CM, etc.

    if not listado_items:
        return filas

    valor_es_farmacos = "SI" if es_farmacos else "NO"

    # 1) Construimos filas con neto e impuestos como vengan de la API
    suma_neto = 0
    for it in listado_items:
        espec = it.get("EspecificacionComprador") or ""

        cantidad = to_int_or_none(it.get("Cantidad"))
        valor_unit = to_int_or_none(it.get("PrecioNeto"))
        impuestos_item_api = to_int_or_none(it.get("TotalImpuestos"))
        total_bruto_item_api = to_int_or_none(it.get("Total"))  # Total de la línea (si viene)

        if cantidad is not None and valor_unit is not None:
            total_neto_item = cantidad * valor_unit
        else:
            total_neto_item = None

        if total_neto_item is not None:
            suma_neto += total_neto_item

        fila = {
            "FechaConsulta": fecha_consultada_str,
            "FechaCreacionOC": fecha_creacion_str,
            "FechaEnvioOC": fecha_envio_str,
            "FechaEnvioProveedorOC": fecha_envio_prov_str,
            "FechaAceptacionOC": fecha_aceptacion_str,
            "CodigoOC": oc.get("Codigo"),
            "CodigoLicitacion": oc.get("CodigoLicitacion"),
            "TipoOrdenCompra": tipo_oc,
            "EsFarmacos": valor_es_farmacos,
            "EstadoOC": estado_mapeado,
            "NombreComprador": comprador.get("NombreContacto"),
            "NombreUnidad": comprador.get("NombreUnidad"),
            "NombreOrganizacion": comprador.get("NombreOrganismo"),
            "RutProveedor": proveedor.get("RutSucursal"),
            "NombreProveedor": proveedor.get("Nombre"),
            "EspecificacionComprador": espec,
            "Cantidad": cantidad,
            "ValorUnitario": valor_unit,
            "TotalNetoItem": total_neto_item,
            "ImpuestosItem": impuestos_item_api,
            "TotalBrutoItem": total_bruto_item_api,
            "TotalNetoOC": total_neto_oc,
            "ImpuestosOC": impuestos_oc,
            "TotalBrutoOC": total_bruto_oc,
        }

        filas.append(fila)

    # 2) Ajuste de impuestos por línea si solo vienen a nivel OC
    if impuestos_oc is not None and impuestos_oc > 0:
        todos_sin_impuesto = all(
            (fila.get("ImpuestosItem") is None or fila.get("ImpuestosItem") == 0)
            for fila in filas
        )
        if todos_sin_impuesto and suma_neto and suma_neto > 0:
            restante = impuestos_oc
            for fila in filas[:-1]:
                neto = fila.get("TotalNetoItem") or 0
                imp_calc = int(round(impuestos_oc * neto / suma_neto))
                fila["ImpuestosItem"] = imp_calc
                fila["TotalBrutoItem"] = (fila["TotalNetoItem"] or 0) + imp_calc
                restante -= imp_calc
            ultima = filas[-1]
            imp_ult = max(restante, 0)
            ultima["ImpuestosItem"] = imp_ult
            ultima["TotalBrutoItem"] = (ultima["TotalNetoItem"] or 0) + imp_ult
        else:
            for fila in filas:
                neto = fila.get("TotalNetoItem")
                imp = fila.get("ImpuestosItem")
                if neto is not None and imp is not None:
                    fila["TotalBrutoItem"] = neto + imp

    return filas


# =========================
# PROCESAR UN DÍA (UN ARCHIVO)
# =========================

def procesar_un_dia(fecha: dt.date, incluir_farmacos: bool):
    """
    Procesa un solo día:
      - Obtiene listado básico
      - Pide detalle de cada OC con reintentos
      - Genera:
          OC_HBSJO_YYYYMMDD_detalle.csv
          OC_HBSJO_YYYYMMDD_errores.csv (si corresponde)

      - Marca columna EsFarmacos = SI si el código comienza con 1063535.
      - Si incluir_farmacos = False, esas OCs se omiten.
    """
    print("\n=== Procesando día:", fecha.strftime("%d-%m-%Y"), "===")
    fecha_consultada_str = fecha.strftime("%d/%m/%Y")

    listado_basico = obtener_ocs_basicas_por_fecha(fecha)

    errores = []
    filas = []

    total_listado = 0
    total_farmacos = 0
    total_procesadas = 0

    if listado_basico is None:
        print("    ⚠ Error al obtener el listado de OCs (la API no respondió).")
        errores.append({
            "CodigoOC": f"LISTADO_{fecha.strftime('%Y%m%d')}",
            "Motivo": "Error en listado diario (API no respondió después de reintentos)"
        })
    else:
        total_listado = len(listado_basico)
        if not listado_basico:
            print("    No se encontraron OCs para este día (listado vacío).")
        else:
            print(f"    Se encontraron {total_listado} OCs básicas para este día.")

            for i, oc_b in enumerate(listado_basico, start=1):
                codigo = oc_b.get("Codigo")
                if not codigo:
                    continue

                es_farmacos = str(codigo).startswith("1063535")
                if es_farmacos:
                    total_farmacos += 1

                if es_farmacos and not incluir_farmacos:
                    print(f"    ({i}/{total_listado}) Código OC: {codigo} → OC de Fármacos, se excluye (según configuración).")
                    continue

                print(f"    ({i}/{total_listado}) Código OC: {codigo} (EsFarmacos={ 'SI' if es_farmacos else 'NO' })")

                detalle = None
                for intento in range(1, MAX_REINTENTOS_DETALLE + 1):
                    print(f"        [Detalle] Intento {intento} de {MAX_REINTENTOS_DETALLE}...")
                    detalle = obtener_detalle_oc(codigo)
                    if detalle:
                        break
                    time.sleep(ESPERA_DETALLE)

                if not detalle:
                    print(f"        ⚠ No se pudo obtener detalle para la OC {codigo} tras {MAX_REINTENTOS_DETALLE} intentos.")
                    errores.append({
                        "CodigoOC": codigo,
                        "Motivo": f"Error al obtener detalle (API sin respuesta tras {MAX_REINTENTOS_DETALLE} intentos)"
                    })
                    continue

                filas_oc = construir_filas_items(detalle, fecha_consultada_str, es_farmacos)
                if filas_oc:
                    filas.extend(filas_oc)
                    total_procesadas += 1

                time.sleep(ESPERA_ENTRE_OC)

    # Resumen del día
    print("    ---- Resumen del día ----")
    print(f"    Total OCs en listado: {total_listado}")
    print(f"    Total OCs de Fármacos (códigos 1063535): {total_farmacos}")
    print(f"    Total OCs finalmente procesadas (con detalle OK): {total_procesadas}")
    print("    -------------------------")

    # Guardar resultados del día
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    nombre_base_dia = fecha.strftime("%Y%m%d")

    columnas = [
        "FechaConsulta",
        "FechaCreacionOC",
        "FechaEnvioOC",
        "FechaEnvioProveedorOC",
        "FechaAceptacionOC",
        "CodigoOC",
        "CodigoLicitacion",
        "TipoOrdenCompra",
        "EsFarmacos",
        "EstadoOC",
        "NombreComprador",
        "NombreUnidad",
        "NombreOrganizacion",
        "RutProveedor",
        "NombreProveedor",
        "EspecificacionComprador",
        "Cantidad",
        "ValorUnitario",
        "TotalNetoItem",
        "ImpuestosItem",
        "TotalBrutoItem",
        "TotalNetoOC",
        "ImpuestosOC",
        "TotalBrutoOC",
    ]

    if filas:
        filas_ordenadas = sorted(
            filas,
            key=lambda f: (
                str(f.get("CodigoOC") or ""),
                str(f.get("EspecificacionComprador") or "")
            )
        )

        archivo_detalle = CARPETA_SALIDA / f"OC_HBSJO_{nombre_base_dia}_detalle.csv"

        with open(archivo_detalle, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columnas, delimiter=';')
            writer.writeheader()
            for fila in filas_ordenadas:
                fila_filtrada = {col: fila.get(col) for col in columnas}
                writer.writerow(fila_filtrada)

        print("    Archivo detalle generado:", archivo_detalle)
    else:
        print("    No se generó archivo de detalle para este día (no hubo filas).")

    if errores:
        archivo_errores = CARPETA_SALIDA / f"OC_HBSJO_{nombre_base_dia}_errores.csv"
        with open(archivo_errores, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["CodigoOC", "Motivo"], delimiter=';')
            writer.writeheader()
            writer.writerows(errores)

        print("    Archivo de errores generado:", archivo_errores)
    else:
        print("    No hubo errores para este día.")


# =========================
# PROCESAR PERÍODO (DÍA POR DÍA)
# =========================

def procesar_periodo(fecha_inicio: dt.date, fecha_fin: dt.date, incluir_farmacos: bool):
    """
    Recorre desde fecha_inicio hasta fecha_fin (ambas inclusive)
    y genera un archivo POR DÍA.
    """
    if fecha_inicio > fecha_fin:
        fecha_inicio, fecha_fin = fecha_fin, fecha_inicio

    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        procesar_un_dia(fecha_actual, incluir_farmacos)
        fecha_actual += dt.timedelta(days=1)


# =========================
# ENTRADA DE FECHA (MENÚ)
# =========================

def pedir_fecha_manual():
    texto = input("Ingresa la fecha en formato dd-mm-aaaa: ").strip()
    try:
        d, m, a = texto.split("-")
        return dt.date(int(a), int(m), int(d))
    except Exception:
        print("Formato inválido. Ejemplo: 11-12-2025")
        return None


def pedir_rango_fechas():
    print("Ingresa el rango de fechas:")
    ini = input("  Fecha INICIO (dd-mm-aaaa): ").strip()
    fin = input("  Fecha FIN    (dd-mm-aaaa): ").strip()
    try:
        di, mi, ai = ini.split("-")
        df, mf, af = fin.split("-")
        fecha_ini = dt.date(int(ai), int(mi), int(di))
        fecha_fin = dt.date(int(af), int(mf), int(df))
        return fecha_ini, fecha_fin
    except Exception:
        print("Formato inválido. Ejemplo: 01-01-2025 y 31-12-2025")
        return None, None


def pedir_incluir_farmacos():
    """
    Pregunta al usuario si desea incluir las OCs de Fármacos (códigos 1063535).
    Devuelve True si se deben incluir, False si se deben excluir.
    """
    while True:
        resp = input("¿Deseas incluir las OCs de Fármacos (códigos 1063535)? (S/N): ").strip().upper()
        if resp == "S":
            return True
        if resp == "N":
            return False
        print("Por favor responde 'S' o 'N'.")


if __name__ == "__main__":
    print("ÓRDENES DE COMPRA HBSJO - Exportador por día (archivos diarios)")
    print("Selecciona opción:")
    print("1) Solo un día: HOY")
    print("2) Solo un día: FECHA MANUAL (dd-mm-aaaa)")
    print("3) RANGO DE FECHAS (dd-mm-aaaa a dd-mm-aaaa)  [genera un archivo por cada día]")

    opcion = input("Opción: ").strip()
    hoy = dt.date.today()

    incluir_farmacos = pedir_incluir_farmacos()

    if opcion == "1":
        procesar_un_dia(hoy, incluir_farmacos)
    elif opcion == "2":
        fecha = pedir_fecha_manual()
        if fecha is None:
            sys.exit(0)
        procesar_un_dia(fecha, incluir_farmacos)
    elif opcion == "3":
        fecha_ini, fecha_fin = pedir_rango_fechas()
        if fecha_ini is None or fecha_fin is None:
            sys.exit(0)
        procesar_periodo(fecha_ini, fecha_fin, incluir_farmacos)
    else:
        print("Opción no válida.")
        sys.exit(0)
