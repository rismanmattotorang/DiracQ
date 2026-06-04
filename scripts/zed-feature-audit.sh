#!/usr/bin/env bash
# Reproducible evidence for DiracQ ⊇ Zed (feature parity by construction) plus
# the DiracQ QC superiority delta. Run after scripts/vendor-zed.sh.
#
# The parity argument is structural: DiracQ is an additive-delta fork (ADR-00/
# ADR-01, G4) — the DiracQ editor binary IS the upstream Zed Cargo workspace
# built together with the additive diracq_* crates. No Zed crate is removed or
# patched in place, so every Zed feature is inherited unchanged.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
zed="$root/third_party/zed"

if [ ! -d "$zed/crates" ]; then
  echo "Zed not vendored. Run scripts/vendor-zed.sh first." >&2
  exit 1
fi

echo "== Upstream Zed =="
echo "version:   $(grep -m1 '^version' "$zed/crates/zed/Cargo.toml" | cut -d'"' -f2)"
echo "crates:    $(ls "$zed/crates" | wc -l | tr -d ' ')"
echo "editor LOC: $(find "$zed/crates/editor" -name '*.rs' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')"

echo
echo "== Zed user-facing features present (inherited unchanged) =="
feat="vim terminal terminal_view git git_ui collab call channel project_panel \
outline_panel search task tasks_ui dap debugger_ui diagnostics editor multi_buffer \
language lsp languages extension extension_host theme theme_selector agent agent_ui \
acp_thread agent_servers copilot edit_prediction repl markdown_preview \
command_palette file_finder go_to_line settings_ui journal feedback onboarding"
present=0; total=0
for f in $feat; do
  total=$((total+1))
  if [ -d "$zed/crates/$f" ]; then present=$((present+1)); else echo "  MISSING: $f"; fi
done
echo "  feature crates present: $present / $total"

echo
echo "== Additive-delta invariant: Zed sources untouched by DiracQ =="
# DiracQ never edits Zed crate sources in place. The only build-time change is
# build-gpui.sh STAGING crates/diracq_gpui into the workspace (an addition).
if git -C "$zed" rev-parse --git-dir >/dev/null 2>&1; then
  modified=$(git -C "$zed" status --porcelain -- crates ':!crates/diracq_gpui' | wc -l | tr -d ' ')
  echo "  modified/deleted Zed crate sources: $modified (expected 0 — additions only)"
fi

echo
echo "== DiracQ additive layer (the QC superiority delta) =="
for c in diracq_services diracq_viz diracq_lsp diracq_compile dirac_passes \
         diracq_selene diracq_hugr diracq_circuit diracq_mol diracq_app diracq_gpui; do
  [ -d "$root/crates/$c" ] && echo "  + crates/$c"
done
[ -d "$root/extensions/guppy" ] && echo "  + extensions/guppy (Guppy language, WASM)"
[ -d "$root/sidecar" ] && echo "  + sidecar (Selene/TKET/HF/molecular JSON-RPC services)"
[ -d "$root/agents/athena" ] && echo "  + agents/athena (ACP agent: orchestration, doc→circuit, synthesis)"

echo
echo "DiracQ = Zed workspace (all features) ⊕ the additive QC layer above."
