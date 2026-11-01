import numpy as np
import pandas as pd
import pytest

from demand_forecast.data import synthetic_series
from demand_forecast.evaluation import backtest, seasonal_naive, temporal_folds
from demand_forecast.features import MIN_HISTORY, feature_row, training_matrix
from demand_forecast.model import load_model, save_model, train


def test_target_cannot_change_its_own_features():
    frame = synthetic_series(240)
    original_x, original_y = training_matrix(frame)
    target_index = 100
    frame.loc[target_index, "demand"] = 999999
    changed_x, changed_y = training_matrix(frame)
    np.testing.assert_array_equal(original_x[target_index - MIN_HISTORY], changed_x[target_index - MIN_HISTORY])
    assert original_y[target_index - MIN_HISTORY] != changed_y[target_index - MIN_HISTORY]
    assert original_x[target_index + 1 - MIN_HISTORY, 5] != changed_x[target_index + 1 - MIN_HISTORY, 5]


def test_feature_lags_have_correct_offsets():
    row = feature_row(pd.Timestamp("2024-01-29"), list(range(28)), pd.Timestamp("2024-01-01"))
    assert row[0] == 28
    assert row[5:8] == [27.0, 21.0, 14.0]
    assert row[8] == 24
    assert row[9] == 13.5


def test_folds_are_chronological_disjoint_and_cover_the_final_days():
    folds = temporal_folds(540, splits=3, horizon=28)
    assert folds == [(456, 484), (484, 512), (512, 540)]
    with pytest.raises(ValueError, match="Histórico insuficiente"):
        temporal_folds(180, 3, 28)


def test_baseline_recurses_without_observing_holdout():
    assert seasonal_naive(list(range(14)), 10) == [7, 8, 9, 10, 11, 12, 13, 7, 8, 9]


def test_model_round_trip_and_forecast_does_not_mutate_history(tmp_path):
    fitted = train(synthetic_series(240), "synthetic-test")
    before = fitted.history.copy()
    first = fitted.forecast(10)
    assert first == fitted.forecast(10)
    assert fitted.history == before
    assert first[0]["date"] == "2022-08-29"
    assert first[-1]["date"] == "2022-09-07"
    assert all(point["demand"] >= 0 for point in first)
    path = tmp_path / "model.joblib"
    save_model(fitted, path)
    assert load_model(path).forecast(10) == first
    with pytest.raises(ValueError):
        fitted.forecast(29)


def test_fold_forecast_does_not_see_values_inside_its_test_window():
    frame = synthetic_series(240)
    cut = 226
    first = train(frame.iloc[:cut]).forecast(14)
    frame.loc[cut:, "demand"] = 999999
    second = train(frame.iloc[:cut]).forecast(14)
    assert first == second


def test_backtest_contains_baseline_and_reports_actual_boundaries():
    report = backtest(synthetic_series(240), splits=2, horizon=7, source="synthetic-test")
    assert len(report["folds"]) == 2
    assert report["folds"][0]["train_end"] < report["folds"][0]["test_start"]
    assert report["aggregate"]["model"]["mae"] >= 0
    assert report["aggregate"]["seasonal_naive"]["rmse"] >= 0

