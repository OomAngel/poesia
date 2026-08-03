#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# package_share.sh — build a clean, sendable PoesIA snapshot for private sharing
#
# Produces:
#   dist/poesia-share-YYYYMMDD.tar.gz     (~13 MB, tracked files only)
#   dist/poesia-share-YYYYMMDD.bundle     (full git history, only if WITH_BUNDLE=1)
#
# Safety: aborts if any secret file (.env_mlflow, *.key, …) is found in the
# archive. Large build artifacts (mlruns/, models/, mlops/data/) are gitignored
# and therefore never enter the archive.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

DATE="$(date +%Y%m%d)"
OUTDIR="${OUTDIR:-dist}"
mkdir -p "$OUTDIR"

TARBALL="$OUTDIR/poesia-share-${DATE}.tar.gz"

echo "→ Packaging tracked files into ${TARBALL}"
git archive --format=tar.gz --prefix="poesia/" -o "$TARBALL" HEAD

echo "→ Verifying no secrets in the archive…"
if tar -tzf "$TARBALL" | grep -qE '(\.env_mlflow$|\.env$|\.key$|\.pem$|config_local\.yaml$)'; then
    echo "✗ ABORT: potential secret file found in archive" >&2
    tar -tzf "$TARBALL" | grep -E '(\.env_mlflow$|\.env$|\.key$|\.pem$|config_local\.yaml$)' >&2
    exit 1
fi

SIZE="$(du -h "$TARBALL" | cut -f1)"
echo "✓ ${TARBALL}  (${SIZE}) — ready to attach to an email (< 25 MB)"

if [[ "${WITH_BUNDLE:-0}" == "1" ]]; then
    BUNDLE="$OUTDIR/poesia-share-${DATE}.bundle"
    echo "→ Creating full-history bundle ${BUNDLE}"
    git bundle create "$BUNDLE" --all
    du -h "$BUNDLE"
    echo "✓ Recipient can run:  git clone ${BUNDLE}"
fi

echo "✓ Done. Next: see share/SHARING_CHECKLIST.md"
