"""
Script de Web Scraping con Login Manual
Este script te permite hacer login manualmente y luego automatiza el scraping
"""
import time
import os
import pickle
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
ARCHIVO_PROVEEDORES = "base_proveedores_contactos_autenticado.csv"
COOKIES_FILE = "mercadopublico_cookies.pkl"
LOGIN_URL = "https://www.mercadopublico.cl/Home"
TIMEOUT = 30

def iniciar_driver():
    """Inicia el navegador en modo visible."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Mantener el navegador abierto después de que termine el script
    chrome_options.add_experimental_option("detach", True)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ Navegador iniciado")
    return driver

def guardar_cookies(driver):
    """Guarda las cookies de la sesión actual."""
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, 'wb') as file:
        pickle.dump(cookies, file)
    print(f"💾 Cookies guardadas en {COOKIES_FILE}")

def cargar_cookies(driver):
    """Carga las cookies guardadas previamente."""
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'rb') as file:
            cookies = pickle.load(file)
        
        # Primero ir al dominio para poder cargar las cookies
        driver.get(LOGIN_URL)
        time.sleep(2)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"⚠️ No se pudo cargar cookie: {e}")
        
        print("✅ Cookies cargadas")
        return True
    else:
        print("ℹ️ No hay cookies guardadas")
        return False

def hacer_login_manual(driver):
    """Guía al usuario para hacer login manualmente."""
    print("\n" + "="*70)
    print("🔐 PROCESO DE LOGIN MANUAL")
    print("="*70)
    print("\n📋 INSTRUCCIONES:")
    print("1. Se abrirá el navegador en Mercado Público")
    print("2. Haz clic en 'Ingresar' (esquina superior derecha)")
    print("3. Completa el login con ClaveÚnica")
    print("4. Espera a que cargue tu página de inicio")
    print("5. Vuelve a esta consola y presiona ENTER")
    print("\n⏳ Abriendo navegador...")
    
    driver.get(LOGIN_URL)
    time.sleep(3)
    
    input("\n✋ Presiona ENTER cuando hayas completado el login... ")
    
    # Guardar cookies para futuras sesiones
    guardar_cookies(driver)
    print("✅ Login completado y cookies guardadas")

def verificar_autenticacion(driver):
    """Verifica si el usuario está autenticado."""
    try:
        # Buscar elementos que solo aparecen cuando estás logueado
        # Por ejemplo, el nombre de usuario o un menú de usuario
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        # Intenta encontrar algún elemento que indique que estás logueado
        # Esto puede variar, ajusta según la estructura de la página
        try:
            # Buscar si hay un botón de "Ingresar" (no logueado) o perfil (logueado)
            elementos_login = driver.find_elements(By.XPATH, "//*[contains(text(), 'Ingresar')]")
            if len(elementos_login) > 0:
                print("⚠️ No estás autenticado")
                return False
            else:
                print("✅ Sesión autenticada detectada")
                return True
        except:
            return False
    except Exception as e:
        print(f"⚠️ Error verificando autenticación: {e}")
        return False

def extraer_info_empresa(driver, rut):
    """Extrae información básica de la empresa."""
    info = {
        "RUT": rut,
        "RazonSocial": "No encontrada",
        "NombreFantasia": "",
        "EstadoHabilidad": "",
        "DomicilioLegal": ""
    }
    
    try:
        # Buscar h3 para Razón Social y RUT
        h3_elements = driver.find_elements(By.TAG_NAME, "h3")
        for h3 in h3_elements:
            texto = h3.text.strip()
            if "RUT" in texto:
                info["RUT"] = texto.replace("RUT", "").strip()
            elif texto != "":
                info["RazonSocial"] = texto
        
        print(f"   📋 Razón Social: {info['RazonSocial']}")
        print(f"   🆔 RUT: {info['RUT']}")
        
        # Buscar tabla de información del proveedor
        try:
            tabla_info = driver.find_element(By.XPATH, "//table[@aria-label='Información del proveedor']")
            filas = tabla_info.find_elements(By.TAG_NAME, "tr")
            
            for fila in filas:
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
        except:
            pass
    
    except Exception as e:
        print(f"   ⚠️ Error extrayendo info básica: {e}")
    
    return info

def extraer_contactos(driver, info_empresa):
    """Extrae todos los contactos de la tabla."""
    contactos = []
    
    try:
        # Scroll para cargar contenido
        print("   📜 Haciendo scroll...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        # Buscar tabla de contactos
        print("   🔍 Buscando tabla de contactos...")
        
        # Intentar múltiples selectores
        tabla_contactos = None
        selectores = [
            "//table[@aria-label='Contacto de la empresa']",
            "//table[contains(@aria-label, 'Contacto')]",
            "//table[contains(@class, 'MuiTable-root')]"
        ]
        
        for selector in selectores:
            try:
                tabla_contactos = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                print(f"   ✅ Tabla encontrada con: {selector}")
                break
            except TimeoutException:
                continue
        
        if not tabla_contactos:
            print("   ⚠️ No se encontró tabla de contactos")
            return contactos
        
        # Extraer filas
        time.sleep(2)
        filas = tabla_contactos.find_elements(By.TAG_NAME, "tr")
        print(f"   📊 Filas encontradas: {len(filas)}")
        
        for idx, fila in enumerate(filas):
            try:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                
                if len(celdas) == 0:
                    continue
                
                # Verificar si es encabezado
                clase = celdas[0].get_attribute("class") or ""
                if "head" in clase.lower():
                    print(f"      Fila {idx}: Encabezado (saltada)")
                    continue
                
                # Debe tener 4 columnas: Nombre, Cargo, Email, Teléfono
                if len(celdas) >= 4:
                    # Extraer texto de cada celda
                    def extraer_texto(celda):
                        parrafos = celda.find_elements(By.TAG_NAME, "p")
                        if parrafos:
                            return parrafos[0].text.strip()
                        return celda.text.strip()
                    
                    nombre = extraer_texto(celdas[0])
                    cargo = extraer_texto(celdas[1])
                    email = extraer_texto(celdas[2])
                    telefono = extraer_texto(celdas[3])
                    
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
                        print(f"      ✅ {nombre} | {cargo} | {email}")
            
            except Exception as e:
                print(f"      ⚠️ Error en fila {idx}: {e}")
                continue
        
        print(f"   🎉 Total contactos: {len(contactos)}")
    
    except Exception as e:
        print(f"   ❌ Error extrayendo contactos: {e}")
    
    return contactos

def extraer_datos_proveedor(rut, driver):
    """Extrae toda la información de un proveedor."""
    url = f"https://proveedor.mercadopublico.cl/ficha/{rut}"
    
    print(f"\n{'='*70}")
    print(f"🔍 Procesando RUT: {rut}")
    print(f"🌐 URL: {url}")
    print(f"{'='*70}\n")
    
    try:
        driver.get(url)
        print("   ⏳ Cargando página...")
        
        WebDriverWait(driver, TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)
        print("   ✅ Página cargada")
        
        # Extraer información
        info_empresa = extraer_info_empresa(driver, rut)
        contactos = extraer_contactos(driver, info_empresa)
        
        # Si no hay contactos, guardar al menos la info de la empresa
        if len(contactos) == 0:
            print("   ℹ️ Sin contactos, guardando solo info de empresa")
            contactos.append({
                **info_empresa,
                "ContactoNombre": "N/A",
                "ContactoCargo": "N/A",
                "ContactoEmail": "N/A",
                "ContactoTelefono": "N/A",
                "FechaActualizacion": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return contactos
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    print("\n" + "="*70)
    print("🚀 WEB SCRAPING MERCADO PÚBLICO - CON AUTENTICACIÓN")
    print("="*70 + "\n")
    
    driver = iniciar_driver()
    
    try:
        # Intentar cargar cookies guardadas
        cookies_cargadas = cargar_cookies(driver)
        
        if cookies_cargadas:
            # Verificar si la sesión sigue válida
            if not verificar_autenticacion(driver):
                print("⚠️ Sesión expirada, necesitas hacer login nuevamente")
                hacer_login_manual(driver)
        else:
            # No hay cookies, hacer login manual
            hacer_login_manual(driver)
        
        # Lista de RUTs a procesar
        print("\n" + "="*70)
        print("📋 INGRESA LOS RUTs A PROCESAR")
        print("="*70)
        print("Puedes ingresar:")
        print("1. Un solo RUT: 76.780.759-7")
        print("2. Varios RUTs separados por coma: 76.780.759-7, 12.345.678-9")
        print("3. Dejar en blanco para usar el ejemplo: 76.780.759-7")
        
        entrada = input("\n🔢 RUTs: ").strip()
        
        if entrada == "":
            ruts = ["76.780.759-7"]
        else:
            ruts = [rut.strip() for rut in entrada.split(",")]
        
        print(f"\n📊 Total RUTs a procesar: {len(ruts)}")
        
        # Procesar cada RUT
        todos_los_datos = []
        
        for i, rut in enumerate(ruts):
            print(f"\n[{i+1}/{len(ruts)}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            resultado = extraer_datos_proveedor(rut, driver)
            
            if resultado:
                todos_los_datos.extend(resultado)
                print(f"✅ RUT {rut} procesado ({len(resultado)} registros)")
            else:
                print(f"❌ Error procesando RUT {rut}")
            
            # Pausa entre RUTs
            if i < len(ruts) - 1:
                print("⏸️ Pausa de 3 segundos...")
                time.sleep(3)
        
        # Guardar resultados
        print("\n" + "="*70)
        print("💾 GUARDANDO RESULTADOS")
        print("="*70)
        
        if todos_los_datos:
            df = pd.DataFrame(todos_los_datos)
            
            # Si existe archivo previo, combinar
            if os.path.exists(ARCHIVO_PROVEEDORES):
                df_anterior = pd.read_csv(ARCHIVO_PROVEEDORES)
                # Eliminar registros viejos de los RUTs procesados
                df_anterior = df_anterior[~df_anterior['RUT'].isin(ruts)]
                df = pd.concat([df_anterior, df], ignore_index=True)
            
            df.to_csv(ARCHIVO_PROVEEDORES, index=False, encoding='utf-8-sig')
            
            print(f"✅ Datos guardados en: {ARCHIVO_PROVEEDORES}")
            print(f"📊 Total registros: {len(df)}")
            
            print("\n📋 VISTA PREVIA:")
            print(df.to_string())
        else:
            print("⚠️ No se obtuvieron datos")
        
        print("\n" + "="*70)
        print("✅ PROCESO COMPLETADO")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    finally:
        print("\n⏸️ Presiona ENTER para cerrar el navegador...")
        input()
        driver.quit()
        print("✅ Navegador cerrado")

if __name__ == "__main__":
    main()
