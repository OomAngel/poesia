#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# GGUF conversion tools for scripts/convert_adapters_to_gguf.py
# ═══════════════════════════════════════════════════════════════════════
#   scripts/setup_gguf_tools.sh [--check]
#
# convert_adapters_to_gguf.py merges an adapter into its base model, then needs
# llama.cpp's convert_hf_to_gguf.py and a built llama-quantize in
# ~/.local/share/llama.cpp (LLAMA_CPP_DIR there). `pip install gguf` is not
# enough: the converter imports its checkout-local packages, and the
# llama-cpp-python wheel ships only shared libraries.
#
# The checkout is pinned to the llama.cpp commit vendored by the llama-cpp-python
# release scripts/build_llama_cpp.sh installs (LLAMA_CPP_PYTHON_VERSION, default
# 0.3.35), so the GGUF files match the runtime that loads them on either machine.
# llama-quantize is a CPU build: no CUDA toolkit needed. Run it in the poesia env
# (the converter uses its torch, transformers and numpy).
# --check only reports whether the tools are in place (non-zero if not).
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

DIR="${LLAMA_CPP_DIR:-$HOME/.local/share/llama.cpp}"
VERSION="${LLAMA_CPP_PYTHON_VERSION:-0.3.35}"
# llama-cpp-python v0.3.35's vendor/llama.cpp submodule (GitHub contents API, 2026-09-27).
COMMIT_0_3_35="4df29be4f4c3673f428170fda944a5b19f743bb8"

die() { echo "setup_gguf_tools.sh: $*" >&2; exit 1; }

check() {
    local ok=0
    for f in convert_hf_to_gguf.py gguf-py/gguf/__init__.py build/bin/llama-quantize; do
        if [[ -e "$DIR/$f" ]]; then echo "ok       $DIR/$f"; else echo "MISSING  $DIR/$f"; ok=1; fi
    done
    if [[ -d "$DIR/.git" ]]; then echo "commit   $(git -C "$DIR" rev-parse HEAD)"; fi
    return "$ok"
}

case "${1:-}" in
    --check) check; exit $? ;;
    "") ;;
    *) sed -n '5p' "${BASH_SOURCE[0]}" | sed 's/^#   //' >&2; exit 2 ;;
esac

if [[ "$VERSION" == 0.3.35 ]]; then
    commit="$COMMIT_0_3_35"
else
    commit="$(gh api "repos/abetlen/llama-cpp-python/contents/vendor/llama.cpp?ref=v$VERSION" --jq .sha)" \
        || die "cannot look up the llama.cpp commit of llama-cpp-python $VERSION (gh api)"
fi

echo "llama.cpp $commit (vendored by llama-cpp-python $VERSION) -> $DIR"
if [[ ! -d "$DIR/.git" ]]; then
    mkdir -p "$DIR"
    git -C "$DIR" init -q
    git -C "$DIR" remote add origin https://github.com/ggml-org/llama.cpp.git
fi
git -C "$DIR" fetch -q --depth 1 origin "$commit"
git -C "$DIR" checkout -q --force FETCH_HEAD

cmake -S "$DIR" -B "$DIR/build" -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build "$DIR/build" --target llama-quantize -j "$(nproc)" >/dev/null
check
