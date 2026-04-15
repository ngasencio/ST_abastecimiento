import csv
import datetime as dt
import json
import pathlib
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# =========================
# CONFIGURACIÓN FIJA SSO (COMPRA ÁGIL)
# =========================
CODIGO_ORGANISMO = "7296"  # SSO
TICKET = "2798F2D3-0AC5-4323-9BB9-5E90618194BA"
REGION_LOS_LAGOS = 10
RUT_SSO = "616076000"

# Códigos de organismo del SSO en Compra Ágil (primer nivel del código)
CODIGOS_ORGANISMO_SSO = [
    "1057532",
    "1077241", 
    "1180747",
    "1057976",
    "1057922",
    "1057727"
]

# RUTAS
RUTA_API = pathlib.Path(__file__).parent.absolute()
CARPETA_BASE = RUTA_API / "CA_DSSO"
CARPETA_DIARIO = CARPETA_BASE / "DIARIO"
CARPETA_MAESTROS = CARPETA_BASE / "MAESTROS"

# Aseguramos que existan las carpetas
CARPETA_DIARIO.mkdir(parents=True, exist_ok=True)
CARPETA_MAESTROS.mkdir(parents=True, exist_ok=True)

# Configuración de rendimiento (SEGURO - SIN CONCURRENCIA)
MAX_REINTENTOS = 5
ESPERA_ENTRE_INTENTOS = 2.0
ESPERA_ENTRE_DETALLES = 0.8  # Pausa entre llamadas de detalle
ESPERA_ENTRE_PAGINAS = 0.5   # Pausa entre páginas de listado

URL_BASE_API = "https://api2.mercadopublico.cl"
URL_LISTADO = f"{URL_BASE_API}/v2/compra-agil"

# =========================
# CLASES DE CONFIGURACIÓN
# =========================

@dataclass(frozen=True)
class ApiConfig:
    """Configuración de acceso a API Compra Ágil v2."""
    ticket: str
    region: int
    max_reintentos: int = MAX_REINTENTOS
    espera_base: float = ESPERA_ENTRE_INTENTOS
    timeout: int = 30
    url_base: str = URL_BASE_API


class MercadoPublicoCompraAgilClient:
    """Cliente para la API de Compra Ágil v2 con backoff y manejo de errores."""

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._ctx = ssl._create_unverified_context()

    def get_json(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Realiza petición GET con reintentos y backoff."""
        if params:
            url_completa = url + "?" + urllib.parse.urlencode(params)
        else:
            url_completa = url
        
        # Añadir ticket al header
        headers = {"ticket": self.cfg.ticket}
        req = urllib.request.Request(url_completa, headers=headers)
        
        last_err: Optional[Exception] = None

        for intento in range(1, self.cfg.max_reintentos + 1):
            try:
                with urllib.request.urlopen(req, context=self._ctx, timeout=self.cfg.timeout) as resp:
                    data = json.load(resp)
                    
                    # Verificar respuesta exitosa
                    if data.get("success") == "NOK":
                        print(f"⚠️  API retornó error: {data.get('errors')}")
                        return None
                    
                    return data
                    
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Rate limit alcanzado
                    retry_after = int(e.headers.get('Retry-After', 60))
                    print(f"⚠️  Rate limit alcanzado. Esperando {retry_after} segundos...")
                    time.sleep(retry_after)
                    continue
                elif e.code == 401:
                    print(f"❌ Error de autenticación. Verifica el ticket.")
                    return None
                elif e.code == 404:
                    return None
                else:
                    last_err = e
                    time.sleep(self.cfg.espera_base * intento)
                    
            except Exception as e:
                last_err = e
                time.sleep(self.cfg.espera_base * intento)

        print(f"⚠️  API sin respuesta tras {self.cfg.max_reintentos} intentos: {last_err}")
        return None

    def obtener_listado_con_paginacion(self, params_base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Obtiene el listado completo de Compras Ágiles con paginación automática.
        Retorna lista de items (no detalles, solo el listado básico).
        """
        params = {**params_base, "region": self.cfg.region, "tamano_pagina": 50, "numero_pagina": 1}
        
        items_totales = []
        
        # Primera página
        print(f"   📄 Obteniendo página 1...")
        data = self.get_json(URL_LISTADO, params)
        
        if not data or not data.get("payload"):
            print("   ⚠️  No se pudo obtener primera página o no hay datos.")
            return []
        
        paginacion = data["payload"]["paginacion"]
        total_paginas = paginacion["total_paginas"]
        total_resultados = paginacion["total_resultados"]
        
        print(f"   📊 Total: {total_resultados} registros en {total_paginas} páginas")
        
        # Agregar items de primera página
        items_totales.extend(data["payload"]["items"])
        
        # Resto de páginas
        for num_pagina in range(2, total_paginas + 1):
            print(f"   📄 Obteniendo página {num_pagina}/{total_paginas}...")
            params["numero_pagina"] = num_pagina
            
            data = self.get_json(URL_LISTADO, params)
            if not data or not data.get("payload"):
                print(f"   ⚠️  Falló página {num_pagina}")
                continue
            
            items_totales.extend(data["payload"]["items"])
            time.sleep(ESPERA_ENTRE_PAGINAS)
        
        print(f"   ✅ Total items listado extraídos: {len(items_totales)}")
        return items_totales

    def obtener_detalle_compra_agil(self, codigo: str) -> Optional[Dict[str, Any]]:
        """Obtiene el detalle completo de una Compra Ágil específica."""
        url = f"{self.cfg.url_base}/v2/compra-agil/{codigo}"
        data = self.get_json(url)
        
        if data and data.get("payload"):
            return data["payload"]
        return None


# =========================
# FUNCIONES AUXILIARES
# =========================

def normalizar_rut(rut: str) -> str:
    """Normaliza RUT removiendo puntos, guiones y espacios."""
    if not rut:
        return ""
    return rut.replace(".", "").replace("-", "").replace(" ", "").upper()


def es_compra_agil_sso(codigo_compra_agil: str, rut_comprador: str) -> bool:
    """
    Valida si una Compra Ágil pertenece al SSO mediante doble validación.
    
    Validación 1: El código de organismo (primer nivel) debe estar en la lista del SSO
    Validación 2: El RUT del comprador debe ser el del SSO
    
    Args:
        codigo_compra_agil: Código de la Compra Ágil (ej: "1057532-942-COT25")
        rut_comprador: RUT del organismo comprador
    
    Returns:
        True si cumple AMBAS validaciones (código Y RUT), False en caso contrario
    """
    # Validación 1: Código de organismo
    try:
        primer_nivel = codigo_compra_agil.split("-")[0]
        codigo_valido = primer_nivel in CODIGOS_ORGANISMO_SSO
    except:
        codigo_valido = False
    
    # Validación 2: RUT
    rut_normalizado = normalizar_rut(rut_comprador)
    rut_sso_normalizado = normalizar_rut(RUT_SSO)
    rut_valido = rut_normalizado == rut_sso_normalizado
    
    # Debe cumplir AMBAS validaciones
    return codigo_valido and rut_valido


def limpiar(texto):
    """Limpia texto para CSV."""
    if texto is None:
        return ""
    return str(texto).replace("\n", " ").replace(";", ",").replace("\r", " ").strip()


def to_float(val):
    """Convierte valor a float de forma segura."""
    try:
        return float(val)
    except:
        return 0.0


def buscar_codigo_oc(id_oc: int, rut_proveedor: str, monto_total: float, fecha_cierre: dt.date) -> Optional[str]:
    """
    Busca el código alfanumérico de una OC (ej: 1057532-537-AG26) a partir del ID numérico.
    
    La API de Compra Ágil v2 solo retorna id_orden_compra (numérico), pero no codigo_orden_compra.
    Esta función usa la API v1 de Órdenes de Compra para encontrar el código cruzando:
    - Fecha de emisión (rango de 7 días después del cierre de CA)
    - RUT del proveedor
    - Monto total
    
    Args:
        id_oc: ID numérico de la OC (ej: 54628510)
        rut_proveedor: RUT del proveedor ganador (ej: "15.422.299-5")
        monto_total: Monto total de la cotización (ej: 211168)
        fecha_cierre: Fecha de cierre de la Compra Ágil
    
    Returns:
        Código de la OC (ej: "1057532-537-AG26") o None si no se encuentra
    """
    import urllib.request
    import urllib.parse
    import json
    
    # Normalizar RUT (eliminar puntos, guiones)
    rut_normalizado = normalizar_rut(rut_proveedor)
    
    # Buscar en un rango de 10 días después del cierre
    for dias in range(10):
        fecha_busqueda = fecha_cierre + dt.timedelta(days=dias)
        fecha_str = fecha_busqueda.strftime("%d/%m/%Y")
        
        # Construir URL para API v1 de OC
        params = {
            "fecha": fecha_str,
            "codigo_organismo": CODIGO_ORGANISMO  # 7296 (SSO)
        }
        
        url = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json?" + urllib.parse.urlencode(params)
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.load(resp)
                
                # Iterar sobre las OCs encontradas
                for oc in data.get("Listado", []):
                    rut_oc = normalizar_rut(oc.get("RutProveedor", ""))
                    monto_oc = to_float(oc.get("Total", 0))
                    
                    # Verificar coincidencia por RUT y monto (tolerancia de $1000)
                    if rut_oc == rut_normalizado and abs(monto_oc - monto_total) < 1000:
                        return oc.get("Codigo")
                        
        except Exception:
            # Si falla la búsqueda en esta fecha, continuar con la siguiente
            continue
    
    # No se encontró el código
    return None


def _write_csv_dicts(path: pathlib.Path, rows: List[Dict[str, Any]], delimiter: str = ";") -> None:
    """Escritura CSV consistente y rápida para lista de dicts."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as csvfile:
        w = csv.DictWriter(csvfile, fieldnames=rows[0].keys(), delimiter=delimiter)
        w.writeheader()
        w.writerows(rows)


def _extraer_tablas_normalizadas(detalle: Dict[str, Any], buscar_codigo_oc: bool = False) -> Tuple[
    Dict[str, Any],           # Resumen
    List[Dict[str, Any]],     # Productos Solicitados
    List[Dict[str, Any]],     # Proveedores
    List[Dict[str, Any]],     # Productos Cotizados
    List[Dict[str, Any]]      # Documentos
]:
    """
    Normaliza el JSON de detalle de Compra Ágil en 5 tablas relacionales.
    Extrae TODOS los campos disponibles en la API.
    
    Args:
        detalle: Diccionario con el detalle de la Compra Ágil
        buscar_codigo_oc: Si True, busca el código alfanumérico de OC en API v1 (más lento)
    """
    
    codigo = detalle.get("codigo", "")
    
    # ==================
    # TABLA 1: RESUMEN
    # ==================
    estado = detalle.get("estado", {})
    convocatoria = detalle.get("convocatoria", {})
    fechas = detalle.get("fechas", {})
    entrega = detalle.get("entrega", {})
    presupuesto = detalle.get("presupuesto", {})
    # IMPORTANTE: La API retorna id_orden_compra en la raíz, NO en un objeto "orden_compra"
    # Esto difiere de la documentación del PDF
    institucion = detalle.get("institucion", {})
    resumen_obj = detalle.get("resumen", {})
    motivos = detalle.get("motivos", {})
    flags = detalle.get("flags", {})
    
    resumen = {
        # Identificación básica
        "CodigoCompraAgil": codigo,
        "Nombre": limpiar(detalle.get("nombre")),
        "Descripcion": limpiar(detalle.get("descripcion")),
        
        # Estado
        "EstadoID": estado.get("id_estado"),
        "EstadoCodigo": estado.get("codigo"),
        "EstadoGlosa": estado.get("glosa"),
        
        # Convocatoria
        "ConvocatoriaEstado": convocatoria.get("estado_convocatoria"),
        "ConvocatoriaDescripcion": convocatoria.get("descripcion"),
        "FechaCierrePrimerLlamado": convocatoria.get("fecha_cierre_primer_llamado"),
        "FechaCierreSegundoLlamado": convocatoria.get("fecha_cierre_segundo_llamado"),
        
        # Fechas
        "FechaPublicacion": fechas.get("fecha_publicacion"),
        "FechaCierre": fechas.get("fecha_cierre"),
        "FechaUltimoCambio": fechas.get("fecha_ultimo_cambio"),
        "FechaCancelacion": fechas.get("fecha_cancelacion"),
        
        # Entrega
        "DireccionEntrega": limpiar(entrega.get("direccion_entrega")),
        "PlazoEntregaDias": entrega.get("plazo_entrega_dias"),
        
        # Presupuesto
        "TipoPresupuesto": presupuesto.get("tipo_presupuesto"),
        "Moneda": presupuesto.get("moneda"),
        "PresupuestoEstimado": presupuesto.get("presupuesto_estimado"),
        "MontoDisponible": presupuesto.get("monto_disponible"),
        "MontoDisponibleCLP": presupuesto.get("monto_disponible_clp"),
        "ValorCambioMoneda": presupuesto.get("valor_cambio_moneda"),
        "FechaCambioMoneda": presupuesto.get("fecha_cambio_moneda"),
        
        # Orden de Compra (la API retorna estos campos en la raíz, no en un objeto)
        # IMPORTANTE: El estado "oc_emitida" NO se usa en la práctica por la API.
        # Las OCs emitidas mantienen estado "proveedor_seleccionado" pero con id_orden_compra lleno.
        # Para detectar OCs emitidas: verificar si id_orden_compra is not None
        "OC_ID": detalle.get("id_orden_compra"),
        "OC_Codigo": None,  # Se llenará después si buscar_codigo_oc=True
        # Nota: codigo_orden_compra y estado_orden_compra NO existen en la respuesta real
        
        # Institución
        "OrganismoComprador": limpiar(institucion.get("organismo_comprador")),
        "RutComprador": institucion.get("rut"),
        "UnidadCompra": limpiar(institucion.get("unidad_compra")),
        "Region": institucion.get("region"),
        "NombreRegion": institucion.get("nombre_region"),
        
        # Resumen
        "MultaSancion": resumen_obj.get("multa_sancion"),
        "TotalOfertasRecibidas": resumen_obj.get("total_ofertas_recibidas"),
        "TotalDemandas": resumen_obj.get("total_demandas"),
        
        # Motivos
        "MotivoCancelacion": limpiar(motivos.get("motivo_cancelacion")),
        "MotivoDesierta": limpiar(motivos.get("motivo_desierta")),
        "MotivoSeleccion": limpiar(motivos.get("motivo_seleccion")),
        
        # Flags
        "RequisitosMedioambientales": flags.get("considera_requisitos_medioambientales"),
        "RequisitosImpactoSocial": flags.get("considera_requisitos_impacto_social_economico"),
        
        # Contadores
        "TotalDocumentos": len(detalle.get("documentos", [])),
        "TotalProductosSolicitados": len(detalle.get("productos_solicitados", [])),
        "TotalProveedoresCotizando": len(detalle.get("proveedores_cotizando", []))
    }
    
    # ==================
    # TABLA 2: PRODUCTOS SOLICITADOS
    # ==================
    productos_solicitados = []
    for prod in detalle.get("productos_solicitados", []):
        productos_solicitados.append({
            "CodigoCompraAgil": codigo,
            "CodigoProducto": prod.get("codigo_producto"),
            "Nombre": limpiar(prod.get("nombre")),
            "Descripcion": limpiar(prod.get("descripcion")),
            "Cantidad": prod.get("cantidad"),
            "UnidadMedida": prod.get("unidad_medida")
        })
    
    # ==================
    # TABLA 3: PROVEEDORES
    # ==================
    proveedores = []
    for prov in detalle.get("proveedores_cotizando", []):
        # La API retorna campos adicionales no documentados
        # estado_cotizacion viene como int, no como objeto
        fechas_prov = prov.get("fechas", {})
        
        proveedores.append({
            "CodigoCompraAgil": codigo,
            "RutProveedor": prov.get("rut_proveedor"),
            "RazonSocial": limpiar(prov.get("razon_social")),
            "EsEMT": prov.get("es_emt"),
            
            # Estado cotización (viene como int en la API real, no como objeto)
            "EstadoCotizacionID": prov.get("estado"),
            "JustificacionInadmisibilidad": limpiar(prov.get("justificacion_inadmisibilidad")),
            
            # Selección
            "ProveedorSeleccionado": prov.get("proveedor_seleccionado"),
            "EstadoPorComprador": prov.get("estado_por_comprador"),
            
            # OC vinculada al proveedor (campo adicional encontrado)
            "IDOrdenCompra": prov.get("id_oc"),
            
            # Fechas
            "FechaCreacion": prov.get("fecha_creacion"),
            "FechaVigencia": prov.get("fecha_vigencia"),
            
            # Montos
            "ValorNeto": prov.get("valor_neto"),
            "TotalImpuesto": prov.get("total_impuesto"),
            "MontoDespacho": prov.get("monto_despacho"),
            "MontoTotal": prov.get("monto_total"),
            "NombreImpuesto": prov.get("nombre_impuesto"),
            "PorcentajeImpuesto": prov.get("porcentaje_impuesto"),
            
            # Descripciones
            "DescripcionCotizacion": limpiar(prov.get("descripcion_cotizacion")),
            "Descripcion": limpiar(prov.get("descripcion")),
            
            # Campos adicionales encontrados en la API
            "IDCotizacion": prov.get("id_cotizacion"),
            "CodigoSucursalEmpresa": prov.get("codigo_sucursal_empresa"),
            "CodigoEmpresa": prov.get("codigo_empresa"),
            "Activo": prov.get("activo"),
            
            # Contador
            "TotalProductosCotizados": len(prov.get("productos_cotizados", []))
        })
    
    # ==================
    # TABLA 4: PRODUCTOS COTIZADOS
    # ==================
    productos_cotizados = []
    for prov in detalle.get("proveedores_cotizando", []):
        rut_proveedor = prov.get("rut_proveedor")
        
        for prod_cot in prov.get("productos_cotizados", []):
            productos_cotizados.append({
                "CodigoCompraAgil": codigo,
                "RutProveedor": rut_proveedor,
                "CodigoProducto": prod_cot.get("codigo_producto"),
                "NombreProducto": limpiar(prod_cot.get("nombre_producto")),
                "Descripcion": limpiar(prod_cot.get("descripcion")),
                "Cantidad": prod_cot.get("cantidad"),
                "PrecioUnitario": prod_cot.get("precio_unitario"),
                "MontoTotalProducto": prod_cot.get("monto_total_producto")
            })
    
    # ==================
    # TABLA 5: DOCUMENTOS
    # ==================
    documentos = []
    for doc in detalle.get("documentos", []):
        documentos.append({
            "CodigoCompraAgil": codigo,
            "IDDocumento": doc.get("id"),
            "NombreDocumento": limpiar(doc.get("nombre"))
        })
    
    return resumen, productos_solicitados, proveedores, productos_cotizados, documentos


def procesar_dia(
    fecha_dt: dt.date,
    modo_actualizar: bool = False,
    ticket: str = TICKET,
    region: int = REGION_LOS_LAGOS
) -> bool:
    """
    Descarga Compras Ágiles del SSO para una fecha específica (según fecha_ultimo_cambio).
    
    FILTRO DOBLE (máxima seguridad):
    1. Pre-filtro por código de organismo (6 códigos SSO) - NO descarga detalles innecesarios
    2. Validación por RUT del SSO - Confirma que es SSO
    
    Solo se guardan registros que cumplen AMBAS validaciones.
    
    Genera 5 archivos CSV en CARPETA_DIARIO:
    - COMPRA_AGIL_SSO_YYYYMMDD_RESUMEN.csv
    - COMPRA_AGIL_SSO_YYYYMMDD_PRODUCTOS.csv
    - COMPRA_AGIL_SSO_YYYYMMDD_PROVEEDORES.csv
    - COMPRA_AGIL_SSO_YYYYMMDD_PRODUCTOS_COTIZADOS.csv
    - COMPRA_AGIL_SSO_YYYYMMDD_DOCUMENTOS.csv
    
    Args:
        fecha_dt: Fecha a procesar
        modo_actualizar: Si True, sobrescribe archivos existentes
        ticket: Ticket de API
        region: Código de región (10 = Los Lagos)
    
    Returns:
        True si se encontraron y procesaron datos del SSO
    """
    fecha_str = fecha_dt.strftime("%Y%m%d")
    
    # Archivos de salida
    arch_resumen = CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{fecha_str}_RESUMEN.csv"
    arch_productos = CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{fecha_str}_PRODUCTOS.csv"
    arch_proveedores = CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{fecha_str}_PROVEEDORES.csv"
    arch_prod_cotizados = CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{fecha_str}_PRODUCTOS_COTIZADOS.csv"
    arch_documentos = CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{fecha_str}_DOCUMENTOS.csv"
    
    # Verificar si ya existe
    if not modo_actualizar and arch_resumen.exists():
        print(f"   ⚠️  {fecha_str} ya descargado. Use opción 6 para actualizar.")
        return False
    
    print(f"\n{'='*60}")
    print(f"📅 PROCESANDO: {fecha_dt.strftime('%d-%m-%Y')}")
    print(f"🏥 ORGANISMO: Servicio de Salud Osorno")
    print(f"🔐 VALIDACIÓN DOBLE:")
    print(f"   1️⃣ Código organismo: {', '.join(CODIGOS_ORGANISMO_SSO)}")
    print(f"   2️⃣ RUT: {RUT_SSO}")
    print(f"{'='*60}")
    
    # Cliente API
    cfg = ApiConfig(ticket=ticket, region=region)
    client = MercadoPublicoCompraAgilClient(cfg)
    
    # PASO 1: Obtener listado del día (filtrar por fecha_ultimo_cambio)
    fecha_inicio = dt.datetime.combine(fecha_dt, dt.time.min).replace(tzinfo=dt.timezone.utc)
    fecha_fin = dt.datetime.combine(fecha_dt, dt.time.max).replace(tzinfo=dt.timezone.utc)
    
    params_base = {
        "cambio_desde": fecha_inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cambio_hasta": fecha_fin.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ordenar_por": "FechaUltimaModificacion"
    }
    
    print("\n🔍 PASO 1: Obteniendo listado del día (Región Los Lagos)...")
    items = client.obtener_listado_con_paginacion(params_base)
    
    if not items:
        print(f"   ℹ️  No hay Compras Ágiles con cambios en {fecha_dt.strftime('%d-%m-%Y')}")
        return False
    
    codigos = [item["codigo"] for item in items]
    print(f"   ✅ Encontrados {len(codigos)} códigos en Región 10")
    
    # PASO 2: Obtener detalles y filtrar por código SSO + RUT
    print(f"\n📦 PASO 2: Descargando detalles y filtrando por SSO...")
    print(f"   🔍 Validación doble: Código de organismo + RUT")
    
    detalles_sso = []
    descartados_codigo = 0
    descartados_rut = 0
    
    for i, codigo in enumerate(codigos, 1):
        # Pre-filtro rápido por código (antes de descargar detalle)
        primer_nivel = codigo.split("-")[0]
        
        if primer_nivel not in CODIGOS_ORGANISMO_SSO:
            # Descartado por código - ni siquiera descargamos el detalle
            descartados_codigo += 1
            print(f"   [{i}/{len(codigos)}] {codigo}... ⊗ Código organismo ({primer_nivel})")
            continue
        
        # Si pasa el filtro de código, descargamos el detalle
        print(f"   [{i}/{len(codigos)}] {codigo}...", end=" ", flush=True)
        
        detalle = client.obtener_detalle_compra_agil(codigo)
        
        if detalle:
            # Validación final por RUT
            rut_comprador = normalizar_rut(detalle.get("institucion", {}).get("rut", ""))
            rut_sso_norm = normalizar_rut(RUT_SSO)
            
            if rut_comprador == rut_sso_norm:
                detalles_sso.append(detalle)
                print("✅ SSO (Código + RUT)")
            else:
                descartados_rut += 1
                organismo = detalle.get("institucion", {}).get("organismo_comprador", "Otro")
                print(f"⊗ RUT no coincide ({organismo[:25]})")
        else:
            print("❌ Error")
        
        time.sleep(ESPERA_ENTRE_DETALLES)
    
    # Reporte de filtrado mejorado
    total_descartados = descartados_codigo + descartados_rut
    print(f"\n   📊 RESULTADO DEL FILTRADO:")
    print(f"   ✅ SSO (ambas validaciones): {len(detalles_sso)} registros")
    print(f"   ⊗ Descartados por código organismo: {descartados_codigo} registros")
    print(f"   ⊗ Descartados por RUT: {descartados_rut} registros")
    print(f"   📉 Total descartados: {total_descartados} registros")
    print(f"   ⚡ Eficiencia: {descartados_codigo} detalles NO descargados (ahorro de tiempo)")
    
    if not detalles_sso:
        print(f"   ℹ️  No se encontraron Compras Ágiles del SSO en {fecha_dt.strftime('%d-%m-%Y')}")
        return False
    
    # PASO 3: Normalizar en 5 tablas
    print(f"\n🔄 PASO 3: Normalizando {len(detalles_sso)} registros del SSO...")
    
    todos_resumenes = []
    todos_productos = []
    todos_proveedores = []
    todos_prod_cotizados = []
    todos_documentos = []
    
    for detalle in detalles_sso:
        resumen, productos, proveedores, prod_cotizados, documentos = _extraer_tablas_normalizadas(detalle)
        
        todos_resumenes.append(resumen)
        todos_productos.extend(productos)
        todos_proveedores.extend(proveedores)
        todos_prod_cotizados.extend(prod_cotizados)
        todos_documentos.extend(documentos)
    
    # PASO 3.5: Buscar códigos de OC (OPCIONAL - comentar para ahorrar tiempo)
    # Esta búsqueda es lenta porque usa la API v1 de OC
    # Descomentar solo si necesitas los códigos alfanuméricos de OC
    """
    print(f"\n🔍 PASO 3.5: Buscando códigos de OC (puede tomar varios minutos)...")
    for i, resumen in enumerate(todos_resumenes):
        if resumen["OC_ID"]:
            # Buscar proveedor ganador para obtener RUT y monto
            provs = [p for p in todos_proveedores if p["CodigoCompraAgil"] == resumen["CodigoCompraAgil"] and p["ProveedorSeleccionado"]]
            if provs:
                prov_ganador = provs[0]
                codigo_oc = buscar_codigo_oc(
                    id_oc=int(resumen["OC_ID"]),
                    rut_proveedor=prov_ganador["RutProveedor"],
                    monto_total=to_float(prov_ganador["MontoTotal"]),
                    fecha_cierre=dt.datetime.strptime(resumen["FechaCierre"], "%Y-%m-%d %H:%M").date()
                )
                if codigo_oc:
                    todos_resumenes[i]["OC_Codigo"] = codigo_oc
                    print(f"   ✅ {resumen['CodigoCompraAgil']}: OC {codigo_oc}")
                else:
                    print(f"   ⊗ {resumen['CodigoCompraAgil']}: OC no encontrada")
    """
    
    # PASO 4: Escribir CSVs
    print(f"\n💾 PASO 4: Guardando CSVs...")
    
    _write_csv_dicts(arch_resumen, todos_resumenes)
    print(f"   ✅ {arch_resumen.name}: {len(todos_resumenes)} registros")
    
    if todos_productos:
        _write_csv_dicts(arch_productos, todos_productos)
        print(f"   ✅ {arch_productos.name}: {len(todos_productos)} registros")
    
    if todos_proveedores:
        _write_csv_dicts(arch_proveedores, todos_proveedores)
        print(f"   ✅ {arch_proveedores.name}: {len(todos_proveedores)} registros")
    
    if todos_prod_cotizados:
        _write_csv_dicts(arch_prod_cotizados, todos_prod_cotizados)
        print(f"   ✅ {arch_prod_cotizados.name}: {len(todos_prod_cotizados)} registros")
    
    if todos_documentos:
        _write_csv_dicts(arch_documentos, todos_documentos)
        print(f"   ✅ {arch_documentos.name}: {len(todos_documentos)} registros")
    
    print(f"\n✨ DÍA {fecha_str} COMPLETADO EXITOSAMENTE.\n")
    return True


def unificar_base_datos():
    """
    Lee todos los archivos de CARPETA_DIARIO y crea Maestros consolidados 
    en CARPETA_MAESTROS (sobrescribe si existen).
    """
    print("\n" + "="*60)
    print("🔄 UNIFICANDO BASE DE DATOS (DIARIO → MAESTROS)")
    print("="*60)
    
    archivos_diario = sorted(CARPETA_DIARIO.glob("COMPRA_AGIL_SSO_*_RESUMEN.csv"))
    
    if not archivos_diario:
        print("\n   ⚠️  No se encontraron archivos en DIARIO. Ejecute primero las opciones 1-3.")
        return
    
    print(f"\n   📂 Encontrados {len(archivos_diario)} días de datos en DIARIO")
    
    # --- RESUMEN ---
    print("\n   🔄 Consolidando RESUMEN...")
    df_resumen_completo = pd.concat(
        [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_diario],
        ignore_index=True
    )
    df_resumen_completo.drop_duplicates(subset=["CodigoCompraAgil"], keep="last", inplace=True)
    
    ruta_m_resumen = CARPETA_MAESTROS / "Maestro_Resumen.csv"
    df_resumen_completo.to_csv(ruta_m_resumen, sep=";", index=False, encoding="utf-8-sig")
    print(f"   ✅ {ruta_m_resumen.name}: {len(df_resumen_completo)} registros")
    
    # --- PRODUCTOS ---
    archivos_productos = sorted(CARPETA_DIARIO.glob("COMPRA_AGIL_SSO_*_PRODUCTOS.csv"))
    if archivos_productos:
        print("   🔄 Consolidando PRODUCTOS...")
        df_productos = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_productos],
            ignore_index=True
        )
        df_productos.drop_duplicates(subset=["CodigoCompraAgil", "CodigoProducto"], keep="last", inplace=True)
        
        ruta_m_productos = CARPETA_MAESTROS / "Maestro_Productos.csv"
        df_productos.to_csv(ruta_m_productos, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ {ruta_m_productos.name}: {len(df_productos)} registros")
    
    # --- PROVEEDORES ---
    archivos_proveedores = sorted(CARPETA_DIARIO.glob("COMPRA_AGIL_SSO_*_PROVEEDORES.csv"))
    if archivos_proveedores:
        print("   🔄 Consolidando PROVEEDORES...")
        df_proveedores = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_proveedores],
            ignore_index=True
        )
        df_proveedores.drop_duplicates(subset=["CodigoCompraAgil", "RutProveedor"], keep="last", inplace=True)
        
        ruta_m_proveedores = CARPETA_MAESTROS / "Maestro_Proveedores.csv"
        df_proveedores.to_csv(ruta_m_proveedores, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ {ruta_m_proveedores.name}: {len(df_proveedores)} registros")
    
    # --- PRODUCTOS COTIZADOS ---
    archivos_prod_cot = sorted(CARPETA_DIARIO.glob("COMPRA_AGIL_SSO_*_PRODUCTOS_COTIZADOS.csv"))
    if archivos_prod_cot:
        print("   🔄 Consolidando PRODUCTOS COTIZADOS...")
        df_prod_cot = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_prod_cot],
            ignore_index=True
        )
        df_prod_cot.drop_duplicates(
            subset=["CodigoCompraAgil", "RutProveedor", "CodigoProducto"],
            keep="last",
            inplace=True
        )
        
        ruta_m_prod_cot = CARPETA_MAESTROS / "Maestro_Productos_Cotizados.csv"
        df_prod_cot.to_csv(ruta_m_prod_cot, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ {ruta_m_prod_cot.name}: {len(df_prod_cot)} registros")
    
    # --- DOCUMENTOS ---
    archivos_docs = sorted(CARPETA_DIARIO.glob("COMPRA_AGIL_SSO_*_DOCUMENTOS.csv"))
    if archivos_docs:
        print("   🔄 Consolidando DOCUMENTOS...")
        df_docs = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_docs],
            ignore_index=True
        )
        df_docs.drop_duplicates(subset=["CodigoCompraAgil", "IDDocumento"], keep="last", inplace=True)
        
        ruta_m_docs = CARPETA_MAESTROS / "Maestro_Documentos.csv"
        df_docs.to_csv(ruta_m_docs, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ {ruta_m_docs.name}: {len(df_docs)} registros")
    
    print("\n✨ UNIFICACIÓN COMPLETADA EXITOSAMENTE.")


def refresh_base_datos(f_ini: dt.date, f_fin: dt.date):
    """
    Descarga rango, lee Maestros, actualiza (Upsert) y guarda.
    
    Proceso:
    1. Descarga días del rango a DIARIO (filtrados por SSO)
    2. Lee Maestros existentes
    3. Actualiza con los nuevos datos (Upsert)
    4. Guarda Maestros actualizados
    """
    print(f"\n{'='*60}")
    print(f"🚀 REFRESH DE BASE DE DATOS ({f_ini.strftime('%d-%m-%Y')} al {f_fin.strftime('%d-%m-%Y')})")
    print(f"🏥 Solo SSO - Validación doble (Código + RUT)")
    print(f"{'='*60}")
    
    # PASO 1: Descarga a DIARIO
    d_actual = f_ini
    dias_descargados = []
    
    while d_actual <= f_fin:
        hubo_datos = procesar_dia(d_actual, modo_actualizar=True)
        if hubo_datos:
            dias_descargados.append(d_actual)
        d_actual += dt.timedelta(days=1)
    
    if not dias_descargados:
        print("\n⚠️  No se encontraron nuevos datos del SSO en el rango seleccionado.")
        return
    
    print(f"\n🔄 INTEGRANDO NUEVOS DATOS A LOS MAESTROS (UPSERT)...")
    
    # PASO 2: Actualizar cada tabla
    
    # --- RESUMEN ---
    ruta_m_resumen = CARPETA_MAESTROS / "Maestro_Resumen.csv"
    if ruta_m_resumen.exists():
        df_master_res = pd.read_csv(ruta_m_resumen, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_res = pd.DataFrame()
    
    archivos_nuevos_res = [
        CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{d.strftime('%Y%m%d')}_RESUMEN.csv"
        for d in dias_descargados
    ]
    
    # Filtrar solo archivos que existen
    archivos_existentes = [f for f in archivos_nuevos_res if f.exists()]
    
    if not archivos_existentes:
        print("\n⚠️  No se encontraron archivos nuevos de RESUMEN para integrar.")
        return
    
    df_nuevos_res = pd.concat(
        [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_existentes],
        ignore_index=True
    )
    
    if not df_nuevos_res.empty:
        df_final_res = pd.concat([df_master_res, df_nuevos_res])
        df_final_res.drop_duplicates(subset=["CodigoCompraAgil"], keep="last", inplace=True)
        df_final_res.to_csv(ruta_m_resumen, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Resumen: {len(df_final_res)} registros")
    
    # --- PRODUCTOS ---
    ruta_m_productos = CARPETA_MAESTROS / "Maestro_Productos.csv"
    if ruta_m_productos.exists():
        df_master_prod = pd.read_csv(ruta_m_productos, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_prod = pd.DataFrame()
    
    archivos_nuevos_prod = [
        CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{d.strftime('%Y%m%d')}_PRODUCTOS.csv"
        for d in dias_descargados
    ]
    archivos_nuevos_prod = [f for f in archivos_nuevos_prod if f.exists()]
    
    if archivos_nuevos_prod:
        df_nuevos_prod = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_prod],
            ignore_index=True
        )
        
        # Borrar productos de CAs actualizadas (solo si hay datos nuevos)
        if not df_nuevos_prod.empty and not df_nuevos_res.empty:
            cas_actualizadas = df_nuevos_res["CodigoCompraAgil"].unique()
            if not df_master_prod.empty:
                df_master_prod = df_master_prod[~df_master_prod["CodigoCompraAgil"].isin(cas_actualizadas)]
        
        df_final_prod = pd.concat([df_master_prod, df_nuevos_prod])
        df_final_prod.to_csv(ruta_m_productos, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Productos: {len(df_final_prod)} registros")
    
    # --- PROVEEDORES ---
    ruta_m_prov = CARPETA_MAESTROS / "Maestro_Proveedores.csv"
    if ruta_m_prov.exists():
        df_master_prov = pd.read_csv(ruta_m_prov, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_prov = pd.DataFrame()
    
    archivos_nuevos_prov = [
        CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{d.strftime('%Y%m%d')}_PROVEEDORES.csv"
        for d in dias_descargados
    ]
    archivos_nuevos_prov = [f for f in archivos_nuevos_prov if f.exists()]
    
    if archivos_nuevos_prov:
        df_nuevos_prov = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_prov],
            ignore_index=True
        )
        
        # Borrar proveedores de CAs actualizadas (solo si hay datos nuevos)
        if not df_nuevos_prov.empty and not df_nuevos_res.empty:
            cas_actualizadas = df_nuevos_res["CodigoCompraAgil"].unique()
            if not df_master_prov.empty:
                df_master_prov = df_master_prov[~df_master_prov["CodigoCompraAgil"].isin(cas_actualizadas)]
        
        df_final_prov = pd.concat([df_master_prov, df_nuevos_prov])
        df_final_prov.to_csv(ruta_m_prov, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Proveedores: {len(df_final_prov)} registros")
    
    # --- PRODUCTOS COTIZADOS ---
    ruta_m_prod_cot = CARPETA_MAESTROS / "Maestro_Productos_Cotizados.csv"
    if ruta_m_prod_cot.exists():
        df_master_pc = pd.read_csv(ruta_m_prod_cot, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_pc = pd.DataFrame()
    
    archivos_nuevos_pc = [
        CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{d.strftime('%Y%m%d')}_PRODUCTOS_COTIZADOS.csv"
        for d in dias_descargados
    ]
    archivos_nuevos_pc = [f for f in archivos_nuevos_pc if f.exists()]
    
    if archivos_nuevos_pc:
        df_nuevos_pc = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_pc],
            ignore_index=True
        )
        
        # Borrar productos cotizados de CAs actualizadas (solo si hay datos nuevos)
        if not df_nuevos_pc.empty and not df_nuevos_res.empty:
            cas_actualizadas = df_nuevos_res["CodigoCompraAgil"].unique()
            if not df_master_pc.empty:
                df_master_pc = df_master_pc[~df_master_pc["CodigoCompraAgil"].isin(cas_actualizadas)]
        
        df_final_pc = pd.concat([df_master_pc, df_nuevos_pc])
        df_final_pc.to_csv(ruta_m_prod_cot, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Productos Cotizados: {len(df_final_pc)} registros")
    
    # --- DOCUMENTOS ---
    ruta_m_docs = CARPETA_MAESTROS / "Maestro_Documentos.csv"
    if ruta_m_docs.exists():
        df_master_docs = pd.read_csv(ruta_m_docs, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_docs = pd.DataFrame()
    
    archivos_nuevos_docs = [
        CARPETA_DIARIO / f"COMPRA_AGIL_SSO_{d.strftime('%Y%m%d')}_DOCUMENTOS.csv"
        for d in dias_descargados
    ]
    archivos_nuevos_docs = [f for f in archivos_nuevos_docs if f.exists()]
    
    if archivos_nuevos_docs:
        df_nuevos_docs = pd.concat(
            [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_docs],
            ignore_index=True
        )
        
        # Borrar documentos de CAs actualizadas (solo si hay datos nuevos)
        if not df_nuevos_docs.empty and not df_nuevos_res.empty:
            cas_actualizadas = df_nuevos_res["CodigoCompraAgil"].unique()
            if not df_master_docs.empty:
                df_master_docs = df_master_docs[~df_master_docs["CodigoCompraAgil"].isin(cas_actualizadas)]
        
        df_final_docs = pd.concat([df_master_docs, df_nuevos_docs])
        df_final_docs.to_csv(ruta_m_docs, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Documentos: {len(df_final_docs)} registros")
    
    print("\n✨ PROCESO DE REFRESH COMPLETADO EXITOSAMENTE.")


# =========================
# MENÚ PRINCIPAL
# =========================

if __name__ == "__main__":
    while True:
        # Obtener fecha actual en formato dd-mm-yyyy
        fecha_hoy = dt.date.today().strftime("%d-%m-%Y")
        
        print("\n" + "="*60)
        print("   EXTRACTOR COMPRA ÁGIL SSO - V1")
        print("   (Región Los Lagos - Solo SSO)")
        print("="*60)
        print(f"1) Hoy ({fecha_hoy})")
        print("2) Manual (Un día a DIARIO)")
        print("3) Rango de fechas (Solo descarga lo nuevo a DIARIO)")
        print("-" * 60)
        print("5) UNIFICAR BASE DATOS (Crea Maestros desde DIARIO)")
        print("6) REFRESH BASE DATOS (Descarga Rango + Actualiza Maestros)")
        print("0) Salir")
        
        op = input("\nSeleccione opción: ")
        
        try:
            if op == "0":
                print("\n👋 Saliendo del programa...")
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
                
                if d1 > d2:
                    print("\n⚠️  Error: La fecha inicial no puede ser posterior a la fecha final.")
                    continue
                
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
                
                if d_ini > d_fin:
                    print("\n⚠️  Error: La fecha inicial no puede ser posterior a la fecha final.")
                    continue
                
                refresh_base_datos(d_ini, d_fin)
            
            else:
                print("\n⚠️  Opción inválida.")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()