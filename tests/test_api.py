from fastapi.testclient import TestClient
import pytest

from demand_forecast.api import create_app
from demand_forecast.data import synthetic_series
from demand_forecast.model import save_model, train


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    path = tmp_path_factory.mktemp("artifact") / "model.joblib"
    save_model(train(synthetic_series(240), "synthetic-api-test"), path)
    return path


def test_missing_artifact_is_a_service_error_not_a_fake_prediction(tmp_path):
    with TestClient(create_app(tmp_path / "missing.joblib")) as client:
        assert client.get("/health").json() == {"status": "ok", "artifact_exists": False}
        assert client.post("/forecast", json={"horizon": 7}).status_code == 503


def test_valid_prediction_and_metadata(artifact):
    with TestClient(create_app(artifact)) as client:
        response = client.post("/forecast", json={"horizon": 3})
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["predictions"]) == 3
        assert payload["predictions"][0]["date"] > payload["trained_through"]
        assert payload["strategy"] == "recursive"
        assert client.get("/model").json()["source"] == "synthetic-api-test"


@pytest.mark.parametrize("payload", [{"horizon": 0}, {"horizon": 29}, {"horizon": True}, {"horizon": "7"}, {"horizon": 1, "weather": 0.8}])
def test_request_rejects_invalid_horizon_and_unknown_fields(artifact, payload):
    with TestClient(create_app(artifact)) as client:
        assert client.post("/forecast", json=payload).status_code == 422

