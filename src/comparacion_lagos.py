"""Síntesis reproducible para comparar la señal de cianobacteria entre lagos."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from analisis_temporal import detect_peaks
from configuracion import LAKES, TABLES_DIR


def _percentage(numerator: int | float, denominator: int | float) -> float:
    """Devuelve un porcentaje o NaN si el denominador no es válido."""
    return 100 * numerator / denominator if denominator else np.nan


def build_lake_comparison(
    metrics: pd.DataFrame,
    high_extent: pd.DataFrame,
    persistences: Mapping[str, Mapping[str, np.ndarray]] | None = None,
    persistence_cutoff: float = 0.5,
) -> pd.DataFrame:
    """Resume intensidad, frecuencia y persistencia con reglas comunes.

    La intensidad corresponde a los promedios por escena; la frecuencia, a las
    fechas críticas y a la extensión que supera el percentil 90 global. La
    persistencia expresa el porcentaje de píxeles observados que fue alto en al
    menos la mitad de sus fechas válidas.
    """
    required_metrics = {"lago", "fecha", "cianobacteria_promedio", "cobertura_valida_pct"}
    required_extent = {"lago", "fecha", "umbral_alto", "porcentaje_area_alta"}
    missing_metrics = required_metrics - set(metrics.columns)
    missing_extent = required_extent - set(high_extent.columns)
    if missing_metrics:
        raise ValueError(f"Faltan columnas de métricas: {sorted(missing_metrics)}")
    if missing_extent:
        raise ValueError(f"Faltan columnas de extensión: {sorted(missing_extent)}")
    if not 0 < persistence_cutoff <= 1:
        raise ValueError("El corte de persistencia debe estar entre 0 y 1.")

    peaks = detect_peaks(metrics)
    rows: list[dict[str, object]] = []
    for lake, group in metrics.groupby("lago", sort=True):
        group = group.copy()
        group["fecha"] = pd.to_datetime(group["fecha"])
        group = group.sort_values("fecha")
        extent = high_extent.loc[high_extent["lago"] == lake].copy()
        if extent.empty:
            raise ValueError(f"No hay extensión de valores altos para {lake}.")
        extent["fecha"] = pd.to_datetime(extent["fecha"])
        extent = extent.sort_values("fecha")
        peak_row = group.loc[group["cianobacteria_promedio"].idxmax()]
        area_row = extent.loc[extent["porcentaje_area_alta"].idxmax()]
        critical_count = int(peaks.loc[(peaks["lago"] == lake) & peaks["es_pico"]].shape[0])

        persistent_pct = np.nan
        observed_pixels = 0
        persistent_pixels = 0
        if persistences and lake in persistences:
            layer = np.asarray(persistences[lake]["persistencia"], dtype=float)
            finite = np.isfinite(layer)
            observed_pixels = int(finite.sum())
            persistent_pixels = int((layer[finite] >= persistence_cutoff).sum())
            persistent_pct = _percentage(persistent_pixels, observed_pixels)

        rows.append(
            {
                "lago": lake,
                "nombre_lago": LAKES.get(lake, {}).get("display_name", lake),
                "fechas_analizadas": int(len(group)),
                "cianobacteria_promedio_escenas_ug_l": float(group["cianobacteria_promedio"].mean()),
                "cianobacteria_mediana_escenas_ug_l": float(group["cianobacteria_promedio"].median()),
                "cianobacteria_maxima_ug_l": float(peak_row["cianobacteria_promedio"]),
                "fecha_maxima": peak_row["fecha"].strftime("%Y-%m-%d"),
                "fechas_criticas": critical_count,
                "porcentaje_fechas_criticas": _percentage(critical_count, len(group)),
                "umbral_alto_ug_l": float(extent["umbral_alto"].iloc[0]),
                "area_alta_promedio_pct": float(extent["porcentaje_area_alta"].mean()),
                "area_alta_maxima_pct": float(area_row["porcentaje_area_alta"]),
                "fecha_area_alta_maxima": area_row["fecha"].strftime("%Y-%m-%d"),
                "cobertura_valida_promedio_pct": float(group["cobertura_valida_pct"].mean()),
                "pixeles_observados_persistencia": observed_pixels,
                "pixeles_persistencia_alta": persistent_pixels,
                "area_persistencia_alta_pct": persistent_pct,
                "criterio_persistencia": f"Valor alto en al menos {persistence_cutoff:.0%} de las fechas válidas",
            }
        )
    return pd.DataFrame(rows).sort_values("lago", ignore_index=True)


def save_lake_comparison(comparison: pd.DataFrame, filename: str = "comparacion_lagos.csv") -> Path:
    """Guarda la tabla de evidencia del ejercicio 7."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLES_DIR / filename
    comparison.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def plot_lake_comparison(comparison: pd.DataFrame):
    """Visualiza métricas comparables de intensidad, frecuencia y persistencia."""
    import matplotlib.pyplot as plt

    labels = comparison["nombre_lago"].tolist()
    positions = np.arange(len(comparison))
    width = 0.36
    colors = ("#0B6E69", "#D98C10")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    axes[0, 0].bar(positions - width / 2, comparison["cianobacteria_promedio_escenas_ug_l"], width, label="Promedio de escenas", color=colors[0])
    axes[0, 0].bar(positions + width / 2, comparison["cianobacteria_maxima_ug_l"], width, label="Máximo de escena", color=colors[1])
    axes[0, 0].set(title="Intensidad de la señal", ylabel="Clorofila-a estimada (µg/L)", xticks=positions, xticklabels=labels)
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].bar(positions, comparison["porcentaje_fechas_criticas"], color="#5C7AEA")
    axes[0, 1].set(title="Frecuencia de fechas críticas", ylabel="% de fechas oficiales", xticks=positions, xticklabels=labels, ylim=(0, 100))

    axes[1, 0].bar(positions - width / 2, comparison["area_alta_promedio_pct"], width, label="Promedio", color=colors[0])
    axes[1, 0].bar(positions + width / 2, comparison["area_alta_maxima_pct"], width, label="Máximo", color=colors[1])
    axes[1, 0].set(title="Extensión por encima del umbral alto", ylabel="% de píxeles válidos", xticks=positions, xticklabels=labels, ylim=(0, 100))
    axes[1, 0].legend(fontsize=8)

    axes[1, 1].bar(positions, comparison["area_persistencia_alta_pct"], color="#A64D79")
    axes[1, 1].set(title="Persistencia espacial de valores altos", ylabel="% de píxeles observados", xticks=positions, xticklabels=labels, ylim=(0, 100))

    for axis in axes.flat:
        axis.grid(axis="y", alpha=.25)
        axis.tick_params(axis="x", labelrotation=0, labelsize=9)
    fig.suptitle("Comparación entre lagos con criterios comunes", fontsize=14, fontweight="bold")
    return fig
