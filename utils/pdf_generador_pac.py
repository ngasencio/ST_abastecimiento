from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime
import tempfile
import os
from fpdf import FPDF

# ==============================
# PDF GENERATOR - PAC DSSO
# ==============================


def generar_pdf_pac(
    df_datos,
    total_proyectos,
    monto_total,
    fig_plotly
):
    # ==============================
    # PALETA DE COLORES (CSS → PDF)
    # ==============================
    COLOR_PRIMARIO = colors.HexColor("#1A4564")
    COLOR_SECUNDARIO = colors.HexColor("#68B4F3")
    COLOR_FONDO = colors.HexColor("#E7F3FD")
    COLOR_BLANCO = colors.white
    COLOR_GRIS = colors.HexColor("#e0e6ef")

    # ==============================
    # ARCHIVOS TEMPORALES
    # ==============================
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "Reporte_PAC_2026.pdf")
    img_path = os.path.join(temp_dir, "grafico_pac.png")

    # Exportar gráfico Plotly a imagen
    fig_plotly.write_image(img_path, width=900, height=400)

    # ==============================
    # DOCUMENTO PDF
    # ==============================
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TituloPrincipal",
        fontSize=22,
        textColor=COLOR_PRIMARIO,
        alignment=1,
        spaceAfter=14,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="TextoNormal",
        fontSize=10,
        spaceAfter=8
    ))

    contenido = []

    # ==============================
    # TÍTULO
    # ==============================
    contenido.append(
        Paragraph(
            "REPORTE PLAN ANUAL DE COMPRAS 2026",
            styles["TituloPrincipal"]
        )
    )

    contenido.append(
        Paragraph(
            f"Fecha de generación: {datetime.today().strftime('%d-%m-%Y')}",
            styles["TextoNormal"]
        )
    )

    contenido.append(Spacer(1, 14))

    # ==============================
    # HEADER SECCIÓN - RESUMEN
    # ==============================
    contenido.append(
        Table(
            [["Resumen General"]],
            colWidths=[450],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_SECUNDARIO),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
    )

    contenido.append(Spacer(1, 10))

    # ==============================
    # KPI CARDS
    # ==============================
    tabla_kpi = Table(
        [
            ["Cantidad de Proyectos", f"{total_proyectos:,}"],
            ["Monto Estimado", f"${monto_total:,.0f}"],
        ],
        colWidths=[260, 160]
    )

    tabla_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BLANCO),
        ("BOX", (0, 0), (-1, -1), 1.5, COLOR_PRIMARIO),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
        ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, -1), COLOR_PRIMARIO),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    contenido.append(tabla_kpi)
    contenido.append(Spacer(1, 18))

    # ==============================
    # HEADER SECCIÓN - GRÁFICO
    # ==============================
    contenido.append(
        Table(
            [["Análisis Mensual"]],
            colWidths=[450],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_SECUNDARIO),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
    )

    contenido.append(Spacer(1, 10))
    contenido.append(Image(img_path, width=500, height=220))
    contenido.append(Spacer(1, 20))

    # ==============================
    # TABLA DE DATOS
    # ==============================
    df_tabla = (
        df_datos
        .loc[:, ["ID Proyecto", "Departamento_SHORT", "Fecha de Inicio Compra"]]
        .head(20)
    )

    tabla_datos = Table(
        [df_tabla.columns.tolist()] + df_tabla.values.tolist(),
        repeatRows=1
    )

    tabla_datos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    contenido.append(
        Paragraph(
            "<b>Detalle de Proyectos (primeros 20)</b>",
            styles["TextoNormal"]
        )
    )
    contenido.append(tabla_datos)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # --- TÍTULO ---
    pdf.cell(190, 10, "Reporte Plan Anual de Compras 2026", ln=True, align="C")
    pdf.ln(10)
    
    # --- KPIs PRINCIPALES ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(95, 10, f"Total Proyectos: {total_proyectos}", border=1)
    pdf.cell(95, 10, f"Monto Total: ${monto_total:,.0f}", border=1, ln=True)
    pdf.ln(5)

    # --- GRÁFICO ---
    # (Aquí va tu lógica actual para guardar fig_plotly como imagen e insertarla)
    # image_path = "temp_chart.png"
    # fig_plotly.write_image(image_path)
    # pdf.image(image_path, x=10, y=None, w=180)
    # pdf.ln(5)

    # =============================================================================
    # NUEVA SECCIÓN: RESUMEN DE ESTADOS
    # =============================================================================
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "Resumen de Ejecucion Temporal", ln=True)
    pdf.set_font("Arial", "", 10)
    
    # Calculamos el resumen dentro de la función para asegurar consistencia
    resumen = df_datos.groupby("Estado_PAC").agg({
        "ID Proyecto": "count",
        "Suma de Monto Total Ítem Año 2026": "sum"
    }).reset_index()

    # Cabecera de Tabla Resumen
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(70, 8, "Estado", border=1, fill=True)
    pdf.cell(50, 8, "Cant. Proyectos", border=1, fill=True)
    pdf.cell(70, 8, "Monto Estimado", border=1, fill=True, ln=True)

    # Datos de Resumen
    for _, fila in resumen.iterrows():
        pdf.cell(70, 8, str(fila["Estado_PAC"]), border=1)
        pdf.cell(50, 8, str(fila["ID Proyecto"]), border=1)
        pdf.cell(70, 8, f"$ {fila['Suma de Monto Total Ítem Año 2026']:,.0f}", border=1, ln=True)
    
    pdf.ln(10)

    # =============================================================================
    # NUEVA SECCIÓN: DETALLE PENDIENTES DEL MES
    # =============================================================================
    df_mes = df_datos[df_datos["Estado_PAC"] == "🟡 PAC PENDIENTE (Mes Actual)"]
    
    if not df_mes.empty:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 10, "Detalle Proyectos Pendientes (Mes Actual)", ln=True)
        pdf.set_font("Arial", "B", 9)
        
        # Cabeceras detalle
        pdf.cell(30, 8, "ID Proy.", border=1)
        pdf.cell(80, 8, "Subdireccion", border=1)
        pdf.cell(40, 8, "Fecha Inicio", border=1)
        pdf.cell(40, 8, "Monto", border=1, ln=True)
        
        pdf.set_font("Arial", "", 8)
        for _, fila in df_mes.iterrows():
            pdf.cell(30, 7, str(fila["ID Proyecto"]), border=1)
            # Cortar texto si es muy largo
            sub_text = (str(fila["Subdirección"])[:40] + '..') if len(str(fila["Subdirección"])) > 40 else str(fila["Subdirección"])
            pdf.cell(80, 7, sub_text, border=1)
            pdf.cell(40, 7, fila["Fecha de Inicio Compra"].strftime('%d-%m-%Y'), border=1)
            pdf.cell(40, 7, f"$ {fila['Suma de Monto Total Ítem Año 2026']:,.0f}", border=1, ln=True)
    else:
        pdf.set_font("Arial", "I", 10)
        pdf.cell(190, 10, "No hay proyectos pendientes para el mes actual.", ln=True)

    # ==============================
    # GENERAR PDF
    # ==============================
    doc.build(contenido)

    return pdf_path
