#!/usr/bin/env bash
# hw-profile — diagnose this machine's GPU and print the environment tier that
# repo env scripts build for. Canonical copy; repos vendor it as
# scripts/hw_profile.sh (keep the copies identical; see MACHINES.md).
#
#   bin/hw-profile            human-readable summary
#   bin/hw-profile --env      KEY=value lines, for `eval "$(hw-profile --env)"`
#   bin/hw-profile --json     one JSON object
#   bin/hw-profile --record   write machines/<hostname>.json next to this script's repo
#
# Tiers (decided by what the GPU can run, not by the driver alone: the laptop's
# driver can report CUDA 13 while its Maxwell GPU has no CUDA 13 builds):
#   gpu-cuda13  compute capability >= 7.5 and a driver that supports CUDA 13
#   gpu-cuda12  compute capability 5.0-7.4, or a driver below CUDA 13
#   cpu         no NVIDIA GPU, nvidia-smi missing, or compute capability < 5.0
#
# Overrides for testing or CI: HW_PROFILE forces the tier; NVIDIA_SMI points at
# another nvidia-smi (e.g. a stub that prints recorded output).
set -euo pipefail

mode="${1:-}"
# nvidia-smi may be off PATH under sudo, systemd units or runner jobs; under WSL it
# lives in /usr/lib/wsl/lib. Missing it must mean "no GPU found", never a crash.
smi="${NVIDIA_SMI:-}"
if [[ -z "$smi" ]]; then
    smi="$(command -v nvidia-smi 2>/dev/null || true)"
    for candidate in /usr/lib/wsl/lib/nvidia-smi /usr/bin/nvidia-smi; do
        if [[ -z "$smi" && -x "$candidate" ]]; then smi="$candidate"; fi
    done
    smi="${smi:-nvidia-smi}"
fi

host="$(hostname)"
os="$(lsb_release -ds 2>/dev/null || uname -sr)"
if grep -qi microsoft /proc/version 2>/dev/null; then
    wsl=""
    if command -v wsl.exe >/dev/null 2>&1; then
        wsl="$(wsl.exe --version 2>/dev/null | tr -d '\0\r' | sed -n 's/^WSL version: //p' | head -1 || true)"
    fi
    wsl="${wsl:-2 (version unknown)}"
else
    wsl="no"
fi

gpu="" cc="" vram_mib="" driver="" driver_cuda=""
if command -v "$smi" >/dev/null 2>&1; then
    if line="$("$smi" --query-gpu=name,compute_cap,memory.total,driver_version \
                --format=csv,noheader,nounits 2>/dev/null | head -1)" && [[ -n "$line" ]]; then
        IFS=',' read -r gpu cc vram_mib driver <<< "$line"
        gpu="$(echo "$gpu" | sed -E 's/^ +| +$//g')"
        cc="${cc// /}"; vram_mib="${vram_mib// /}"; driver="${driver// /}"
        # Header says "CUDA Version: X" natively and "CUDA UMD Version: X" under WSL.
        driver_cuda="$("$smi" 2>/dev/null | sed -n -E 's/.*CUDA (UMD )?Version: *([0-9]+\.[0-9]+).*/\2/p' | head -1)"
    fi
fi

cuda_arch=""
if [[ -n "$cc" ]]; then
    cuda_arch="$(( ${cc%%.*} * 10 + ${cc##*.} ))"
fi

tier="cpu"
if [[ -n "$cuda_arch" && "$cuda_arch" -ge 50 && -n "$driver_cuda" ]]; then
    if [[ "$cuda_arch" -ge 75 && "${driver_cuda%%.*}" -ge 13 ]]; then
        tier="gpu-cuda13"
    elif [[ "${driver_cuda%%.*}" -ge 12 ]]; then
        tier="gpu-cuda12"
    fi
fi
tier="${HW_PROFILE:-$tier}"

case "$mode" in
    --env)
        printf 'HW_TIER=%s\nHW_GPU=%q\nHW_CC=%s\nHW_CUDA_ARCH=%s\nHW_VRAM_MIB=%s\nHW_DRIVER=%s\nHW_DRIVER_CUDA=%s\nHW_HOST=%s\n' \
            "$tier" "$gpu" "$cc" "$cuda_arch" "$vram_mib" "$driver" "$driver_cuda" "$host"
        ;;
    --json|--record)
        json="$(printf '{\n  "hostname": "%s",\n  "tier": "%s",\n  "gpu": "%s",\n  "compute_capability": "%s",\n  "cuda_arch": "%s",\n  "vram_mib": "%s",\n  "driver": "%s",\n  "driver_max_cuda": "%s",\n  "os": "%s",\n  "wsl": "%s",\n  "recorded": "%s"\n}\n' \
            "$host" "$tier" "$gpu" "$cc" "$cuda_arch" "$vram_mib" "$driver" "$driver_cuda" "$os" "$wsl" "$(date +%F)")"
        if [[ "$mode" == --record ]]; then
            dir="$(cd "$(dirname "$0")/.." && pwd)/machines"
            mkdir -p "$dir"
            printf '%s' "$json" > "$dir/$host.json"
            echo "Recorded $dir/$host.json — review and commit it."
        else
            printf '%s' "$json"
        fi
        ;;
    "")
        echo "host:        $host ($os; WSL: $wsl)"
        echo "gpu:         ${gpu:-none} (compute capability ${cc:-n/a}, ${vram_mib:-0} MiB)"
        echo "driver:      ${driver:-n/a} (supports CUDA up to ${driver_cuda:-n/a})"
        echo "tier:        $tier"
        ;;
    *)
        echo "usage: hw-profile [--env|--json|--record]" >&2
        exit 2
        ;;
esac
