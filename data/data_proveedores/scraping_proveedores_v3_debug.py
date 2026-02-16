"""
Script de Web Scraping V3 - Con debugging visual
Este script toma capturas de pantalla y guarda el HTML para debugging
"""
import time
import os
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
ARCHIVO_PROVEEDORES = "base_proveedores_contactos_v3.csv"
DEBUG_DIR = "debug_screenshots"
TIMEOUT = 30

# Crear directorio para screenshots
if not os.path.exists(DEBUG_DIR):
    os.makedirs(DEBUG_DIR)

def iniciar_driver():
    """Inicia el navegador en modo visible para debugging."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ Navegador iniciado")
    return driver

def guardar_debug(driver, rut, paso):
    """Guarda screenshot y HTML para debugging."""
    timestamp = time.strftime("%H%M%S")
    
    # Screenshot
    screenshot_path = os.path.join(DEBUG_DIR, f"{rut}_{paso}_{timestamp}.png")
    driver.save_screenshot(screenshot_path)
    print(f"   📸 Screenshot guardado: {screenshot_path}")
    
    # HTML
    html_path = os.path.join(DEBUG_DIR, f"{rut}_{paso}_{timestamp}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"   📄 HTML guardado: {html_path}")

def extraer_datos_completos(rut, driver):
    """Extrae información de la empresa y contactos."""
    url = f"https://proveedor.mercadopublico.cl/ficha/{rut}"
    
    print(f"\n{'='*70}")
    print(f"🔍 Procesando RUT: {rut}")
    print(f"🌐 URL: {url}")
    print(f"{'='*70}\n")
    
    try:
        # Navegar
        driver.get(url)
        print("⏳ Cargando página...")
        time.sleep(5)
        
        # Screenshot inicial
        guardar_debug(driver, rut, "01_inicial")
        
        # Esperar a que cargue
        WebDriverWait(driver, TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ Página cargada")
        
        # Extraer información básica
        info_empresa = {
            "RUT": rut,
            "RazonSocial": "No encontrada",
            "NombreFantasia": "",
            "EstadoHabilidad": "",
            "DomicilioLegal": ""
        }
        
        # Buscar h3 para Razón Social y RUT
        try:
            h3_elements = driver.find_elements(By.TAG_NAME, "h3")
            for h3 in h3_elements:
                texto = h3.text.strip()
                if "RUT" in texto:
                    info_empresa["RUT"] = texto.replace("RUT", "").strip()
                elif texto != "":
                    info_empresa["RazonSocial"] = texto
            
            print(f"📋 Razón Social: {info_empresa['RazonSocial']}")
            print(f"🆔 RUT: {info_empresa['RUT']}")
        except Exception as e:
            print(f"⚠️ Error extrayendo info básica: {e}")
        
        # Scroll completo para cargar todo
        print("\n📜 Haciendo scroll completo...")
        total_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(0, total_height, 300):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.5)
        
        time.sleep(3)
        guardar_debug(driver, rut, "02_despues_scroll")
        
        # Buscar TODAS las tablas en la página
        print("\n🔍 Buscando todas las tablas en la página...")
        todas_las_tablas = driver.find_elements(By.TAG_NAME, "table")
        print(f"📊 Total de tablas encontradas: {len(todas_las_tablas)}")
        
        contactos = []
        
        for idx, tabla in enumerate(todas_las_tablas):
            try:
                aria_label = tabla.get_attribute("aria-label") or "Sin etiqueta"
                print(f"\n   Tabla {idx + 1}: aria-label='{aria_label}'")
                
                # Verificar si es la tabla de contactos
                if "contacto" in aria_label.lower() or "empresa" in aria_label.lower():
                    print(f"   ✅ ¡Posible tabla de contactos encontrada!")
                    
                    # Extraer filas
                    filas = tabla.find_elements(By.TAG_NAME, "tr")
                    print(f"   📝 Filas en esta tabla: {len(filas)}")
                    
                    for fila_idx, fila in enumerate(filas):
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        
                        if len(celdas) == 0:
                            continue
                        
                        # Verificar si es encabezado
                        clase = celdas[0].get_attribute("class") or ""
                        if "head" in clase.lower():
                            print(f"      Fila {fila_idx}: Encabezado")
                            continue
                        
                        # Si tiene 4 celdas, probablemente sea un contacto
                        if len(celdas) >= 4:
                            # Extraer texto de cada celda
                            textos = []
                            for celda in celdas[:4]:
                                # Buscar párrafos dentro de la celda
                                parrafos = celda.find_elements(By.TAG_NAME, "p")
                                if parrafos:
                                    texto = parrafos[0].text.strip()
                                else:
                                    texto = celda.text.strip()
                                textos.append(texto)
                            
                            nombre, cargo, email, telefono = textos
                            
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
                                print(f"      ✅ Contacto: {nombre} | {cargo} | {email} | {telefono}")
            
            except Exception as e:
                print(f"   ⚠️ Error procesando tabla {idx + 1}: {e}")
                continue
        
        # Screenshot final
        guardar_debug(driver, rut, "03_final")
        
        print(f"\n🎉 Total contactos extraídos: {len(contactos)}")
        
        # Si no hay contactos, guardar al menos la info de la empresa
        if len(contactos) == 0:
            print("ℹ️ No se encontraron contactos, guardando solo info de empresa")
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
        print(f"❌ Error: {e}")
        guardar_debug(driver, rut, "ERROR")
        return None

def main():
    print("\n" + "="*70)
    print("🚀 WEB SCRAPING V3 - CON DEBUGGING VISUAL")
    print("="*70 + "\n")
    
    # RUT de prueba
    ruts = ["76.780.759-7"]
    
    driver = iniciar_driver()
    
    todos_los_datos = []
    
    try:
        for rut in ruts:
            resultado = extraer_datos_completos(rut, driver)
            if resultado:
                todos_los_datos.extend(resultado)
            time.sleep(3)
        
        # Guardar resultados
        if todos_los_datos:
            df = pd.DataFrame(todos_los_datos)
            df.to_csv(ARCHIVO_PROVEEDORES, index=False, encoding='utf-8-sig')
            print(f"\n💾 Datos guardados en: {ARCHIVO_PROVEEDORES}")
            print(f"📊 Total registros: {len(df)}")
            print("\n📋 VISTA PREVIA:")
            print(df.to_string())
        else:
            print("\n⚠️ No se obtuvieron datos")
    
    finally:
        print("\n⏸️ Presiona ENTER para cerrar el navegador...")
        input()
        driver.quit()
        print("✅ Navegador cerrado")

if __name__ == "__main__":
    main()
