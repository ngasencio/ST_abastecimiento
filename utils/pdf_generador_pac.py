from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime
import tempfile
import os

# ==============================
# PDF GENERATOR - PAC 2026
# ==============================

def generar_pdf_pac(df_datos, total_proyectos, monto_total, fig_plotly):
    # 1. Configuración de Colores y Estilos
    COLOR_PRIMARIO = colors.HexColor("#1A4564")
    COLOR_SECUNDARIO = colors.HexColor("#68B4F3")
    COLOR_FONDO = colors.HexColor("#E7F3FD")
    COLOR_GRIS = colors.HexColor("#e0e6ef")
    ANCHO_UTIL = 480  # Ancho total seguro para evitar desbordamientos

    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "Reporte_PAC_2026.pdf")
    img_path = os.path.join(temp_dir, "grafico_pac.png")

    # Exportar gráfico
    fig_plotly.write_image(img_path, width=900, height=400)

    # Crear documento
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    estilo_titulo = ParagraphStyle(
        "Titulo", parent=styles["Heading1"], fontSize=20, 
        textColor=COLOR_PRIMARIO, alignment=1, spaceAfter=20
    )
    estilo_subtitulo = ParagraphStyle(
        "Subtitulo", parent=styles["Heading2"], fontSize=14, 
        textColor=COLOR_PRIMARIO, spaceBefore=15, spaceAfter=10
    )
    estilo_celda = ParagraphStyle("Celda", parent=styles["Normal"], fontSize=8)

    contenido = []

    # ==============================
    # HEADER Y TITULO
    # ==============================
    contenido.append(Paragraph("REPORTE PLAN ANUAL DE COMPRAS 2026", estilo_titulo))
    contenido.append(Paragraph(f"Generado el: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles["Normal"]))
    contenido.append(Spacer(1, 20))

    # ==============================
    # TABLA KPI (RESUMEN GENERAL)
    # ==============================
    tabla_kpi = Table([
        [Paragraph("<b>Cantidad de Proyectos</b>", styles["Normal"]), f"{total_proyectos:,}"],
        [Paragraph("<b>Monto Estimado Total</b>", styles["Normal"]), f"${monto_total:,.0f}"]
    ], colWidths=[300, 180])

    tabla_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 1.5, COLOR_PRIMARIO),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 12),
    ]))
    contenido.append(tabla_kpi)
    contenido.append(Spacer(1, 25))

    # ==============================
    # ANÁLISIS DE ESTADOS (NUEVO)
    # ==============================
    contenido.append(Paragraph("Resumen de Ejecución Temporal", estilo_subtitulo))
    
    resumen = df_datos.groupby("Estado_PAC").agg({
        "ID Proyecto": "count",
        "Suma de Monto Total Ítem Año 2026": "sum"
    }).reset_index()

    datos_resumen = [["Estado", "Cant.", "Monto Estimado"]]
    for _, fila in resumen.iterrows():
        datos_resumen.append([
            fila["Estado_PAC"], 
            str(fila["ID Proyecto"]), 
            f"$ {fila['Suma de Monto Total Ítem Año 2026']:,.0f}"
        ])

    tabla_est = Table(datos_resumen, colWidths=[240, 60, 180])
    tabla_est.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECUNDARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(tabla_est)

    # ==============================
    # GRÁFICO Plotly
    # ==============================
    contenido.append(Paragraph("Análisis de Planificación Mensual", estilo_subtitulo))
    contenido.append(Image(img_path, width=ANCHO_UTIL, height=200))
    contenido.append(Spacer(1, 20))

    # ==============================
    # DETALLE PENDIENTES DEL MES (NUEVO)
    # ==============================
    df_mes = df_datos[df_datos["Estado_PAC"] == "🟡 PAC PENDIENTE (Mes Actual)"].head(15)
    
    if not df_mes.empty:
        contenido.append(Paragraph("Proyectos Pendientes (Mes Actual - Top 15)", estilo_subtitulo))
        
        # Formatear datos para la tabla
        header_pend = ["ID Proy.", "Subdirección", "Fecha Inicio", "Monto"]
        datos_pend = [header_pend]
        
        for _, fila in df_mes.iterrows():
            datos_pend.append([
                str(fila["ID Proyecto"]),
                Paragraph(str(fila["Subdirección"]), estilo_celda), # Paragraph permite salto de línea
                fila["Fecha de Inicio Compra"].strftime('%d-%m-%Y'),
                f"${fila['Suma de Monto Total Ítem Año 2026']:,.0f}"
            ])

        # Anchos: 60 (ID) + 240 (Subdir) + 80 (Fecha) + 100 (Monto) = 480
        tabla_pend = Table(datos_pend, colWidths=[60, 240, 80, 100])
        tabla_pend.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        contenido.append(tabla_pend)
    
    # ==============================
    # TABLA DETALLE GENERAL (Top 20)
    # ==============================
    contenido.append(Paragraph("Detalle General de Proyectos (Top 20)", estilo_subtitulo))
    
    df_detalle = df_datos.loc[:, ["ID Proyecto", "Departamento_SHORT", "Fecha de Inicio Compra"]].head(20)
    # Convertir fechas a string para evitar errores en Table
    df_detalle["Fecha de Inicio Compra"] = df_detalle["Fecha de Inicio Compra"].dt.strftime('%d-%m-%Y')
    
    datos_det = [["ID Proyecto", "Departamento", "Fecha Inicio"]] + df_detalle.values.tolist()
    
    tabla_det = Table(datos_det, colWidths=[100, 280, 100], repeatRows=1)
    tabla_det.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_GRIS),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    
    contenido.append(tabla_det)

    # Construcción final del PDF
    doc.build(contenido)
    return pdf_path