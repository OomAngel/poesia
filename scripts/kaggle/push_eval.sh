#!/usr/bin/env bash
# Push the Kaggle eval (plain 4-bit Apertus 8B vs the same with the dataset's adapter, es/it/de/fr, seeds
# 0 and 3) pinned to an engine commit that is on GitHub, at a sampling temperature ("" = engine default).
# Needs no secret, so it starts from the API. Results: kernels output -> results/{plain,lora}-s{0,3}-{lang}.json
#   scripts/kaggle/push_eval.sh <poesia commit> [temperature, e.g. 0.6] [penalties, e.g. 0.03,0.08 or 0.03,0.08,lex]
# With penalties the second arm is the same plain file ranked with those weights (repeat,opening)
# instead of the adapter; results are plain-*.json and pen-*.json.      (DRY_RUN=1: show, do not push)
set -euo pipefail
REF=$(git -C ~/dev/poesia rev-parse "$1") TEMP=${2:-} PEN=${3:-}
git -C ~/dev/poesia branch -r --contains "$REF" | grep -q origin/ || { echo "$REF is not pushed" >&2; exit 1; }
K=$(ls ~/.cache/uv/archive-v0/*/bin/kaggle | head -1)
D=$(mktemp -d); HERE=$(dirname "$(readlink -f "$0")")
cp "$HERE/eval/kernel-metadata.json" "$D/"
sed -e "s/POESIA_REF_PLACEHOLDER/$REF/" -e "s/^TEMPERATURE = \"\"/TEMPERATURE = \"$TEMP\"/" -e "s/^PENALTIES = \"\"/PENALTIES = \"$PEN\"/" "$HERE/eval_line_adapter.py" > "$D/eval_line_adapter.py"
grep -n '^POESIA_REF\|^TEMPERATURE\|^PENALTIES' "$D/eval_line_adapter.py"
[ -n "${DRY_RUN:-}" ] && { echo "dry run: would push $D"; exit 0; }
(cd /tmp && "$K" kernels push -p "$D")
