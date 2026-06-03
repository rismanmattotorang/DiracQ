#!/usr/bin/env bash
# Vendor the upstream Zed fork base as a PINNED dependency (ADR-00/ADR-01, G4).
#
# DiracQ never edits Zed in place. This script checks out a pinned Zed tag into
# third_party/zed so the GPU fork crates (built with --features gpui) and the
# editor binary can link GPUI. The pin is recorded in docs/compatibility-matrix.md;
# bump it as a *managed* upgrade (rebase the additive delta), never a silent drift.
set -euo pipefail

ZED_REPO="${ZED_REPO:-https://github.com/zed-industries/zed}"
# Pin a concrete tag/commit before release; "main" here is a placeholder.
ZED_REF="${ZED_REF:-main}"
DEST="third_party/zed"

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [ -d "$DEST/.git" ]; then
  echo "[vendor-zed] updating existing checkout at $DEST to $ZED_REF"
  git -C "$DEST" fetch --depth 1 origin "$ZED_REF"
  git -C "$DEST" checkout --force FETCH_HEAD
else
  echo "[vendor-zed] cloning $ZED_REPO@$ZED_REF (shallow) into $DEST"
  mkdir -p third_party
  git clone --depth 1 --branch "$ZED_REF" "$ZED_REPO" "$DEST" 2>/dev/null \
    || git clone --depth 1 "$ZED_REPO" "$DEST"
fi

echo "[vendor-zed] done. Build the GPU surfaces with:  cargo build -p diracq_app --features gpui"
echo "[vendor-zed] NOTE: third_party/zed is gitignored — it is a pinned dependency, not committed source."
