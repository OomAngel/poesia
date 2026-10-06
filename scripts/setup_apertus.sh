#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# Apertus v1.5 8B for PoesIA: download, GGUF Q4_K_M, Ollama (Hack Apertus)
# ═══════════════════════════════════════════════════════════════════════
#   scripts/setup_apertus.sh [--official] [--keep-f16] [--skip-download] [--no-ollama]
#   scripts/setup_apertus.sh --check
#
# Run in WSL on the desktop, in the poesia env (scripts/env.sh). Steps:
#   1. download the text backbone of Apertus v1.5 8B
#      (andreasmartin/apertus-v1.5-8b-text: the official model with its image and
#      audio towers removed, stock ApertusForCausalLM, ~16 GB bf16) and record the
#      resolved revisions in $APERTUS_DIR/provenance.json;
#      --official also downloads the gated official weights (swiss-ai/Apertus-v1.5-8B,
#      ~18 GB). Accept the terms on its Hugging Face page and `hf auth login` first.
#   2. check the chat template uses Apertus' turn tokens (the Ollama template below
#      depends on them);
#   3. convert to GGUF f16 with llama.cpp's convert_hf_to_gguf.py, then quantize to
#      Q4_K_M (~5 GB) with llama-quantize. Both come from scripts/setup_gguf_tools.sh,
#      pinned to llama.cpp 4df29be, which registers ApertusForCausalLM (checked
#      2026-10-06: conversion/llama.py, src/llama-arch.cpp LLM_ARCH_APERTUS);
#   4. register the GGUF in Ollama over its REST API (works whether Ollama runs in
#      Windows or in WSL; OLLAMA_HOST, default http://localhost:11434) as
#      $APERTUS_OLLAMA_NAME (default apertus-v1.5-8b-text:q4km), with the Apertus
#      chat format from llama.cpp's models/templates/Apertus-8B-Instruct.jinja and
#      thinking ("Deliberation") disabled;
#   5. smoke test: one Spanish line through /api/chat.
# Disk: ~16 GB download + ~16 GB f16 + ~5 GB Q4 during the run; the f16 is deleted
# afterwards unless --keep-f16. --check reports what is already in place.
# Then: OLLAMA_MODEL=apertus-v1.5-8b-text:q4km poesia write --llm ollama --theme luna
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APERTUS_DIR="${APERTUS_DIR:-$PROJECT_ROOT/models/apertus}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/.local/share/llama.cpp}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
NAME="${APERTUS_OLLAMA_NAME:-apertus-v1.5-8b-text:q4km}"

TEXT_REPO="andreasmartin/apertus-v1.5-8b-text"
OFFICIAL_REPO="swiss-ai/Apertus-v1.5-8B"
TEXT_DIR="$APERTUS_DIR/hf-text"
OFFICIAL_DIR="$APERTUS_DIR/hf-official"
F16="$APERTUS_DIR/apertus-v1.5-8b-text-f16.gguf"
Q4="$APERTUS_DIR/apertus-v1.5-8b-text-Q4_K_M.gguf"

OFFICIAL=0; KEEP_F16=0; SKIP_DOWNLOAD=0; OLLAMA=1; CHECK=0
for arg in "$@"; do
    case "$arg" in
        --official) OFFICIAL=1 ;;
        --keep-f16) KEEP_F16=1 ;;
        --skip-download) SKIP_DOWNLOAD=1 ;;
        --no-ollama) OLLAMA=0 ;;
        --check) CHECK=1 ;;
        *) sed -n '5,6p' "${BASH_SOURCE[0]}" | sed 's/^#   //' >&2; exit 2 ;;
    esac
done

die() { echo "setup_apertus.sh: $*" >&2; exit 1; }
step() { echo; echo "── $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

ollama_up() { curl -fsS --max-time 5 "$OLLAMA_HOST/api/version" >/dev/null 2>&1; }
ollama_has() {
    curl -fsS --max-time 10 "$OLLAMA_HOST/api/tags" 2>/dev/null \
        | python -c "import json,sys; n=sys.argv[1]; sys.exit(0 if any(m['name']==n for m in json.load(sys.stdin)['models']) else 1)" "$NAME"
}

if (( CHECK )); then
    for f in "$TEXT_DIR/config.json" "$Q4"; do
        if [[ -e "$f" ]]; then echo "ok       $f"; else echo "MISSING  $f"; fi
    done
    [[ -e "$OFFICIAL_DIR/config.json" ]] && echo "ok       $OFFICIAL_DIR (official weights)"
    bash "$SCRIPT_DIR/setup_gguf_tools.sh" --check || true
    if ollama_up; then
        if ollama_has; then echo "ok       Ollama model $NAME"; else echo "MISSING  Ollama model $NAME"; fi
    else
        echo "MISSING  Ollama at $OLLAMA_HOST (not running)"
    fi
    exit 0
fi

have python || die "python not found: activate the poesia env first (source scripts/poesia_env.sh)"
have curl || die "curl not found"
mkdir -p "$APERTUS_DIR"

# ── 1. Download ─────────────────────────────────────────────────────────
if (( ! SKIP_DOWNLOAD )); then
    have hf || die "the hf CLI is missing: pip install -U 'huggingface_hub[cli]' in the poesia env"
    step "1. Downloading $TEXT_REPO -> $TEXT_DIR (~16 GB; resumes if interrupted)"
    hf download "$TEXT_REPO" --local-dir "$TEXT_DIR"
    if (( OFFICIAL )); then
        step "1b. Downloading the official $OFFICIAL_REPO -> $OFFICIAL_DIR (~18 GB, gated)"
        hf download "$OFFICIAL_REPO" --local-dir "$OFFICIAL_DIR" || die \
            "official download refused: accept the terms at https://huggingface.co/$OFFICIAL_REPO while signed in, run 'hf auth login', then rerun with --official"
    fi
    python - "$APERTUS_DIR/provenance.json" "$TEXT_REPO" "$OFFICIAL_REPO" "$OFFICIAL" <<'PY'
import json, sys
from datetime import datetime, timezone
from huggingface_hub import model_info
out, text_repo, official_repo, official = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
record = {"recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "models": {}}
for repo in [text_repo] + ([official_repo] if official else []):
    try:
        info = model_info(repo)
        record["models"][repo] = {"revision": info.sha, "license": (info.card_data or {}).get("license")}
    except Exception as exc:  # provenance is best-effort; the download already succeeded
        record["models"][repo] = {"error": str(exc)}
record["derived_from"] = "swiss-ai/Apertus-v1.5-8B (text backbone; image and audio towers removed)"
json.dump(record, open(out, "w"), indent=2)
print(f"provenance -> {out}")
PY
fi
[[ -f "$TEXT_DIR/config.json" ]] || die "no model at $TEXT_DIR (run without --skip-download)"

# ── 2. Chat format check ────────────────────────────────────────────────
step "2. Checking the chat template's turn tokens"
python - "$TEXT_DIR" <<'PY'
import json, pathlib, sys
d = pathlib.Path(sys.argv[1])
text = ""
for name in ("chat_template.jinja", "tokenizer_config.json"):
    p = d / name
    if p.exists():
        text += p.read_text(encoding="utf-8")
need = ["<|system_start|>", "<|developer_start|>", "<|user_start|>", "<|user_end|>",
        "<|assistant_start|>", "<|assistant_end|>"]
missing = [t for t in need if t not in text]
if missing:
    sys.exit(f"chat template lacks {missing}: the Ollama template in this script would be wrong; stop and compare with {d}")
print("ok: Apertus turn tokens present")
PY

# ── 3. GGUF ─────────────────────────────────────────────────────────────
if [[ ! -f "$Q4" ]]; then
    step "3. llama.cpp conversion tools ($LLAMA_CPP_DIR)"
    bash "$SCRIPT_DIR/setup_gguf_tools.sh" --check >/dev/null 2>&1 || bash "$SCRIPT_DIR/setup_gguf_tools.sh"
    if [[ ! -f "$F16" ]]; then
        step "3a. Converting to GGUF f16 -> $F16"
        python "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" "$TEXT_DIR" --outtype f16 --outfile "$F16" \
            || die "conversion failed. If it says the BPE pre-tokenizer was not recognized, the v1.5 vocabulary needs a hash entry in llama.cpp; fall back to transformers 4-bit (see docs in career-assets hack-apertus.md)"
    fi
    step "3b. Quantizing to Q4_K_M -> $Q4"
    "$LLAMA_CPP_DIR/build/bin/llama-quantize" "$F16" "$Q4" Q4_K_M
    (( KEEP_F16 )) || { rm -f "$F16"; echo "removed $F16 (use --keep-f16 to keep it)"; }
else
    echo "GGUF already present: $Q4"
fi

# ── 4. Ollama ───────────────────────────────────────────────────────────
if (( ! OLLAMA )); then
    echo; echo "Done (Ollama step skipped). GGUF: $Q4"
    exit 0
fi
step "4. Registering $NAME in Ollama at $OLLAMA_HOST"
ollama_up || die "Ollama is not reachable at $OLLAMA_HOST: start it (Windows tray or 'ollama serve'), or set OLLAMA_HOST, then rerun with --skip-download"
python - "$OLLAMA_HOST" "$NAME" "$Q4" <<'PY'
import hashlib, json, sys, urllib.request
host, name, path = sys.argv[1], sys.argv[2], sys.argv[3]
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 24), b""):
        h.update(chunk)
digest = "sha256:" + h.hexdigest()

def call(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=3600) as resp:
        return resp.status, resp.read()

try:
    status, _ = call("HEAD", f"{host}/api/blobs/{digest}")
except urllib.error.HTTPError as exc:
    status = exc.code
if status != 200:
    print(f"uploading {path} to Ollama ({digest[:19]}...)")
    import os
    with open(path, "rb") as f:  # streamed: the file is ~5 GB
        call("POST", f"{host}/api/blobs/{digest}", data=f,
             headers={"Content-Type": "application/octet-stream",
                      "Content-Length": str(os.path.getsize(path))})

# Apertus chat format (llama.cpp models/templates/Apertus-8B-Instruct.jinja), thinking off.
template = (
    "{{- if .System }}<|system_start|>{{ .System }}<|system_end|>"
    "{{- else }}<|system_start|>You are Apertus, a helpful assistant created by the SwissAI initiative.<|system_end|>{{- end }}"
    "<|developer_start|>Deliberation: disabled\nTool Capabilities: disabled<|developer_end|>"
    "{{- range .Messages }}"
    "{{- if eq .Role \"user\" }}<|user_start|>{{ .Content }}<|user_end|>"
    "{{- else if eq .Role \"assistant\" }}<|assistant_start|>{{ .Content }}<|assistant_end|>"
    "{{- end }}{{- end }}<|assistant_start|>"
)
body = {
    "model": name,
    "files": {path.rsplit("/", 1)[-1]: digest},
    "template": template,
    "parameters": {"stop": ["<|assistant_end|>", "<|user_start|>"], "num_ctx": 4096},
    "stream": False,
}
status, out = call("POST", f"{host}/api/create", data=json.dumps(body).encode(),
                   headers={"Content-Type": "application/json"})
print(out.decode()[:300])
PY

# ── 5. Smoke test ───────────────────────────────────────────────────────
step "5. Smoke test"
python - "$OLLAMA_HOST" "$NAME" <<'PY'
import json, sys, time, urllib.request
host, name = sys.argv[1], sys.argv[2]
body = {"model": name, "stream": False, "options": {"temperature": 0.7, "seed": 0},
        "messages": [{"role": "user", "content":
            "Escribe un solo verso endecasílabo sobre la luna. Responde solo con el verso."}]}
t0 = time.time()
req = urllib.request.Request(f"{host}/api/chat", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as resp:
    msg = json.loads(resp.read())["message"]["content"].strip()
print(f"{name} ({time.time() - t0:.1f} s): {msg}")
if not msg or "<|" in msg:
    sys.exit("smoke test output is empty or leaks template tokens: check the template")
PY
echo
echo "Ready. Next: OLLAMA_MODEL=$NAME poesia write --llm ollama --theme luna"
