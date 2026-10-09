#!/usr/bin/env bash
# Train the line adapter on Hugging Face Jobs (one L4) with the same worker as the Kaggle
# notebook (scripts/kaggle/train_line_adapter.py: loss on the answer and its end token, the
# page's request shape). No clicks: the job gets HF_TOKEN through --secrets.
#
#   hf jobs run --detach --flavor l4x1 --timeout 2h --secrets HF_TOKEN -e POESIA_REF=<commit> \
#     -e DATA=distill/lines-70b-2026-10-09.jsonl -e ADAPTER_OUT=adapters/line-v1 \
#     nvidia/cuda:12.8.1-devel-ubuntu24.04 bash -c "set -e; apt-get update -qq; \
#       apt-get install -y -qq curl ca-certificates python3 python3-venv >/dev/null; curl -fsSL -o /t.sh \
#       https://raw.githubusercontent.com/OomAngel/poesia/<commit>/scripts/hf_jobs/train_line_adapter.sh; bash /t.sh"
set -euo pipefail
POESIA_REF=${POESIA_REF:?}
DATA=${DATA:?path of the training JSONL inside RESULTS_REPO}
ADAPTER_OUT=${ADAPTER_OUT:?where the adapter goes inside RESULTS_REPO}
RESULTS_REPO=${RESULTS_REPO:-GrootCappuccino/poesia-experiments}
EPOCHS=${EPOCHS:-2} LR=${LR:-1e-4} ACCUM=${ACCUM:-8}
W=/work; mkdir -p $W/out
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null && export PATH="$HOME/.local/bin:$PATH"
uv venv -q --python 3.12 $W/venv && . $W/venv/bin/activate
uv pip install -q torch transformers peft accelerate bitsandbytes huggingface_hub
curl -fsSL -o $W/kaggle_train.py "https://raw.githubusercontent.com/OomAngel/poesia/$POESIA_REF/scripts/kaggle/train_line_adapter.py"
python - "$RESULTS_REPO" "$DATA" <<'PY'
import importlib.util, sys
from huggingface_hub import hf_hub_download, snapshot_download
repo, data = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("k", "/work/kaggle_train.py"); k = importlib.util.module_from_spec(spec); spec.loader.exec_module(k)
open("/work/worker.py", "w").write(k.WORKER)
hf_hub_download(repo, data, repo_type="dataset", local_dir="/work/data")
snapshot_download("andreasmartin/apertus-v1.5-8b-text", local_dir="/work/model",
                  allow_patterns=["*.json", "*.safetensors", "*.jinja", "*.model", "*.txt"])
PY
MODEL=$W/model DATA=$W/data/$DATA OUT=$W/out EPOCHS=$EPOCHS LR=$LR ACCUM=$ACCUM MAXLEN=1024 python $W/worker.py
python - "$RESULTS_REPO" "$ADAPTER_OUT" <<'PY'
import sys
from huggingface_hub import HfApi
repo, out = sys.argv[1:3]
api = HfApi()
api.upload_folder(repo_id=repo, repo_type="dataset", folder_path="/work/out/adapter", path_in_repo=out, commit_message=f"{out}: adapter")
api.upload_file(path_or_fileobj="/work/out/train_log.json", path_in_repo=f"{out}/train_log.json", repo_id=repo, repo_type="dataset")
print(f"uploaded {out}")
PY
