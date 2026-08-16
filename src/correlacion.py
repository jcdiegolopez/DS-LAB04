"""Correlaciones exploratorias del ejercicio 6.

La unidad de análisis es lago-fecha: cada fila representa el promedio de los
píxeles válidos de una escena. Con solo 11 fechas por lago, los resultados son
exploratorios y no prueban causalidad.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from configuracion import TABLES_DIR


def correlation_table(metrics: pd.DataFrame) -> pd.DataFrame:
    """Calcula Pearson, Spearman, n y p-valor por lago e índice."""
    from scipy.stats import pearsonr, spearmanr

    rows: list[dict[str, object]] = []
    pairs = {
        "cianobacteria_vs_ndvi": "ndvi_promedio",
        "cianobacteria_vs_ndwi": "ndwi_promedio",
    }
    for lake, group in metrics.groupby("lago", sort=True):
        for relation, predictor in pairs.items():
            valid = group[["cianobacteria_promedio", predictor]].dropna()
            x = valid["cianobacteria_promedio"].to_numpy(dtype=float)
            y = valid[predictor].to_numpy(dtype=float)
            if len(valid) < 3 or np.std(x) == 0 or np.std(y) == 0:
                rows.append({"lago": lake, "relacion": relation, "predictor": predictor,
                             "n_fechas": len(valid), "pearson_r": np.nan,
                             "pearson_p": np.nan, "spearman_rho": np.nan,
                             "spearman_p": np.nan, "interpretacion": "No estimable por variación insuficiente."})
                continue
            pearson_r, pearson_p = pearsonr(x, y)
            spearman_rho, spearman_p = spearmanr(x, y)
            strength = "débil" if abs(pearson_r) < 0.3 else ("moderada" if abs(pearson_r) < 0.7 else "fuerte")
            direction = "positiva" if pearson_r > 0 else "negativa"
            rows.append({"lago": lake, "relacion": relation, "predictor": predictor,
                         "n_fechas": len(valid), "pearson_r": pearson_r,
                         "pearson_p": pearson_p, "spearman_rho": spearman_rho,
                         "spearman_p": spearman_p,
                         "interpretacion": f"Relación {direction} {strength}; no implica causalidad."})
    result = pd.DataFrame(rows)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(TABLES_DIR / "correlaciones_por_lago.csv", index=False, encoding="utf-8-sig")
    return result


def plot_correlations(metrics: pd.DataFrame):
    """Genera cuatro dispersogramas, dos relaciones por cada lago."""
    import matplotlib.pyplot as plt

    relations = [("ndvi_promedio", "NDVI"), ("ndwi_promedio", "NDWI")]
    lakes = list(metrics["lago"].drop_duplicates())
    fig, axes = plt.subplots(len(lakes), 2, figsize=(12, 5 * len(lakes)), squeeze=False, constrained_layout=True)
    labels = {"amatitlan": "Lago de Amatitlán", "atitlan": "Lago de Atitlán"}
    for row, lake in enumerate(lakes):
        group = metrics.loc[metrics["lago"] == lake]
        for col, (predictor, label) in enumerate(relations):
            ax = axes[row, col]
            valid = group[["cianobacteria_promedio", predictor]].dropna()
            ax.scatter(valid[predictor], valid["cianobacteria_promedio"], color="#176b87", alpha=.85)
            if len(valid) >= 2 and valid[predictor].nunique() > 1:
                slope, intercept = np.polyfit(valid[predictor], valid["cianobacteria_promedio"], 1)
                x = np.linspace(valid[predictor].min(), valid[predictor].max(), 50)
                ax.plot(x, slope * x + intercept, color="#d1495b", linewidth=1.5, label="Tendencia lineal")
                ax.legend()
            ax.set(title=f"{labels.get(lake, lake)}: cianobacteria vs {label}",
                   xlabel=f"{label} promedio", ylabel="Cianobacteria promedio")
            ax.grid(alpha=.25)
    return fig

