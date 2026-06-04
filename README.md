<div align="center">

# DiracQ

### The IDE for the quantum era.

**One workspace to write, compile, simulate, and reason about quantum programs —
across every quantum backend — with AI woven through the whole loop.**

_Built by [**Dirac Technologies**](https://dirac.id) — a deep-tech quantum computing startup from Indonesia._

[![CI](https://github.com/rismanmattotorang/diracq/actions/workflows/ci.yml/badge.svg)](https://github.com/rismanmattotorang/diracq/actions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Built on Zed](https://img.shields.io/badge/editor-Zed%20%2F%20GPUI-orange.svg)](https://github.com/zed-industries/zed)
[![Rust](https://img.shields.io/badge/core-Rust-black.svg)](https://www.rust-lang.org/)
[![Status: alpha](https://img.shields.io/badge/status-alpha-yellow.svg)](#-project-status)

[Vision](#-the-vision) · [Why now](#-why-now) · [What DiracQ is](#-what-diracq-is) · [Architecture](#-architecture) · [Quick start](#-quick-start) · [Roadmap](#-roadmap) · [Company](#-about-dirac-technologies)

</div>

---

## 🌌 The vision

Quantum computing is where classical computing was before the IDE: brilliant
hardware, fragmented tooling. Today a quantum researcher juggles a SDK here, a
transpiler there, a simulator in a notebook, a vendor console for hardware, and a
pile of papers in another window — stitching them together by hand on every
experiment.

**DiracQ collapses that into one surface.** It is our bid to build *the most
complete integrated development environment for quantum computing* — uniting
**simulators, quantum languages, real code, and AI augmentation** for **every
quantum hardware backend**, so that going from an idea (or a paper, or a
molecule) to a validated quantum result is a single, fluid, trustworthy loop.

> We are not building a thin wrapper around one vendor's SDK. We are building the
> **ecosystem layer** for quantum software — the place the work actually happens.

## ⚡ Why now

Three curves are crossing at once, and DiracQ sits exactly at the intersection:

- **Hardware is real and plural.** Trapped ions, superconducting qubits, neutral
  atoms and photonics are all shipping. The winning tools will be *hardware-plural*
  from day one — not locked to a single vendor.
- **Quantum languages grew up.** Type-safe, resource-aware languages (linear
  types, no-cloning enforced at compile time) make it possible to catch the
  expensive class of quantum bugs *at the keystroke* instead of after a costly run.
- **AI can now do real scientific reasoning.** Foundation models for chemistry,
  biology and physics — plus agentic orchestration — can read the literature,
  draft programs, and pre-screen candidates, while a human stays in command at
  every gate that spends real money or runs real hardware.

DiracQ is built so these three reinforce each other inside one editor.

## 🧭 What DiracQ is

DiracQ is a **native, GPU-accelerated desktop IDE** — built as an additive fork of
[Zed](https://github.com/zed-industries/zed) (Rust/GPUI), packaged with **Tauri v2**.
It makes the quantum toolchain feel *built-in, not bolted on*:

| Pillar | What it means in DiracQ |
| --- | --- |
| 🧪 **Simulators** | First-class, reproducible local emulation (seeded, noise-configurable) so you iterate on a laptop before touching hardware. |
| 🔤 **Languages** | Real language intelligence for quantum code — completion, hovers, and **linear-type/ownership diagnostics inline as you type** (no-cloning, use-after-measure caught before a single shot). |
| 🧱 **Codes** | Compile pipelines, circuit & graph canvases, and domain-aware optimisation passes — your programs, visualized and optimized natively on the GPU. |
| 🤖 **AI augmentation** | An agentic layer — *Athena* — that turns a paper, a prompt, or a molecule into a type-checked, emulated, **cited** result, with a hard validation gate and a human approval step before anything irreversible. |

### The DiracQ loop

```
  paper / prompt / molecule
        │
   ┌────▼─────┐   ┌─────────┐   ┌──────────┐   ┌──────────────────────────┐   ┌────────┐
   │  PLAN &  │──▶│ CODE-GEN│──▶│  TYPE-   │──▶│  EMULATE  +  COMPARE TO   │──▶│ REPORT │
   │ RETRIEVE │   │ (Guppy) │   │  CHECK   │   │  CLASSICAL BASELINE       │   │ +cites │
   └──────────┘   └─────────┘   └────┬─────┘   └────────────┬─────────────┘   └────────┘
                       ▲              │  fail → repair       │
                       └──────────────┘            human gate ▼ (the one paid/irreversible step)
                                                        real quantum hardware
```

Nothing is trusted until it **type-checks, emulates, and beats a classical
baseline**. The agent accelerates you; **you** approve the hardware run.

### First-class today, hardware-plural by design

DiracQ's first complete vertical integrates the open-source **Quantinuum** stack —
the **Guppy** language, the **HUGR** intermediate representation, the **TKET/tket2**
compiler, and the **Selene** emulator — as first-class citizens. The architecture
is deliberately backend-agnostic: HUGR-based IR, a swappable compile/emulate
service contract, and a capability-scoped runtime bridge mean **additional
hardware backends and simulators plug in behind the same interfaces** as we expand
the ecosystem.

## 🏗 Architecture

DiracQ follows one uncompromising rule: **never fork the things that move fast.**
Upstream Zed, Tauri and the Quantinuum stack are *pinned dependencies, extended
through documented seams* — never patched in place. For each capability we pick
the **lightest integration seam** that works: a WASM extension, then an agent
server, then (only for true GPU surfaces) a fork crate.

```
L6  Product surfaces   Editor · Agent chat · HUGR viewer · Molecule viewer · Emulation panel · Palette · CI hooks
L5  Agentic AI (Athena) Planner · Retriever (RAG) · Code-gen · Validator · Reporter   (LangGraph · tools · memory)
L4  Integration svcs   Guppy LSP · Compile service · Emulation service · AI inference sidecar · Molecular I/O
L3  IPC & runtime      Tauri Commands · JSON-RPC 2.0 sidecar · event bus · capability-scoped permissions
L2  App shell          Tauri v2 (Rust core + WebView) · window/menus/updater · keychain & secrets
L1  Editor core        Zed (GPUI, Rust) · buffers · language registry · tree-sitter · WGPU
L0  Foundations        Quantum stacks & IRs · AI models · simulators & hardware backends
```

DiracQ owns **L4–L6** (plus a thin L1 registration); everything below is adopted
and extended. See **[`ARCHITECTURE.md`](ARCHITECTURE.md)** for the repository map,
**[`docs/adr/`](docs/adr/README.md)** for the decisions, and
**[`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md)** for the full plan.

### Repository at a glance

| Path | Layer | What |
| --- | --- | --- |
| `crates/diracq_services` | L4 | Service traits + IPC payload contracts |
| `crates/diracq_lsp` | L4 | Guppy LSP (Rust front + language worker) |
| `crates/diracq_compile`, `crates/dirac_passes` | L4 | Compile service + `dirac.chem` optimisation passes |
| `crates/diracq_{selene,hugr,circuit,mol}` | L6 | GPU fork crates (GPUI panels & canvases) |
| `crates/diracq_app` | L1/L6 | Glue — the entire fork delta |
| `extensions/guppy` | L1 | Guppy language WASM extension |
| `sidecar/` | L4 | Python JSON-RPC sidecar (emulate / compile / AI inference / molecular) |
| `agents/athena` | L5 | Athena agent server (LangGraph orchestration) |
| `src-tauri/` | L2/L3 | Tauri shell + least-privilege capabilities |

## 🆚 A strict superset of Zed

DiracQ inherits **every** feature of [Zed](https://github.com/zed-industries/zed)
1.7.0 (all 235 crates — Vim, Git, the debugger, the terminal, real-time
collaboration, the extension ecosystem, themes, edit-prediction, the AI agent
panel) **unchanged**, because it is an *additive-delta fork*: the DiracQ binary is
the Zed workspace built with the additive `diracq_*` crates — **0 Zed sources are
modified**. On top, DiracQ adds the entire quantum toolchain Zed has no equivalent
for. See the verified matrix in **[`docs/FEATURE_PARITY.md`](docs/FEATURE_PARITY.md)**
(reproduce with `./scripts/zed-feature-audit.sh`).

```
DiracQ  =  Zed (all features, unchanged)  ⊕  quantum language · emulation · compile · canvases · agent
```

## 🚀 Quick start

> DiracQ is engineered so the **entire additive layer builds and tests without a
> vendored editor or GPU** — GPUI is gated behind a Cargo feature. You can explore
> the contracts, the LSP, the sidecar and the agent today.

```bash
# 1. Check the additive Rust workspace standalone (no Zed / no GPUI required).
cargo check --workspace

# 2. Smoke-test the Python sidecar (stdlib dispatcher).
cd sidecar && pip install pydantic pytest && PYTHONPATH=. pytest -q

# 3. Build the full editor binary with GPU surfaces (when you're ready):
./scripts/vendor-zed.sh                 # vendor the pinned Zed base
cargo build -p diracq_app --features gpui
```

## 🗺 Roadmap

We ship value early and defer the scarce, expensive parts (real hardware) until
the local loop is rock-solid. Each phase has an explicit exit gate.

| Phase | Theme | Exit criterion |
| --- | --- | --- |
| **P1 — Shell** | Editor fork, Tauri shell, IPC bridge, sidecar supervisor | A signed build that edits files and round-trips a JSON-RPC call |
| **P2 — Quantum** | Guppy LSP, grammar, compile, simulate, circuit/HUGR viewers | Author → compile → emulate a Bell/H₂ kernel in-IDE, reproducibly |
| **P3 — Agentic** | LangGraph agents, RAG, AI model sidecar, molecular pipeline | A paper → validated emulated result with a cited report |
| **P4 — Hardware** | Multi-backend submission, gated runs, calibrated noise, CI benchmarks | A validated pilot run on real hardware, benchmarked vs. classical |

Milestones are demonstrable on a simulator with **no hardware**: **M1 Edit** →
**M2 Run** → **M3 See** → **M4 Augment**. Full detail, workstreams (A–H),
acceptance tests and performance budgets live in
[`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md).

## 📦 Project status

**Alpha — building in the open.** This repository is the architectural scaffold
plus the phased roadmap: every workstream has its crate/service, typed interface
and acceptance test in place, with `TODO`s marking implementation per phase. The
Rust workspace compiles cleanly (`fmt` + `clippy -D warnings`), the Guppy
extension and language config exist, the sidecar dispatcher runs, and the Athena
agent skeleton is wired. We are now implementing the workstreams milestone by
milestone — follow along.

## 🧬 Design principles

Ranked — when two conflict, the lower number wins:

1. **Correctness-first** — type-check, emulate, and baseline before you trust a result.
2. **Native quantum UX** — the quantum stack feels built-in.
3. **Agentic, not autonomous** — humans approve every irreversible or paid action.
4. **Open-stack, no fork drift** — extend through seams; pin versions; contribute upstream.
5. **Secure by construction** — capability-scoped IPC, sandboxed sidecars, keychain-only secrets.
6. **Performance** — sub-frame editor latency; heavy work off the UI thread.
7. **Reproducibility** — seeds, versions and metrics recorded for every run.

## 🤝 Contributing

DiracQ is built to be developed incrementally, workstream by workstream. Each is
scoped to a crate or service with a typed interface and an acceptance test — a
perfect unit of contribution. Start with [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md)
§3, pick a workstream, and build against the seam. Issues and PRs welcome.

## 🏢 About Dirac Technologies

[**Dirac Technologies**](https://dirac.id) is a deep-tech quantum computing
startup based in Indonesia. We are building the software ecosystem for the
quantum era — tools, languages, and AI that make quantum computing usable by
scientists and engineers, not just specialists. DiracQ is our flagship: the
developer surface where quantum work gets done.

We are building from Southeast Asia for the world. If quantum software is your
thing — research, Rust, compilers, GPUI, or agentic AI — we'd love to talk.

🌐 [dirac.id](https://dirac.id)

## 📄 License

Apache-2.0 — see [`LICENSE`](LICENSE).

<div align="center">
<sub>DiracQ · built by Dirac Technologies · Bandung / Jakarta, Indonesia 🇮🇩 · for the quantum era</sub>
</div>
