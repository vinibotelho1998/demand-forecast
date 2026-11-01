"""The input contract deliberately excludes observed future weather and user counts."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import pandas as pd

UCI_URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"


def validate_series(frame: pd.DataFrame) -> pd.DataFrame:
    if not {"date", "demand"}.issubset(frame.columns):
        raise ValueError("CSV precisa das colunas date e demand, ou dteday e cnt da UCI.")
    result = frame[["date", "demand"]].copy()
    try:
        result["date"] = pd.to_datetime(result["date"], errors="raise")
        result["demand"] = pd.to_numeric(result["demand"], errors="raise").astype(float)
    except (ValueError, TypeError) as error:
        raise ValueError("Datas ou valores de demanda inválidos.") from error
    if result.empty or result.isna().any().any():
        raise ValueError("A série não pode estar vazia nem conter valores ausentes.")
    if not pd.api.types.is_datetime64_any_dtype(result["date"]):
        raise ValueError("Use datas diárias sem misturar fusos ou formatos incompatíveis.")
    if result["date"].dt.tz is not None:
        raise ValueError("Use datas locais sem fuso, uma observação por dia.")
    if not (result["date"] == result["date"].dt.normalize()).all():
        raise ValueError("A série deve usar datas diárias, sem horário.")
    if not np.isfinite(result["demand"]).all() or (result["demand"] < 0).any():
        raise ValueError("Demanda deve ser finita e não negativa.")
    result = result.sort_values("date").reset_index(drop=True)
    if result["date"].duplicated().any():
        raise ValueError("Há datas duplicadas; agregue explicitamente antes de treinar.")
    if not result["date"].diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError("Há dias ausentes; decida o tratamento antes de treinar.")
    return result


def load_series(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if {"dteday", "cnt"}.issubset(frame.columns):
        frame = frame.rename(columns={"dteday": "date", "cnt": "demand"})
    return validate_series(frame)


def synthetic_series(days: int = 540, seed: int = 42) -> pd.DataFrame:
    if not 240 <= days <= 10000:
        raise ValueError("A demonstração exige entre 240 e 10000 dias.")
    dates = pd.date_range("2022-01-01", periods=days, freq="D")
    rng = np.random.default_rng(seed)
    index = np.arange(days)
    weekday = np.array(dates.dayofweek)
    demand = (
        220 + 0.22 * index + 75 * np.sin(2 * np.pi * index / 365.25)
        + np.where(weekday < 5, 60, -35) + rng.normal(0, 16, days)
    )
    return pd.DataFrame({"date": dates, "demand": np.maximum(0, np.round(demand))})


def download_uci(output: Path) -> None:
    """Read only the expected member; never extract arbitrary zip paths."""
    with urlopen(UCI_URL, timeout=30) as response:
        payload = response.read(5_000_001)
    if len(payload) > 5_000_000:
        raise ValueError("Arquivo UCI excedeu o tamanho esperado de 5 MB.")
    with ZipFile(BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.rsplit("/", 1)[-1] == "day.csv"]
        if len(names) != 1:
            raise ValueError("O arquivo recebido não contém um único day.csv.")
        if archive.getinfo(names[0]).file_size > 5_000_000:
            raise ValueError("CSV extraído excedeu o limite esperado.")
        frame = pd.read_csv(archive.open(names[0]))
    normalized = validate_series(frame.rename(columns={"dteday": "date", "cnt": "demand"}))
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output, index=False, date_format="%Y-%m-%d")

