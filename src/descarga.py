"""Funciones de descarga y control de calidad para la Persona 1.

Estas funciones no contienen credenciales. La autenticación debe abrirse de
forma interactiva desde el notebook antes de iniciar una descarga.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from configuracion import (
    COLLECTION_ID,
    LAKES,
    OFFICIAL_SCENES,
    REQUIRED_BANDS,
    PROJECT_ROOT,
    TABLES_DIR,
    next_day,
    scene_output_path,
)


def connect_copernicus():
    """Conecta a Copernicus Data Space y solicita autenticación OIDC segura."""
    import openeo

    return openeo.connect("https://openeo.dataspace.copernicus.eu").authenticate_oidc()


def build_inventory() -> pd.DataFrame:
    """Crea el inventario de las 22 fechas autorizadas por el laboratorio."""
    rows: list[dict[str, Any]] = []
    for lake, scenes in OFFICIAL_SCENES.items():
        for iso_date, cloudiness, satellite, note in scenes:
            output = scene_output_path(lake, iso_date)
            rows.append(
                {
                    "lago": lake,
                    "nombre_lago": LAKES[lake]["display_name"],
                    "fecha": iso_date,
                    "satelite": satellite,
                    "nubosidad_oficial_pct": cloudiness,
                    "bandas_solicitadas": ",".join(REQUIRED_BANDS),
                    # Ruta relativa para que el inventario funcione en cualquier computadora
                    # que conserve la estructura del proyecto.
                    "ruta_salida": output.relative_to(PROJECT_ROOT).as_posix(),
                    "estado_descarga": "pendiente",
                    "observaciones": note,
                }
            )
    inventory = pd.DataFrame(rows).sort_values(["lago", "fecha"], ignore_index=True)
    validate_inventory(inventory)
    return inventory


def validate_inventory(inventory: pd.DataFrame) -> None:
    """Falla temprano si faltan fechas o se mezclan fechas no autorizadas."""
    expected_counts = {lake: len(scenes) for lake, scenes in OFFICIAL_SCENES.items()}
    counts = inventory.groupby("lago").size().to_dict()
    if counts != expected_counts:
        raise ValueError(f"Inventario inválido. Esperado {expected_counts}; recibido {counts}.")

    for lake, scenes in OFFICIAL_SCENES.items():
        expected_dates = {scene[0] for scene in scenes}
        found_dates = set(inventory.loc[inventory["lago"] == lake, "fecha"])
        if found_dates != expected_dates:
            raise ValueError(f"Las fechas de {lake} no coinciden con las oficiales.")


def save_inventory(inventory: pd.DataFrame) -> Path:
    """Guarda el inventario de control y crea su carpeta si hace falta."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLES_DIR / "inventario_datos.csv"
    inventory.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def load_official_scene(connection, lake: str, iso_date: str):
    """Carga una fecha oficial con únicamente B03, B04 y B08.

    El intervalo [fecha, fecha+1) evita incluir escenas de otra fecha. La
    selección final de escena queda auditada por la fecha oficial del enunciado.
    """
    if lake not in LAKES:
        raise KeyError(f"Lago desconocido: {lake}")
    official_dates = {scene[0] for scene in OFFICIAL_SCENES[lake]}
    if iso_date not in official_dates:
        raise ValueError(f"{iso_date} no es una fecha oficial de {lake}.")

    return connection.load_collection(
        COLLECTION_ID,
        spatial_extent=LAKES[lake]["bounds"],
        temporal_extent=[iso_date, next_day(iso_date)],
        bands=list(REQUIRED_BANDS),
    )


def download_official_scene(connection, lake: str, iso_date: str, overwrite: bool = False) -> Path:
    """Ejecuta un trabajo openEO y descarga el GeoTIFF mínimo de una fecha."""
    output_path = scene_output_path(lake, iso_date)
    if output_path.exists() and not overwrite:
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cube = load_official_scene(connection, lake, iso_date)
    job = connection.create_job(cube.save_result(format="GTIFF"), title=f"Lab4 {lake} {iso_date}")
    job.start_and_wait()
    job.download_results(str(output_path))
    return output_path


def validate_geotiff(path: str | Path) -> dict[str, Any]:
    """Comprueba que el archivo descargado es un raster georreferenciado de 3 bandas."""
    import rasterio

    path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with rasterio.open(path) as source:
        if source.count != len(REQUIRED_BANDS):
            raise ValueError(
                f"{path.name} tiene {source.count} bandas; se esperaban {len(REQUIRED_BANDS)} ({REQUIRED_BANDS})."
            )
        if source.crs is None:
            raise ValueError(f"{path.name} no tiene sistema de referencia espacial.")
        return {
            "ruta": str(path),
            "bandas": source.count,
            "crs": str(source.crs),
            "ancho": source.width,
            "alto": source.height,
            "resolucion": tuple(source.res),
            "nodata": source.nodata,
        }


def update_download_status(inventory: pd.DataFrame) -> pd.DataFrame:
    """Marca cada fila como descargada solo cuando el GeoTIFF pasa validación."""
    result = inventory.copy()
    statuses = []
    for path in result["ruta_salida"]:
        try:
            validate_geotiff(path)
            statuses.append("descargado_validado")
        except FileNotFoundError:
            statuses.append("pendiente")
        except Exception as error:  # Se conserva el detalle para revisar la escena.
            statuses.append(f"requiere_revision: {error}")
    result["estado_descarga"] = statuses
    return result
