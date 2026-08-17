"""Genera el informe final integrado del Laboratorio 4."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tablas"
FIGURES = ROOT / "outputs" / "figuras"
OUTPUT_DIR = ROOT / "outputs" / "pdf"
OUTPUT_PATH = OUTPUT_DIR / "Informe_final_analisis_cianobacterias.pdf"


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def number(value: float, decimals: int = 2) -> str:
    return f"{float(value):.{decimals}f}"


def image_if_available(path: Path, width: float, height: float) -> Image | None:
    if not path.exists():
        return None
    graphic = Image(str(path))
    graphic._restrictSize(width, height)
    graphic.hAlign = "CENTER"
    return graphic


def footer(canvas, document=None) -> None:
    left_margin = document.leftMargin if document is not None else .65 * inch
    right_margin = document.rightMargin if document is not None else .65 * inch
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#52616B"))
    canvas.drawString(left_margin, 0.42 * inch, "Laboratorio 4 - Análisis geoespacial de cianobacterias")
    canvas.drawRightString(letter[0] - right_margin, 0.42 * inch, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


class FooterCanvas(pdfcanvas.Canvas):
    """Añade el pie al final para que las imágenes no lo cubran."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        for state in self._saved_page_states:
            self.__dict__.update(state)
            footer(self)
            super().showPage()
        super().save()


def result_table(comparison: pd.DataFrame, body: ParagraphStyle, small: ParagraphStyle) -> Table:
    rows = [[
        paragraph("Métrica", small),
        *[paragraph(escape(name), small) for name in comparison["nombre_lago"]],
    ]]
    metrics = [
        ("Promedio de escenas (µg/L)", "cianobacteria_promedio_escenas_ug_l", 2),
        ("Máximo y fecha (µg/L)", None, 2),
        ("Fechas críticas", "fechas_criticas", 0),
        ("Área alta promedio (%)", "area_alta_promedio_pct", 2),
        ("Área alta máxima (%)", "area_alta_maxima_pct", 2),
        ("Persistencia alta (%)", "area_persistencia_alta_pct", 2),
    ]
    for label, column, decimals in metrics:
        values: list[Paragraph] = [paragraph(label, body)]
        for item in comparison.itertuples(index=False):
            if column is None:
                text = f"{number(item.cianobacteria_maxima_ug_l, decimals)} ({item.fecha_maxima})"
            elif pd.isna(getattr(item, column)):
                text = "No estimable"
            else:
                text = number(getattr(item, column), decimals)
            values.append(paragraph(text, body))
        rows.append(values)
    table = Table(rows, colWidths=[2.2 * inch, 2.0 * inch, 2.0 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3C5D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#B8C4CE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def figure_block(path: Path, caption: str, body: ParagraphStyle, width: float = 6.2 * inch, height: float = 4.7 * inch):
    graphic = image_if_available(path, width, height)
    if graphic is None:
        return [paragraph(f"Figura no disponible al generar el informe: <i>{escape(path.name)}</i>.", body)]
    return [graphic, Spacer(1, 3), paragraph(caption, body), Spacer(1, 9)]


def main() -> Path:
    comparison_path = TABLES / "comparacion_lagos.csv"
    if not comparison_path.exists():
        raise FileNotFoundError("Primero ejecute el notebook para generar comparacion_lagos.csv.")
    comparison = pd.read_csv(comparison_path)
    if comparison.shape[0] != 2:
        raise ValueError("La comparación final debe incluir exactamente dos lagos.")

    amatitlan = comparison.loc[comparison["lago"] == "amatitlan"].iloc[0]
    atitlan = comparison.loc[comparison["lago"] == "atitlan"].iloc[0]
    threshold = comparison["umbral_alto_ug_l"].iloc[0]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#0B3C5D"), alignment=TA_CENTER, spaceAfter=10)
    subtitle = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=colors.HexColor("#52616B"), alignment=TA_CENTER, spaceAfter=22)
    heading = ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#0B3C5D"), spaceBefore=13, spaceAfter=7)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.4, leading=13.3, spaceAfter=8)
    small = ParagraphStyle("ReportSmall", parent=body, fontSize=8, leading=10)

    document = SimpleDocTemplate(
        str(OUTPUT_PATH), pagesize=letter, rightMargin=.65 * inch, leftMargin=.65 * inch,
        topMargin=.62 * inch, bottomMargin=.9 * inch, title="Informe final - Laboratorio 4", author="Equipo Laboratorio 4",
    )
    story = [
        paragraph("Laboratorio 4: análisis geoespacial de cianobacterias", title),
        paragraph("Informe final para interpretación ambiental - Lagos de Amatitlán y Atitlán", subtitle),
        paragraph("Resumen ejecutivo", heading),
        paragraph(
            f"Se analizaron 22 fechas oficiales Sentinel-2, 11 por lago, entre enero de 2025 y julio de 2026. Con el producto numérico CyanoLakes, Amatitlán presentó un promedio entre escenas de <b>{number(amatitlan.cianobacteria_promedio_escenas_ug_l)} µg/L</b>, mayor que Atitlán ({number(atitlan.cianobacteria_promedio_escenas_ug_l)} µg/L). El máximo observado fue {number(amatitlan.cianobacteria_maxima_ug_l)} µg/L en Amatitlán ({amatitlan.fecha_maxima}) y {number(atitlan.cianobacteria_maxima_ug_l)} µg/L en Atitlán ({atitlan.fecha_maxima}). Estos resultados describen la señal satelital estimada, no una medición de campo ni una prueba causal.",
            body,
        ),
        paragraph("Datos y método", heading),
        paragraph(
            f"Las escenas se obtuvieron de Sentinel-2 L2A mediante Copernicus Data Space. NDVI se calculó con B08 y B04; NDWI, con B03 y B08. La cianobacteria se estimó con la formulación numérica de CyanoLakes Chlorophyll-a NDCI. Nodata, divisiones no válidas y píxeles sin clasificación de agua se excluyeron de las métricas. Un valor alto se definió una sola vez como el percentil 90 global de todos los píxeles válidos ({number(threshold)} µg/L). Una fecha crítica es un máximo local que alcanza al menos el percentil 75 del promedio de su propio lago.",
            body,
        ),
        paragraph("Comparación cuantitativa", heading),
        result_table(comparison, body, small),
        Spacer(1, 9),
        paragraph("La tabla combina intensidad (promedios y máximos), frecuencia (fechas críticas), extensión de valores altos y persistencia. Las métricas se calcularon con las mismas definiciones para ambos lagos; por ello permiten una comparación exploratoria, aunque no sustituyen una máscara vectorial precisa ni validación in situ.", body),
        PageBreak(),
        paragraph("Resultados temporales y comparativos", heading),
        *figure_block(FIGURES / "comparacion_lagos.png", "Figura 1. Comparación integrada de intensidad, frecuencia y persistencia espacial. Las barras resumen las 11 fechas oficiales de cada lago; las escalas de porcentaje se limitan a 0-100 %.", body),
        *figure_block(FIGURES / "correlaciones_por_lago.png", "Figura 2. Relaciones exploratorias, por lago y fecha, entre la señal de cianobacteria y los índices NDVI/NDWI. Con 11 observaciones por lago, las líneas de tendencia no demuestran causalidad.", body, height=4.4 * inch),
        PageBreak(),
        paragraph("Distribución espacial", heading),
        *figure_block(FIGURES / "amatitlan_mapas_comparativos.png", "Figura 3. Amatitlán: fechas baja, intermedia y pico con una escala común dentro del panel. El contorno blanco indica valores iguales o superiores al umbral alto global.", body, height=2.85 * inch),
        *figure_block(FIGURES / "atitlan_mapas_comparativos.png", "Figura 4. Atitlán: comparación equivalente de fechas baja, intermedia y pico. La lectura debe centrarse en cambios dentro del lago y en la extensión relativa de los valores altos.", body, height=2.85 * inch),
        PageBreak(),
        paragraph("Interpretación y discusión", heading),
        paragraph(
            f"La evidencia de la Tabla 1 y la Figura 1 muestra una mayor intensidad media y una mayor extensión promedio de valores altos en Amatitlán durante las fechas analizadas. En particular, su mayor área alta fue {number(amatitlan.area_alta_maxima_pct)} % de los píxeles válidos, frente a {number(atitlan.area_alta_maxima_pct)} % en Atitlán. Ambos lagos tuvieron {int(amatitlan.fechas_criticas)} y {int(atitlan.fechas_criticas)} fechas críticas, respectivamente; el conteo por sí solo no debe interpretarse como mayor riesgo sin considerar la magnitud y la cobertura de cada escena.",
            body,
        ),
        paragraph(
            "Las diferencias pueden ser compatibles con contrastes de aportes de nutrientes, presión urbana, uso del suelo, morfometría, temperatura, viento y mezcla del agua. Estas son hipótesis de contexto: las imágenes y los índices de este análisis no permiten adjudicar una causa concreta. Para evaluarlas se necesitan registros de calidad de agua, precipitación, temperatura, caudales, uso del suelo y muestreos de campo coincidentes con las fechas satelitales.",
            body,
        ),
        paragraph("Limitaciones", heading),
        paragraph(
            "La salida de CyanoLakes es una estimación indirecta de clorofila-a y no una observación directa de biomasa de cianobacterias. Las nubes, la cobertura parcial, los píxeles mixtos y el criterio de agua pueden afectar los resultados. Además, todavía no se integró un polígono vectorial preciso para cada lago; por ello las métricas se limitan a los píxeles que la máscara espectral considera válidos. La serie abarca un periodo limitado y no demuestra estacionalidad climática ni causalidad.",
            body,
        ),
        paragraph("Conclusiones", heading),
        paragraph(
            "1. El flujo de trabajo usa exclusivamente las 22 fechas oficiales y conserva un inventario, tablas de métricas y figuras reproducibles. 2. La comparación indica mayor señal media y máxima en Amatitlán para este conjunto de fechas, mientras que Atitlán presenta sus máximos concentrados en menos escenas. 3. El umbral alto común permite comparar extensión y persistencia sin cambiar el criterio entre lagos. 4. Los resultados deben usarse para priorizar validación de campo y seguimiento, no para diagnosticar por sí solos una floración ni sus causas.",
            body,
        ),
        paragraph("Referencias", heading),
        paragraph("Copernicus Data Space Ecosystem. Sentinel-2 L2A, acceso mediante openEO.", small),
        paragraph("Sentinel Hub Custom Scripts. CyanoLakes Chlorophyll-a NDCI L1C. https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/cyanobacteria_chla_ndci_l1c/", small),
        paragraph("Kravitz, J. & Matthews, M. (2020). Chlorophyll-a for cyanobacteria blooms from Sentinel-2. CyanoLakes.", small),
    ]
    document.build(story, canvasmaker=FooterCanvas)
    return OUTPUT_PATH


if __name__ == "__main__":
    print(main())
