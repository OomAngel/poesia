#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# PoesIA Training Launcher
# ═══════════════════════════════════════════════════════════════════════
# Unified entry point for training — handles env setup, Docker vs local,
# GPU validation, and cleanup.
#
# Usage:
#   ./scripts/launch_training.sh local   mlops/configs/train_qwen3b.yaml
#   ./scripts/launch_training.sh docker  mlops/configs/train_qwen3b.yaml
#   ./scripts/launch_training.sh local   mlops/configs/train_smoke.yaml  --dry-run
#   ./scripts/launch_training.sh local   --list-configs
#   ./scripts/launch_training.sh help
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
POESIA_ENV="$SCRIPT_DIR/poesia_env.sh"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

# ── Help ───────────────────────────────────────────────────────────────
show_help() {
    cat <<EOF
${CYAN}PoesIA Training Launcher${NC}

Usage:
  ./scripts/launch_training.sh <mode> [config] [options]

Modes:
  local   Run training on host machine (uses conda env 'poesia')
  docker  Run training in Docker container via docker-compose

Config:
  Path to a YAML config in mlops/configs/
  Use --list-configs to see available configs

Options:
  --dry-run  Validate environment but don't actually train
  --help     Show this help

Examples:
  # Quick smoke test (1.5B, 1 epoch):
  ./scripts/launch_training.sh local mlops/configs/train_smoke.yaml

  # Full Qwen2.5-3B training:
  ./scripts/launch_training.sh local mlops/configs/train_qwen3b.yaml

  # Docker mode:
  ./scripts/launch_training.sh docker mlops/configs/train_qwen3b.yaml

  # List configs:
  ./scripts/launch_training.sh local --list-configs
EOF
    exit 0
}

# ── List available configs ─────────────────────────────────────────────
list_configs() {
    echo -e "${CYAN}Available training configs:${NC}"
    for f in "$PROJECT_ROOT"/mlops/configs/*.yaml; do
        name=$(basename "$f")
        desc=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# //' || echo "")
        printf "  %-35s %s\n" "$name" "$desc"
    done
    exit 0
}

# ── Validate config exists ─────────────────────────────────────────────
validate_config() {
    local config="$1"
    if [ ! -f "$config" ]; then
        if [ -f "$PROJECT_ROOT/$config" ]; then
            echo "$PROJECT_ROOT/$config"
            return 0
        fi
        fail "Config not found: $config"
        info "Use --list-configs to see available configs"
        exit 1
    fi
    echo "$config"
}

# ── Run locally ────────────────────────────────────────────────────────
run_local() {
    local config_path="$1"
    local dry_run="${2:-false}"

    echo -e "\n${CYAN}═══ Local Training Run ═══${NC}"
    echo "  Config:  ${config_path#$PROJECT_ROOT/}"
    echo "  GPU:     $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo 'N/A')"
    echo "  Env:     ${CONDA_DEFAULT_ENV:-<not activated>}"
    echo "  Tracking: ${MLFLOW_TRACKING_URI:-sqlite:///mlruns/mlflow.db}"
    echo ""

    if [ "$dry_run" = "true" ]; then
        info "DRY RUN — stopping here. Environment is ready."
        info "Would run: python scripts/train_poetry_lora.py ${config_path#$PROJECT_ROOT/}"
        return 0
    fi

    # ── Confirm ────────────────────────────────────────────────────────
    config_name=$(basename "$config_path")
    echo -e "${YELLOW}About to start training with '${config_name}'.${NC}"
    echo -e "${YELLOW}This may take 30min–2h and use significant GPU memory.${NC}"
    echo ""
    read -r -p "Proceed? [y/N] " reply
    if [[ ! "$reply" =~ ^[Yy]$ ]]; then
        info "Cancelled."
        exit 0
    fi

    # ── Run ────────────────────────────────────────────────────────────
    echo ""
    info "Starting training..."
    echo ""

    cd "$PROJECT_ROOT"
    if [ -n "${POESIA_CONDA_RUN:-}" ]; then
        $POESIA_CONDA_RUN python scripts/train_poetry_lora.py "$config_path"
    else
        python scripts/train_poetry_lora.py "$config_path"
    fi

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}✅ Training complete!${NC}"
        # Auto-run post-training pipeline
        info "Running post-training pipeline..."
        bash "$SCRIPT_DIR/post_training_pipeline.sh" 2>/dev/null || warn "Post-training pipeline skipped"
    else
        echo -e "\n${RED}❌ Training failed (exit code $exit_code)${NC}"
    fi
    return $exit_code
}

# ── Run in Docker ──────────────────────────────────────────────────────
run_docker() {
    local config_path="$1"
    local dry_run="${2:-false}"

    echo -e "\n${CYAN}═══ Docker Training Run ═══${NC}"
    echo "  Config:  ${config_path#$PROJECT_ROOT/}"
    echo "  Compose: docker/docker-compose.yml"
    echo ""

    if [ "$dry_run" = "true" ]; then
        info "DRY RUN — environment validated."
        info "Would run: docker compose -f docker/docker-compose.yml run training \\"
        info "              python scripts/train_poetry_lora.py ${config_path#$PROJECT_ROOT/}"
        return 0
    fi

    config_name=$(basename "$config_path")
    echo -e "${YELLOW}About to start Docker training with '${config_name}'.${NC}"
    echo -e "${YELLOW}This will build the Docker image if not cached.${NC}"
    echo ""
    read -r -p "Proceed? [y/N] " reply
    if [[ ! "$reply" =~ ^[Yy]$ ]]; then
        info "Cancelled."
        exit 0
    fi

    echo ""
    info "Starting Docker training..."
    docker compose \
        -f "$PROJECT_ROOT/docker/docker-compose.yml" \
        run --rm training \
        python scripts/train_poetry_lora.py "$config_path"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}✅ Docker training complete!${NC}"
    else
        echo -e "\n${RED}❌ Docker training failed (exit code $exit_code)${NC}"
    fi
    return $exit_code
}

# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

MODE="${1:-help}"
shift 2>/dev/null || true

case "$MODE" in
    help|--help|-h)
        show_help
        ;;
    *)
        CONFIG=""
        DRY_RUN="false"
        for arg in "$@"; do
            case "$arg" in
                --dry-run) DRY_RUN="true" ;;
                --list-configs) list_configs ;;
                *) CONFIG="$arg" ;;
            esac
        done
        if [ -z "$CONFIG" ] && [ "$MODE" != "--list-configs" ]; then
            CONFIG="mlops/configs/train_smoke.yaml"
            warn "No config specified — defaulting to smoke test"
        fi
        ;;
esac

if [ -n "${CONFIG:-}" ]; then
    CONFIG=$(validate_config "$CONFIG")
fi

case "$MODE" in
    local)
        # shellcheck disable=SC1090
        source "$POESIA_ENV" --source
        run_local "$CONFIG" "$DRY_RUN"
        ;;
    docker)
        # shellcheck disable=SC1090
        source "$POESIA_ENV" --source 2>/dev/null || true
        run_docker "$CONFIG" "$DRY_RUN"
        ;;
    dpo)
        # DPO doesn't need a separate config — uses mlops/configs/dpo_v1.yaml
        CONFIG="mlops/configs/dpo_v1.yaml"
        # shellcheck disable=SC1090
        source "$POESIA_ENV" --source
        echo -e "\n${CYAN}═══ DPO Training Run ═══${NC}"
        echo "  Config:  mlops/configs/dpo_v1.yaml"
        echo "  GPU:     $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
        echo ""
        if [ "$DRY_RUN" = "true" ]; then
            info "DRY RUN — would run: python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml"
            exit 0
        fi
        echo -e "${YELLOW}About to start DPO training (~30-60 min).${NC}"
        read -r -p "Proceed? [y/N] " reply
        if [[ ! "$reply" =~ ^[Yy]$ ]]; then
            info "Cancelled."
            exit 0
        fi
        cd "$PROJECT_ROOT"
        if [ -n "${POESIA_CONDA_RUN:-}" ]; then
            $POESIA_CONDA_RUN python scripts/train_poetry_dpo.py "mlops/configs/dpo_v1.yaml"
        else
            python scripts/train_poetry_dpo.py "mlops/configs/dpo_v1.yaml"
        fi
        local dpo_exit=$?
        if [ $dpo_exit -eq 0 ]; then
            info "Running post-training pipeline..."
            bash "$SCRIPT_DIR/post_training_pipeline.sh" 2>/dev/null || warn "Post-training pipeline skipped"
        fi
        exit $dpo_exit
        ;;
    --list-configs)
esac
