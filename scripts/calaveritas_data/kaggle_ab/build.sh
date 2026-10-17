#!/usr/bin/env bash
# Pack the calaveritas engine for the Kaggle A/B into OUT/dataset/engine.tar.gz (private dataset).
# Only the engine: calaveritas + phonology modules, word lists, generate_batch.py, the few-shot file.
# OUT must be outside the repo (the few-shot file holds poems; poems never go into git).
#   build.sh OUT_DIR KAGGLE_USER
set -euo pipefail
OUT=$1 USER_=$2
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
FEW=$ROOT/seeds/poetry_corpus/external/calaveritas/transcriptions/fewshot.json
STAGE=$OUT/stage
rm -rf "$STAGE" && mkdir -p "$STAGE/src/poesia" "$OUT/dataset"
cp "$ROOT/src/poesia/__init__.py" "$STAGE/src/poesia/"
rsync -a --exclude __pycache__ --exclude static "$ROOT/src/poesia/calaveritas" "$STAGE/src/poesia/"
rsync -a --exclude __pycache__ "$ROOT/src/poesia/phonology" "$STAGE/src/poesia/"
mkdir -p "$STAGE/src/poesia/wordlists" && cp "$ROOT"/src/poesia/wordlists/{__init__.py,es.txt,en.txt} "$STAGE/src/poesia/wordlists/"
cp "$ROOT/scripts/calaveritas_data/generate_batch.py" "$FEW" "$STAGE/"
git -C "$ROOT" rev-parse --short HEAD > "$STAGE/COMMIT"
git -C "$ROOT" diff --quiet HEAD -- src scripts || echo "+uncommitted" >> "$STAGE/COMMIT"
tar -C "$STAGE" -czf "$OUT/dataset/engine.tar.gz" .
cat > "$OUT/dataset/dataset-metadata.json" <<META
{"title": "calaveritas-engine", "id": "$USER_/calaveritas-engine", "licenses": [{"name": "other"}]}
META
echo "built $OUT/dataset/engine.tar.gz ($(du -h "$OUT/dataset/engine.tar.gz" | cut -f1), commit $(tr '\n' ' ' < "$STAGE/COMMIT"))"
