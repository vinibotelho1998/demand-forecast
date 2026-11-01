"""Expanding-window folds with fully recursive forecasts inside each holdout."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from demand_forecast.data import validate_series
from demand_forecast.model import MAX_HORIZON, train


def temporal_folds(length: int, splits: int = 3, horizon: int = 28) -> list[tuple[int, int]]:
    if splits < 1 or splits > 12 or not 1 <= horizon <= MAX_HORIZON:
        raise ValueError("Use 1 a 12 folds e horizonte de 1 a 28 dias.")
    first_end = length - splits * horizon
    if first_end < 120:
        raise ValueError("Histórico insuficiente: preserve 120 dias antes do primeiro teste.")
    return [(first_end + i * horizon, first_end + (i + 1) * horizon) for i in range(splits)]


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    errors = actual - predicted
    return {"mae": round(float(np.abs(errors).mean()), 4), "rmse": round(math.sqrt(float((errors ** 2).mean())), 4)}


def seasonal_naive(history: list[float], horizon: int) -> list[float]:
    if len(history) < 7:
        raise ValueError("Baseline semanal precisa de sete observações.")
    forecast = history.copy()
    for _ in range(horizon):
        forecast.append(forecast[-7])
    return forecast[-horizon:]


def backtest(frame: pd.DataFrame, splits: int = 3, horizon: int = 28, source: str = "unspecified") -> dict:
    frame = validate_series(frame)
    folds = []
    all_actual, all_predicted, all_baseline = [], [], []
    for train_end, test_end in temporal_folds(len(frame), splits, horizon):
        training = frame.iloc[:train_end].copy()
        testing = frame.iloc[train_end:test_end]
        fitted = train(training, source=source)
        predicted = np.array([item["demand"] for item in fitted.forecast(horizon)])
        baseline = np.array(seasonal_naive(training["demand"].tolist(), horizon))
        actual = testing["demand"].to_numpy(dtype=float)
        folds.append({
            "train_start": training["date"].iloc[0].date().isoformat(),
            "train_end": training["date"].iloc[-1].date().isoformat(),
            "test_start": testing["date"].iloc[0].date().isoformat(),
            "test_end": testing["date"].iloc[-1].date().isoformat(),
            "training_rows": len(training), "model": metrics(actual, predicted),
            "seasonal_naive": metrics(actual, baseline),
        })
        all_actual.extend(actual)
        all_predicted.extend(predicted)
        all_baseline.extend(baseline)
    actual = np.array(all_actual)
    model_metrics = metrics(actual, np.array(all_predicted))
    baseline_metrics = metrics(actual, np.array(all_baseline))
    return {
        "source": source, "observations": len(frame), "horizon_days": horizon,
        "protocol": "expanding-window; recursive 28-lag features; no holdout updates within a fold",
        "folds": folds, "aggregate": {"model": model_metrics, "seasonal_naive": baseline_metrics},
        "mae_improvement_percent": round(100 * (1 - model_metrics["mae"] / baseline_metrics["mae"]), 2) if baseline_metrics["mae"] else None,
        "interpretation": "Positive improvement means lower MAE; negative means the baseline won. No tuning on these folds.",
    }

