"""Build every feature from the forecast date and observations strictly before it."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

MIN_HISTORY = 28
FEATURE_NAMES = [
    "day_index", "weekday_sin", "weekday_cos", "year_sin", "year_cos",
    "lag_1", "lag_7", "lag_14", "mean_7", "mean_28", "std_7",
]


def feature_row(date: pd.Timestamp, history: Sequence[float], origin: pd.Timestamp) -> list[float]:
    if len(history) < MIN_HISTORY:
        raise ValueError(f"São necessários pelo menos {MIN_HISTORY} dias anteriores.")
    recent = np.asarray(history[-MIN_HISTORY:], dtype=float)
    return [
        float((date - origin).days),
        math.sin(2 * math.pi * date.dayofweek / 7),
        math.cos(2 * math.pi * date.dayofweek / 7),
        math.sin(2 * math.pi * date.dayofyear / 365.25),
        math.cos(2 * math.pi * date.dayofyear / 365.25),
        float(recent[-1]), float(recent[-7]), float(recent[-14]),
        float(recent[-7:].mean()), float(recent.mean()), float(recent[-7:].std()),
    ]


def training_matrix(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    values = frame["demand"].to_numpy(dtype=float, copy=True)
    origin = frame["date"].iloc[0]
    rows = [feature_row(frame["date"].iloc[i], values[:i], origin) for i in range(MIN_HISTORY, len(frame))]
    return np.asarray(rows, dtype=float), values[MIN_HISTORY:]

