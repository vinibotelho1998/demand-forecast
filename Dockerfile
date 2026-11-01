FROM python:3.11-slim
WORKDIR /app
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src ./src
RUN pip install --no-cache-dir --no-deps . && useradd --create-home appuser
COPY data/demo.csv ./data/demo.csv
RUN demand-forecast train --data data/demo.csv --source synthetic-seed42 --model var/model.joblib \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8002
CMD ["uvicorn", "demand_forecast.api:app", "--host", "0.0.0.0", "--port", "8002"]

