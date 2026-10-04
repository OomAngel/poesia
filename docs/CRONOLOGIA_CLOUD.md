# CronologIA — Cloud Migration Guide

> MLflow experiment tracking for PoesIA: from local Docker → serverless → full cloud.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                       PoesIA                                  │
│   (training script, evaluation, experiments.py)              │
│                         │                                     │
│            MLFLOW_TRACKING_URI                                │
│                         │                                     │
│                         ▼                                     │
│  ┌─────────────────────────────────────────────────────┐     │
│  │            CronologIA — Experiment Tracking          │     │
│  │                                                      │     │
│  │  ┌──────────────┐      ┌──────────────────┐          │     │
│  │  │  PostgreSQL   │──────▶   MLflow Server   │          │     │
│  │  │  (metadata)  │      │  (REST API + UI) │          │     │
│  │  └──────────────┘      └──────────────────┘          │     │
│  │         │                       │                     │     │
│  │         ▼                       ▼                     │     │
│  │  ┌──────────────┐      ┌──────────────────┐          │     │
│  │  │  experiments  │      │    Artifact       │          │     │
│  │  │   .jsonl      │      │    Snapshots      │          │     │
│  │  │  (your backup)│      │  (adapter zips)   │          │     │
│  │  └──────────────┘      └──────────────────┘          │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

**Key design:** Your `experiments.jsonl` is always the independent backup.
The PostgreSQL DB is a fast query cache, never the single source of truth.

---

## Tier 1: Local Docker (zero cloud, zero cost)

```bash
cd cronologia
docker compose up -d
```

`cronologia/docker-compose.yml` is a standalone variant; the canonical local stack is
`docker compose -f docker/docker-compose.yml up -d postgres mlflow-ui`
(`docs/INFRASTRUCTURE_DECISIONS.md`). Docker images have not been rebuilt since the
Python 3.13 switch.

- **DB:** Local PostgreSQL container
- **UI:** http://localhost:5000
- **Backup:** `mlops/mlflow_metadata_dump.sql` (in git) + optional `pg_dump`
- **Limits:** Only runs when Docker is up on the machine that hosts it.

---

## Tier 2: Docker + Neon (serverless Postgres in cloud)

[Neon](https://neon.tech) offers a free tier: 500MB storage, 3 branches, autosuspend.

```bash
# 1. Create free account at https://neon.tech
# 2. Get connection string from dashboard
# 3. Set env (fill {user}, {password} and {host} from the dashboard):
export DATABASE_URL="postgresql://{user}:{password}@{host}/mlflow?sslmode=require"

# 4. Start only the UI (DB lives in Neon)
docker compose up -d cronologia-ui
```

```yaml
# docker-compose.neon.yml (partial override)
services:
  cronologia-db:
    profiles: ["local"]  # disabled when using Neon
  cronologia-ui:
    environment:
      DATABASE_URL: "${DATABASE_URL}"
    command: >
      mlflow server --backend-store-uri ${DATABASE_URL}
      --default-artifact-root ./volumes/artifacts --host 0.0.0.0
```

**Pros:** Database is always available. Data survives laptop loss.
**Cons:** Neon free tier suspends after 5min idle (wakes on query).
**Backup:** `pg_dump` weekly → store alongside `mlops/mlflow_metadata_dump.sql`.

---

## Tier 3: Full Cloud (MLflow as a service)

Deploy MLflow server on [Railway](https://railway.app) or [Fly.io](https://fly.io) so it's always accessible.

### Railway

```bash
# railway.json (one-click deploy)
{
  "build": {
    "dockerfile": "Dockerfile.mlflow"
  },
  "services": [{
    "name": "cronologia-ui",
    "port": 5000
  }]
}
```

```dockerfile
# sketch; the repo's MLflow image is docker/mlflow.Dockerfile
FROM ghcr.io/mlflow/mlflow:v3.14.0
CMD mlflow server \
  --backend-store-uri ${DATABASE_URL} \
  --default-artifact-root ${ARTIFACT_BUCKET} \
  --host 0.0.0.0 --port 5000
```

**Railway free tier:** $5 credit/month (~2 services running continuously).
**Fly.io free tier:** 3 shared VMs, 256MB RAM each — enough for MLflow.

### Cost comparison

| Tier | Monthly | Uptime | Setup time |
|------|---------|--------|------------|
| Local Docker | **$0** | Host machine only | 5 min |
| Docker + Neon | **$0** | DB always up | 15 min |
| Railway | ~**$5** | Full cloud | 30 min |
| Fly.io | **$0** | Full cloud (limited RAM) | 30 min |

---

## Migration Path

```
Local Docker ──► Docker + Neon ──► Railway/Fly.io
  (Tier 1)       (5 min change)     (30 min deploy)
```

Each step is a forward-compatible change to the same `docker-compose.yml`.
No data loss — migrate with `pg_dump` → import to Neon → update URI.
