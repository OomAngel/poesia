#!/usr/bin/env bash
# Quantisation test on Hugging Face Jobs: build GGUF quantisations of Apertus v1.5 8B text,
# serve each with llama.cpp, run the PoesIA safety and metre benchmarks, upload the reports.
# Runs online so the local GPU stays free (benchmark 3 ran the same steps on the RTX 3070).
#
#   hf jobs run --detach --flavor l4x1 --timeout 4h --secrets HF_TOKEN \
#     -e QUANTS="Q4_K_M Q5_K_M Q6_K" -e POESIA_REF=<commit> -e CUDA_ARCH=89 \
#     nvidia/cuda:12.8.1-devel-ubuntu24.04 bash -c "set -e; apt-get update -qq; \
#       apt-get install -y -qq curl ca-certificates >/dev/null; curl -fsSL -o /q.sh \
#       https://raw.githubusercontent.com/OomAngel/poesia/<commit>/scripts/hf_jobs/quant_eval.sh; bash /q.sh"
#
# Not "curl ... | bash": the CUDA image has no curl, and a pipe turned "command not found" into
# an empty script that exited 0, so the first run (2026-10-08) "completed" having done nothing.
#
# Environment: QUANTS (space-separated llama-quantize types), POESIA_REF (engine commit),
# LLAMA_CPP_REF (default: the local server's build), CUDA_ARCH (89 = L4, 86 = A10G /
# RTX 30xx, 80 = A100), SEEDS (default "0 3"; empty skips metre), SAFETY_DATA (test sets; a
# set under data/safety/generated/ is scored on its writer-judge agreed items), RESULTS_REPO (private dataset repo, created if
# missing). HF_TOKEN must allow job runs, gated reads and writes to your own repos.
set -euo pipefail
QUANTS=${QUANTS:-"Q6_K"}
POESIA_REF=${POESIA_REF:?set POESIA_REF to an engine commit}
LLAMA_CPP_REF=${LLAMA_CPP_REF:-f498f864f}  # build 11459, as the local Docker server in benchmark 3
CUDA_ARCH=${CUDA_ARCH:-89}
SEEDS=${SEEDS-"0 3"}  # empty: skip the metre benchmark
SAFETY_DATA=${SAFETY_DATA:-data/safety/safety_reflections.jsonl}  # space-separated JSONL sets
RESULTS_REPO=${RESULTS_REPO:-GrootCappuccino/poesia-experiments}
RUN=${JOB_ID:-local-$(date +%s)}
W=/work; OUT=$W/results/$RUN; mkdir -p "$W" "$OUT"
log() { printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "1/6 system packages"
apt-get update -qq && apt-get install -y -qq git cmake curl ca-certificates build-essential >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null && export PATH="$HOME/.local/bin:$PATH"

log "2/6 llama.cpp $LLAMA_CPP_REF for sm_$CUDA_ARCH"
git clone -q https://github.com/ggml-org/llama.cpp "$W/llama.cpp" && git -C "$W/llama.cpp" checkout -q "$LLAMA_CPP_REF"
cmake -S "$W/llama.cpp" -B "$W/llama.cpp/build" -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" \
  -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF >/dev/null
cmake --build "$W/llama.cpp/build" -j"$(nproc)" --target llama-server llama-quantize >/dev/null
BIN=$W/llama.cpp/build/bin

log "3/6 PoesIA $POESIA_REF and Python 3.13"
curl -fsSL "https://github.com/OomAngel/poesia/archive/$POESIA_REF.tar.gz" | tar -xz -C "$W"
P=$(ls -d "$W"/poesia-*) && cd "$P"
uv venv -q --python 3.13 "$W/venv" && . "$W/venv/bin/activate"
uv pip install -q -e ".[spanish,english-scan,mlops]" huggingface_hub
# The converter pins its own transformers/numpy/torch: a separate environment, so they
# cannot change the one PoesIA is measured in.
uv venv -q --python 3.12 "$W/convenv"
VIRTUAL_ENV="$W/convenv" uv pip install -q -r "$W/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt" \
  --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu

log "4/6 Apertus v1.5 8B text (full precision) -> f16 GGUF"
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("andreasmartin/apertus-v1.5-8b-text", local_dir="/work/hf-text")
PY
"$W/convenv/bin/python" "$W/llama.cpp/convert_hf_to_gguf.py" "$W/hf-text" --outtype f16 --outfile "$W/f16.gguf" >/dev/null

wait_ready() { for _ in $(seq 120); do curl -s -m3 localhost:8080/health | grep -q '"ok"' && return 0; sleep 5; done; return 1; }
for Q in $QUANTS; do
  log "5/6 $Q: quantise, serve, test"
  "$BIN/llama-quantize" "$W/f16.gguf" "$W/$Q.gguf" "$Q" >/dev/null
  "$BIN/llama-server" -m "$W/$Q.gguf" --alias poesia-apertus --jinja -ngl 99 -c 4096 -np 3 \
    --host 127.0.0.1 --port 8080 > "$OUT/server-$Q.log" 2>&1 &
  SERVER=$!
  wait_ready || { echo "server for $Q did not start"; tail -20 "$OUT/server-$Q.log"; kill $SERVER; continue; }
  export LLM_BASE_URL=http://127.0.0.1:8080/v1 LLM_NAME=poesia-apertus LLM_API_KEY=x
  # Positive control first: a server that answers nothing would score as "no answer".
  python scripts/check_endpoint.py | tee "$OUT/check-$Q.txt"
  for d in $SAFETY_DATA; do
    extra=""; case "$d" in */generated/*) extra="--agreed-only";; esac
    python scripts/evaluate_safety_screen.py --openai-compat --data "$d" $extra \
      --out "$OUT/safety-$Q-$(basename "$d" .jsonl).json" >/dev/null
  done
  pids=()
  for s in $SEEDS; do for l in es en it; do
    python scripts/evaluate_adapter_mlflow.py --openai-compat --languages "$l" --samples 3 \
      --seed "$s" --out "$OUT/metre-$Q-s$s-$l.json" > "$OUT/metre-$Q-s$s-$l.log" 2>&1 & pids+=($!)
  done; done
  wait "${pids[@]}" || echo "some $Q runs failed; their logs are uploaded"
  kill $SERVER; wait $SERVER 2>/dev/null || true
  stat -c '%n %s' "$W/$Q.gguf" >> "$OUT/sizes.txt"
done

log "6/6 upload reports to $RESULTS_REPO (private)"
nvidia-smi --query-gpu=name,memory.total --format=csv > "$OUT/gpu.txt"
printf 'quants=%s\npoesia=%s\nllama_cpp=%s\nseeds=%s\n' "$QUANTS" "$POESIA_REF" "$LLAMA_CPP_REF" "$SEEDS" > "$OUT/run.txt"
python - "$RESULTS_REPO" "$OUT" "$RUN" <<'PY'
import sys
from huggingface_hub import HfApi
repo, out, run = sys.argv[1:4]
api = HfApi()
api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=out, path_in_repo=f"quant-eval/{run}")
print(f"uploaded to https://huggingface.co/datasets/{repo}/tree/main/quant-eval/{run}")
PY
