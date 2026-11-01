import pandas as pd
import pytest

from demand_forecast.data import load_series, synthetic_series, validate_series


def test_demo_is_reproducible_and_daily():
    pd.testing.assert_frame_equal(synthetic_series(240, 7), synthetic_series(240, 7))
    assert len(validate_series(synthetic_series(240))) == 240


@pytest.mark.parametrize("problem", ["duplicate", "gap", "negative", "nan", "infinity", "time"])
def test_invalid_history_is_rejected(problem):
    frame = synthetic_series(240).iloc[:5].copy()
    if problem == "duplicate":
        frame.loc[1, "date"] = frame.loc[0, "date"]
    elif problem == "gap":
        frame = frame.drop(index=2)
    elif problem == "negative":
        frame.loc[2, "demand"] = -1
    elif problem == "nan":
        frame.loc[2, "demand"] = float("nan")
    elif problem == "infinity":
        frame.loc[2, "demand"] = float("inf")
    else:
        frame.loc[2, "date"] += pd.Timedelta(hours=1)
    with pytest.raises(ValueError):
        validate_series(frame)


def test_uci_import_uses_only_total_demand_and_date(tmp_path):
    path = tmp_path / "day.csv"
    path.write_text("dteday,cnt,casual,registered,temp\n2011-01-01,100,40,60,0.2\n2011-01-02,200,80,120,0.4\n")
    series = load_series(path)
    assert series.columns.tolist() == ["date", "demand"]
    assert series["demand"].tolist() == [100.0, 200.0]

