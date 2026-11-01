from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from demand_forecast.data import validate_series
from demand_forecast.features import FEATURE_NAMES, MIN_HISTORY, feature_row, training_matrix

MAX_HORIZON = 28
ARTIFACT_VERSION = 1


@dataclass
class DemandModel:
    estimator: HistGradientBoostingRegressor
    history: list[float]
    trained_through: pd.Timestamp
    origin: pd.Timestamp
    training_rows: int
    source: str
    artifact_version: int = ARTIFACT_VERSION

    def forecast(self, horizon: int) -> list[dict]:
        if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= MAX_HORIZON:
            raise ValueError(f"Horizonte deve estar entre 1 e {MAX_HORIZON} dias.")
        history = self.history.copy()
        predictions = []
        # Small batches are faster with one native thread and do not monopolize the host.
        with threadpool_limits(limits=1):
            for offset in range(1, horizon + 1):
                date = self.trained_through + pd.Timedelta(days=offset)
                features = np.asarray([feature_row(date, history, self.origin)])
                value = max(0.0, float(self.estimator.predict(features)[0]))
                predictions.append({"date": date.date().isoformat(), "demand": round(value, 3)})
                history.append(value)
        return predictions

    def metadata(self) -> dict:
        return {
            "artifact_version": self.artifact_version,
            "model": "HistGradientBoostingRegressor",
            "trained_through": self.trained_through.date().isoformat(),
            "training_rows": self.training_rows,
            "source": self.source,
            "features": FEATURE_NAMES,
            "max_horizon_days": MAX_HORIZON,
            "strategy": "recursive",
        }


def train(frame: pd.DataFrame, source: str = "unspecified") -> DemandModel:
    frame = validate_series(frame)
    if len(frame) < 120:
        raise ValueError("Treinamento exige pelo menos 120 dias consecutivos.")
    features, target = training_matrix(frame)
    estimator = HistGradientBoostingRegressor(
        max_iter=120, max_leaf_nodes=15, min_samples_leaf=12,
        learning_rate=0.08, l2_regularization=1.0, early_stopping=False, random_state=42,
    )
    with threadpool_limits(limits=1):
        estimator.fit(features, target)
    return DemandModel(
        estimator=estimator,
        history=frame["demand"].tail(MIN_HISTORY).tolist(),
        trained_through=frame["date"].iloc[-1], origin=frame["date"].iloc[0],
        training_rows=len(frame), source=source,
    )


def save_model(model: DemandModel, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(model, temporary)
    temporary.replace(path)


def load_model(path: str | Path) -> DemandModel:
    # joblib uses pickle: only load artifacts produced by this project in a trusted directory.
    model = joblib.load(path)
    if not isinstance(model, DemandModel) or model.artifact_version != ARTIFACT_VERSION:
        raise ValueError("Artefato incompatível; treine novamente com esta versão.")
    return model

