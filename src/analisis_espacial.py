"""Análisis espacial y exploratorio de cianobacteria (ejercicios 5 y 8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from configuracion import TABLES_DIR
from indices import metrics_for_scene


def select_comparison_dates(metrics: pd.DataFrame, lake: str) -> pd.DataFrame:
    """Elige fechas baja, intermedia y máxima por promedio, sin elegir fechas no oficiales."""
    data = metrics.loc[metrics["lago"] == lake].copy()
    if data.empty:
        raise ValueError(f"No hay métricas para {lake}.")
    data["fecha"] = pd.to_datetime(data["fecha"])
    data = data.sort_values("cianobacteria_promedio")
    positions = {"baja": 0, "intermedia": len(data) // 2, "pico": len(data) - 1}
    selected = []
    used: set[int] = set()
    for label, position in positions.items():
        candidates = sorted(range(len(data)), key=lambda value: (abs(value - position), value))
        index = next(value for value in candidates if value not in used)
        used.add(index)
        row = data.iloc[index].copy()
        row["categoria_comparacion"] = label
        selected.append(row)
    return pd.DataFrame(selected).sort_values("categoria_comparacion", key=lambda col: col.map({"baja": 0, "intermedia": 1, "pico": 2}))


def load_lake_stack(lake: str, dates: list[str] | None = None) -> tuple[np.ndarray, np.ndarray, list[str], dict[str, Any]]:
    """Carga cianobacteria y máscara válida por fecha en una grilla común."""
    from configuracion import OFFICIAL_SCENES

    official = [date for date, *_ in OFFICIAL_SCENES[lake]]
    requested = dates or official
    invalid = set(requested) - set(official)
    if invalid:
        raise ValueError(f"Fechas no oficiales para {lake}: {sorted(invalid)}")

    layers, masks, loaded_dates, metadata = [], [], [], None
    expected_shape = None
    for iso_date in requested:
        _, arrays = metrics_for_scene(lake, iso_date)
        layer, valid = arrays["cianobacteria"].astype("float32"), arrays["valid_mask"].astype(bool)
        if expected_shape is None:
            expected_shape, metadata = layer.shape, arrays["metadata"]
        if layer.shape != expected_shape:
            raise ValueError(f"La grilla de {lake} {iso_date} no coincide con las demás fechas.")
        layers.append(np.where(valid, layer, np.nan))
        masks.append(valid)
        loaded_dates.append(iso_date)
    if not layers:
        raise FileNotFoundError(f"No se encontraron rasteres comparables de cianobacteria para {lake}.")
    return np.stack(layers), np.stack(masks), loaded_dates, metadata or {}


def high_value_threshold(stack: np.ndarray, percentile: float = 90) -> float:
    """Umbral reproducible: percentil global de todos los píxeles válidos de ambos lagos."""
    values = stack[np.isfinite(stack)]
    if values.size == 0:
        raise ValueError("No hay píxeles válidos para definir el umbral.")
    return float(np.nanpercentile(values, percentile))


def extent_and_persistence(lake: str, threshold: float, dates: list[str] | None = None) -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, Any]]:
    """Calcula área alta por fecha y frecuencia de persistencia por píxel."""
    stack, valid, loaded_dates, metadata = load_lake_stack(lake, dates)
    high = (stack >= threshold) & valid
    valid_count, high_count = valid.sum(axis=0), high.sum(axis=0)
    persistence = np.divide(high_count, valid_count, out=np.full(valid_count.shape, np.nan, dtype="float32"), where=valid_count > 0)
    rows = []
    for index, iso_date in enumerate(loaded_dates):
        pixels_valid = int(valid[index].sum())
        pixels_high = int(high[index].sum())
        rows.append({
            "lago": lake, "fecha": iso_date, "umbral_alto": threshold,
            "pixeles_validos": pixels_valid, "pixeles_altos": pixels_high,
            "porcentaje_area_alta": 100 * pixels_high / pixels_valid if pixels_valid else np.nan,
        })
    arrays = {"persistencia": persistence, "conteo_alto": high_count, "conteo_valido": valid_count}
    return pd.DataFrame(rows), arrays, metadata


def monthly_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Resume la señal por mes; es descriptivo, no una prueba de estacionalidad."""
    data = metrics.copy()
    data["fecha"] = pd.to_datetime(data["fecha"])
    data["mes"] = data["fecha"].dt.month
    result = (data.groupby(["lago", "mes"], as_index=False)
              .agg(n_fechas=("fecha", "size"),
                   cianobacteria_promedio_media=("cianobacteria_promedio", "mean"),
                   cianobacteria_promedio_mediana=("cianobacteria_promedio", "median"))
              .sort_values(["lago", "mes"], ignore_index=True))
    return result


def save_spatial_tables(extent: pd.DataFrame, seasonality: pd.DataFrame) -> tuple[Path, Path]:
    """Guarda las tablas que respaldan los ejercicios 8.1 y 8.4."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    extent_path = TABLES_DIR / "extension_area_alta_por_fecha.csv"
    seasonality_path = TABLES_DIR / "resumen_mensual_cianobacteria.csv"
    extent.to_csv(extent_path, index=False, encoding="utf-8-sig")
    seasonality.to_csv(seasonality_path, index=False, encoding="utf-8-sig")
    return extent_path, seasonality_path


def plot_comparison_maps(lake: str, selected: pd.DataFrame, threshold: float, cmap: str = "viridis"):
    """Panel baja/intermedia/pico con escala común y píxeles altos delimitados."""
    import matplotlib.pyplot as plt

    dates = [pd.Timestamp(value).strftime("%Y-%m-%d") for value in selected["fecha"]]
    stack, valid, loaded_dates, _ = load_lake_stack(lake, dates)
    finite = stack[np.isfinite(stack)]
    vmin, vmax = np.nanpercentile(finite, [2, 98])
    fig, axes = plt.subplots(1, len(loaded_dates), figsize=(5 * len(loaded_dates), 5), constrained_layout=True)
    axes = np.atleast_1d(axes)
    for axis, layer, mask, row in zip(axes, stack, valid, selected.itertuples(index=False)):
        image = axis.imshow(layer, cmap=cmap, vmin=vmin, vmax=vmax)
        axis.contour((layer >= threshold) & mask, levels=[0.5], colors="white", linewidths=.65)
        axis.set(title=f"{row.categoria_comparacion.title()}: {pd.Timestamp(row.fecha):%Y-%m-%d}", xticks=[], yticks=[])
    fig.colorbar(image, ax=axes, label="Clorofila-a estimada por CyanoLakes (µg/L)")
    fig.suptitle(f"{lake.title()}: comparación espacial (contorno blanco = ≥ percentil 90 global)")
    return fig


def plot_persistence(lake: str, persistence: np.ndarray):
    """Mapa de proporción de observaciones válidas con valor alto."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    image = ax.imshow(persistence * 100, cmap="magma", vmin=0, vmax=100)
    ax.set(title=f"{lake.title()}: persistencia de valores altos", xticks=[], yticks=[])
    fig.colorbar(image, ax=ax, label="% de fechas válidas ≥ umbral alto")
    return fig


def plot_distributions(lake: str, dates: list[str] | None = None):
    """Histogramas y boxplots de distribuciones de píxeles válidos por fecha."""
    import matplotlib.pyplot as plt

    stack, _, loaded_dates, _ = load_lake_stack(lake, dates)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), constrained_layout=True)
    values = [layer[np.isfinite(layer)] for layer in stack]
    for layer, iso_date in zip(values, loaded_dates):
        axes[0].hist(layer, bins=35, alpha=.35, label=iso_date, density=True)
    axes[0].set(title=f"{lake.title()}: distribución por fecha", xlabel="Clorofila-a estimada (µg/L)", ylabel="Densidad")
    axes[0].legend(fontsize=7, ncol=2)
    axes[1].boxplot(values, tick_labels=loaded_dates, showfliers=False)
    axes[1].set(title=f"{lake.title()}: variación entre fechas", xlabel="Fecha", ylabel="Clorofila-a estimada (µg/L)")
    plt.setp(axes[1].get_xticklabels(), rotation=45, ha="right", fontsize=8)
    return fig
