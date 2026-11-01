from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from demand_forecast.data import download_uci, load_series, synthetic_series
from demand_forecast.evaluation import backtest
from demand_forecast.model import load_model, save_model, train


def main() -> None:
    parser = argparse.ArgumentParser(description="Forecast diário com avaliação temporal reproduzível.")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Gera dados sintéticos; não contém observações reais.")
    demo.add_argument("--days", type=int, default=540)
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--output", type=Path, default=Path("data/demo.csv"))
    download = sub.add_parser("download-uci", help="Baixa day.csv da UCI; requer internet.")
    download.add_argument("--output", type=Path, default=Path("data/uci-day.csv"))
    for name in ("train", "evaluate"):
        command = sub.add_parser(name)
        command.add_argument("--data", type=Path, required=True)
        command.add_argument("--source", required=True, help="Ex.: synthetic-seed42 ou uci-bike-sharing")
        if name == "train":
            command.add_argument("--model", type=Path, default=Path("var/model.joblib"))
        else:
            command.add_argument("--splits", type=int, default=3)
            command.add_argument("--horizon", type=int, default=28)
            command.add_argument("--output", type=Path, default=Path("reports/evaluation.json"))
    predict = sub.add_parser("predict")
    predict.add_argument("--model", type=Path, default=Path("var/model.joblib"))
    predict.add_argument("--horizon", type=int, default=7)
    args = parser.parse_args()
    try:
        if args.command == "demo":
            frame = synthetic_series(args.days, args.seed)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(args.output, index=False, date_format="%Y-%m-%d")
            print(f"{len(frame)} dias sintéticos gravados em {args.output}")
        elif args.command == "download-uci":
            download_uci(args.output)
            print(f"Base UCI normalizada em {args.output}; veja data/README.md para atribuição.")
        elif args.command == "train":
            model = train(load_series(args.data), source=args.source)
            save_model(model, args.model)
            print(json.dumps(model.metadata(), indent=2, ensure_ascii=False))
        elif args.command == "evaluate":
            report = backtest(load_series(args.data), args.splits, args.horizon, args.source)
            report["input_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
            report["runtime"] = {
                "python": platform.python_version(), "numpy": np.__version__,
                "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(report["aggregate"], indent=2))
            print(f"Relatório: {args.output}")
        else:
            print(json.dumps(load_model(args.model).forecast(args.horizon), indent=2))
    except (ValueError, FileNotFoundError, OSError) as error:
        parser.exit(2, f"Erro: {error}\n")


if __name__ == "__main__":
    main()

