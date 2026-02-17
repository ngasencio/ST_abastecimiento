import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from style.ui import cargar_css

cargar_css()

def app():
    st.markdown("## 🤖 Automatización de Descargas - Panel SS Osorno")
    
    # --- RUTAS RELATIVAS ---
    base_path = os.getcwd() 
    DOWNLOAD_DIR = os.path.abspath(os.path.join(base_path, "data", "data_panel"))
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # --- INTERFAZ ---
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1: rut_user = st.text_input("RUT", value="18577822")
    with col2: dv_user = st.text_input("DV", value="3")
    with col3: pass_user = st.text_input("Contraseña", type="password", value="123456")

    if st.button("🚀 Iniciar Proceso Completo"):
        status_text = st.empty()
        progress_bar = st.progress(0)

        try:
            status_text.text("Iniciando navegador...")
            chrome_options = Options()
            prefs = {
                "download.default_directory": DOWNLOAD_DIR,
                "download.prompt_for_download": False,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            wait = WebDriverWait(driver, 20)

            # 1. LOGIN
            status_text.text("Ingresando credenciales...")
            driver.get("https://panel.ssosorno.cl/panel_documental/app/solicitudes_compras/abastecimiento/exportar.php")
            
            wait.until(EC.presence_of_element_located((By.ID, "rut"))).send_keys(rut_user)
            driver.find_element(By.ID, "dv").send_keys(dv_user)
            driver.find_element(By.ID, "clave").send_keys(pass_user)
            driver.find_element(By.XPATH, "//button[contains(text(), 'Acceder')]").click()
            
            time.sleep(5) # Espera a que cargue el dashboard
            progress_bar.progress(20)

            # 2. ACCEDER A REPORTES (Navegación por menú)
            # Buscamos el <span> que dice "Reportes" y hacemos clic en su enlace (<a>)
            status_text.text("Navegando al menú de Reportes...")
            try:
                # Usamos un selector XPATH para encontrar el span de "Reportes"
                link_reportes = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Reportes')]/parent::a")))
                link_reportes.click()
                time.sleep(3)
            except Exception as e:
                st.warning("No se pudo hacer clic en el menú, intentando acceso directo por URL...")
                driver.get("https://panel.ssosorno.cl/panel_documental/app/solicitudes_compras/abastecimiento/exportar.php")
            
            progress_bar.progress(40)

            # 3. DESCARGAR LOS 6 REPORTES
            botones_id = ["totalfscy", "totalfscdy", "totalcarrofsc"] # Agrega los otros 3 aquí
            
            status_text.text("Iniciando descarga de archivos...")
            for idx, b_id in enumerate(botones_id):
                try:
                    # Esperar y clicar cada botón de exportar
                    btn = wait.until(EC.element_to_be_clickable((By.ID, b_id)))
                    btn.click()
                    status_text.text(f"Descargando: {b_id}...")
                    time.sleep(4) 
                except:
                    st.error(f"Error con el botón {b_id}")
                
                # Actualizar progreso
                current_p = 40 + int((idx+1) * (60/len(botones_id)))
                progress_bar.progress(min(current_p, 100))

            status_text.text("Descargas finalizadas.")
            time.sleep(2)
            driver.quit()
            st.success(f"Archivos guardados en: {DOWNLOAD_DIR}")
            st.write(os.listdir(DOWNLOAD_DIR))

        except Exception as e:
            st.error(f"Error: {e}")
            if 'driver' in locals(): driver.quit()

if __name__ == "__main__":
    app()