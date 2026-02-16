import time
import csv
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
ARCHIVO_PROVEEDORES = "base_proveedores_contactos_v2.csv"
TIMEOUT_GENERAL = 20  # Aumentado a 20 segundos
TIMEOUT_TABLA = 30    # 30 segundos para la tabla de contactos
REINTENTOS_MAX = 3    # Número de reintentos por RUT

def iniciar_driver(headless=False):
    """Configura e inicia el navegador.
    
    Args:
        headless (bool): Si True, ejecuta sin ventana visible. False para ver el navegador.
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # Opciones adicionales para estabilidad
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent para evitar detección
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Navegador iniciado correctamente")
        return driver
    except Exception as e:
        print(f"❌ Error al iniciar el navegador: {e}")
        raise

def esperar_carga_completa(driver, timeout=10):
    """Espera a que la página termine de cargar completamente."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return True
    except TimeoutException:
        print("⚠️ Timeout esperando carga completa de página")
        return False

def extraer_info_basica(driver, rut):
    """Extrae información básica de la empresa (Razón Social, RUT, etc.)."""
    info = {
        "RUT": rut,
        "RazonSocial": "No encontrada",
        "NombreFantasia": "",
        "EstadoHabilidad": "",
        "DomicilioLegal": ""
    }
    
    try:
        wait = WebDriverWait(driver, TIMEOUT_GENERAL)
        
        # Extraer Razón Social y RUT desde los h3
        h3_elements = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "h3")))
        
        for h3 in h3_elements:
            texto = h3.text.strip()
            if "RUT" in texto:
                info["RUT"] = texto.replace("RUT", "").strip()
            elif texto != "":
                info["RazonSocial"] = texto
        
        print(f"   📋 Razón Social: {info['RazonSocial']}")
        print(f"   🆔 RUT: {info['RUT']}")
        
        # Extraer tabla de información del proveedor
        try:
            tabla_info = driver.find_element(By.XPATH, "//table[@aria-label='Información del proveedor']")
            filas_info = tabla_info.find_elements(By.TAG_NAME, "tr")
            
            for fila in filas_info:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                if len(celdas) == 2:
                    clave = celdas[0].text.strip()
                    valor = celdas[1].text.strip()
                    
                    if "Nombre de fantasía" in clave:
                        info["NombreFantasia"] = valor
                    elif "Estado de habilidad" in clave:
                        info["EstadoHabilidad"] = valor
                    elif "Domicilio legal" in clave:
                        info["DomicilioLegal"] = valor
            
            print(f"   🏢 Nombre Fantasía: {info['NombreFantasia']}")
            
        except NoSuchElementException:
            print("   ⚠️ No se encontró tabla de información del proveedor")
    
    except Exception as e:
        print(f"   ❌ Error extrayendo información básica: {e}")
    
    return info

def extraer_contactos(driver, info_empresa):
    """Extrae todos los contactos de la tabla de contactos."""
    contactos = []
    
    try:
        # Hacer scroll hacia abajo para activar la carga de contenido dinámico
        print("   📜 Haciendo scroll para cargar contenido dinámico...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # Scroll hacia arriba para ver la tabla de contactos
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        # Esperar específicamente a que la tabla de contactos esté presente
        print("   ⏳ Esperando tabla de contactos...")
        wait = WebDriverWait(driver, TIMEOUT_TABLA)
        
        # Intentar múltiples selectores
        tabla_contactos = None
        selectores = [
            "//table[@aria-label='Contacto de la empresa']",
            "//table[contains(@class, 'MuiTable-root')]",
            "//tbody[contains(@class, 'MuiTableBody-root')]/.."
        ]
        
        for selector in selectores:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                tabla_contactos = driver.find_element(By.XPATH, selector)
                print(f"   ✅ Tabla encontrada con selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not tabla_contactos:
            raise NoSuchElementException("No se encontró la tabla de contactos con ningún selector")
        
        # Esperar un poco más para que se rendericen los datos
        time.sleep(3)
        
        # Extraer todas las filas
        filas = tabla_contactos.find_elements(By.TAG_NAME, "tr")
        print(f"   📊 Total de filas encontradas: {len(filas)}")
        
        contactos_encontrados = 0
        
        for idx, fila in enumerate(filas):
            try:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                
                if len(celdas) == 0:
                    continue
                
                # Verificar si es fila de encabezado
                clase_primera_celda = celdas[0].get_attribute("class") or ""
                if "MuiTableCell-head" in clase_primera_celda:
                    print(f"   📌 Fila {idx}: Encabezado (saltada)")
                    continue
                
                # Verificar que tenga las 4 columnas esperadas
                if len(celdas) < 4:
                    print(f"   ⚠️ Fila {idx}: Solo tiene {len(celdas)} celdas (esperadas 4)")
                    continue
                
                # Extraer datos de cada celda
                # Nombre (celda 0)
                p_nombre = celdas[0].find_elements(By.TAG_NAME, "p")
                nombre = p_nombre[0].text.strip() if p_nombre else celdas[0].text.strip()
                
                # Cargo (celda 1)
                p_cargo = celdas[1].find_elements(By.TAG_NAME, "p")
                cargo = p_cargo[0].text.strip() if p_cargo else celdas[1].text.strip()
                
                # Email (celda 2)
                p_email = celdas[2].find_elements(By.TAG_NAME, "p")
                email = p_email[0].text.strip() if p_email else celdas[2].text.strip()
                
                # Teléfono (celda 3)
                p_telefono = celdas[3].find_elements(By.TAG_NAME, "p")
                telefono = p_telefono[0].text.strip() if p_telefono else celdas[3].text.strip()
                
                # Solo agregar si al menos tiene nombre
                if nombre and nombre != "":
                    contacto = {
                        "RUT": info_empresa["RUT"],
                        "RazonSocial": info_empresa["RazonSocial"],
                        "NombreFantasia": info_empresa["NombreFantasia"],
                        "EstadoHabilidad": info_empresa["EstadoHabilidad"],
                        "DomicilioLegal": info_empresa["DomicilioLegal"],
                        "ContactoNombre": nombre,
                        "ContactoCargo": cargo,
                        "ContactoEmail": email,
                        "ContactoTelefono": telefono,
                        "FechaActualizacion": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    contactos.append(contacto)
                    contactos_encontrados += 1
                    print(f"   ✅ Contacto {contactos_encontrados}: {nombre} - {cargo} - {email}")
                
            except Exception as e:
                print(f"   ⚠️ Error procesando fila {idx}: {e}")
                continue
        
        if contactos_encontrados == 0:
            print("   ⚠️ No se encontraron contactos en la tabla")
        else:
            print(f"   🎉 Total contactos extraídos: {contactos_encontrados}")
    
    except TimeoutException:
        print("   ❌ Timeout: La tabla de contactos no cargó a tiempo")
    except NoSuchElementException as e:
        print(f"   ❌ No se encontró la tabla de contactos: {e}")
    except Exception as e:
        print(f"   ❌ Error inesperado extrayendo contactos: {e}")
    
    return contactos


def extraer_datos_ficha(rut, driver, intento=1):
    """Extrae toda la información de la ficha de un proveedor.
    
    Args:
        rut (str): RUT del proveedor
        driver: Instancia del navegador Selenium
        intento (int): Número de intento actual
    
    Returns:
        list: Lista de diccionarios con los datos extraídos
    """
    url = f"https://proveedor.mercadopublico.cl/ficha/{rut}"
    
    print(f"\n{'='*60}")
    print(f"🔍 Procesando RUT: {rut} (Intento {intento}/{REINTENTOS_MAX})")
    print(f"🌐 URL: {url}")
    print(f"{'='*60}")
    
    try:
        # Navegar a la URL
        driver.get(url)
        print("   ⏳ Navegando a la página...")
        
        # Esperar a que la página cargue
        if not esperar_carga_completa(driver, TIMEOUT_GENERAL):
            raise TimeoutException("La página no terminó de cargar")
        
        print("   ✅ Página cargada")
        
        # Extraer información básica
        info_empresa = extraer_info_basica(driver, rut)
        
        # Extraer contactos
        contactos = extraer_contactos(driver, info_empresa)
        
        # Si no se encontraron contactos, guardar al menos la info de la empresa
        if len(contactos) == 0:
            print("   ℹ️ No hay contactos, guardando solo información de empresa")
            contactos.append({
                **info_empresa,
                "ContactoNombre": "N/A",
                "ContactoCargo": "N/A",
                "ContactoEmail": "N/A",
                "ContactoTelefono": "N/A",
                "FechaActualizacion": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return contactos
    
    except TimeoutException as e:
        print(f"   ⏱️ Timeout: {e}")
        if intento < REINTENTOS_MAX:
            print(f"   🔄 Reintentando... ({intento + 1}/{REINTENTOS_MAX})")
            time.sleep(5)
            return extraer_datos_ficha(rut, driver, intento + 1)
        else:
            print(f"   ❌ Máximo de reintentos alcanzado para {rut}")
            return None
    
    except WebDriverException as e:
        print(f"   ❌ Error del navegador: {e}")
        if intento < REINTENTOS_MAX:
            print(f"   🔄 Reiniciando navegador y reintentando...")
            driver.quit()
            time.sleep(3)
            driver = iniciar_driver(headless=False)
            return extraer_datos_ficha(rut, driver, intento + 1)
        else:
            print(f"   ❌ Máximo de reintentos alcanzado para {rut}")
            return None
    
    except Exception as e:
        print(f"   ❌ Error inesperado: {type(e).__name__}: {e}")
        return None

def actualizar_base_proveedores(listado_ruts, headless=False):
    """Ciclo principal para procesar RUTs y actualizar el CSV.
    
    Args:
        listado_ruts (list): Lista de RUTs a procesar
        headless (bool): Si True, ejecuta el navegador sin ventana
    
    Returns:
        pd.DataFrame: DataFrame con todos los datos actualizados
    """
    print("\n" + "="*60)
    print("🚀 INICIANDO WEB SCRAPING DE PROVEEDORES V2")
    print("="*60)
    
    driver = iniciar_driver(headless=headless)
    
    # Cargar base existente
    if os.path.exists(ARCHIVO_PROVEEDORES):
        df_base = pd.read_csv(ARCHIVO_PROVEEDORES)
        print(f"📂 Base existente cargada: {len(df_base)} registros")
    else:
        df_base = pd.DataFrame()
        print("📂 No existe base previa, se creará una nueva")
    
    total = len(listado_ruts)
    nuevos_datos = []
    exitosos = 0
    fallidos = 0
    
    print(f"\n📊 Total de proveedores a procesar: {total}\n")
    
    try:
        for i, rut in enumerate(listado_ruts):
            print(f"\n[{i+1}/{total}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            resultado = extraer_datos_ficha(rut, driver)
            
            if resultado:
                nuevos_datos.extend(resultado)
                exitosos += 1
                print(f"✅ RUT {rut} procesado exitosamente ({len(resultado)} registros)")
            else:
                fallidos += 1
                print(f"❌ RUT {rut} falló después de {REINTENTOS_MAX} intentos")
            
            # Pausa entre solicitudes
            if i < total - 1:  # No pausar después del último
                print(f"⏸️ Pausa de 3 segundos antes del siguiente RUT...")
                time.sleep(3)
    
    finally:
        print("\n🔒 Cerrando navegador...")
        driver.quit()
    
    # Guardar resultados
    print("\n" + "="*60)
    print("📊 RESUMEN DEL PROCESO")
    print("="*60)
    print(f"✅ Exitosos: {exitosos}/{total}")
    print(f"❌ Fallidos: {fallidos}/{total}")
    print(f"📝 Total registros nuevos: {len(nuevos_datos)}")
    
    if nuevos_datos:
        df_nuevos = pd.DataFrame(nuevos_datos)
        
        # Eliminar registros viejos de los RUTs procesados
        if not df_base.empty:
            df_base = df_base[~df_base['RUT'].isin(listado_ruts)]
            print(f"🔄 Registros antiguos eliminados: {len(df_base)}")
        
        # Combinar datos
        df_final = pd.concat([df_base, df_nuevos], ignore_index=True)
        df_final.to_csv(ARCHIVO_PROVEEDORES, index=False, encoding='utf-8-sig')
        
        print(f"💾 Datos guardados en: {ARCHIVO_PROVEEDORES}")
        print(f"📊 Total registros en base: {len(df_final)}")
        print("="*60 + "\n")
        
        return df_final
    else:
        print("⚠️ No se obtuvieron datos nuevos")
        print("="*60 + "\n")
        return df_base

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    # Ejemplo de uso
    print("\n🎯 MODO DE PRUEBA - SCRAPING PROVEEDORES V2\n")
    
    # RUT de ejemplo (puedes cambiarlo)
    ruts_ejemplo = ["76.780.759-7"]
    
    # Ejecutar con navegador VISIBLE para debugging (headless=False)
    # Cambia a headless=True cuando esté funcionando correctamente
    df_resultado = actualizar_base_proveedores(ruts_ejemplo, headless=False)
    
    if not df_resultado.empty:
        print("\n📋 VISTA PREVIA DE LOS DATOS:")
        print(df_resultado.to_string())
