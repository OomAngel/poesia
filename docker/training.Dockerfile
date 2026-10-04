# ── PoesIA Training Dockerfile ──────────────────────────────────────
# Build:    docker build -f docker/training.Dockerfile -t poesia-train .
# Run:      docker run --gpus all -v $PWD/models:/app/models poesia-train
#           docker run --gpus all -v $PWD/models:/app/models poesia-train mlops/configs/train_ruli.yaml
# Data:     the corpus is never baked into the image (.dockerignore); mount it:
#           -v $PWD/seeds/poetry_corpus:/app/seeds/poetry_corpus -v $PWD/mlops/data:/app/mlops/data
# ─────────────────────────────────────────────────────────────────────

FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# Python 3.13 (the project's one version); Ubuntu 22.04 has no 3.13 package, so uv installs it.
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV UV_PYTHON_INSTALL_DIR=/opt/python VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH
RUN uv python install 3.13 && uv venv /opt/venv --python 3.13

WORKDIR /app

# Copy all source code
COPY pyproject.toml .
COPY src/ src/
COPY mlops/ mlops/
COPY scripts/ scripts/
COPY seeds/ seeds/

# Training libraries are unpinned here, unlike requirements/gpu-cuda13.txt (open task).
RUN uv pip install --no-cache "." && \
    uv pip install --no-cache mlflow transformers datasets peft bitsandbytes accelerate sentence-transformers

# Models mounted at runtime (not baked in)
VOLUME ["/app/models"]

ENTRYPOINT ["python", "scripts/train_poetry_lora.py"]
CMD ["mlops/configs/train_v1.yaml"]
