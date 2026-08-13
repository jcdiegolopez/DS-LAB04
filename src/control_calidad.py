"""Controles de integración para el avance del Laboratorio 4.

Estas verificaciones no sustituyen el análisis: dejan evidencia clara de qué
insumos están disponibles y de qué debe corregirse antes de entregar. Así se
evita que una figura o una tabla se interprete como válida si faltan rasteres,
la máscara del lago o la salida numérica del algoritmo de cianobacteria.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from configuracion import TABLES_DIR, scene_output_path
from indices import CYANO_SCRIPT_NAME, cyano_output_path


def _check(name: str, passed: bool, evidence: str, action: str) -> dict[str, str]:
    return {
        "criterio": name,
        "estado": "cumple" if passed else "pendiente",
        "evidencia": evidence,
        "accion_requerida": "" if passed else action,
    }


def build_quality_checklist(inventory: pd.DataFrame) -> pd.DataFrame:
    """Evalúa requisitos verificables del avance sin modificar los insumos."""
    expected = {"amatitlan": 11, "atitlan": 11}
    counts = inventory.groupby("lago").size().to_dict()
    official_dates = len(inventory) == 22 and counts == expected

    raw_paths = [scene_output_path(row.lago, row.fecha) for row in inventory.itertuples(index=False)]
    cyano_paths = [cyano_output_path(row.lago, row.fecha) for row in inventory.itertuples(index=False)]
    raw_available = sum(path.exists() for path in raw_paths)
    cyano_available = sum(path.exists() for path in cyano_paths)
    output_metrics = TABLES_DIR / "metricas_por_fecha.csv"

    checks: list[dict[str, Any]] = [
        _check(
            "Se usan exactamente las 22 fechas oficiales",
            official_dates,
            f"Inventario: {len(inventory)} filas; distribución por lago: {counts}.",
            "Corregir configuracion.py o el inventario antes de continuar.",
        ),
        _check(
            "Rasteres B03, B04 y B08 disponibles",
            raw_available == len(raw_paths),
            f"Rasteres encontrados: {raw_available} de {len(raw_paths)}.",
            "Regenerar las descargas con openEO o compartir data/raw fuera de Git.",
        ),
        _check(
            "Producto numérico de cianobacteria disponible",
            cyano_available == len(cyano_paths),
            f"Rasteres numéricos encontrados: {cyano_available} de {len(cyano_paths)}. Producto esperado: {CYANO_SCRIPT_NAME}.",
            "Exportar un raster numérico alineado por fecha desde la evaluación documentada del script; una imagen RGB no es suficiente para las métricas.",
        ),
        _check(
            "Tabla de métricas por lago y fecha",
            output_metrics.exists(),
            f"Ruta esperada: {output_metrics.relative_to(TABLES_DIR.parent.parent)}.",
            "Ejecutar la sección 3 cuando estén disponibles los rasteres mínimos y de cianobacteria.",
        ),
    ]
    return pd.DataFrame(checks)


def save_quality_checklist(checklist: pd.DataFrame) -> Path:
    """Guarda la lista de control para revisión cruzada y el informe preliminar."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLES_DIR / "lista_control_calidad_avance.csv"
    checklist.to_csv(path, index=False, encoding="utf-8-sig")
    return path
