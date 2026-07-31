# ── PoesIA Serving Dockerfile ────────────────────────────────────────
# Build:    docker build -f docker/serving.Dockerfile -t poesia-serve .
# Run:      docker run -p 8000:8000 -v $PWD/models:/app/models poesia-serve
# ─────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

RUN apt-get update && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install core dependencies (no GPU libs needed for serving via MLflow)
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy package
COPY src/ src/
COPY pyproject.toml .
RUN pip install -e "."

# Model registry URI (override with env var at runtime)
ENV MLFLOW_TRACKING_URI="sqlite:///mlruns/mlflow.db"

# Serve the latest registered production model
# Override with specific model URI via CMD
EXPOSE 8000
ENTRYPOINT ["mlflow", "models", "serve"]
CMD ["--model-uri", "models:/poesia-lora-soneto-structured/latest", "--host", "0.0.0.0", "--port", "8000"]
