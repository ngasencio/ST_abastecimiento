import urllib.request
import urllib.parse
import json
import datetime as dt
import pathlib
import csv
import ssl
import time
import os
import pandas as pd  # NUEVO: Importamos Pandas para manejo eficiente de datos

# =========================
# CONFIGURACIÓN FIJA SSO (LICITACIONES)
# =========================
CODIGO_ORGANISMO = "7296"
TICKET = "2798F2D3-0AC5-4323-9BB9-5E90618194BA"

# RUTAS
RUTA_API = pathlib.Path(__file__).parent.absolute()
CARPETA_BASE = RUTA_API / "LI_DSSO"
CARPETA_DIARIO = CARPETA_BASE / "DIARIO"      # Carpeta de descargas diarias
CARPETA_MAESTROS = CARPETA_BASE / "MAESTROS"  # Nueva carpeta para los consolidados

MAX_REINTENTOS = 5
ESPERA_ENTRE_INTENTOS = 4.0

# Aseguramos que existan las carpetas
CARPETA_DIARIO.mkdir(parents=True, exist_ok=True)
CARPETA_MAESTROS.mkdir(parents=True, exist_ok=True)

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
# PROCESAMIENTO DIARIO
# =========================

def procesar_dia(fecha_dt, modo_actualizar=False):
    """
    Descarga licitaciones de un día específico y guarda los CSV en DIARIO.
    Retorna True si encontró datos, False si no.
    """
    fecha_consulta = fecha_dt.strftime("%d/%m/%Y")
    f_str = fecha_dt.strftime("%Y%m%d")
    
    ruta_res = CARPETA_DIARIO / f"LICITACION_SSO_{f_str}_RESUMEN.csv"
    ruta_det = CARPETA_DIARIO / f"LICITACION_SSO_{f_str}_DETALLES.csv"

    if modo_actualizar:
        print(f"\n>>> ACTUALIZANDO: Verificando archivos del {fecha_consulta}...")
        if ruta_res.exists(): ruta_res.unlink()
        if ruta_det.exists(): ruta_det.unlink()

    print(f"\n>>> LICITACIONES SSO: {fecha_consulta}")
    
    params = {
        "fecha": fecha_dt.strftime("%d%m%Y"),
        "CodigoOrganismo": CODIGO_ORGANISMO,
        "ticket": TICKET
    }
    
    data_listado = llamada_api(params)
    
    if not data_listado or not data_listado.get("Listado"):
        print("    ⚠ Sin licitaciones publicadas/modificadas este día.")
        return False

    licitaciones_basicas = data_listado["Listado"]
    db_resumen = []
    db_detalles = []

    print(f"    Se encontraron {len(licitaciones_basicas)} licitaciones. Descargando detalles...")

    for i, item_b in enumerate(licitaciones_basicas, 1):
        codigo = item_b.get("CodigoExterno")
        print(f"    [{i}/{len(licitaciones_basicas)}] Procesando: {codigo}", end="\r")
        
        lic = obtener_detalle_licitacion(codigo)
        if not lic: continue

        comp = lic.get("Comprador") or {}
        fech = lic.get("Fechas") or {}
        
        # TABLA 1: RESUMEN
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
            "FechaCreacion": fech.get("FechaCreacion"),
            "FechaPublicacion": fech.get("FechaPublicacion"),
            "FechaCierre": fech.get("FechaCierre"),
            "FechaAdjudicacion": fech.get("FechaAdjudicacion"),
            "FechaEstimadaFirma": fech.get("FechaEstimadaFirma"),
            "FechaInicioContrato": fech.get("FechaInicio"),
            "C_Unidad": comp.get("NombreUnidad"),
            "C_RutUnidad": comp.get("RutUnidad"),
            "C_Usuario": comp.get("NombreUsuario"),
            "C_Cargo": comp.get("CargoUsuario"),
            "Resp_Contrato": lic.get("NombreResponsableContrato"),
            "Resp_Email": lic.get("EmailResponsableContrato"),
            "Resp_Pago": lic.get("NombreResponsablePago"),
            "TiempoDuracionContrato": lic.get("TiempoDuracionContrato"),
            "UnidadTiempoDuracion": lic.get("UnidadTiempoDuracionContrato"),
            "EsRenovable": lic.get("EsRenovable")
        })

        # TABLA 2: DETALLES
        obj_items = lic.get("Items") or {}
        items_list = obj_items.get("Listado") or []
        if not isinstance(items_list, list): items_list = []

        for it in items_list:
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
                "RutGanador": adj.get("RutProveedor", ""),
                "NombreGanador": adj.get("NombreProveedor", ""),
                "MontoUnitarioGanador": to_float(adj.get("MontoUnitario")),
                "CantidadAdjudicada": to_float(adj.get("Cantidad"))
            })
        time.sleep(0.2)

    if db_resumen:
        for nombre, data in {ruta_res: db_resumen, ruta_det: db_detalles}.items():
            with open(nombre, "w", newline="", encoding="utf-8-sig") as csvfile:
                if data:
                    w = csv.DictWriter(csvfile, fieldnames=data[0].keys(), delimiter=";")
                    w.writeheader()
                    w.writerows(data)
        print(f"\n✅ Guardado en DIARIO: {f_str}")
        return True
    return False

# =======================================================
# NUEVAS FUNCIONES: GESTIÓN DE BASES DE DATOS (MAESTROS)
# =======================================================

def unificar_base_datos():
    """
    Lee TODOS los CSVs de la carpeta DIARIO y reconstruye los Maestros desde cero.
    """
    print("\n🔄 UNIFICANDO BASE DE DATOS COMPLETA...")
    
    # 1. Identificar archivos
    all_resumen = list(CARPETA_DIARIO.glob("*_RESUMEN.csv"))
    all_detalle = list(CARPETA_DIARIO.glob("*_DETALLES.csv"))
    
    if not all_resumen:
        print("❌ No hay archivos en la carpeta DIARIO para unificar.")
        return

    # 2. Procesar Resumen
    print(f"   Leyendo {len(all_resumen)} archivos de Resumen...")
    df_list = []
    for f in all_resumen:
        try:
            # dtype=str para evitar errores de interpretación, parse_dates después si se desea
            df = pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str)
            df_list.append(df)
        except Exception as e:
            print(f"   ⚠ Error leyendo {f.name}: {e}")

    if df_list:
        df_maestro_res = pd.concat(df_list, ignore_index=True)
        # Deduplicar: Si una licitación aparece en varios días, nos quedamos con la última versión descargada
        # (Asumiendo que el orden de lectura o fecha archivo importa, pero aquí unificamos todo "a bruto")
        df_maestro_res.drop_duplicates(subset=["CodigoLicitacion"], keep="last", inplace=True)
        
        ruta_m_res = CARPETA_MAESTROS / "Maestro_Resumen.csv"
        df_maestro_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Resumen creado: {len(df_maestro_res)} registros.")

    # 3. Procesar Detalles
    print(f"   Leyendo {len(all_detalle)} archivos de Detalles...")
    df_list_det = []
    for f in all_detalle:
        try:
            df = pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str)
            df_list_det.append(df)
        except: pass

    if df_list_det:
        df_maestro_det = pd.concat(df_list_det, ignore_index=True)
        # Deduplicar detalles: Misma lógica, keep last
        df_maestro_det.drop_duplicates(subset=["CodigoLicitacion", "Correlativo"], keep="last", inplace=True)
        
        ruta_m_det = CARPETA_MAESTROS / "Maestro_Detalle.csv"
        df_maestro_det.to_csv(ruta_m_det, sep=";", index=False, encoding="utf-8-sig")
        print(f"   ✅ Maestro Detalle creado: {len(df_maestro_det)} registros.")

def refresh_base_datos(f_inicio, f_fin):
    """
    1. Descarga el rango de fechas.
    2. Carga los Maestros actuales.
    3. Realiza un 'Upsert' (Actualiza existentes, inserta nuevos).
    """
    print(f"\n🚀 INICIANDO REFRESH INTELIGENTE ({f_inicio} a {f_fin})")
    
    # --- PASO 1: DESCARGA DE NUEVOS DATOS ---
    d_actual = f_inicio
    archivos_nuevos_res = []
    archivos_nuevos_det = []
    
    while d_actual <= f_fin:
        hubo_datos = procesar_dia(d_actual, modo_actualizar=True)
        if hubo_datos:
            f_str = d_actual.strftime("%Y%m%d")
            archivos_nuevos_res.append(CARPETA_DIARIO / f"LICITACION_SSO_{f_str}_RESUMEN.csv")
            archivos_nuevos_det.append(CARPETA_DIARIO / f"LICITACION_SSO_{f_str}_DETALLES.csv")
        d_actual += dt.timedelta(days=1)
    
    if not archivos_nuevos_res:
        print("\n⚠ No se encontraron datos nuevos en el rango. Los Maestros no se tocaron.")
        return

    print("\n🔄 INTEGRANDO DATOS NUEVOS A LOS MAESTROS...")

    # --- PASO 2: CARGAR Y ACTUALIZAR RESUMEN ---
    ruta_m_res = CARPETA_MAESTROS / "Maestro_Resumen.csv"
    
    # Cargar Maestro Existente
    if ruta_m_res.exists():
        df_master = pd.read_csv(ruta_m_res, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master = pd.DataFrame()
        
    # Cargar Nuevos
    lista_dfs_nuevos = [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_res]
    df_nuevos = pd.concat(lista_dfs_nuevos, ignore_index=True)
    
    # Lógica UPSERT para Resumen:
    # Concatenamos Maestro + Nuevos. Al hacer drop_duplicates con keep='last', 
    # los registros nuevos (que están al final) sobrescriben a los viejos si el CodigoLicitacion se repite.
    df_total_res = pd.concat([df_master, df_nuevos], ignore_index=True)
    df_total_res.drop_duplicates(subset=["CodigoLicitacion"], keep="last", inplace=True)
    
    # Guardar
    df_total_res.to_csv(ruta_m_res, sep=";", index=False, encoding="utf-8-sig")
    print(f"   ✅ Maestro Resumen actualizado. Total registros: {len(df_total_res)}")

    # --- PASO 3: CARGAR Y ACTUALIZAR DETALLES ---
    ruta_m_det = CARPETA_MAESTROS / "Maestro_Detalle.csv"
    
    if ruta_m_det.exists():
        df_master_det = pd.read_csv(ruta_m_det, sep=";", encoding="utf-8-sig", dtype=str)
    else:
        df_master_det = pd.DataFrame()

    lista_dfs_nuevos_det = [pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str) for f in archivos_nuevos_det]
    df_nuevos_det = pd.concat(lista_dfs_nuevos_det, ignore_index=True)
    
    # Lógica UPSERT para Detalles (Más delicada):
    # Si una licitación se actualizó, sus items pueden haber cambiado (borrado o agregado).
    # Estrategia: Borrar del maestro TODOS los items de las licitaciones que vienen en el paquete nuevo,
    # y luego insertar los nuevos items limpios.
    
    codigos_actualizados = df_nuevos_det["CodigoLicitacion"].unique()
    
    # Filtramos el maestro: Dejamos solo lo que NO se está actualizando
    df_master_det_filtrado = df_master_det[~df_master_det["CodigoLicitacion"].isin(codigos_actualizados)]
    
    # Unimos
    df_total_det = pd.concat([df_master_det_filtrado, df_nuevos_det], ignore_index=True)
    
    # Guardar
    df_total_det.to_csv(ruta_m_det, sep=";", index=False, encoding="utf-8-sig")
    print(f"   ✅ Maestro Detalle actualizado. Total registros: {len(df_total_det)}")


if __name__ == "__main__":
    while True:
        print("\n=========================================")
        print("   GESTOR DE LICITACIONES SSO (7296)")
        print("   (Con Pandas & Maestros)")
        print("=========================================")
        print("1) Descargar HOY (Solo descarga)")
        print("2) Manual (Un día - Solo descarga)")
        print("3) Descargar Rango (Sin unificar)")
        print("4) Borrar y Re-Descargar Rango (Sin unificar)")
        print("-" * 30)
        print("5) UNIFICAR BASE DATOS (Reconstruye Maestros desde carpeta DIARIO)")
        print("6) REFRESH BASE DATOS (Descarga Rango + Actualiza Maestros)")
        print("0) Salir")
        
        op = input("\nSeleccione opción: ")
        
        try:
            if op == "0": break
            
            elif op == "1": 
                procesar_dia(dt.date.today())
            
            elif op == "2":
                f_in = input("Fecha (dd-mm-aaaa): ")
                procesar_dia(dt.datetime.strptime(f_in, "%d-%m-%Y").date())
            
            elif op == "3" or op == "4":
                es_actualizacion = (op == "4")
                if es_actualizacion: print("\n⚠ SE BORRARÁN LOS ARCHIVOS DIARIOS EN EL RANGO.")
                ini = input("Desde (dd-mm-aaaa): ")
                fin = input("Hasta (dd-mm-aaaa): ")
                d1 = dt.datetime.strptime(ini, "%d-%m-%Y").date()
                d2 = dt.datetime.strptime(fin, "%d-%m-%Y").date()
                while d1 <= d2:
                    procesar_dia(d1, modo_actualizar=es_actualizacion)
                    d1 += dt.timedelta(days=1)
            
            elif op == "5":
                unificar_base_datos()
                
            elif op == "6":
                ini = input("Desde (dd-mm-aaaa): ")
                fin = input("Hasta (dd-mm-aaaa): ")
                d1 = dt.datetime.strptime(ini, "%d-%m-%Y").date()
                d2 = dt.datetime.strptime(fin, "%d-%m-%Y").date()
                refresh_base_datos(d1, d2)

        except Exception as e: 
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()