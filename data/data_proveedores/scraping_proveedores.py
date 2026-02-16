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
from webdriver_manager.chrome import ChromeDriverManager
import streamlit as st

# --- CONFIGURACIÓN ---
ARCHIVO_PROVEEDORES = "base_proveedores_contactos.csv"

# Esperar específicamente a que la tabla de contactos sea visible

def iniciar_driver():
    """Configura e inicia el navegador en modo headless (sin ventana)."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Cambiar a False si quieres ver el proceso
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extraer_datos_ficha(rut, driver):
    """Extrae la información de la empresa y sus contactos desde la ficha."""
    url = f"https://proveedor.mercadopublico.cl/ficha/{rut}"
    driver.get(url)
    
    datos_finales = []
    
    try:
        # Esperar a que la página cargue (buscamos la razón social)
        wait = WebDriverWait(driver, 15)
        # Buscamos el h3 que no contiene "RUT" para la Razón Social
        h3_elements = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "h3")))
        
        razon_social = "No encontrada"
        rut_confirmado = rut
        
        for h3 in h3_elements:
            texto = h3.text.strip()
            if "RUT" in texto:
                rut_confirmado = texto.replace("RUT", "").strip()
            elif texto != "":
                razon_social = texto

        # --- EXTRAER TABLA INFORMACIÓN PROVEEDOR ---
        info_empresa = {}
        try:
            tabla_info = driver.find_element(By.XPATH, "//table[@aria-label='Información del proveedor']")
            filas_info = tabla_info.find_elements(By.TAG_NAME, "tr")
            for fila in filas_info:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                if len(celdas) == 2:
                    clave = celdas[0].text.strip()
                    valor = celdas[1].text.strip()
                    info_empresa[clave] = valor
        except:
            print(f"⚠️ No se encontró tabla de información general para {rut}")

        # --- EXTRAER TABLA DE CONTACTOS ---
        try:
            # Esperar a que la tabla de contactos esté presente
            wait.until(EC.presence_of_element_located((By.XPATH, "//table[@aria-label='Contacto de la empresa']")))
            
            # Localizamos la tabla específicamente por su etiqueta de accesibilidad
            tabla_contactos = driver.find_element(By.XPATH, "//table[@aria-label='Contacto de la empresa']")
            filas_contactos = tabla_contactos.find_elements(By.TAG_NAME, "tr")
            
            # Iteramos sobre todas las filas y verificamos si son encabezados o datos
            for fila in filas_contactos:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                
                # Verificar si es una fila de encabezado (contiene MuiTableCell-head)
                if len(celdas) > 0:
                    # Verificamos si la primera celda tiene la clase de encabezado
                    clase_primera_celda = celdas[0].get_attribute("class")
                    if "MuiTableCell-head" in clase_primera_celda:
                        # Es una fila de encabezado, la saltamos
                        continue
                
                # Es una fila de datos
                if len(celdas) >= 4:
                    # PROCESO ESPECIAL PARA EL NOMBRE (Celda 0)
                    # El HTML tiene: <p>Juan Pablo Moreno</p><p>Contacto</p>
                    # Solo queremos el primer párrafo.
                    p_nombre = celdas[0].find_elements(By.TAG_NAME, "p")
                    nombre_limpio = p_nombre[0].text.strip() if p_nombre else celdas[0].text.strip()
                    
                    # PROCESO PARA EL CARGO (Celda 1)
                    p_cargo = celdas[1].find_elements(By.TAG_NAME, "p")
                    cargo_limpio = p_cargo[0].text.strip() if p_cargo else celdas[1].text.strip()
                    
                    # PROCESO PARA EL EMAIL (Celda 2)
                    # Aquí el email suele venir solo en un párrafo, .text basta.
                    p_email = celdas[2].find_elements(By.TAG_NAME, "p")
                    email_limpio = p_email[0].text.strip() if p_email else celdas[2].text.strip()
                    
                    # PROCESO PARA EL TELÉFONO (Celda 3)
                    p_telefono = celdas[3].find_elements(By.TAG_NAME, "p")
                    telefono_limpio = p_telefono[0].text.strip() if p_telefono else celdas[3].text.strip()

                    contacto = {
                        "RUT": rut_confirmado,
                        "RazonSocial": razon_social,
                        "NombreFantasia": info_empresa.get("Nombre de fantasía", ""),
                        "ContactoNombre": nombre_limpio,
                        "ContactoCargo": cargo_limpio,
                        "ContactoEmail": email_limpio,
                        "ContactoTelefono": telefono_limpio,
                        "FechaActualizacion": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    datos_finales.append(contacto)
                    
        except Exception as e:
            print(f"⚠️ No se encontraron contactos detallados para el RUT {rut}. Error: {e}")
            # Si no hay contactos, guardamos al menos la info de la empresa
            datos_finales.append({
                "RUT": rut_confirmado,
                "RazonSocial": razon_social,
                "NombreFantasia": info_empresa.get("Nombre de fantasía", ""),
                "EstadoHabilidad": info_empresa.get("Estado de habilidad", ""),
                "DomicilioLegal": info_empresa.get("Domicilio legal", ""),
                "ContactoNombre": "N/A", "ContactoCargo": "N/A", "ContactoEmail": "N/A", "ContactoTelefono": "N/A",
                "FechaActualizacion": time.strftime("%Y-%m-%d %H:%M:%S")
            })

    except Exception as e:
        print(f"❌ Error procesando RUT {rut}: {e}")
        return None

    return datos_finales

def actualizar_base_proveedores(listado_ruts):
    """Ciclo principal para procesar RUTs y actualizar el CSV."""
    driver = iniciar_driver()
    
    # Cargar base existente para no duplicar o para saber qué actualizar
    if os.path.exists(ARCHIVO_PROVEEDORES):
        df_base = pd.read_csv(ARCHIVO_PROVEEDORES)
    else:
        df_base = pd.DataFrame()

    total = len(listado_ruts)
    nuevos_datos = []

    print(f"🚀 Iniciando scraping de {total} proveedores...")

    for i, rut in enumerate(listado_ruts):
        print(f"[{i+1}/{total}] Procesando RUT: {rut}")
        
        # Opcional: Si el RUT ya está actualizado recientemente, podrías saltarlo
        # if not df_base.empty and rut in df_base['RUT'].values: ...
        
        resultado = extraer_datos_ficha(rut, driver)
        
        if resultado:
            nuevos_datos.extend(resultado)
        
        # Pausa breve para evitar bloqueos
        time.sleep(2)

    driver.quit()

    if nuevos_datos:
        df_nuevos = pd.DataFrame(nuevos_datos)
        
        # Unir con la base anterior: 
        # Eliminamos registros viejos de los RUTs que acabamos de consultar
        if not df_base.empty:
            df_base = df_base[~df_base['RUT'].isin(listado_ruts)]
        
        df_final = pd.concat([df_base, df_nuevos], ignore_index=True)
        df_final.to_csv(ARCHIVO_PROVEEDORES, index=False, encoding='utf-8-sig')
        print(f"✅ Proceso terminado. Datos guardados en {ARCHIVO_PROVEEDORES}")
        return df_final
    else:
        print("❌ No se obtuvieron datos nuevos.")
        return df_base

# --- INTEGRACIÓN CON TU FLUJO ---
if __name__ == "__main__":
    # Como mencionaste que trabajas con df_filtrado:
    # Supongamos que df_filtrado tiene una columna 'RutProveedor'
    try:
        # Aquí es donde entra tu df_filtrado con filtros aplicados
        ruts_a_consultar = df_filtrado['RutProveedor'].unique().tolist()
        
        # Ejecutar actualización
        df_proveedores_actualizado = actualizar_base_proveedores(ruts_a_consultar)
        
        # Ahora podrías usar df_proveedores_actualizado para tu lógica de correos
        # Ejemplo: df_atrasados = df_filtrado[df_filtrado['DiasRetraso'] > n]
        # merge con df_proveedores_actualizado para obtener el email.
        
    except NameError:
        print("Nota: df_filtrado no definido. Usando ejemplo manual.")
        ruts_ejemplo = ["76.780.759-7"]
        actualizar_base_proveedores(ruts_ejemplo)