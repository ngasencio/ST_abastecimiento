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

# ==============================
# PDF GENERATOR - PAC DSSO
# ==============================

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

    # ==============================
    # GENERAR PDF
    # ==============================
    doc.build(contenido)

    return pdf_path
