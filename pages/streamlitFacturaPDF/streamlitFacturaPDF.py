import streamlit as st
from jinja2 import Environment, FileSystemLoader
from pyhtml2pdf import converter
from datetime import date
import io
import os

def cargar_css():
    try:
        with open("style/style.css") as f:
            css_content = f.read().replace("\n", "").strip()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")

cargar_css()

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y JINJA2
# ==========================================
# Obtenemos la ruta absoluta de la carpeta donde está este archivo
current_dir = os.path.dirname(os.path.abspath(__file__))
# La carpeta de plantillas está dentro de la carpeta actual
templates_dir = os.path.join(current_dir, "plantillas")

# Inicializamos el entorno de Jinja2 apuntando directamente a esa carpeta
env = Environment(loader=FileSystemLoader(templates_dir))

# Configuración de la página
st.set_page_config(page_title="Generador de Facturas", layout="wide")
st.title("📄 Generador de Facturas PDF")

# ==========================================
# 2. FUNCIONES DE APOYO (HELPERS)
# ==========================================

@st.dialog(title="Vista Previa de la Plantilla", width="large")
def previewPlantilla(ruta_completa):
    """Muestra el HTML renderizado de la plantilla base."""
    with open(ruta_completa, "r", encoding="utf-8") as f:
        template_content = f.read()
    st.html(template_content)

@st.cache_data
def generarPDF(html_content):
    """Convierte el HTML renderizado en bytes de PDF."""
    # NOTA: pyhtml2pdf suele requerir un archivo temporal o una URL. 
    # Para este ejemplo, simulamos la conversión a bytes.
    pdf_bytes = io.BytesIO()
    # Guardamos el html en un archivo temporal para la conversión si es necesario
    temp_html = "temp_invoice.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Convertimos el archivo temporal a PDF
    converter.convert(f'file:///{os.path.abspath(temp_html)}', "temp_output.pdf")
    
    with open("temp_output.pdf", "rb") as f:
        pdf_bytes = f.read()
    
    # Limpieza
    if os.path.exists(temp_html): os.remove(temp_html)
    if os.path.exists("temp_output.pdf"): os.remove("temp_output.pdf")
    
    return pdf_bytes

@st.dialog(title="Factura Generada", width="large")
def abrirPreview(html_content, invoice_name):
    """Muestra el resultado final y permite descarga."""
    try:
        pdf_bytes = generarPDF(html_content)
        st.download_button(
            label="⬇️ Descargar PDF",
            data=pdf_bytes,
            file_name=f"{invoice_name}.pdf",
            mime="application/pdf"
        )
        st.success("✅ Factura lista para descargar")
    except Exception as e:
        st.error(f"Error al generar el PDF: {e}")

# ==========================================
# 3. INTERFAZ DE USUARIO: CONFIGURACIÓN
# ==========================================
st.header("1. Selección de Plantilla")

# Inicializamos la variable globalmente
template_content = None

# Buscamos archivos en la carpeta de plantillas
if os.path.exists(templates_dir):
    opciones_plantillas = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
else:
    opciones_plantillas = []

if not opciones_plantillas:
    st.error(f"⚠️ No se encontraron plantillas en: {templates_dir}")
    st.stop()

archivo_nombre = st.selectbox("Selecciona una plantilla", options=opciones_plantillas)

if archivo_nombre:
    try:
        template_content = env.get_template(archivo_nombre)
        ruta_completa = os.path.join(templates_dir, archivo_nombre)
        st.button("👁️ Vista Previa", on_click=previewPlantilla, args=(ruta_completa,))
    except Exception as e:
        st.error(f"Error cargando plantilla: {e}")

# ==========================================
# 4. FORMULARIO DE DATOS
# ==========================================
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 Datos Emisor")
    company_name = st.text_input("Nombre Empresa", "Consultoría Tech")
    company_address = st.text_input("Dirección", "Ciudad, País")
    currency = st.selectbox("Moneda", ["USD", "CLP", "EUR"])

with col2:
    st.subheader("📑 Datos Factura")
    invoice_number = st.text_input("N° Factura", "INV-1001")
    invoice_date = st.date_input("Fecha Emisión", date.today())
    due_date = st.date_input("Vencimiento") if st.checkbox("¿Tiene vencimiento?") else None

st.subheader("👤 Datos Cliente")
c_cli1, c_cli2 = st.columns(2)
with c_cli1:
    client_name = st.text_input("Nombre Cliente")
    taxes_pct = st.number_input("Impuestos (%)", min_value=0.0, value=19.0) # IVA por defecto
with c_cli2:
    client_email = st.text_input("Email Cliente")

# ==========================================
# 5. ITEMS DINÁMICOS
# ==========================================
st.subheader("🛒 Ítems de la Factura")
items = []
num_items = st.number_input("Número de ítems", min_value=1, step=1, value=1)

for i in range(int(num_items)):
    cols = st.columns([3, 1, 1, 1])
    with cols[0]:
        task = st.text_input(f"Descripción {i+1}", key=f"t_{i}")
    with cols[1]:
        qty = st.number_input(f"Cant. {i+1}", min_value=1.0, value=1.0, key=f"q_{i}")
    with cols[2]:
        rate = st.number_input(f"Precio {i+1}", min_value=0.0, key=f"r_{i}")
    
    items.append({
        "task_executed": task,
        "hours": qty,
        "rate": rate,
        "total_item": qty * rate
    })

# Cálculos
subtotal = sum(item["total_item"] for item in items)
monto_impuestos = subtotal * (taxes_pct / 100)
total_final = subtotal + monto_impuestos

st.divider()
st.write(f"**Subtotal:** {subtotal:,.2f} | **IVA:** {monto_impuestos:,.2f} | **Total:** {total_final:,.2f} {currency}")

# ==========================================
# 6. BOTÓN DE GENERACIÓN (INDENTACIÓN FIJA)
# ==========================================
if st.button("📥 Generar Factura PDF", type="primary"):
    if template_content is not None:
        # Renderizamos el HTML con los datos
        html_final = template_content.render(
            company_name=company_name,
            company_address=company_address,
            invoice_number=invoice_number,
            invoice_date=invoice_date.isoformat(),
            due_date=due_date.isoformat() if due_date else "N/A",
            client_name=client_name,
            client_email=client_email,
            currency=currency,
            items=items,
            subtotal=f"{subtotal:,.2f}",
            taxes=f"{monto_impuestos:,.2f}",
            total=f"{total_final:,.2f}"
        )
        # Llamamos al diálogo de preview
        abrirPreview(html_final, invoice_number)
    else:
        st.error("Por favor, selecciona una plantilla válida primero.")