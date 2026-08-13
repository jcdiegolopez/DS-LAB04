"""Configuración oficial y centralizada para el Laboratorio 4.

No modifique las fechas sin una instrucción explícita del docente: el enunciado
indica que todos los grupos deben trabajar exclusivamente con estas escenas.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tablas"

# Bounding boxes entregados en el enunciado del laboratorio (EPSG:4326).
LAKES = {
    "amatitlan": {
        "display_name": "Lago de Amatitlán",
        "bounds": {
            "west": -90.638065,
            "east": -90.512924,
            "south": 14.412347,
            "north": 14.493799,
            "crs": "EPSG:4326",
        },
    },
    "atitlan": {
        "display_name": "Lago de Atitlán",
        "bounds": {
            "west": -91.326256,
            "east": -91.07151,
            "south": 14.5948,
            "north": 14.750979,
            "crs": "EPSG:4326",
        },
    },
}

# Las bandas mínimas permiten calcular NDVI (B04/B08) y NDWI (B03/B08).
REQUIRED_BANDS = ("B03", "B04", "B08")
COLLECTION_ID = "SENTINEL2_L2A"

# Fecha, nubosidad y satélite reportados oficialmente por el laboratorio.
OFFICIAL_SCENES = {
    "amatitlan": [
        ("2025-01-28", 0.06, "Sentinel-2B", ""),
        ("2025-04-15", 0.09, "Sentinel-2A", ""),
        ("2025-04-28", 1.03, "Sentinel-2B", ""),
        ("2025-11-24", 0.50, "Sentinel-2B", ""),
        ("2026-01-08", 0.77, "Sentinel-2C", ""),
        ("2026-02-02", 0.39, "Sentinel-2B", ""),
        ("2026-02-07", 0.02, "Sentinel-2C", "Cobertura válida parcial aproximada: 57.1%."),
        ("2026-03-29", 0.01, "Sentinel-2C", ""),
        ("2026-04-13", 0.09, "Sentinel-2B", ""),
        ("2026-04-28", 4.96, "Sentinel-2C", ""),
        ("2026-06-19", 13.00, "Sentinel-2A", ""),
    ],
    "atitlan": [
        ("2025-01-18", 0.02, "Sentinel-2B", ""),
        ("2025-04-13", 0.54, "Sentinel-2C", ""),
        ("2025-05-13", 4.37, "Sentinel-2C", ""),
        ("2025-07-17", 3.57, "Sentinel-2A", ""),
        ("2025-11-21", 3.15, "Sentinel-2A", ""),
        ("2025-12-29", 3.17, "Sentinel-2C", ""),
        ("2026-02-12", 0.04, "Sentinel-2B", ""),
        ("2026-03-24", 3.17, "Sentinel-2B", ""),
        ("2026-04-13", 0.01, "Sentinel-2B", ""),
        ("2026-04-28", 4.96, "Sentinel-2C", ""),
        ("2026-07-22", 4.02, "Sentinel-2B", ""),
    ],
}


def next_day(iso_date: str) -> str:
    """Devuelve el límite superior exclusivo para consultar una sola fecha."""
    return (date.fromisoformat(iso_date) + timedelta(days=1)).isoformat()


def scene_output_path(lake: str, iso_date: str) -> Path:
    """Ruta estándar y reproducible para la descarga mínima de una escena."""
    return RAW_DATA_DIR / lake / f"{lake}_{iso_date}_B03_B04_B08.tif"

