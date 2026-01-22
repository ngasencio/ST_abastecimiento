# utils/pdf_generator.py

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime
import tempfile
import os


def generar_pdf_pac(
    df_datos,
    total_proyectos,
    monto_total,
    fig_plotly
):
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "Reporte_PAC_2026.pdf")
    img_path = os.path.join(temp_dir, "grafico_pac.png")

    # Exportar gráfico Plotly a imagen
    fig_plotly.write_image(img_path, width=900, height=400)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    contenido = []

    contenido.append(Paragraph("Reporte Plan Anual de Compras 2026", styles["Title"]))
    contenido.append(Spacer(1, 12))
    contenido.append(
        Paragraph(
            f"Fecha de generación: {datetime.today().strftime('%d-%m-%Y')}",
            styles["Normal"]
        )
    )
    contenido.append(Spacer(1, 20))

    tabla_kpi = Table(
        [
            ["Indicador", "Valor"],
            ["Cantidad de Proyectos", f"{total_proyectos:,}"],
            ["Monto Estimado", f"${monto_total:,.0f}"]
        ],
        colWidths=[220, 180]
    )

    tabla_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT")
    ]))

    contenido.append(Paragraph("Resumen General", styles["Heading2"]))
    contenido.append(tabla_kpi)
    contenido.append(Spacer(1, 20))

    contenido.append(Paragraph("Análisis Mensual", styles["Heading2"]))
    contenido.append(Image(img_path, width=500, height=220))
    contenido.append(Spacer(1, 20))

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
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    contenido.append(Paragraph("Detalle de Proyectos (primeros 20)", styles["Heading2"]))
    contenido.append(tabla_datos)

    doc.build(contenido)

    return pdf_path
