"""Genera el informe preliminar del avance (ejercicios 1 a 4)."""

from __future__ import annotations

from pathlib import Path
import sys
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from control_calidad import build_quality_checklist, save_quality_checklist
from descarga import build_inventory


OUTPUT_DIR = ROOT / "outputs" / "pdf"
OUTPUT_PATH = OUTPUT_DIR / "Informe_preliminar_avance_lab4.pdf"


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#52616B"))
    canvas.drawString(document.leftMargin, 0.45 * inch, "Laboratorio 4 - Avance (ejercicios 1 a 4)")
    canvas.drawRightString(letter[0] - document.rightMargin, 0.45 * inch, f"Página {document.page}")
    canvas.restoreState()


def main() -> Path:
    inventory = build_inventory()
    checklist = build_quality_checklist(inventory)
    save_quality_checklist(checklist)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0B3C5D"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    subtitle = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        textColor=colors.HexColor("#52616B"),
        alignment=TA_CENTER,
        leading=15,
        spaceAfter=22,
    )
    heading = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0B3C5D"),
        spaceBefore=13,
        spaceAfter=7,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        spaceAfter=8,
    )
    small = ParagraphStyle(
        "ReportSmall",
        parent=body,
        fontSize=8,
        leading=10,
    )

    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        rightMargin=0.68 * inch,
        leftMargin=0.68 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title="Informe preliminar - Laboratorio 4",
        author="Equipo Laboratorio 4",
    )
    story = [
        paragraph("Laboratorio 4: análisis geoespacial de cianobacterias", title),
        paragraph("Informe preliminar del avance - Ejercicios 1 a 4", subtitle),
        paragraph("Propósito del avance", heading),
        paragraph(
            "El objetivo es construir una cadena reproducible para analizar la señal de cianobacteria en los lagos de Amatitlán y Atitlán con 11 fechas oficiales Sentinel-2 por lago. El alcance de este documento se limita al avance: conexión, obtención de datos, índices espectrales y análisis temporal inicial.",
            body,
        ),
        paragraph("1. Conexión con Sentinel-2", heading),
        paragraph(
            "El notebook se conecta a Copernicus Data Space Ecosystem mediante openEO y autenticación OIDC. Las credenciales no se guardan en el repositorio. La colección empleada es Sentinel-2 L2A y las rutas se resuelven desde la raíz del proyecto para facilitar la reproducción en otro equipo.",
            body,
        ),
        paragraph("2. Datos, área de estudio y control de trazabilidad", heading),
        paragraph(
            "El inventario contiene 22 escenas oficiales: 11 para Amatitlán (2025-01-28 a 2026-06-19) y 11 para Atitlán (2025-01-18 a 2026-07-22). Para NDVI y NDWI se solicitan únicamente B03, B04 y B08. Cada fila del inventario registra fecha, satélite, nubosidad reportada, ruta y estado de descarga.",
            body,
        ),
        paragraph("3. Índices y manejo de valores inválidos", heading),
        paragraph(
            "NDVI se calcula como (B08 - B04) / (B08 + B04) y NDWI como (B03 - B08) / (B03 + B08). Las divisiones por cero, nodata y píxeles excluidos por máscara se convierten en valores faltantes para no inflar promedios. La cianobacteria se debe estimar mediante un producto numérico del algoritmo CyanoLakes Chlorophyll-a NDCI L1C; la salida RGB del visualizador no debe utilizarse como variable cuantitativa.",
            body,
        ),
        paragraph("4. Análisis temporal previsto", heading),
        paragraph(
            "La tabla de métricas debe resumir píxeles válidos, cobertura, promedio, mediana y desviación estándar por lago y fecha. Se define una fecha crítica como un máximo local cuyo promedio es igual o superior al percentil 75 de su propio lago. Los factores ambientales como lluvia, temperatura, nutrientes y viento se discutirán como hipótesis, no como causalidad demostrada por las imágenes.",
            body,
        ),
        paragraph("Estado de control de calidad", heading),
    ]

    rows = [[
        paragraph("Criterio", small),
        paragraph("Estado", small),
        paragraph("Evidencia", small),
    ]]
    for row in checklist.itertuples(index=False):
        rows.append([
            paragraph(row.criterio, small),
            paragraph(row.estado, small),
            paragraph(row.evidencia, small),
        ])
    table = Table(rows, colWidths=[2.05 * inch, 0.78 * inch, 3.47 * inch], repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3C5D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for index, status in enumerate(checklist["estado"], start=1):
        table_style.append(("TEXTCOLOR", (1, index), (1, index), colors.HexColor("#1B5E20") if status == "cumple" else colors.HexColor("#9A4D00")))
    table.setStyle(TableStyle(table_style))
    story.extend([table, Spacer(1, 10)])

    pending_actions = checklist.loc[checklist["estado"] != "cumple", ["criterio", "accion_requerida"]]
    story.append(paragraph("Acciones requeridas antes de interpretar resultados", heading))
    for action in pending_actions.itertuples(index=False):
        story.append(paragraph(f"<b>{escape(action.criterio)}:</b> {escape(action.accion_requerida)}", small))
        story.append(Spacer(1, 4))

    pending = int((checklist["estado"] != "cumple").sum())
    story.extend([
        paragraph("Lectura del estado actual", heading),
        paragraph(
            f"La revisión automática identifica {pending} requisito(s) pendiente(s) en esta copia del repositorio. Por integridad académica, el informe no presenta promedios, picos ni mapas como si ya estuvieran verificados. Cuando estén disponibles los rasteres B03/B04/B08, el producto numérico de cianobacteria y la máscara del lago, el notebook genera las métricas y las figuras correspondientes.",
            body,
        ),
        paragraph("Limitaciones", heading),
        paragraph(
            "Las imágenes satelitales entregan una estimación indirecta de la condición del agua. Nubes, cobertura parcial, píxeles mixtos, ausencia de una máscara precisa y límites del modelo pueden afectar los valores. Cualquier conclusión ambiental debe indicar la figura o tabla que la respalda y separar observaciones de hipótesis.",
            body,
        ),
        paragraph("Referencias", heading),
        paragraph(
            "Sentinel Hub Custom Scripts. CyanoLakes Chlorophyll-a NDCI L1C. https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/cyanobacteria_chla_ndci_l1c/", small,
        ),
        paragraph(
            "Kravitz, J. & Matthews, M. (2020). Chlorophyll-a for cyanobacteria blooms from Sentinel-2. CyanoLakes.", small,
        ),
    ])
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT_PATH


if __name__ == "__main__":
    print(main())
