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

# Importación de datos
import api.LI_data_loader as loader
cargar_css()

# ============== CONFIGURACIÓN DE PÁGINA ===================
st.set_page_config(
    page_title="Dashboard Licitaciones 2026",
    page_icon="📄",
    layout="wide"
)



# ============== CARGA DE DATOS ===================
@st.cache_data
def obtener_datos():
    df_res, df_det = loader.cargar_maestros()
    return df_res, df_det

try:
    df_MaestroLI_Resumen, df_MaestroLI_Detalle = obtener_datos()
    
    if df_MaestroLI_Resumen.empty:
        st.error("No se encontraron datos. Ejecuta el actualizador primero.")
        st.stop()
    else:
        st.success(f"Datos cargados: {len(df_MaestroLI_Resumen)} licitaciones disponibles.")
        
except Exception as e:
    st.error(f"Ocurrió un error en la carga: {e}")
    st.stop()

# ============== DEFINIR DF ===================
df_res = df_MaestroLI_Resumen.copy()
df_det = df_MaestroLI_Detalle.copy()

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

# ============== FUNCIONES AUXILIARES ===================

def obtener_semana_actual():
    """Retorna el inicio y fin de la semana actual (lunes a domingo)"""
    hoy = pd.Timestamp.now().normalize()
    inicio_semana = hoy - pd.Timedelta(days=hoy.weekday())  # Lunes
    fin_semana = inicio_semana + pd.Timedelta(days=6)  # Domingo
    return inicio_semana, fin_semana

def obtener_proxima_semana():
    """Retorna el inicio y fin de la próxima semana"""
    inicio_actual, _ = obtener_semana_actual()
    inicio_proxima = inicio_actual + pd.Timedelta(days=7)
    fin_proxima = inicio_proxima + pd.Timedelta(days=6)
    return inicio_proxima, fin_proxima

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

# ============== NORMALIZACIÓN DE DATOS ===================
for col in ["Estado", "C_Usuario", "C_Unidad"]:
    if col in df_res.columns:
        df_res[col] = df_res[col].astype(str).str.strip()

# Normalización de fechas
columnas_fechas = [
    "FechaCreacion", "FechaPublicacion", "FechaCierre", 
    "FechaAdjudicacion", "FechaEstimadaFirma", "FechaInicioContrato"
]

for col in columnas_fechas:
    if col in df_res.columns:
        df_res[col] = pd.to_datetime(df_res[col], errors='coerce', dayfirst=True)

# Crear columna FechaClave (fecha más cercana) para df_res
def obtener_fecha_mas_cercana(row):
    fechas_validas = []
    for col in columnas_fechas:
        if col in row.index and pd.notna(row[col]):
            fechas_validas.append(row[col])
    return min(fechas_validas) if fechas_validas else pd.NaT

df_res['FechaClave'] = df_res.apply(obtener_fecha_mas_cercana, axis=1)

# ============== HEADER ===================
st.markdown("""
    <div style="
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #138AEC 0%, #3E9FEF 100%);
        color: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(19, 138, 236, 0.3);
    ">
        <div style="font-size: 32px; font-weight: 800; margin-bottom: 8px;">
            📄 Dashboard de Licitaciones 2026
        </div>
        <div style="font-size: 16px; opacity: 0.95;">
            Gestión y seguimiento semanal de licitaciones - Red de Salud
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============== FILTRO DE VISTA SEMANAL ===================
st.markdown("## 📅 Filtro de Vista Semanal")

col_filtro1, col_filtro2, col_filtro3 = st.columns([2, 2, 1])

with col_filtro1:
    vista_semanal = st.selectbox(
        "Seleccionar Vista",
        ["Todas las Licitaciones", "Esta Semana", "Próxima Semana", "Esta Semana + Próxima Semana"],
        index=0
    )

with col_filtro2:
    inicio_actual, fin_actual = obtener_semana_actual()
    inicio_proxima, fin_proxima = obtener_proxima_semana()
    
    if vista_semanal == "Esta Semana":
        st.info(f"📆 {inicio_actual.strftime('%d/%m/%Y')} - {fin_actual.strftime('%d/%m/%Y')}")
    elif vista_semanal == "Próxima Semana":
        st.info(f"📆 {inicio_proxima.strftime('%d/%m/%Y')} - {fin_proxima.strftime('%d/%m/%Y')}")
    elif vista_semanal == "Esta Semana + Próxima Semana":
        st.info(f"📆 {inicio_actual.strftime('%d/%m/%Y')} - {fin_proxima.strftime('%d/%m/%Y')}")

# ============== FILTROS ADICIONALES ===================
st.markdown("### 🔍 Filtros Adicionales")

col1, col2, col3, col4 = st.columns(4)

df_cascada = df_res.copy()

# Filtro Estado
with col1:
    opciones_estado = sorted(df_cascada["Estado"].dropna().unique())
    estado_sel = st.multiselect("📌 Estado", opciones_estado, placeholder="Todos")

if estado_sel:
    df_cascada = df_cascada[df_cascada["Estado"].isin(estado_sel)]

# Filtro Usuario
with col2:
    opciones_usuario = sorted(df_cascada["C_Usuario"].dropna().unique())
    usuario_sel = st.multiselect("👤 Usuario", opciones_usuario, placeholder="Todos")

if usuario_sel:
    df_cascada = df_cascada[df_cascada["C_Usuario"].isin(usuario_sel)]

# Filtro Unidad
with col3:
    opciones_unidad = sorted(df_cascada["C_Unidad"].dropna().unique())
    unidad_sel = st.multiselect("🏢 Unidad", opciones_unidad, placeholder="Todos")

if unidad_sel:
    df_cascada = df_cascada[df_cascada["C_Unidad"].isin(unidad_sel)]

# ============== APLICAR FILTROS ===================
df_res_filtrado = df_res.copy()

if estado_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["Estado"].isin(estado_sel)]
if usuario_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["C_Usuario"].isin(usuario_sel)]
if unidad_sel:
    df_res_filtrado = df_res_filtrado[df_res_filtrado["C_Unidad"].isin(unidad_sel)]

# La columna FechaClave ya existe en df_res, solo copiamos el dataframe filtrado
# (ya incluye la columna FechaClave porque se copia de df_res)

# Aplicar filtro semanal
if vista_semanal == "Esta Semana":
    df_res_filtrado = df_res_filtrado[
        (df_res_filtrado['FechaClave'] >= inicio_actual) & 
        (df_res_filtrado['FechaClave'] <= fin_actual)
    ]
elif vista_semanal == "Próxima Semana":
    df_res_filtrado = df_res_filtrado[
        (df_res_filtrado['FechaClave'] >= inicio_proxima) & 
        (df_res_filtrado['FechaClave'] <= fin_proxima)
    ]
elif vista_semanal == "Esta Semana + Próxima Semana":
    df_res_filtrado = df_res_filtrado[
        (df_res_filtrado['FechaClave'] >= inicio_actual) & 
        (df_res_filtrado['FechaClave'] <= fin_proxima)
    ]

# Sincronizar con detalle
df_det_filtrado = df_det[df_det["CodigoLicitacion"].isin(df_res_filtrado["CodigoLicitacion"])]

# ============== KPIs ===================
st.markdown("## 📈 Resumen Ejecutivo")

c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

with c_kpi1:
    total_lic_general = df_res["CodigoLicitacion"].nunique()
    total_lic_filtrado = df_res_filtrado["CodigoLicitacion"].nunique()
    porcentaje_lic = (total_lic_filtrado / total_lic_general) * 100 if total_lic_general > 0 else 0
    
    st.metric(
        "📋 Total Licitaciones",
        f"{total_lic_filtrado:,}",
        f"{porcentaje_lic:.1f}% del total"
    )

with c_kpi2:
    monto_total_gral = df_res["MontoEstimado"].sum()
    monto_total_filt = df_res_filtrado["MontoEstimado"].sum()
    porcentaje_monto = (monto_total_filt / monto_total_gral) * 100 if monto_total_gral > 0 else 0
    
    st.metric(
        "💰 Monto Estimado",
        f"${monto_total_filt:,.0f}",
        f"{porcentaje_monto:.1f}% del total"
    )

with c_kpi3:
    total_items = df_det_filtrado['Cantidad'].sum() if 'Cantidad' in df_det_filtrado.columns else 0
    st.metric(
        "📦 Total Items",
        f"{int(total_items):,}"
    )

with c_kpi4:
    estados_criticos = df_res_filtrado[df_res_filtrado['Estado'].str.contains('Publicada|Cierre', case=False, na=False)]
    st.metric(
        "⚠️ Estados Críticos",
        f"{len(estados_criticos)}"
    )

# ============== COMPARATIVA SEMANAL ===================
st.markdown("---")
st.markdown("## 📊 Comparativa Semanal")

col_comp1, col_comp2 = st.columns(2)

# Esta Semana
df_esta_semana = df_res[
    (df_res['FechaClave'] >= inicio_actual) & 
    (df_res['FechaClave'] <= fin_actual)
]

# Próxima Semana
df_proxima_semana = df_res[
    (df_res['FechaClave'] >= inicio_proxima) & 
    (df_res['FechaClave'] <= fin_proxima)
]

with col_comp1:
    st.markdown("### 📅 Esta Semana")
    st.metric("Licitaciones", len(df_esta_semana))
    st.metric("Monto Total", f"${df_esta_semana['MontoEstimado'].sum():,.0f}")
    
    if len(df_esta_semana) > 0:
        fig_esta = px.pie(
            df_esta_semana,
            names='Estado',
            title='Distribución por Estado',
            hole=0.4
        )
        fig_esta.update_layout(height=300)
        st.plotly_chart(fig_esta, use_container_width=True)

with col_comp2:
    st.markdown("### 📅 Próxima Semana")
    st.metric("Licitaciones", len(df_proxima_semana))
    st.metric("Monto Total", f"${df_proxima_semana['MontoEstimado'].sum():,.0f}")
    
    if len(df_proxima_semana) > 0:
        fig_proxima = px.pie(
            df_proxima_semana,
            names='Estado',
            title='Distribución por Estado',
            hole=0.4
        )
        fig_proxima.update_layout(height=300)
        st.plotly_chart(fig_proxima, use_container_width=True)

# ============== TABLA DE DATOS ===================
st.markdown("---")
st.markdown("## 📋 Detalle de Licitaciones")

# Ordenar por fecha clave
df_res_filtrado_sorted = df_res_filtrado.sort_values(by='FechaClave', ascending=True, na_position='last')

# Preparar columnas para mostrar
columnas_mostrar = ['CodigoLicitacion', 'Nombre', 'Estado', 'MontoEstimado', 'C_Usuario', 'C_Unidad', 'FechaClave']
columnas_disponibles = [col for col in columnas_mostrar if col in df_res_filtrado_sorted.columns]

with st.expander("🔍 Ver Tabla Completa", expanded=True):
    st.dataframe(
        df_res_filtrado_sorted[columnas_disponibles].style.format({
            "MontoEstimado": "${:,.0f}",
            "FechaClave": lambda t: t.strftime("%d/%m/%Y") if pd.notna(t) else "-"
        }, na_rep="-"),
        height=400,
        use_container_width=True
    )

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

# ============== ANÁLISIS LEAN & OKR ===================
st.markdown("---")
st.markdown("## ⏱️ Análisis de Flujo de Valor (Lean VSM)")

df_lean = df_res_filtrado.copy()

# Cálculo de Lead Times
df_lean['LT_Total'] = (df_lean['FechaInicioContrato'] - df_lean['FechaCreacion']).dt.days
df_lean['T_Prep'] = (df_lean['FechaPublicacion'] - df_lean['FechaCreacion']).dt.days
df_lean['T_Mercado'] = (df_lean['FechaCierre'] - df_lean['FechaPublicacion']).dt.days
df_lean['T_Evaluacion'] = (df_lean['FechaAdjudicacion'] - df_lean['FechaCierre']).dt.days
df_lean['T_Formalizacion'] = (df_lean['FechaInicioContrato'] - df_lean['FechaAdjudicacion']).dt.days

# Limpieza
cols_tiempos = ['LT_Total', 'T_Prep', 'T_Mercado', 'T_Evaluacion', 'T_Formalizacion']
for col in cols_tiempos:
    if col in df_lean.columns:
        df_lean[col] = df_lean[col].apply(lambda x: x if x >= 0 else np.nan)

# OKRs
st.subheader("🎯 Estado de OKRs Operacionales")

licitaciones_cerradas = df_lean.dropna(subset=['LT_Total'])
lt_promedio = licitaciones_cerradas['LT_Total'].mean() if not licitaciones_cerradas.empty else 0

tasa_adjudicacion = 0
if len(df_lean) > 0:
    adjudicadas = df_lean[df_lean['Estado'].str.contains('Adjudicada', case=False, na=False)].shape[0]
    tasa_adjudicacion = (adjudicadas / len(df_lean)) * 100

okr1, okr2, okr3 = st.columns(3)

with okr1:
    st.markdown("**O1: Agilidad del Proceso**")
    st.metric(
        label="Lead Time Promedio",
        value=f"{lt_promedio:.1f} días",
        delta="-5 días (Meta)" if lt_promedio > 0 else None,
        delta_color="inverse"
    )

with okr2:
    st.markdown("**O2: Eficacia de Licitación**")
    st.metric(
        label="Tasa de Adjudicación",
        value=f"{tasa_adjudicacion:.1f}%",
        delta="vs 85% (Meta)"
    )

with okr3:
    st.markdown("**O3: Eficiencia Administrativa**")
    total_items_lean = df_det_filtrado['Cantidad'].sum() if 'Cantidad' in df_det_filtrado.columns else 1
    monto_total_lean = df_res_filtrado['MontoEstimado'].sum()
    ratio_valor = monto_total_lean / total_items_lean if total_items_lean > 0 else 0
    
    st.metric(
        label="Valor por Item",
        value=f"${ratio_valor:,.0f}"
    )

# Visualizaciones Lean
if not licitaciones_cerradas.empty and 'Tipo' in licitaciones_cerradas.columns:
    st.markdown("### ⏳ Desglose de Tiempos por Tipo")
    
    df_melt = licitaciones_cerradas.groupby('Tipo')[['T_Prep', 'T_Mercado', 'T_Evaluacion', 'T_Formalizacion']].mean().reset_index()
    df_melt = df_melt.melt(id_vars='Tipo', var_name='Etapa', value_name='Días')
    
    nombres_etapa = {
        'T_Prep': '1. Preparación',
        'T_Mercado': '2. Mercado',
        'T_Evaluacion': '3. Evaluación',
        'T_Formalizacion': '4. Formalización'
    }
    df_melt['Etapa'] = df_melt['Etapa'].map(nombres_etapa)
    
    fig_lt = px.bar(
        df_melt,
        x='Tipo',
        y='Días',
        color='Etapa',
        title="Lead Time por Etapas",
        text_auto='.1f',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_lt.update_layout(template="plotly_white", height=400)
    st.plotly_chart(fig_lt, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #6c757d; padding: 20px;">
        <p><strong>Dashboard de Licitaciones 2026</strong></p>
        <p>Dirección de Abastecimiento - Red de Salud</p>
        <p style="font-size: 12px;">Desarrollado con Streamlit | Última actualización: {}</p>
    </div>
""".format(pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)


# ==============================================================================
# 1. CONFIGURACIÓN Y CARGA DE DATOS
# ==============================================================================
def app(df_res_filtrado):
    st.markdown("## 📊 Tablero de Control de Licitaciones (Enfoque Lean)")
    st.markdown("Monitorización del flujo de valor, lead times y próximos hitos críticos.")

    # --- A. PREPROCESAMIENTO DE DATOS ---
    # 1. Normalización de Fechas (ISO a Datetime)
    cols_fechas = [
        "FechaCreacion", "FechaPublicacion", "FechaCierre", 
        "FechaAdjudicacion", "FechaInicioContrato", "FechaEstimadaFirma"
    ]
    
    for col in cols_fechas:
        if col in df_res_filtrado.columns:
            # Coerce maneja errores convirtiéndolos en NaT (Not a Time)
            df_res_filtrado[col] = pd.to_datetime(df_res_filtrado[col], errors='coerce')

    # 2. Normalización de Usuarios (C_Usuario)
    if "C_Usuario" in df_res_filtrado.columns:
        df_res_filtrado["C_Usuario"] = df_res_filtrado["C_Usuario"].astype(str).str.upper().str.strip()
    else:
        df_res_filtrado["C_Usuario"] = "SIN ASIGNAR"

    # 3. Lógica de "Próximo Hito" (Determinación de Fecha Clave)
    now = pd.Timestamp.now()
    
    def obtener_fecha_clave(row):
        # Lógica: Busca la primera fecha futura en el flujo del proceso
        # Flujo: Cierre -> Adjudicación -> Firma -> Inicio
        if pd.notna(row['FechaCierre']) and row['FechaCierre'] >= now:
            return row['FechaCierre'], "🔴 Por Cerrar"
        elif pd.notna(row['FechaAdjudicacion']) and row['FechaAdjudicacion'] >= now:
            return row['FechaAdjudicacion'], "🟡 Por Adjudicar"
        elif pd.notna(row['FechaEstimadaFirma']) and row['FechaEstimadaFirma'] >= now:
            return row['FechaEstimadaFirma'], "🔵 Por Firmar"
        elif pd.notna(row['FechaInicioContrato']) and row['FechaInicioContrato'] >= now:
            return row['FechaInicioContrato'], "🟢 Por Iniciar"
        else:
            return pd.NaT, "⚪ Histórico/Vencido"

    # Aplicamos la lógica y separamos en dos columnas
    df_res_filtrado[['FechaClave', 'EstadoFlujo']] = df_res_filtrado.apply(
        lambda row: pd.Series(obtener_fecha_clave(row)), axis=1
    )

    # ==============================================================================
    # 2. INDICADORES LEAN (LEAD TIMES & FLUJO)
    # ==============================================================================
    # Basado en Lean: "El tiempo total que un cliente espera... (Lead Time)" [cite: 991]
    
    st.markdown("### ⏱️ Indicadores de Flujo (Lead Times)")
    
    # Cálculo de Lead Times (Días)
    # Lead Time Administrativo: Creación a Publicación
    df_res_filtrado['LT_Admin'] = (df_res_filtrado['FechaPublicacion'] - df_res_filtrado['FechaCreacion']).dt.days
    # Lead Time Mercado: Publicación a Cierre
    df_res_filtrado['LT_Mercado'] = (df_res_filtrado['FechaCierre'] - df_res_filtrado['FechaPublicacion']).dt.days
    # Lead Time Resolución: Cierre a Adjudicación
    df_res_filtrado['LT_Resolucion'] = (df_res_filtrado['FechaAdjudicacion'] - df_res_filtrado['FechaCierre']).dt.days

    # Métricas Promedio
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_resolucion = df_res_filtrado['LT_Resolucion'].mean()
        st.metric("Ciclo de Resolución", f"{avg_resolucion:.1f} días", help="Promedio días entre Cierre y Adjudicación")
    with col2:
        pendientes_adjudicar = len(df_res_filtrado[df_res_filtrado['EstadoFlujo'] == "🟡 Por Adjudicar"])
        st.metric("Cola de Adjudicación", f"{pendientes_adjudicar}", delta_color="inverse", help="Licitaciones cerradas esperando adjudicación")
    with col3:
        prox_cierre = len(df_res_filtrado[df_res_filtrado['EstadoFlujo'] == "🔴 Por Cerrar"])
        st.metric("Cierres Próximos", f"{prox_cierre}", help="Licitaciones activas en mercado")
    with col4:
        total_monto = df_res_filtrado['MontoEstimado'].sum()
        st.metric("Volumen en Juego", f"${total_monto:,.0f}")

    # ==============================================================================
    # 3. GESTIÓN VISUAL Y PRÓXIMOS EVENTOS
    # ==============================================================================
    # Basado en Lean: "Hacer visibles los problemas" y "Control Visual" [cite: 748, 968]
    
    st.divider()
    st.markdown("### 📅 Agenda de Prioridades (Semanal)")
    
    # Filtros de tiempo para "Esta semana" y "Próxima semana"
    hoy = pd.Timestamp.now().normalize()
    fin_esta_semana = hoy + pd.Timedelta(days=(6 - hoy.weekday()))
    fin_prox_semana = fin_esta_semana + pd.Timedelta(days=7)
    
    # Crear un dataframe "Melted" para tener todos los eventos en una sola columna de fecha
    # Esto permite ver si cierra o se adjudica en la misma vista
    df_eventos = df_res_filtrado.melt(
        id_vars=['CodigoLicitacion', 'Nombre', 'C_Usuario', 'Estado'], 
        value_vars=['FechaCierre', 'FechaAdjudicacion', 'FechaEstimadaFirma'],
        var_name='TipoEvento', 
        value_name='FechaEvento'
    ).dropna(subset=['FechaEvento'])
    
    # Filtrar eventos próximos
    df_eventos_prox = df_eventos[
        (df_eventos['FechaEvento'] >= hoy) & 
        (df_eventos['FechaEvento'] <= fin_prox_semana)
    ].sort_values('FechaEvento')

    # Visualización por Comprador (Carga de trabajo)
    if not df_eventos_prox.empty:
        col_graf, col_ag = st.columns([1, 2])
        
        with col_graf:
            st.markdown("**Carga de Trabajo Próxima (Eventos)**")
            fig_carga = px.bar(
                df_eventos_prox, 
                x="C_Usuario", 
                color="TipoEvento",
                title="Eventos por Comprador (Próx. 14 días)",
                labels={"count": "Cantidad de Eventos"},
                color_discrete_map={
                    "FechaCierre": "#e74c3c",       # Rojo (Urgente)
                    "FechaAdjudicacion": "#f1c40f", # Amarillo (Proceso)
                    "FechaEstimadaFirma": "#2ecc71" # Verde (Finalización)
                }
            )
            fig_carga.update_layout(xaxis_title=None, showlegend=True)
            st.plotly_chart(fig_carga, use_container_width=True)
            
        with col_ag:
            st.markdown("**Detalle de Próximos Vencimientos**")
            st.dataframe(
                df_eventos_prox[['FechaEvento', 'CodigoLicitacion', 'TipoEvento', 'C_Usuario', 'Nombre']].style.format({
                    "FechaEvento": lambda t: t.strftime("%d-%m-%Y")
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "TipoEvento": st.column_config.TextColumn("Hito", help="Cierre, Adjudicación o Firma"),
                    "C_Usuario": "Responsable",
                    "CodigoLicitacion": "ID Licitación"
                }
            )
    else:
        st.info("✅ No hay eventos críticos (Cierres o Adjudicaciones) programados para los próximos 14 días.")

    # ==============================================================================
    # 4. TABLA MAESTRA DETALLADA
    # ==============================================================================
    st.markdown("---")
    st.markdown("## 📋 Panel de Control de Procesos (Gemba)")
    
    # Ordenar por fecha clave (lo más urgente arriba)
    df_sorted = df_res_filtrado.sort_values(by='FechaClave', ascending=True, na_position='last')
    
    # Columnas a mostrar
    cols_view = [
        'EstadoFlujo', 'FechaClave', 'CodigoLicitacion', 'Nombre', 
        'MontoEstimado', 'C_Usuario', 'Tipo', 'Estado'
    ]
    
    # Filtro rápido por estado de flujo
    filtro_estado = st.multiselect(
        "Filtrar por Etapa del Proceso:",
        options=["🔴 Por Cerrar", "🟡 Por Adjudicar", "🔵 Por Firmar", "🟢 Por Iniciar"],
        default=["🔴 Por Cerrar", "🟡 Por Adjudicar"]
    )
    
    if filtro_estado:
        df_sorted = df_sorted[df_sorted['EstadoFlujo'].isin(filtro_estado)]

    st.dataframe(
        df_sorted[cols_view],
        use_container_width=True,
        hide_index=True,
        column_config={
            "MontoEstimado": st.column_config.NumberColumn("Monto", format="$ %,.0f"),
            "FechaClave": st.column_config.DateColumn(
                "Próx. Hito", 
                format="DD/MM/YYYY",
                help="Fecha del próximo evento crítico"
            ),
            "EstadoFlujo": st.column_config.TextColumn("Urgencia", help="Estado calculado según fechas"),
            "C_Usuario": "Comprador",
            "CodigoLicitacion": "ID"
        },
        height=500
    )

    # Nota sobre metodología Lean
    with st.expander("📘 Referencia Metodológica Lean"):
        st.markdown("""
        * **Lead Time (Tiempo de Respuesta)[cite: 991]:** Tiempo total que transcurre desde que se crea la necesidad hasta que se resuelve (Adjudicación). Reducir este tiempo es clave para el flujo.
        * **Control Visual[cite: 968]:** El uso de semáforos (🔴🟡🟢) permite identificar desviaciones del estándar de manera inmediata.
        * **Heijunka (Nivelación)[cite: 797]:** El gráfico de carga por comprador ayuda a nivelar el trabajo y evitar cuellos de botella en personas específicas.
        """)

# Para ejecutar independientemente
# if __name__ == "__main__":
#     # Cargar datos dummy para prueba si es necesario
#     # app(df)