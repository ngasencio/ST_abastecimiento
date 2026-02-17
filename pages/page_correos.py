import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
import time
from style.ui import cargar_css

cargar_css()

# --- Configuración de la Página ---
st.set_page_config(page_title="Email Pro Sender", page_icon="📧")
st.title("📧 Envío Masivo Profesional (HTML + PDF)")

# --- 1. BARRA LATERAL: Credenciales ---
with st.sidebar:
    st.header("Configuración")
    email_sender = st.text_input("Tu correo Outlook", placeholder="usuario@outlook.com")
    email_password = st.text_input("Contraseña de Aplicación", type="password")
    st.info("Nota: Si usas autenticación de dos pasos, recuerda usar una 'Contraseña de Aplicación'.")

# --- 2. ÁREA PRINCIPAL: Carga de Datos ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("1. Sube lista de contactos (Excel/CSV)", type=['xlsx', 'csv'])
with col2:
    attachment_file = st.file_uploader("2. Sube el reporte PDF (Opcional)", type=['pdf'])

# --- 3. DISEÑO DEL CORREO (HTML) ---
st.subheader("3. Redacción del Correo")
subject = st.text_input("Asunto del correo", "Reporte Mensual de Resultados")

# Plantilla HTML por defecto con CSS en línea (inline styles)
html_template = """
<div style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
    <h2 style="color: #00468c;">Hola, {nombre}</h2>
    <p>Espero que estés teniendo una excelente semana.</p>
    <p>Adjunto a este correo encontrarás el <strong>Reporte PDF</strong> solicitado.</p>
    <hr style="border: 0; border-top: 1px solid #eee;">
    <p style="font-size: 12px; color: #777;">
        Saludos cordiales,<br>
        <strong>El Equipo de Finanzas</strong><br>
        <a href="https://tue-mpresa.com">www.tu-empresa.com</a>
    </p>
</div>
"""

body_html = st.text_area("Cuerpo en HTML (Usa {nombre} para personalizar)", value=html_template, height=300)

# Vista previa del HTML
st.caption("Vista previa aproximada del correo:")
st.markdown(body_html.replace("{nombre}", "Juan Pérez"), unsafe_allow_html=True)

# --- FUNCIÓN DE ENVÍO ROBUSTA ---
def send_email_pro(sender, password, receiver, subject, html_content, attachment=None):
    try:
        # Crear el contenedor del mensaje
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = subject

        # Adjuntar el cuerpo HTML
        msg.attach(MIMEText(html_content, 'html'))

        # Lógica para adjuntar el PDF (si existe)
        if attachment is not None:
            # Creamos el objeto adjunto
            part = MIMEBase('application', 'octet-stream')
            # Leemos los bytes del archivo subido por Streamlit
            part.set_payload(attachment.getvalue())
            # Codificamos a base64 (necesario para enviar archivos por email)
            encoders.encode_base64(part)
            # Añadimos las cabeceras
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={attachment.name}',
            )
            msg.attach(part)

        # Conexión al servidor SMTP de Outlook
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls() # Encriptación
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        return True
        
    except Exception as e:
        return f"Error: {str(e)}"

# --- 4. BOTÓN DE ENVÍO ---
st.divider()
if st.button("🚀 Enviar Campaña", type="primary"):
    if not email_sender or not email_password:
        st.error("⚠️ Faltan las credenciales de Outlook en la barra lateral.")
        st.stop()
    
    if not uploaded_file:
        st.error("⚠️ Sube un archivo de Excel o CSV con los contactos.")
        st.stop()

    # Leer archivo
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        st.stop()

    # Validar columnas
    # Buscamos columnas flexibles (Email, email, Correo, etc.)
    df.columns = [c.lower() for c in df.columns] 
    if 'email' not in df.columns:
        st.error("El archivo debe tener una columna llamada 'Email' o 'email'.")
        st.stop()

    # Iniciar proceso
    progress_text = st.empty()
    my_bar = st.progress(0)
    total = len(df)
    sent_count = 0

    for index, row in df.iterrows():
        receiver_email = row['email']
        
        # Personalización: Buscamos columna 'nombre', si no existe usamos "Cliente"
        user_name = row['nombre'] if 'nombre' in df.columns else "Cliente"
        
        # Reemplazamos el placeholder {nombre} en el HTML por el nombre real
        personal_html = body_html.replace("{nombre}", str(user_name))

        # Enviar
        status = send_email_pro(
            email_sender, 
            email_password, 
            receiver_email, 
            subject, 
            personal_html, 
            attachment_file # Pasamos el archivo PDF (o None)
        )

        if status is True:
            sent_count += 1
        else:
            st.warning(f"Fallo al enviar a {receiver_email}: {status}")

        # Actualizar barra
        my_bar.progress((index + 1) / total)
        progress_text.text(f"Enviando {index + 1} de {total}...")
        
        # Pausa anti-spam
        time.sleep(2) 

    st.success(f"✅ ¡Campaña finalizada! Enviados {sent_count} de {total} correos.")
    # Resetear el puntero del archivo por si se quiere volver a usar sin recargar
    if attachment_file:
        attachment_file.seek(0)