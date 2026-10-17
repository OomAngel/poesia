#!/usr/bin/env bash
# Kaggle side of the calaveritas model A/B. The CLI reads the token from ~/.kaggle/access_token.
#   kaggle.sh OUT_DIR dataset|push|status|output|wait
# dataset: create (first time) or version the private dataset; push: push and start the kernel
# (no secrets needed, so an API push runs as is); output: download results to OUT_DIR/out.
set -euo pipefail
OUT=$1 CMD=${2:-status}
HERE=$(cd "$(dirname "$0")" && pwd)
VENV=$OUT/kaggle-venv
[ -x "$VENV/bin/kaggle" ] || { uv venv -q "$VENV" && uv pip install -q --python "$VENV/bin/python" kaggle; }
K=$VENV/bin/kaggle
USER_=$("$VENV/bin/python" -c 'from kaggle import api; api.authenticate(); print(api.config_values["username"])')
SLUG=$USER_/calaveritas-gptoss-ab
case $CMD in
  user) echo "$USER_" ;;
  dataset)
    if $K datasets status "$USER_/calaveritas-engine" >/dev/null 2>&1; then
      $K datasets version -p "$OUT/dataset" -m "engine $(date +%F_%T)"
    else
      $K datasets create -p "$OUT/dataset"   # private unless --public
    fi ;;
  push)
    mkdir -p "$OUT/kernel" && cp "$HERE/run_ab.py" "$OUT/kernel/"
    sed "s#KAGGLE_USER#$USER_#g" "$HERE/kernel-metadata.json" > "$OUT/kernel/kernel-metadata.json"
    $K kernels push -p "$OUT/kernel" && echo "https://www.kaggle.com/code/$SLUG" ;;
  status) $K kernels status "$SLUG" ;;
  output) mkdir -p "$OUT/out" && $K kernels output "$SLUG" -p "$OUT/out" && ls -la "$OUT/out" ;;
  wait)
    while :; do s=$($K kernels status "$SLUG" 2>&1); echo "$(date +%T) $s"
      case "$s" in *COMPLETE*|*ERROR*|*CANCEL*) break ;; esac; sleep 120; done
    mkdir -p "$OUT/out" && $K kernels output "$SLUG" -p "$OUT/out" >/dev/null && tail -30 "$OUT/out/run.log" ;;
esac
