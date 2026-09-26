#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# PoesIA conda env — create, update or check it for this machine's hardware
# ═══════════════════════════════════════════════════════════════════════
#   scripts/env.sh create [--name NAME] [--dry-run]
#   scripts/env.sh update [--name NAME] [--dry-run]
#   scripts/env.sh check  [--name NAME]
#
# The env is environment.yml (hardware-neutral base) plus requirements/<tier>.txt
# (the layer), resolved together in one pip run so torch comes from the tier's
# PyTorch index. The tier comes from scripts/hw_profile.sh:
#   gpu-cuda13  desktop (RTX 3070, sm_86): torch cu130 + bitsandbytes/trl/datasets (training)
#   gpu-cuda12  laptop (Quadro M1000M, sm_50): torch cu126, no training stack
#   cpu         no usable NVIDIA GPU: torch +cpu
# HW_PROFILE=<tier> forces a tier (e.g. to dry-run the laptop's layer on the desktop).
# The env name is the same on every machine: poesia (--name or POESIA_ENV_NAME).
# llama.cpp is not part of this env: scripts/build_llama_cpp.sh.
# See README.md "Machines" and ~/dev/workspace-governance/MACHINES.md.
#
# --dry-run changes nothing: it prints the plan, lets conda solve the base
# spec (conda env create --dry-run) and lets pip resolve base + layer
# (pip install --dry-run --report). pip needs the env's Python version: it
# uses the env's own python if the env exists, else POESIA_DRYRUN_PYTHON, else
# python3.X on PATH, else `uv python find 3.X`.
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_SPEC="$PROJECT_ROOT/environment.yml"
ENV_NAME="${POESIA_ENV_NAME:-poesia}"

die() { echo "env.sh: $*" >&2; exit 1; }
usage() { sed -n '5,7p' "${BASH_SOURCE[0]}" | sed 's/^#   //'; }

cmd="${1:-}"
[[ $# -gt 0 ]] && shift
dry_run=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) dry_run=1 ;;
        --name) [[ $# -ge 2 ]] || die "--name needs a value"; ENV_NAME="$2"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done
case "$cmd" in
    create|update|check) ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

command -v conda >/dev/null 2>&1 || die "conda not found on PATH"

HW_TIER="" HW_GPU="" HW_CC="" HW_CUDA_ARCH="" HW_DRIVER_CUDA=""
eval "$("$SCRIPT_DIR/hw_profile.sh" --env)"
LAYER="$PROJECT_ROOT/requirements/$HW_TIER.txt"
[[ -f "$LAYER" ]] || die "no layer for tier '$HW_TIER' (expected $LAYER)"

env_exists() {
    conda env list | awk '{print $1}' | grep -qx -- "$ENV_NAME"
}

# Python minor version pinned by the base spec (python=3.13.14 -> 3.13).
base_python() {
    sed -n -E 's/^  - python=([0-9]+\.[0-9]+).*/\1/p' "$BASE_SPEC" | head -1
}

# environment.yml with the layer prepended to its pip section. conda runs pip
# from the spec's directory, so the spec goes to a temp dir and the relative
# `-e .` becomes the absolute project root.
write_merged_spec() {
    awk -v root="$PROJECT_ROOT" -v layer="$LAYER" '
        /^  - pip:[[:space:]]*$/ { print; print "      - -r " layer; next }
        /^      - -e \.[[:space:]]*$/ { print "      - -e " root; next }
        { print }' "$BASE_SPEC" > "$1"
    grep -qF -- "- -r $LAYER" "$1" || die "could not add the layer to the pip section of $BASE_SPEC"
    grep -qF -- "- -e $PROJECT_ROOT" "$1" || die "no '- -e .' line in the pip section of $BASE_SPEC"
}

# The base spec's pip section as a requirements file (for pip --dry-run).
write_base_requirements() {
    awk '/^  - pip:/ { p = 1; next } p && /^      - / { sub(/^      - /, ""); print }' "$BASE_SPEC" \
        | sed "s#^-e \.\$#-e $PROJECT_ROOT#" > "$1"
}

find_dryrun_python() {
    local want; want="$(base_python)"
    if env_exists; then
        conda run -n "$ENV_NAME" python -c 'import sys; print(sys.executable)'
    elif [[ -n "${POESIA_DRYRUN_PYTHON:-}" ]]; then
        echo "$POESIA_DRYRUN_PYTHON"
    elif command -v "python$want" >/dev/null 2>&1; then
        command -v "python$want"
    elif command -v uv >/dev/null 2>&1 && uv python find "$want" >/dev/null 2>&1; then
        uv python find "$want"
    fi
}

print_profile() {
    echo "tier:   $HW_TIER${HW_PROFILE:+ (forced by HW_PROFILE)}"
    echo "gpu:    ${HW_GPU:-none} (compute capability ${HW_CC:-n/a}; driver supports CUDA ${HW_DRIVER_CUDA:-n/a})"
    echo "env:    $ENV_NAME ($(env_exists && echo exists || echo 'does not exist'))"
    echo "base:   ${BASE_SPEC#"$PROJECT_ROOT"/}"
    echo "layer:  ${LAYER#"$PROJECT_ROOT"/}"
}

dry_run_resolve() {
    local tmp="$1" py report
    echo
    echo "── conda: solve the base spec (conda env create --dry-run) ──"
    if conda env create --dry-run -n "$ENV_NAME-dryrun" -f "$BASE_SPEC" >"$tmp/conda.log" 2>&1; then
        echo "ok: the conda part of environment.yml solves"
    else
        cat "$tmp/conda.log" >&2
        die "conda could not solve environment.yml"
    fi

    echo
    echo "── pip: resolve base + layer (pip install --dry-run --report) ──"
    py="$(find_dryrun_python || true)"
    if [[ -z "$py" ]]; then
        echo "skipped: no Python $(base_python) found (set POESIA_DRYRUN_PYTHON)"
        return 0
    fi
    echo "python: $py ($("$py" --version 2>&1))"
    write_base_requirements "$tmp/base-requirements.txt"
    report="$tmp/pip-report.json"
    # Resolving `-e .` makes setuptools write src/poesia.egg-info; remove it again
    # unless it was already there (an existing editable install owns it).
    local egg="$PROJECT_ROOT/src/poesia.egg-info" had_egg=0 ok=1
    [[ -e "$egg" ]] && had_egg=1
    "$py" -m pip install --dry-run --ignore-installed --no-cache-dir --quiet \
        --report "$report" -r "$tmp/base-requirements.txt" -r "$LAYER" >"$tmp/pip.log" 2>&1 || ok=0
    [[ $had_egg -eq 1 ]] || rm -rf "$egg"
    if [[ $ok -eq 0 ]]; then
        cat "$tmp/pip.log" >&2
        die "pip could not resolve environment.yml + ${LAYER#"$PROJECT_ROOT"/}"
    fi
    "$py" - "$report" <<'PY'
import json, sys
installs = json.load(open(sys.argv[1]))["install"]
names = {i["metadata"]["name"].lower(): i["metadata"]["version"] for i in installs}
print(f"ok: {len(installs)} packages resolve")
for key in ("torch", "triton", "bitsandbytes", "trl", "datasets", "peft", "transformers",
            "sentence-transformers", "mlflow"):
    print(f"  {key:<22} {names.get(key, '-')}")
cuda = sorted(n for n in names if n.startswith(("nvidia-", "cuda-")))
print(f"  CUDA runtime wheels    {len(cuda)}" + (f" ({', '.join(cuda[:3])}, ...)" if cuda else ""))
PY
}

create_or_update() {
    local tmp spec
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/poesia-env.XXXXXX")"
    # shellcheck disable=SC2064  # expand now: the trap must remove this run's temp dir
    trap "rm -rf '$tmp'" EXIT
    spec="$tmp/environment.$HW_TIER.yml"
    write_merged_spec "$spec"

    print_profile
    local conda_cmd
    if [[ "$cmd" == create ]]; then
        env_exists && [[ $dry_run -eq 0 ]] && die "env '$ENV_NAME' already exists; run: scripts/env.sh update"
        conda_cmd=(conda env create -n "$ENV_NAME" -f "$spec")
    else
        env_exists || [[ $dry_run -eq 1 ]] || die "env '$ENV_NAME' does not exist; run: scripts/env.sh create"
        conda_cmd=(conda env update -n "$ENV_NAME" -f "$spec")
    fi
    echo
    echo "plan:"
    echo "  1. ${conda_cmd[*]}"
    echo "     (environment.yml with '-r ${LAYER#"$PROJECT_ROOT"/}' added to its pip section)"
    echo "  2. conda env config vars set -n $ENV_NAME HW_TIER=$HW_TIER"
    echo "  3. scripts/env.sh check --name $ENV_NAME"

    if [[ $dry_run -eq 1 ]]; then
        dry_run_resolve "$tmp"
        echo
        echo "dry run: nothing was changed"
        return 0
    fi

    if env_exists; then
        local recorded
        recorded="$(recorded_tier)"
        if [[ -n "$recorded" && "$recorded" != "$HW_TIER" ]]; then
            echo "warning: env '$ENV_NAME' was built for tier $recorded; packages only in that layer stay installed" >&2
        fi
    fi
    "${conda_cmd[@]}"
    conda env config vars set -n "$ENV_NAME" HW_TIER="$HW_TIER" >/dev/null
    echo "set HW_TIER=$HW_TIER on env '$ENV_NAME'"
    rm -rf "$tmp"
    trap - EXIT
    echo
    check
}

recorded_tier() {
    conda env config vars list -n "$ENV_NAME" 2>/dev/null | sed -n -E 's/^HW_TIER *= *//p' | head -1
}

check() {
    local status=0 recorded
    print_profile
    env_exists || die "env '$ENV_NAME' does not exist; run: scripts/env.sh create"
    recorded="$(recorded_tier)"
    echo "HW_TIER recorded on the env: ${recorded:-<not set>}"
    if [[ "$recorded" != "$HW_TIER" ]]; then
        echo "MISMATCH: the env was built for '${recorded:-unknown}', this machine is '$HW_TIER'; run: scripts/env.sh update"
        status=1
    fi
    echo
    # Passed under other names: activating the env exports its own recorded HW_TIER.
    local probe
    probe="$(mktemp "${TMPDIR:-/tmp}/poesia-env-check.XXXXXX.py")"
    # shellcheck disable=SC2064  # expand now: the trap must remove this run's temp file
    trap "rm -f '$probe'" EXIT
    cat > "$probe" <<'PY'
import importlib.util
import os
import sys

tier = os.environ["POESIA_CHECK_TIER"]
arch = os.environ.get("POESIA_CHECK_ARCH", "")
problems = []

try:
    import torch
except ImportError:
    print("torch: not installed")
    sys.exit(1)

print(f"torch: {torch.__version__} (CUDA {torch.version.cuda or 'none'})")
if tier.startswith("gpu-"):
    want_cuda = {"gpu-cuda13": "13", "gpu-cuda12": "12"}[tier]
    if not (torch.version.cuda or "").startswith(want_cuda + "."):
        problems.append(f"torch is not a CUDA {want_cuda} build")
    archs = torch.cuda.get_arch_list() if torch.cuda.is_available() else []
    print(f"torch arch list: {' '.join(archs) or '(CUDA not available)'}")
    if f"sm_{arch}" not in archs:
        problems.append(f"torch build has no sm_{arch} kernels")
    from poesia.device import cuda_usable

    ok = cuda_usable()
    print(f"trivial CUDA op on {torch.cuda.get_device_name(0) if ok else 'the GPU'}: {'ok' if ok else 'FAILED'}")
    if not ok:
        problems.append("a trivial CUDA op does not run")
elif torch.version.cuda:
    problems.append("cpu tier, but torch is a CUDA build")

has_bnb = importlib.util.find_spec("bitsandbytes") is not None
if tier == "gpu-cuda13":
    from poesia.device import bnb_4bit_usable

    ok = bnb_4bit_usable()
    print(f"bitsandbytes 4-bit quantize on the GPU: {'ok' if ok else 'FAILED'}")
    if not ok:
        problems.append("bitsandbytes 4-bit does not run (training and LoRAClient need it)")
    for mod in ("peft", "trl", "datasets", "mlflow"):
        if importlib.util.find_spec(mod) is None:
            problems.append(f"{mod} missing (training stack)")
else:
    print(f"bitsandbytes: {'installed (unused on this tier)' if has_bnb else 'not installed (expected)'}")

for p in problems:
    print(f"MISMATCH: {p}")
print("ok" if not problems else "env does not match this machine's tier")
sys.exit(1 if problems else 0)
PY
    POESIA_CHECK_TIER="$HW_TIER" POESIA_CHECK_ARCH="$HW_CUDA_ARCH" \
        conda run --no-capture-output -n "$ENV_NAME" python "$probe" || status=1
    return "$status"
}

case "$cmd" in
    create|update) create_or_update ;;
    check) check ;;
esac
