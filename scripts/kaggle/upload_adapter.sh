#!/usr/bin/env bash
# Convert a PEFT line adapter (the "adapter/" folder a Kaggle training run outputs) to a GGUF LoRA and
# make it the only file of the private Kaggle dataset poesia-line-adapter-gguf, then wait until Kaggle
# serves it (an eval pushed earlier mounts the previous adapter: happened once, 2026-10-15).
#   scripts/kaggle/upload_adapter.sh <adapter_dir> <name, e.g. line-v5> [train_log.json]   (DRY_RUN=1: convert only)
set -euo pipefail
ADAPTER=$1 NAME=$2 LOG=${3:-}
K=$(ls ~/.cache/uv/archive-v0/*/bin/kaggle | head -1)
L=~/.local/share/llama.cpp
OUT=$(mktemp -d)
# The converter reads the gated base model's config with the token stored by `huggingface-cli login`.
read -r HF_TOKEN < ~/.cache/huggingface/token || [ -n "$HF_TOKEN" ]; export HF_TOKEN  # the file has no final newline
PYTHONPATH=$L/gguf-py CUDA_VISIBLE_DEVICES="" \
  ~/miniconda3/envs/poesia/bin/python $L/convert_lora_to_gguf.py "$ADAPTER" \
  --base-model-id andreasmartin/apertus-v1.5-8b-text --outfile "$OUT/$NAME.gguf"
[ -n "$LOG" ] && cp "$LOG" "$OUT/"
echo '{"title": "poesia-line-adapter-gguf", "id": "angelmarquezaguilar/poesia-line-adapter-gguf", "licenses": [{"name": "other"}]}' > "$OUT/dataset-metadata.json"
[ -n "${DRY_RUN:-}" ] && { ls -la "$OUT"; echo "dry run: would upload $OUT"; exit 0; }
(cd /tmp && "$K" datasets version -p "$OUT" -m "$NAME")
for _ in $(seq 1 40); do
  (cd /tmp && "$K" datasets files angelmarquezaguilar/poesia-line-adapter-gguf 2>/dev/null) | grep -q "$NAME.gguf" && { echo "live: $NAME.gguf"; exit 0; }
  sleep 20
done
echo "not live after 13 min: do not push an eval yet" >&2; exit 1
