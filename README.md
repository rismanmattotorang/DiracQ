# DiracQ

**DiracQ** is an enterprise-grade **Quantum–Classical Integrated Development
Environment (QC-IDE)** for ParagonCorp's quantum and AI engineers.

It is built as an **additive-delta fork of [Zed](https://github.com/zed-industries/zed)**
(Rust / GPUI), packaged as a desktop app with **Tauri v2**, and integrates the
open-source **Quantinuum** stack — the Guppy quantum–classical language, the HUGR
intermediate representation, the TKET/tket2 compiler and the Selene emulator — as
first-class citizens of the editing, language-service and execution experience.
Layered on top is an **agentic AI subsystem ("Athena")** that turns papers,
prompts and molecular inputs (SMILES/PDB/.xyz) into annotated, type-checked and
emulated Guppy programs.

> Derived from the ParaQ technical specification (`ParaQ.pdf`) and implemented
> under the **DiracQ** name. See **[`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md)**
> for the phased plan, **[`ARCHITECTURE.md`](ARCHITECTURE.md)** for the layout, and
> **[`docs/adr/`](docs/adr/README.md)** for the decisions.

## The one architectural rule

DiracQ **never forks the Quantinuum stack and never patches Zed or Tauri
internals in place.** Upstream Zed is a *pinned, vendored dependency*; all DiracQ
code is additive — new `crates/diracq_*`, a WASM extension, a Python sidecar and
an ACP agent. For each capability we pick the **lightest integration seam** that
suffices: WASM extension > ACP agent > GPU fork crate (ADR-00). Only four fork
crates carry GPU surfaces.

## Layout (at a glance)

| Path | Layer | What |
|------|-------|------|
| `crates/diracq_services` | L4 | Service traits + IPC payload types (the contracts) |
| `crates/diracq_lsp` | L4 | Guppy LSP (Rust front + guppylang worker) |
| `crates/diracq_compile`, `crates/dirac_passes` | L4 | TKET compile + `dirac.chem` passes |
| `crates/diracq_{selene,hugr,circuit,mol}` | L6 | GPU fork crates (GPUI panels/canvases) |
| `crates/diracq_app` | L1/L6 | Glue — the entire fork delta |
| `extensions/guppy` | L1 | Guppy WASM extension |
| `sidecar/` | L4 | Python JSON-RPC sidecar (Selene/TKET/HF/molecular) |
| `agents/athena` | L5 | Athena ACP agent (LangGraph) |
| `src-tauri/` | L2/L3 | Tauri shell + least-privilege capabilities |

## Quick start

```bash
# 1. Check the additive Rust workspace standalone (no Zed / no GPUI needed).
cargo check --workspace

# 2. Smoke-test the Python sidecar dispatcher (stdlib only).
cd sidecar && PYTHONPATH=. python -m pytest -q   # needs: pip install pydantic pytest

# 3. When you are ready to build the editor binary with GPU surfaces:
./scripts/vendor-zed.sh                          # vendor the pinned Zed fork base
cargo build -p diracq_app --features gpui
```

## Status

This repository is the **scaffold + roadmap**: every workstream (A–H) has its
crate/service, typed interface and acceptance test in place, with `TODO`s marking
the implementation work per phase. The additive Rust workspace compiles, the
Guppy extension and language config exist, the sidecar dispatcher runs, and the
Athena ACP/LangGraph skeleton is wired. See `DEVELOPMENT_ROADMAP.md` §3 for
per-workstream status.

## Design goals (ranked; lower wins on conflict)

**G1** correctness-first · **G2** native quantum UX · **G3** agentic not autonomous ·
**G4** open-stack no fork drift · **G5** secure by construction · **G6** performance ·
**G7** reproducibility.

## Licence

Apache-2.0 (see `LICENSE`).
