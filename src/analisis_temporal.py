"""Gráficas y detección de picos temporales."""

from __future__ import annotations

import numpy as np
import pandas as pd


def detect_peaks(metrics: pd.DataFrame, value_column: str = "cianobacteria_promedio", percentile: float = 75) -> pd.DataFrame:
    """Marca fechas >= percentil por lago y que son máximo local (o extremo)."""
    data = metrics.copy()
    data["fecha"] = pd.to_datetime(data["fecha"])
    data = data.sort_values(["lago", "fecha"]).reset_index(drop=True)
    data["umbral_percentil_75"] = data.groupby("lago")[value_column].transform(lambda values: values.quantile(percentile / 100))
    local = data.groupby("lago")[value_column].transform(
        lambda values: (values >= values.shift(1).fillna(-np.inf)) & (values >= values.shift(-1).fillna(-np.inf))
    )
    data["es_pico"] = (data[value_column] >= data["umbral_percentil_75"]) & local
    data["criterio_pico"] = f"máximo local y valor >= percentil {percentile:.0f} por lago"
    return data


def plot_cyano_timeseries(peaks: pd.DataFrame, ax=None):
    """Grafica series temporales con fechas críticas señaladas y unidades del script."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 5))
    labels = {"amatitlan": "Lago de Amatitlán", "atitlan": "Lago de Atitlán"}
    for lake, group in peaks.groupby("lago", sort=False):
        ax.plot(group["fecha"], group["cianobacteria_promedio"], marker="o", label=labels.get(lake, lake))
        critical = group[group["es_pico"]]
        ax.scatter(critical["fecha"], critical["cianobacteria_promedio"], s=90, marker="*", zorder=3, label=f"Pico: {labels.get(lake, lake)}")
        for row in critical.itertuples():
            ax.annotate(row.fecha.strftime("%Y-%m-%d"), (row.fecha, row.cianobacteria_promedio), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8)
    ax.set(title="Evolución temporal de cianobacteria", xlabel="Fecha", ylabel="Salida numérica del Cyano Detection Script")
    ax.grid(alpha=.25)
    ax.legend(ncol=2)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    return ax


def temporal_interpretation(peaks: pd.DataFrame) -> pd.DataFrame:
    """Resumen factual para acompañar la gráfica sin inferir causalidad ambiental."""
    summaries = []
    for lake, group in peaks.groupby("lago"):
        max_row = group.loc[group["cianobacteria_promedio"].idxmax()]
        summaries.append({"lago": lake, "fecha_maxima": max_row["fecha"].strftime("%Y-%m-%d"),
                          "valor_maximo": max_row["cianobacteria_promedio"], "numero_picos": int(group["es_pico"].sum()),
                          "interpretacion": "La fecha máxima describe la señal del índice; posibles causas ambientales requieren datos auxiliares (lluvia, viento, nutrientes y campo)."})
    return pd.DataFrame(summaries)
