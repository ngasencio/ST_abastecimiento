
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from style.ui import cargar_css



# ============== LISTA DE USUARIOS Y CORREOS ===================
USUARIOS_CORREOS = {
    "Rubén Uribe": "ruben.uribe@redsalud.gob.cl",
    "Lesly Andrea Díaz Aburto": "lesly.diaz@redsalud.gob.cl",
    "JACQUELINE OYARZUN ALVAREZ": "jacqueline.oyarzuna@redsalud.gob.cl",
    "Cecilia Garay Lemuy": "cecilia.garay@redsalud.gob.cl",
    "Alicia Vidal Paredes": "alicia.vidal@redsalud.gob.cl",
    "JUAN FELIPE ROJEL HUENTRO": "juan.rojel@redsalud.gob.cl",
    "Ivan Vargas Ojeda": "ivan.vargas@redsalud.gob.cl",
    "PAULINA NICOLE LONCOPAN CARRILLO": "paulina.loncopan@redsalud.gob.cl",
    "Ariela Acevedo": "ariela.ariela@redsalud.gob.cl",
    "Jonathan Salvo Currin": "jonathan.salvo@redsalud.gob.cl",
    "ALEJANDRA NICOLE ALMONACID LEVINIERE": "alejandra.almonacid@redsalud.gob.cl",
    "RODRIGO ALEJANDRO LABRIN ESCALONA": "rodrigo.labrin@redsalud.gob.cl",
    "Bastian Miranda Coronado": "bastian.miranda@redsalud.gob.cl",
    "NICOLAS ASENCIO MOREIRA": "nicolas.asencio@redsalud.gob.cl",
    "Verónica Aracely Márquez Aguila": "verónica.márqueza@redsalud.gob.cl",
    "Rosa Vasquez": "rosa.vasquez@redsalud.gob.cl"
}


def generar_html_reporte(df_semana_actual, df_proxima_semana, nombre_destinatario):
    """Genera HTML profesional para el reporte semanal"""
    
    # Estadísticas
    total_actual = len(df_semana_actual)
    total_proxima = len(df_proxima_semana)
    monto_actual = df_semana_actual['MontoEstimado'].sum() if total_actual > 0 else 0
    monto_proxima = df_proxima_semana['MontoEstimado'].sum() if total_proxima > 0 else 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #138AEC 0%, #3E9FEF 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 700;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 14px;
            }}
            .stats {{
                display: flex;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                flex: 1;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #138AEC;
            }}
            .stat-card h3 {{
                margin: 0 0 10px 0;
                color: #138AEC;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .stat-card .value {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
            }}
            .section {{
                margin-bottom: 30px;
            }}
            .section h2 {{
                color: #138AEC;
                font-size: 20px;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e9ecef;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            th {{
                background: #138AEC;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 13px;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #e9ecef;
                font-size: 13px;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #e9ecef;
                text-align: center;
                color: #6c757d;
                font-size: 12px;
            }}
            .no-data {{
                padding: 20px;
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                border-radius: 4px;
                color: #856404;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📄 Reporte Semanal de Licitaciones</h1>
            <p>Red de Salud - Dirección de Abastecimiento</p>
            <p>Generado el {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        
        <p>Estimado/a <strong>{nombre_destinatario}</strong>,</p>
        <p>A continuación se presenta el resumen de licitaciones para esta semana y la próxima:</p>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Esta Semana</h3>
                <div class="value">{total_actual}</div>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;">Licitaciones activas</p>
            </div>
            <div class="stat-card">
                <h3>Próxima Semana</h3>
                <div class="value">{total_proxima}</div>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;">Licitaciones programadas</p>
            </div>
            <div class="stat-card">
                <h3>Monto Total</h3>
                <div class="value">${(monto_actual + monto_proxima):,.0f}</div>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;">Estimado combinado</p>
            </div>
        </div>
    """
    
    # Sección: Esta Semana
    html += """
        <div class="section">
            <h2>📅 Esta Semana</h2>
    """
    
    if total_actual > 0:
        html += """
            <table>
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Nombre</th>
                        <th>Estado</th>
                        <th>Monto Estimado</th>
                        <th>Fecha Clave</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in df_semana_actual.iterrows():
            nombre_corto = row['Nombre'][:50] + "..." if len(str(row['Nombre'])) > 50 else row['Nombre']
            fecha_clave = row.get('FechaClave', 'N/A')
            if pd.notna(fecha_clave) and isinstance(fecha_clave, pd.Timestamp):
                fecha_str = fecha_clave.strftime('%d/%m/%Y')
            else:
                fecha_str = 'N/A'
            
            html += f"""
                    <tr>
                        <td>{row['CodigoLicitacion']}</td>
                        <td>{nombre_corto}</td>
                        <td>{row.get('Estado', 'N/A')}</td>
                        <td>${row['MontoEstimado']:,.0f}</td>
                        <td>{fecha_str}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
        """
    else:
        html += '<div class="no-data">No hay licitaciones programadas para esta semana.</div>'
    
    html += "</div>"
    
    # Sección: Próxima Semana
    html += """
        <div class="section">
            <h2>📅 Próxima Semana</h2>
    """
    
    if total_proxima > 0:
        html += """
            <table>
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Nombre</th>
                        <th>Estado</th>
                        <th>Monto Estimado</th>
                        <th>Fecha Clave</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in df_proxima_semana.iterrows():
            nombre_corto = row['Nombre'][:50] + "..." if len(str(row['Nombre'])) > 50 else row['Nombre']
            fecha_clave = row.get('FechaClave', 'N/A')
            if pd.notna(fecha_clave) and isinstance(fecha_clave, pd.Timestamp):
                fecha_str = fecha_clave.strftime('%d/%m/%Y')
            else:
                fecha_str = 'N/A'
            
            html += f"""
                    <tr>
                        <td>{row['CodigoLicitacion']}</td>
                        <td>{nombre_corto}</td>
                        <td>{row.get('Estado', 'N/A')}</td>
                        <td>${row['MontoEstimado']:,.0f}</td>
                        <td>{fecha_str}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
        """
    else:
        html += '<div class="no-data">No hay licitaciones programadas para la próxima semana.</div>'
    
    html += """
        </div>
        
        <div class="footer">
            <p><strong>Dirección de Abastecimiento - Red de Salud</strong></p>
            <p>Este es un correo automático. Por favor no responder.</p>
        </div>
    </body>
    </html>
    """
    
    return html

def enviar_correo_outlook(destinatario, nombre_destinatario, asunto, cuerpo_html, credenciales):
    """Envía correo HTML a través de Outlook"""
    msg = MIMEMultipart()
    msg['From'] = credenciales['user']
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo_html, 'html'))

    try:
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(credenciales['user'], credenciales['password'])
        server.sendmail(credenciales['user'], destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return str(e)

# ============== MÓDULO DE ENVÍO DE CORREOS ===================
st.markdown("---")
st.markdown("## 📧 Distribución de Reportes por Correo")

col_email1, col_email2 = st.columns([2, 1])

with col_email1:
    st.markdown("""
    **Funcionalidad de Envío Masivo:**
    - Genera reportes semanales consolidados en formato HTML profesional
    - Envía automáticamente a todos los usuarios de la red de salud
    - Incluye comparativa entre semana actual y próxima semana
    - Utiliza Outlook para el envío directo
    """)

with col_email2:
    st.info(f"👥 {len(USUARIOS_CORREOS)} destinatarios configurados")

# Credenciales
with st.expander("⚙️ Configuración de Correo", expanded=False):
    col_cred1, col_cred2 = st.columns(2)
    
    with col_cred1:
        email_sender = st.text_input(
            "Correo Outlook Remitente",
            placeholder="tu.correo@redsalud.gob.cl",
            help="Correo corporativo de Outlook"
        )
    
    with col_cred2:
        email_password = st.text_input(
            "Contraseña de Aplicación",
            type="password",
            help="Contraseña de aplicación de Outlook (no tu contraseña normal)"
        )

# Botón de envío
if st.button("📧 Enviar Reporte Semanal a Todos los Usuarios", type="primary", use_container_width=True):
    
    if not email_sender or not email_password:
        st.error("⚠️ Por favor ingresa las credenciales de correo en la sección de configuración.")
        st.stop()
    
    credenciales = {
        "user": email_sender,
        "password": email_password
    }
    
    # Preparar datos para el reporte
    df_reporte_actual = df_res[
        (df_res['FechaClave'] >= inicio_actual) & 
        (df_res['FechaClave'] <= fin_actual)
    ].copy()
    
    df_reporte_proxima = df_res[
        (df_res['FechaClave'] >= inicio_proxima) & 
        (df_res['FechaClave'] <= fin_proxima)
    ].copy()
    
    # Barra de progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    enviados = 0
    fallidos = 0
    
    total_usuarios = len(USUARIOS_CORREOS)
    
    for idx, (nombre, email) in enumerate(USUARIOS_CORREOS.items()):
        status_text.text(f"Enviando a {nombre} ({idx + 1}/{total_usuarios})...")
        
        # Generar HTML personalizado
        html_reporte = generar_html_reporte(df_reporte_actual, df_reporte_proxima, nombre)
        
        # Enviar correo
        asunto = f"📄 Reporte Semanal de Licitaciones - {inicio_actual.strftime('%d/%m/%Y')}"
        resultado = enviar_correo_outlook(email, nombre, asunto, html_reporte, credenciales)
        
        if resultado is True:
            enviados += 1
        else:
            fallidos += 1
            st.warning(f"❌ Error enviando a {nombre} ({email}): {resultado}")
        
        # Actualizar progreso
        progress_bar.progress((idx + 1) / total_usuarios)
    
    status_text.empty()
    progress_bar.empty()
    
    # Resumen final
    if fallidos == 0:
        st.success(f"✅ ¡Proceso completado! Se enviaron {enviados} correos exitosamente.")
    else:
        st.warning(f"⚠️ Proceso finalizado: {enviados} enviados, {fallidos} fallidos.")

