"""Cálculo de índices espectrales y métricas por fecha."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from configuracion import DATA_DIR, TABLES_DIR, scene_output_path


CYANO_SCRIPT_URL = (
    "https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/"
    "cyanobacteria_chla_ndci_l1c/"
)
CYANO_SCRIPT_NAME = "CyanoLakes Chlorophyll-a NDCI L1C (Kravitz & Matthews, 2020)"
CYANO_DATA_DIR = DATA_DIR / "cyano"


def safe_normalized_difference(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Calcula una diferencia normalizada y convierte nodata/división por cero en NaN."""
    numerator = np.asarray(numerator, dtype="float32")
    denominator = np.asarray(denominator, dtype="float32")
    result = np.full(numerator.shape, np.nan, dtype="float32")
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0)
    np.divide(numerator, denominator, out=result, where=valid)
    return result


def ndvi(b04: np.ndarray, b08: np.ndarray) -> np.ndarray:
    """NDVI = (B08 - B04) / (B08 + B04)."""
    return safe_normalized_difference(np.asarray(b08) - np.asarray(b04), np.asarray(b08) + np.asarray(b04))


def ndwi(b03: np.ndarray, b08: np.ndarray) -> np.ndarray:
    """NDWI = (B03 - B08) / (B03 + B08), definición de McFeeters."""
    return safe_normalized_difference(np.asarray(b03) - np.asarray(b08), np.asarray(b03) + np.asarray(b08))


def read_minimal_bands(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Lee B03/B04/B08 y devuelve máscara válida inicial y metadatos raster."""
    import rasterio

    with rasterio.open(path) as source:
        if source.count != 3:
            raise ValueError(f"Se esperaban 3 bandas B03/B04/B08, no {source.count}, en {path}.")
        bands = source.read(masked=True).astype("float32")
        b03, b04, b08 = (band.filled(np.nan) for band in bands)
        valid = ~np.ma.getmaskarray(bands).any(axis=0)
        # Los valores negativos son artefactos/nodata de procesamiento y no
        # representan reflectancia física; sin esta exclusión NDVI/NDWI puede
        # quedar fuera de su rango teórico [-1, 1].
        valid &= np.isfinite(b03) & np.isfinite(b04) & np.isfinite(b08)
        valid &= (b03 >= 0) & (b04 >= 0) & (b08 >= 0)
        metadata = {"transform": source.transform, "crs": source.crs, "shape": (source.height, source.width)}
    return b03, b04, b08, valid, metadata


def cyano_output_path(lake: str, iso_date: str) -> Path:
    """Ruta esperada para el GeoTIFF de una sola banda exportado por Sentinel Hub."""
    return CYANO_DATA_DIR / lake / f"{lake}_{iso_date}_cyano.tif"


def read_cyano_result(path: str | Path, expected_shape: tuple[int, int] | None = None) -> np.ndarray:
    """Lee una salida numérica de una banda de cianobacteria."""
    import rasterio

    with rasterio.open(path) as source:
        if source.count != 1:
            raise ValueError(f"La salida de cianobacteria debe tener 1 banda numérica: {path}.")
        cyano = source.read(1, masked=True).astype("float32").filled(np.nan)
    if expected_shape is not None and cyano.shape != expected_shape:
        raise ValueError("El raster de cianobacteria no está alineado con B03/B04/B08.")
    return cyano


def metrics_for_scene(lake: str, iso_date: str, lake_mask: np.ndarray | None = None) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Calcula estadísticas comparables para una fecha."""
    b03, b04, b08, valid, metadata = read_minimal_bands(scene_output_path(lake, iso_date))
    if lake_mask is not None:
        if lake_mask.shape != valid.shape:
            raise ValueError("La máscara del lago no coincide con la geometría del raster.")
        valid &= lake_mask.astype(bool)
    ndvi_values, ndwi_values = ndvi(b04, b08), ndwi(b03, b08)
    cyano = read_cyano_result(cyano_output_path(lake, iso_date), expected_shape=valid.shape)
    valid &= np.isfinite(ndvi_values) & np.isfinite(ndwi_values) & np.isfinite(cyano)

    arrays = {"cianobacteria": cyano, "ndvi": ndvi_values, "ndwi": ndwi_values, "valid_mask": valid}
    total = int(valid.size if lake_mask is None else lake_mask.astype(bool).sum())
    row: dict[str, Any] = {"lago": lake, "fecha": iso_date, "pixeles_validos": int(valid.sum()),
                           "cobertura_valida_pct": 100 * valid.sum() / total if total else np.nan,
                           "mascara_lago_aplicada": lake_mask is not None}
    for name, values in arrays.items():
        if name == "valid_mask":
            continue
        selected = values[valid]
        row[f"{name}_promedio"] = float(np.nanmean(selected)) if selected.size else np.nan
        row[f"{name}_mediana"] = float(np.nanmedian(selected)) if selected.size else np.nan
        row[f"{name}_desviacion"] = float(np.nanstd(selected)) if selected.size else np.nan
    return row, arrays | {"metadata": metadata}


def build_metrics_table(inventory: pd.DataFrame, masks: dict[str, np.ndarray] | None = None) -> pd.DataFrame:
    """Construye la tabla maestra con escenas disponibles."""
    rows, incidences = [], []
    for scene in inventory.itertuples(index=False):
        try:
            row, _ = metrics_for_scene(scene.lago, scene.fecha, (masks or {}).get(scene.lago))
            row["incidencia"] = getattr(scene, "observaciones", "")
            rows.append(row)
        except (FileNotFoundError, ValueError) as error:
            incidences.append({"lago": scene.lago, "fecha": scene.fecha, "incidencia": str(error)})
    if not rows:
        raise FileNotFoundError("No hay pares de raster B03/B04/B08 y cianobacteria disponibles para calcular métricas.")
    result = pd.DataFrame(rows).sort_values(["lago", "fecha"], ignore_index=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(TABLES_DIR / "metricas_por_fecha.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(incidences).to_csv(TABLES_DIR / "incidencias_persona2.csv", index=False, encoding="utf-8-sig")
    return result
