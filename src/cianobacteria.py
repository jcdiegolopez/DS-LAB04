"""Producto numérico de cianobacteria basado en CyanoLakes Chlorophyll-a.

La fórmula y reglas de agua/vegetación se basan en el script público de
Kravitz y Matthews (2020) indicado por el enunciado. Se descargan las bandas
L2A mínimas mediante la conexión openEO de Copernicus y se guarda un GeoTIFF
numérico de una banda por lago y fecha.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from configuracion import COLLECTION_ID, LAKES, OFFICIAL_SCENES, PROJECT_ROOT, next_day, scene_output_path
from indices import CYANO_DATA_DIR, cyano_output_path


# La conexión principal del proyecto ya proporciona Sentinel-2 L2A. Se usa
# como insumo para reproducir localmente la formulación del script CyanoLakes.
CYANO_COLLECTION = COLLECTION_ID
CYANO_INPUT_BANDS = ("B02", "B03", "B04", "B05", "B07", "B08", "B8A", "B11", "B12")
CYANO_INPUT_DIR = PROJECT_ROOT / "data" / "cyano_inputs"


def cyano_input_path(lake: str, iso_date: str) -> Path:
    return CYANO_INPUT_DIR / lake / f"{lake}_{iso_date}_cyano_bands.tif"


def _validate_scene(lake: str, iso_date: str) -> None:
    if lake not in LAKES:
        raise KeyError(f"Lago desconocido: {lake}")
    allowed_dates = {scene[0] for scene in OFFICIAL_SCENES[lake]}
    if iso_date not in allowed_dates:
        raise ValueError(f"{iso_date} no es una fecha oficial de {lake}.")


def download_cyano_inputs(connection, lake: str, iso_date: str, overwrite: bool = False) -> Path:
    """Descarga las bandas L2A requeridas para la formulación de cianobacteria."""
    _validate_scene(lake, iso_date)
    output = cyano_input_path(lake, iso_date)
    if output.exists() and not overwrite:
        return output

    output.parent.mkdir(parents=True, exist_ok=True)
    cube = connection.load_collection(
        CYANO_COLLECTION,
        spatial_extent=LAKES[lake]["bounds"],
        temporal_extent=[iso_date, next_day(iso_date)],
        bands=list(CYANO_INPUT_BANDS),
    )
    job = connection.create_job(cube.save_result(format="GTIFF"), title=f"CyanoLakes {lake} {iso_date}")
    job.start_and_wait()
    job.get_results().download_file(target=str(output))
    return output


def _ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    result = np.full(numerator.shape, np.nan, dtype="float32")
    np.divide(numerator, denominator, out=result, where=np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0))
    return result


def _reflectance(values: np.ndarray) -> np.ndarray:
    """Convierte DN a reflectancia cuando la respuesta viene escalada a 0--10000."""
    values = values.astype("float32")
    finite = values[np.isfinite(values)]
    if finite.size and np.nanpercentile(finite, 99) > 2:
        return values / 10000.0
    return values


def calculate_cyano_raster(input_path: str | Path, output_path: str | Path, reference_path: str | Path | None = None) -> Path:
    """Traduce a Python la parte numérica de CyanoLakes Chlorophyll-a L1C."""
    import rasterio

    input_path, output_path = Path(input_path), Path(output_path)
    with rasterio.open(input_path) as source:
        if source.count != len(CYANO_INPUT_BANDS):
            raise ValueError(f"Se esperaban {len(CYANO_INPUT_BANDS)} bandas en {input_path.name}.")
        names = source.descriptions
        arrays = source.read(masked=True).astype("float32")
        template = source.profile.copy()
        input_transform, input_crs = source.transform, source.crs

    # openEO conserva el orden solicitado; se usa la descripción cuando existe.
    position = {name: index for index, name in enumerate(names) if name}
    data = {
        band: _reflectance(arrays[position[band]].filled(np.nan) if band in position else arrays[index].filled(np.nan))
        for index, band in enumerate(CYANO_INPUT_BANDS)
    }
    b, g, r, re1, re3, nir, nirn, swir1, swir2 = (data[band] for band in CYANO_INPUT_BANDS)
    valid = np.logical_and.reduce([np.isfinite(data[band]) & (data[band] >= 0) for band in CYANO_INPUT_BANDS])

    # Water body detection del script CyanoLakes.
    ndvi = _ratio(nir - r, nir + r)
    mndwi = _ratio(g - swir1, g + swir1)
    ndwi = _ratio(g - nir, g + nir)
    ndwi_leaves = _ratio(nir - swir1, nir + swir1)
    aweish = b + 2.5 * g - 1.5 * (nir + swir1) - 0.25 * swir2
    aweinsh = 4 * (g - swir1) - (0.25 * nir + 2.75 * swir1)
    dbsi = _ratio(swir1 - g, swir1 + g) - ndvi
    water = (mndwi > 0.42) | (ndwi > 0.4) | (aweinsh > 0.1879) | (aweish > 0.1112) | (ndvi < -0.2) | (ndwi_leaves > 1)
    water &= ~((aweinsh <= -0.03) | (dbsi > 0))

    # Floating Algal Index y modelo cúbico de clorofila-a del script original.
    fai = re3 - r - (nirn - r) * (783 - 665) / (865 - 665)
    ndci = _ratio(re1 - r, re1 + r)
    chl = 826.57 * ndci**3 - 176.43 * ndci**2 + 19 * ndci + 4.071
    # El modelo está calibrado para concentraciones menores de 500 ug/L.
    # Se excluyen valores fuera de ese intervalo en vez de promediarlos.
    plausible_chl = np.isfinite(chl) & (chl >= 0) & (chl <= 500)
    cyano = np.where(valid & water & (fai <= 0.08) & plausible_chl, chl, np.nan).astype("float32")

    # Las bandas B05, B07, B8A, B11 y B12 son de 20 m. El resultado se
    # remuestrea a la grilla B03/B04/B08 de 10 m para combinarlo por píxel.
    if reference_path is not None:
        from rasterio.warp import Resampling, reproject

        with rasterio.open(reference_path) as reference:
            reference_template = reference.profile.copy()
            aligned = np.full((reference.height, reference.width), -9999.0, dtype="float32")
            reproject(
                source=np.where(np.isfinite(cyano), cyano, -9999.0),
                destination=aligned,
                src_transform=input_transform,
                src_crs=input_crs,
                src_nodata=-9999.0,
                dst_transform=reference.transform,
                dst_crs=reference.crs,
                dst_nodata=-9999.0,
                resampling=Resampling.bilinear,
            )
        cyano = np.where(aligned == -9999.0, np.nan, aligned)
        template = reference_template

    output_path.parent.mkdir(parents=True, exist_ok=True)
    template.update(count=1, dtype="float32", nodata=-9999.0, compress="deflate")
    with rasterio.open(output_path, "w", **template) as destination:
        destination.write(np.where(np.isfinite(cyano), cyano, -9999.0), 1)
        destination.set_band_description(1, "chlorophyll_a_cyanolakes")
    return output_path


def generate_cyano_scene(connection, lake: str, iso_date: str) -> Path:
    """Descarga insumos si faltan y genera (o actualiza) el GeoTIFF numérico."""
    output = cyano_output_path(lake, iso_date)
    inputs = download_cyano_inputs(connection, lake, iso_date)
    return calculate_cyano_raster(inputs, output, reference_path=scene_output_path(lake, iso_date))
