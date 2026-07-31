# ── PoesIA Training Dockerfile ──────────────────────────────────────
# Build:    docker build -f docker/training.Dockerfile -t poesia-train .
# Run:      docker run --gpus all -v $PWD/models:/app/models poesia-train
#           docker run --gpus all -v $PWD/models:/app/models poesia-train mlops/configs/train_ruli.yaml
# ─────────────────────────────────────────────────────────────────────

FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip python3.11-distutils git curl \
    && rm -rf /var/lib/apt/lists/* && \
    python3.11 -m pip install --upgrade pip setuptools wheel -q

WORKDIR /app

# Copy all source code
COPY pyproject.toml .
COPY src/ src/
COPY mlops/ mlops/
COPY scripts/ scripts/
COPY seeds/ seeds/

# Install with Python 3.11 (project requires >=3.11)
# Note: spacy extra is omitted (fails in Python 3.11 containers)
RUN python3.11 -m pip install --no-cache-dir "." && \
    python3.11 -m pip install --no-cache-dir mlflow transformers datasets peft bitsandbytes accelerate sentence-transformers && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python

# Models mounted at runtime (not baked in)
VOLUME ["/app/models"]

ENTRYPOINT ["python", "scripts/train_poetry_lora.py"]
CMD ["mlops/configs/train_v1.yaml"]
