#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# PoesIA Environment Manager
# ═══════════════════════════════════════════════════════════════════════
# Source this OR call as entrypoint:
#   source scripts/poesia_env.sh          # activate env in current shell
#   bash scripts/poesia_env.sh --check    # dry-run: verify without activating
#   bash scripts/poesia_env.sh --print    # print env vars for eval
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
POESIA_CONDA_ENV="poesia"
ENV_FILE="$PROJECT_ROOT/.env_mlflow"
REQUIRED_GPU_MIB=4096

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

# ── Detect conda ──────────────────────────────────────────────────────
detect_conda() {
    if command -v conda &>/dev/null; then
        ok "conda found: $(conda --version)"
        return 0
    fi
    # Try common locations
    for d in "$HOME/miniconda3" "$HOME/anaconda3" "/opt/conda"; do
        if [ -f "$d/etc/profile.d/conda.sh" ]; then
            # shellcheck disable=SC1090
            source "$d/etc/profile.d/conda.sh"
            ok "conda loaded from $d"
            return 0
        fi
    done
    fail "conda not found. Install miniconda or use Docker."
    return 1
}

# ── Activate poesia env ────────────────────────────────────────────────
activate_env() {
    if [ "${CONDA_DEFAULT_ENV:-}" = "$POESIA_CONDA_ENV" ]; then
        ok "Already in conda env '${POESIA_CONDA_ENV}'"
        return 0
    fi

    info "Activating conda env '${POESIA_CONDA_ENV}'..."
    if conda env list | grep -q "^${POESIA_CONDA_ENV}[[:space:]]"; then
        conda activate "$POESIA_CONDA_ENV" 2>/dev/null || {
            # If conda activate doesn't work in subshell, use conda run
            warn "Using 'conda run -n $POESIA_CONDA_ENV' wrapper (not fully activated)"
            export POESIA_CONDA_RUN="conda run -n $POESIA_CONDA_ENV"
            return 0
        }
        ok "conda env '${POESIA_CONDA_ENV}' activated"
    else
        fail "Conda env '${POESIA_CONDA_ENV}' does not exist. Run: conda env create -f environment.yml"
        return 1
    fi
}

# ── Source .env_mlflow ─────────────────────────────────────────────────
load_env_file() {
    if [ -f "$ENV_FILE" ]; then
        # shellcheck disable=SC1090
        set -a; source "$ENV_FILE"; set +a
        ok "Loaded env from ${ENV_FILE#$PROJECT_ROOT/}"
    else
        warn "No .env_mlflow found at $ENV_FILE — using defaults"
        export MLFLOW_TRACKING_URI="sqlite:///mlruns/mlflow.db"
    fi
    info "MLFLOW_TRACKING_URI = ${MLFLOW_TRACKING_URI:-<not set>}"
}

# ── Check GPU ──────────────────────────────────────────────────────────
check_gpu() {
    if ! command -v nvidia-smi &>/dev/null; then
        fail "nvidia-smi not found — no GPU available"
        return 1
    fi

    local gpu_count
    gpu_count=$(nvidia-smi --query-gpu=count --format=csv,noheader 2>/dev/null | head -1 || echo "0")
    if [ "$gpu_count" -eq 0 ]; then
        fail "No NVIDIA GPUs detected"
        return 1
    fi

    local free_mib total_mib
    free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
    total_mib=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
    local used_mib=$(( total_mib - free_mib ))

    ok "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
    info "  VRAM: ${used_mib}MiB used / ${total_mib}MiB total"

    if [ "$free_mib" -lt "$REQUIRED_GPU_MIB" ]; then
        warn "Only ${free_mib}MiB free — training may OOM (need ~${REQUIRED_GPU_MIB}MiB)"
    fi
}

# ── Check Python deps ──────────────────────────────────────────────────
check_python_deps() {
    local missing=()
    for pkg in mlflow torch transformers; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            missing+=("$pkg")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        warn "Missing Python packages: ${missing[*]}"
        info "Run: pip install -e '.[spanish,english]'"
        return 1
    fi
    ok "Core Python packages available"
}

# ── Print env for eval ─────────────────────────────────────────────────
print_env() {
    echo "export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI:-sqlite:///mlruns/mlflow.db}"
    echo "export POESIA_CONDA_ENV=$POESIA_CONDA_ENV"
    echo "export POESIA_PROJECT_ROOT=$PROJECT_ROOT"
    [ -n "${CUDA_VISIBLE_DEVICES:-}" ] && echo "export CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
}

# ── Main ───────────────────────────────────────────────────────────────
main() {
    echo -e "\n${CYAN}═══ PoesIA Environment Check ═══${NC}\n"
    cd "$PROJECT_ROOT"

    detect_conda
    echo
    activate_env
    echo
    load_env_file
    echo
    check_gpu
    echo
    check_python_deps

    echo -e "\n${CYAN}═══════════════════════════════════${NC}\n"
}

case "${1:-}" in
    --check)
        # Dry-run mode — just check, don't activate
        POESIA_DRY_RUN=1 main
        ;;
    --print)
        load_env_file
        print_env
        ;;
    --source)
        # Called as 'source scripts/poesia_env.sh --source' — activates in current shell
        detect_conda
        activate_env
        load_env_file
        check_gpu
        echo -e "${GREEN}✓${NC} Environment ready — you can now run training commands"
        ;;
    *)
        main
        ;;
esac
