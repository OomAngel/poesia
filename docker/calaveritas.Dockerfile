# Public Calaveritas page (PoesIA). Build from the repo root:
#   docker build -f docker/calaveritas.Dockerfile -t calaveritas-web:app .
# Runs as UID 10001 on a read-only root file system. No poems are baked in (AGENTS.md):
# the few-shot examples are mounted read-only at /data/fewshot.json; the LLM key comes from an env file.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NLTK_DATA=/usr/local/share/nltk_data \
    POESIA_CALAV_HOST=0.0.0.0 \
    POESIA_CALAV_PORT=8080 \
    CALAVERITAS_FEWSHOT=/data/fewshot.json

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin calav
WORKDIR /app

# Runtime dependencies only: the web stack and the Spanish/English scanners.
RUN pip install "fastapi>=0.115" "uvicorn>=0.30" "pydantic>=2.6" "python-dotenv>=1.0" \
        "typer>=0.12" "rich>=13.7" fonemas silabeador pronouncing g2p_en \
 && python -m nltk.downloader -q -d "$NLTK_DATA" averaged_perceptron_tagger_eng cmudict

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps . && rm -rf /app/src /root/.cache

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"]
CMD ["poesia-calaveritas"]
