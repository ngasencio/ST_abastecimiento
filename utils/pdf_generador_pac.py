from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime
import tempfile
import os

from fpdf import FPDF
import pandas as pd
import tempfile
import os

class PAC_PDF(FPDF):
    def header(self):
        # Encabezado azul similar al dashboard
        self.set_fill_color(19, 138, 236)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'Reporte Planificación PAC 2026', ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f'Generado el: {pd.Timestamp.now().strftime("%d-%m-%Y %H:%M")}', ln=True, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', align='C')

def generar_pdf_pac(df_datos, total_proyectos, monto_total, fig_plotly):
    pdf = PAC_PDF()
    pdf.add_page()
    
    # --- SECCIÓN KPIs ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 10, f"Total Proyectos: {total_proyectos}", border=1, align='C')
    pdf.cell(5, 10, "") # Espacio
    pdf.cell(90, 10, f"Monto Total: ${monto_total:,.0f}", border=1, align='C')
    pdf.ln(20)

    # --- SECCIÓN GRÁFICO ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        fig_plotly.write_image(tmpfile.name)
        pdf.image(tmpfile.name, x=10, y=None, w=190)
        tmp_img_path = tmpfile.name
    
    pdf.ln(10)
    if os.path.exists(tmp_img_path):
        os.remove(tmp_img_path)

    # --- SECCIÓN TABLA DETALLE ---
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Detalle de Planificación", ln=True)
    pdf.ln(5)

    # Encabezados de tabla
    pdf.set_font('Arial', 'B', 8)
    pdf.set_fill_color(230, 230, 230)
    columnas = ['ID Proyecto', 'Nombre ítem', 'Responsable', 'Fecha Inicio', 'Monto']
    anchos = [35, 60, 40, 25, 30]
    
    for i, col in enumerate(columnas):
        pdf.cell(anchos[i], 8, col, border=1, fill=True, align='C')
    pdf.ln()

    # Filas de la tabla
    pdf.set_font('Arial', '', 7)
    for _, fila in df_datos.iterrows():
        # Formatear datos antes de escribir
        fecha_str = fila['Fecha de Inicio Compra'].strftime('%d-%m-%Y') if pd.notnull(fila['Fecha de Inicio Compra']) else "-"
        monto_str = f"${fila['Suma de Monto Total Ítem Año 2026']:,.0f}"
        
        # Escribir celdas (usamos multi_cell o truncado para que no se desborde el texto largo)
        pdf.cell(anchos[0], 7, str(fila['ID Proyecto'])[:20], border=1)
        pdf.cell(anchos[1], 7, str(fila['Nombre ítem'])[:40], border=1)
        pdf.cell(anchos[2], 7, str(fila['Nombre responsable'])[:25], border=1)
        pdf.cell(anchos[3], 7, fecha_str, border=1, align='C')
        pdf.cell(anchos[4], 7, monto_str, border=1, align='R')
        pdf.ln()

    # Guardar en archivo temporal para retornar
    output_path = "reporte_temp.pdf"
    pdf.output(output_path)
    return output_path