from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from demand_forecast.model import DemandModel, MAX_HORIZON, load_model

logger = logging.getLogger(__name__)


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon: int = Field(default=7, ge=1, le=MAX_HORIZON, strict=True)


class ForecastPoint(BaseModel):
    date: str
    demand: float


class ForecastResponse(BaseModel):
    trained_through: str
    strategy: str
    predictions: list[ForecastPoint]


def create_app(model_path: str | Path | None = None) -> FastAPI:
    application = FastAPI(
        title="Daily Demand Forecast", version="0.1.0",
        description="Recursive daily forecasts. Train a local artifact before serving. Dates refer to the dataset, not today's clock.",
    )
    application.state.model_path = Path(model_path or os.getenv("FORECAST_MODEL_PATH", "var/model.joblib"))
    application.state.model = None

    def current_model() -> DemandModel:
        if application.state.model is None:
            try:
                application.state.model = load_model(application.state.model_path)
            except FileNotFoundError as error:
                raise HTTPException(503, "Modelo ausente. Execute demand-forecast train antes de servir.") from error
            except Exception as error:
                logger.exception("Failed to load forecasting artifact")
                raise HTTPException(503, "Artefato indisponível ou incompatível. Consulte o log e treine novamente.") from error
        return application.state.model

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok", "artifact_exists": application.state.model_path.is_file()}

    @application.get("/model")
    def model_metadata() -> dict:
        return current_model().metadata()

    @application.post("/forecast", response_model=ForecastResponse)
    def forecast(request: ForecastRequest) -> dict:
        model = current_model()
        return {
            "trained_through": model.trained_through.date().isoformat(), "strategy": "recursive",
            "predictions": model.forecast(request.horizon),
        }

    return application


app = create_app()

