#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# llama.cpp for this machine's GPU — llama-cpp-python in the poesia-gpu env
# ═══════════════════════════════════════════════════════════════════════
#   scripts/build_llama_cpp.sh [--dry-run] [--from-source] [--env NAME]
#   scripts/build_llama_cpp.sh --check [--env NAME]
#
# The GGUF backend (src/poesia/generation/llama_cpp.py, --llm llama_cpp) needs
# llama-cpp-python compiled for the GPU it runs on. It lives in its own env,
# poesia-gpu (same name on every machine; --env or POESIA_LLAMA_ENV), which is
# scripts/env.sh's env plus this build; the script creates it if missing.
# The tier and compute capability come from scripts/hw_profile.sh:
#   gpu-cuda13  desktop (RTX 3070, sm_86): the prebuilt CUDA 13.0 wheel, which
#               carries SASS for sm_75/80/86/89/90; no compiler needed. Other
#               architectures, or --from-source: build with nvcc for $HW_CUDA_ARCH.
#   gpu-cuda12  laptop (Quadro M1000M, sm_50): build from source with
#               CMAKE_CUDA_ARCHITECTURES=$HW_CUDA_ARCH and a CUDA 12.x nvcc. CUDA 13
#               dropped compute capability < 7.5, so its nvcc cannot target sm_50.
#   cpu         the prebuilt CPU wheel.
# HW_PROFILE forces the tier; NVIDIA_SMI points hw_profile.sh at another
# nvidia-smi (e.g. a stub printing the laptop's values) to dry-run its path.
# nvcc is taken from CUDACXX, else PATH, else /usr/local/cuda/bin.
# --dry-run prints the plan (tier, arch, nvcc, CMAKE_ARGS, pip command) and
# exits non-zero if the real run would refuse.
# See README.md "Machines" and ~/dev/workspace-governance/MACHINES.md.
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_NAME="${POESIA_LLAMA_ENV:-poesia-gpu}"
# 0.3.35: newest on PyPI, with prebuilt cu130 and cpu wheels (checked 2026-09-26).
VERSION="${LLAMA_CPP_PYTHON_VERSION:-0.3.35}"
WHEEL_INDEX="https://abetlen.github.io/llama-cpp-python/whl"
# SASS architectures in the prebuilt cu130 wheel's libggml-cuda.so (read from its fatbins).
PREBUILT_CU130_SASS="75 80 86 89 90"
HOOK_NAME="poesia_llama_cpp.sh"

die() { echo "build_llama_cpp.sh: $*" >&2; exit 1; }
usage() { sed -n '5,6p' "${BASH_SOURCE[0]}" | sed 's/^#   //'; }

mode=install dry_run=0 from_source=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) dry_run=1 ;;
        --check) mode=check ;;
        --from-source) from_source=1 ;;
        --env) [[ $# -ge 2 ]] || die "--env needs a value"; ENV_NAME="$2"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done

HW_TIER="" HW_GPU="" HW_CC="" HW_CUDA_ARCH="" HW_VRAM_MIB=""
eval "$("$SCRIPT_DIR/hw_profile.sh" --env)"

env_exists() {
    command -v conda >/dev/null 2>&1 && conda env list | awk '{print $1}' | grep -qx -- "$ENV_NAME"
}
in_env() { conda run --no-capture-output -n "$ENV_NAME" "$@"; }

find_nvcc() {
    if [[ -n "${CUDACXX:-}" ]]; then echo "$CUDACXX"
    elif command -v nvcc >/dev/null 2>&1; then command -v nvcc
    elif [[ -x /usr/local/cuda/bin/nvcc ]]; then echo /usr/local/cuda/bin/nvcc
    fi
}
nvcc_release() { "$1" --version 2>/dev/null | sed -n -E 's/.*release ([0-9]+\.[0-9]+).*/\1/p' | head -1; }

# ── Decide the build ────────────────────────────────────────────────────
method="" cmake_args="" pip_cmd=() blockers=() nvcc="" nvcc_ver="" toolkit=""
case "$HW_TIER" in
    gpu-cuda13|gpu-cuda12)
        [[ -n "$HW_CUDA_ARCH" ]] || die "tier $HW_TIER but no compute capability detected"
        cmake_args="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=$HW_CUDA_ARCH"
        if [[ "$HW_TIER" == gpu-cuda13 && $from_source -eq 0 && " $PREBUILT_CU130_SASS " == *" $HW_CUDA_ARCH "* ]]; then
            method=prebuilt-cu130
            pip_cmd=(python -m pip install --no-cache-dir --no-deps --force-reinstall
                     --only-binary llama-cpp-python --index-url "$WHEEL_INDEX/cu130"
                     "llama-cpp-python==$VERSION")
        else
            method=source-cuda
            nvcc="$(find_nvcc || true)"
            toolkit="a CUDA toolkit"
            if ((HW_CUDA_ARCH < 75)); then
                toolkit="a CUDA 12.x toolkit (12.9 is the last release that targets compute capability < 7.5)"
            fi
            if [[ -z "$nvcc" || ! -x "$nvcc" ]]; then
                blockers+=("nvcc not found. Building for sm_$HW_CUDA_ARCH needs $toolkit. In WSL install NVIDIA's cuda-toolkit-12-9 package from the wsl-ubuntu repository (never a Linux display driver), then put its bin/ first on PATH or set CUDACXX=/usr/local/cuda-12.9/bin/nvcc.")
            else
                nvcc_ver="$(nvcc_release "$nvcc")"
                if [[ -z "$nvcc_ver" ]]; then
                    blockers+=("could not read the CUDA release from '$nvcc --version'")
                elif (( HW_CUDA_ARCH < 75 && ${nvcc_ver%%.*} >= 13 )); then
                    blockers+=("$nvcc is CUDA $nvcc_ver, which cannot compile for sm_$HW_CUDA_ARCH (CUDA 13 dropped compute capability < 7.5). Point CUDACXX at a CUDA 12.x nvcc, e.g. /usr/local/cuda-12.9/bin/nvcc.")
                fi
            fi
            pip_cmd=(python -m pip install --no-cache-dir --no-deps --force-reinstall
                     --no-binary llama-cpp-python "llama-cpp-python==$VERSION")
        fi
        ;;
    cpu)
        method=prebuilt-cpu
        cmake_args="(none: prebuilt CPU wheel)"
        pip_cmd=(python -m pip install --no-cache-dir --no-deps --force-reinstall
                 --only-binary llama-cpp-python --index-url "$WHEEL_INDEX/cpu"
                 "llama-cpp-python==$VERSION")
        ;;
    *) die "unknown tier '$HW_TIER'" ;;
esac
[[ "$method" == prebuilt-cu130 ]] && cmake_args="(none: prebuilt wheel; --from-source would use $cmake_args)"

print_plan() {
    echo "tier:        $HW_TIER${HW_PROFILE:+ (forced by HW_PROFILE)}"
    echo "gpu:         ${HW_GPU:-none} (compute capability ${HW_CC:-n/a}, sm_${HW_CUDA_ARCH:-n/a}, ${HW_VRAM_MIB:-0} MiB)"
    echo "env:         $ENV_NAME ($(env_exists && echo exists || echo 'does not exist; created first with: scripts/env.sh create --name '"$ENV_NAME"))"
    echo "package:     llama-cpp-python==$VERSION"
    echo "method:      $method"
    if [[ "$method" == source-cuda ]]; then
        echo "nvcc:        ${nvcc:-not found}${nvcc_ver:+ (CUDA $nvcc_ver)}"
        echo "CMAKE_ARGS:  $cmake_args"
        echo "command:     CMAKE_ARGS=\"$cmake_args\" CUDACXX=${nvcc:-<nvcc>} ${pip_cmd[*]}"
    else
        echo "CMAKE_ARGS:  $cmake_args"
        echo "command:     ${pip_cmd[*]}"
    fi
    [[ "$method" == prebuilt-cu130 ]] && echo "hook:        \$CONDA_PREFIX/etc/conda/{activate,deactivate}.d/$HOOK_NAME (puts torch's nvidia/cu13/lib on LD_LIBRARY_PATH: the wheel links libcudart.so.13 and libcublas.so.13 without bundling them)"
    local b
    for b in "${blockers[@]}"; do echo "REFUSE:      $b"; done
}

# The prebuilt CUDA wheel does not bundle the CUDA runtime; torch's cu130
# wheels (nvidia-cuda-runtime, nvidia-cublas) install it under nvidia/cu13/lib.
write_cuda_lib_hook() {
    local prefix libdir
    prefix="$(in_env python -c 'import sys; print(sys.prefix)')"
    libdir="$(in_env python -c '
import glob, os, sys
import nvidia
hits = [os.path.dirname(p) for d in nvidia.__path__ for p in glob.glob(os.path.join(d, "*", "lib", "libcudart.so.13"))]
print(hits[0] if hits else "")')"
    [[ -n "$libdir" ]] || die "no libcudart.so.13 under the env's nvidia/ packages (is torch a cu130 build? run scripts/env.sh check --name $ENV_NAME)"
    mkdir -p "$prefix/etc/conda/activate.d" "$prefix/etc/conda/deactivate.d"
    cat > "$prefix/etc/conda/activate.d/$HOOK_NAME" <<EOF
# Written by poesia scripts/build_llama_cpp.sh: the prebuilt CUDA 13 llama-cpp-python
# wheel links libcudart.so.13/libcublas.so.13 without bundling them; torch's wheels do.
export POESIA_LLAMA_SAVED_LD_LIBRARY_PATH="\${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="$libdir\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
EOF
    cat > "$prefix/etc/conda/deactivate.d/$HOOK_NAME" <<'EOF'
# Written by poesia scripts/build_llama_cpp.sh; undoes activate.d/poesia_llama_cpp.sh.
if [ -n "${POESIA_LLAMA_SAVED_LD_LIBRARY_PATH:-}" ]; then
    export LD_LIBRARY_PATH="$POESIA_LLAMA_SAVED_LD_LIBRARY_PATH"
else
    unset LD_LIBRARY_PATH
fi
unset POESIA_LLAMA_SAVED_LD_LIBRARY_PATH
EOF
    echo "wrote the LD_LIBRARY_PATH hook for $libdir"
}

check() {
    env_exists || die "env '$ENV_NAME' does not exist; run: scripts/build_llama_cpp.sh"
    local probe status=0
    probe="$(mktemp "${TMPDIR:-/tmp}/poesia-llama-check.XXXXXX.py")"
    # shellcheck disable=SC2064  # expand now: the trap must remove this run's temp file
    trap "rm -f '$probe'" EXIT
    cat > "$probe" <<'PY'
import glob
import os
import sys

tier = os.environ["POESIA_CHECK_TIER"]
root = os.environ["POESIA_PROJECT_ROOT"]
try:
    import llama_cpp
except Exception as e:  # ImportError, or RuntimeError when a CUDA library is missing
    print(f"llama_cpp: does not import: {e}")
    sys.exit(1)
offload = llama_cpp.llama_supports_gpu_offload()
print(f"llama_cpp: {llama_cpp.__version__}, GPU offload: {offload}")
problems = []
if tier.startswith("gpu-") and not offload:
    problems.append("this is a CPU-only build")

path = os.environ.get("LLAMACPP_MODEL_PATH")
if not path:
    found = sorted(glob.glob(os.path.join(root, "models", "*", "*-Q4_K_M.gguf")), key=os.path.getsize)
    path = found[0] if found else None
if path and os.path.exists(path):
    # Same settings as LlamaCppLoRAClient: every layer on the GPU.
    llm = llama_cpp.Llama(model_path=path, n_gpu_layers=-1, n_ctx=512, verbose=False)
    text = llm("Write a soneto in Spanish.\nRhyme scheme: ABBA ABBA CDC DCD.\nTheme: mar.\n\n",
               max_tokens=12, temperature=0)["choices"][0]["text"]
    print(f"GGUF smoke test ({os.path.relpath(path, root)}): {text.strip()!r}")
else:
    print("GGUF smoke test: skipped, no models/*/*-Q4_K_M.gguf (dvc pull) and no LLAMACPP_MODEL_PATH")
for p in problems:
    print(f"MISMATCH: {p}")
sys.exit(1 if problems else 0)
PY
    echo "tier: $HW_TIER; env: $ENV_NAME"
    POESIA_CHECK_TIER="$HW_TIER" POESIA_PROJECT_ROOT="$PROJECT_ROOT" in_env python "$probe" || status=1
    return "$status"
}

if [[ "$mode" == check ]]; then
    check
    exit $?
fi

print_plan
if [[ $dry_run -eq 1 ]]; then
    echo
    if ((${#blockers[@]})); then
        echo "dry run: the real run would refuse (see REFUSE above); nothing was changed"
        exit 1
    fi
    echo "dry run: nothing was changed"
    exit 0
fi
((${#blockers[@]} == 0)) || exit 1

command -v conda >/dev/null 2>&1 || die "conda not found on PATH"
if ! env_exists; then
    echo; echo "── creating env $ENV_NAME (scripts/env.sh create --name $ENV_NAME) ──"
    "$SCRIPT_DIR/env.sh" create --name "$ENV_NAME"
fi
echo; echo "── installing llama-cpp-python==$VERSION ($method) into $ENV_NAME ──"
# Its own dependencies (numpy, jinja2, typing-extensions) are in the base spec already.
in_env python -m pip install --no-cache-dir "diskcache>=5.6.1"
if [[ "$method" == source-cuda ]]; then
    # --no-cache-dir: pip's wheel cache ignores CMAKE_ARGS and could hand back a build for another GPU.
    CMAKE_ARGS="$cmake_args" CUDACXX="$nvcc" in_env "${pip_cmd[@]}"
else
    in_env "${pip_cmd[@]}"
fi
[[ "$method" == prebuilt-cu130 ]] && write_cuda_lib_hook
echo
check
