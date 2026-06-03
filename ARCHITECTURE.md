# DiracQ Architecture

This document maps the seven-layer architecture onto the repository so you can
find where any capability lives. See `DEVELOPMENT_ROADMAP.md` for the phased plan
and `docs/adr/` for the rationale.

## Repository layout

```
DiracQ/
├── Cargo.toml                  # Rust workspace (additive crates; excludes the WASM ext)
├── rust-toolchain.toml         # pinned toolchain + extra targets (matches Zed)
├── crates/
│   ├── diracq_services/        # L4 — service traits + serde IPC payloads (compiles standalone)
│   ├── diracq_viz/             # render models for circuit/HUGR canvases
│   ├── diracq_lsp/             # L4 — Guppy LSP (Rust front + guppylang worker); bin: diracq-guppy-lsp
│   ├── diracq_compile/         # L4 — TKET compile service binding
│   ├── dirac_passes/           # dirac.chem HUGR extension + tket2 passes (feature: tket2)
│   ├── diracq_selene/          # L6 — Selene emulation panel  (fork crate, feature: gpui)
│   ├── diracq_hugr/            # L6 — HUGR graph canvas        (fork crate, feature: gpui)
│   ├── diracq_circuit/         # L6 — circuit canvas           (fork crate, feature: gpui)
│   ├── diracq_mol/             # L6 — molecule viewer          (fork crate, feature: gpui)
│   └── diracq_app/             # L1/L6 — glue: the entire fork delta (registers panels/actions)
├── extensions/
│   └── guppy/                  # L1 — Guppy WASM extension (zed_extension_api, own workspace)
├── sidecar/                    # L4 — Python JSON-RPC sidecar (Selene/TKET/HF/molecular)
│   └── diracq_sidecar/
├── agents/
│   └── athena/                 # L5 — Athena ACP agent server (LangGraph graph + tools)
├── src-tauri/                  # L2/L3 — Tauri shell config (capabilities/default.json)
├── examples/experiment.yaml    # a declarative agentic experiment
├── scripts/vendor-zed.sh       # vendor the pinned Zed fork base into third_party/zed
└── docs/                       # ADRs + compatibility matrix
```

## The two IPC channels (L3)

```
Front-end (GPUI/WebView)  --Tauri Commands (typed, capability-gated)-->  Core (Rust)
Core (Rust)  --JSON-RPC 2.0 over length-prefixed stdio-->  Python sidecar / Athena agent
```

- **Tauri command surface** (Table 5): `compile_guppy` (cap `quantum:compile`),
  `emulate_guppy` (`quantum:emulate`), `resources`, `agent_run` (`agent:run`),
  `agent_approve` (`agent:approve`), `infer` (`model:infer`), `parse_molecule`
  (`mol:parse`), `submit_hardware` (`hw:submit` — **gated, not default**).
- **JSON-RPC namespace:** `selene.* tket.* agent.* model.* mol.*`; notifications
  (no id): `agent.progress`, `selene.shot`, `compile.metric`.
- **OpenAPI facade:** the same operations are exposed by a loopback-only,
  token-gated REST facade so CI can drive compile/emulate without the GUI.

## Why the additive design compiles before Zed is vendored

The GPU fork crates and the glue crate gate all GPUI code behind a `gpui` Cargo
feature (off by default), and `dirac_passes` gates tket2 behind a `tket2` feature.
So `cargo check --workspace` validates every contract type and trait standalone;
only the editor-binary build (`--features gpui`, after `scripts/vendor-zed.sh`)
links GPUI and the Quantinuum crates. This is the additive-delta rule made
mechanical.

## The compilation pipeline (Fig. 3)

```
Guppy @guppy kernel
  → HUGR (typed graph IR)
  → Rebase (native gates)
  → Optimise (minimise 2-qubit gate count & depth)
  → Schedule (transport-aware)
  → dirac.chem (domain passes — dirac_passes crate)
  → qsystem prep (Helios-ready; always last)
  → Runnable HUGR / QIR
```

## The agent workflow (Fig. 4)

```
brief/paper → plan → retrieve → pre-screen (FMs) → code-gen (Guppy)
  → validate (check() → Selene emulate → vs. classical baseline)
      ├─ pass → report (+ provenance)
      └─ fail → repair (back to code-gen)
  → human gate → Helios (optional, the single paid/irreversible step)
```
