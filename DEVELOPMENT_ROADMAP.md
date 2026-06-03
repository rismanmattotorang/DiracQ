# DiracQ — Development Roadmap

> DiracQ is an enterprise-grade Quantum–Classical Integrated Development
> Environment (QC-IDE). It is built as an **additive-delta fork of Zed**
> (Rust/GPUI), packaged with **Tauri v2**, integrating the **Quantinuum** stack
> (Guppy · HUGR · TKET/tket2 · Selene) as first-class citizens, with an
> **agentic AI layer** ("Athena") that turns papers, prompts and molecular
> inputs into type-checked, emulated Guppy programs.
>
> This document derives the implementation programme from the ParaQ technical
> specification (`ParaQ.pdf`), rebranded and scoped as **DiracQ**. It is meant
> to be executed incrementally: every workstream names the crate/service it
> creates, the Zed integration seam it uses, the Quantinuum component it binds,
> the typed interface it must satisfy, and an acceptance test.

---

## 0. Guiding principles (ranked design goals)

When two goals conflict, the lower-numbered one wins.

| ID | Goal | What it means in practice |
|----|------|---------------------------|
| **G1** | Correctness-first | A quantum result is never trusted until type-checked, emulated and compared to a classical baseline. The IDE makes that path the default. |
| **G2** | Native quantum UX | Guppy/HUGR/TKET/Selene feel built-in: completion, diagnostics, graph view and emulation. |
| **G3** | Agentic, not autonomous | AI accelerates the engineer; humans approve at defined gates. The agent never executes irreversible or paid actions alone. |
| **G4** | Open-stack, no fork drift | Adopt and extend Quantinuum OSS and Zed through documented seams; pin versions; **never fork in place**. |
| **G5** | Secure by construction | Tauri capabilities, sandboxed sidecars, least-privilege IPC; secrets only in the OS keychain. |
| **G6** | Performance | Sub-frame editor latency; fast incremental LSP; emulation/inference off the UI thread. |
| **G7** | Reproducibility | Seeds, versions and resource metrics recorded for every emulation and run. |

### The one architectural rule

DiracQ **never forks the Quantinuum stack and never patches Zed or Tauri
internals in place.** The DiracQ-owned layers (L4–L6) only *add* services, GPUI
views, LSP features, HUGR/TKET extensions and Selene plugins through documented
interfaces. Upstream Zed is a **pinned, vendored dependency** under
`third_party/zed` (see `scripts/vendor-zed.sh`); all DiracQ code lives in
`crates/diracq_*`, `crates/dirac_*` and `extensions/`.

---

## 1. The integration-seam decision (ADR-00)

For each capability, choose the **lightest** Zed integration seam that suffices,
in order:

```
WASM extension   >   ACP agent server   >   fork crate (GPUI)
  (no fork)            (separate process)      (GPU surfaces only)
```

This shrinks the fork delta dramatically and lets most of DiracQ be built and
shipped *independently of the editor binary*.

### Capability-to-seam map (the single most important planning artifact)

| Capability | Seam | Quantinuum binding | Where it lives |
|-----------|------|--------------------|----------------|
| Guppy syntax / highlight / indent | WASM extension | tree-sitter-guppy | `extensions/guppy` |
| Guppy LSP (types, HUGR hints) | WASM ext. + sidecar | guppylang, hugr | `extensions/guppy` + `crates/diracq_lsp` |
| Context-aware completion | WASM ext. + agent | guppylang | `extensions/guppy` |
| Selene emulation panel | **Fork crate (GPUI)** | selene-sim | `crates/diracq_selene` |
| HUGR graph canvas | **Fork crate (GPU)** | hugr | `crates/diracq_hugr` |
| Circuit canvas | **Fork crate (GPU)** | tket2 (mermaid/render) | `crates/diracq_circuit` |
| Molecule viewer (SMILES/PDB/xyz) | **Fork crate (GPU)** | RDKit sidecar | `crates/diracq_mol` |
| TKET compile actions | Sidecar + actions | pytket, tket2 | `crates/diracq_compile` + sidecar |
| Athena orchestrator | ACP agent server | all + HF | `agents/athena` (process) |
| Document-to-circuit | ACP agent tool | guppylang + HF | `agents/athena` tools |
| Multimodal synthesis | ACP agent tool | guppylang + HF | `agents/athena` tools |
| HF model inference | Python sidecar | transformers | `sidecar` (diracq_sidecar) |

**Only four `crates/diracq_*` fork crates carry GPU surfaces.** Everything else
ships on its own cadence.

---

## 2. The seven-layer architecture

```
L6 — Product surfaces     Editor panes · Agent chat · HUGR viewer · Molecular viewer · Emulation panel · Palette · CI hooks
L5 — Agentic AI (Athena)  Planner · Retriever (RAG) · Code-gen · Validator · Reporter  (LangGraph · tools · memory)
L4 — Integration services Guppy LSP · TKET compile · Selene emulate · HF inference sidecar · Molecular I/O
L3 — IPC & runtime bridge Tauri Commands · JSON-RPC 2.0 sidecar · event bus · capability-scoped permissions
L2 — Application shell     Tauri v2 (Rust core + WebView) · window/menus/updater · keychain & secrets
L1 — Editor core           Fork of Zed (GPUI, Rust) · buffers · language registry · tree-sitter · WGPU
L0 — Foundations           Quantinuum OSS (Guppy · HUGR · tket2 · Selene · pytket · Nexus) · HF models · Helios/emulators
```

DiracQ owns **L4–L6** (+ a thin set of L1 registrations); **L0–L3** are adopted
and extended, never forked. Control flows down; results/events flow up.

### Three trust zones (Table 6)

| Zone | Process | Trust |
|------|---------|-------|
| Core | Rust: Zed fork + Tauri | Trusted. Holds capability grants + keychain handle; **no model weights**. |
| Sidecar | Python: AI runtime, TKET, Selene, HF | Semi-trusted, sandboxed. Holds models, runs heavy compute; **no secrets**; network via allowlist only. |
| Front-end | GPUI / embedded WebView | Untrusted. May call only granted, capability-scoped commands. |

Privilege flows down the trust order only, never the reverse. Untrusted content
(a parsed paper, a model completion, a web page) can never widen its own
permissions.

---

## 3. Workstreams

Each maps to a crate/service with a typed interface and an acceptance test.

### Workstream A — Guppy language extension (WASM) — *scaffolded*
- **Seam:** WASM extension via `zed_extension_api`. **Creates:** `extensions/guppy/`.
- **Acceptance:** Install as a dev extension; open a `.guppy` file; verify
  highlighting, that the LSP starts, and that a deliberate linear-type violation
  (reusing a measured qubit) surfaces a diagnostic.
- **Status:** `extension.toml`, language config, `highlights/injections/indents.scm`,
  and the `Extension` impl that locates `diracq-guppy-lsp` via the sandbox-safe
  `Worktree` are in place. **TODO:** generate the real `tree-sitter-guppy`
  grammar and pin its commit.

### Workstream B — Guppy LSP and HUGR-aware analysis — *scaffolded*
- **Seam:** Native Rust service (`crates/diracq_lsp`) + a Python `guppylang`
  worker (`sidecar/.../guppy_worker.py`). **Interface:** `GuppyAnalysis` trait
  (`check` / `compile_summary` / `resources`).
- **Acceptance:** On the teleportation example, `check` returns zero diagnostics
  and `compile_summary` reports the expected qubit width; a buffer that drops a
  qubit yields a precise diagnostic with the offending range.
- **TODO:** the stdio LSP loop, the JSON-RPC worker protocol, guppylang
  error→`Diagnostic` range mapping, idle-debounced checks on the background executor.

### Workstream C — Selene emulation panel (fork crate) — *scaffolded*
- **Seam:** Fork crate `crates/diracq_selene` (GPUI view + entity); emulation
  off-thread on the `BackgroundExecutor`. **Interface:** `EmulationService` trait;
  `EmulateRequest`/`EmulateResult` payloads.
- **Acceptance:** A Bell program yields counts on `00`/`11`; the depolarizing
  model introduces a small `01`/`10` fraction; identical seeds reproduce
  identical counts; the UI stays at 120 fps during a 16–20 qubit run.
- **TODO:** the `Render` impl + histogram element (behind `--features gpui`), the
  sidecar `selene.emulate` driver with `selene.shot` streaming, the DiracNoise plugin.

### Workstream D — HUGR & circuit GPU canvases (fork crates) — *scaffolded*
- **Seam:** Fork crates `crates/diracq_hugr` + `crates/diracq_circuit`, each a
  custom GPUI `Element`. **Interface:** `LayoutEngine` → `CircuitLayout` / `GraphLayout`.
- **Acceptance:** A 20-gate circuit renders and pans/zooms without jank;
  collapsing a HUGR region hides children and preserves boundary edges; selecting
  a gate highlights the source span in the editor (bidirectional mapping).
- **TODO:** column-assignment layout from a HUGR dataflow region; the GPUI
  `Element` with hit-testing; selection↔editor-buffer bridge via the project API.

### Workstream E — Athena as an ACP agent server — *scaffolded*
- **Seam:** ACP agent server process `agents/athena` implementing the surface
  Zed's `AgentConnection` expects (no bespoke chat UI). **Interface:** `AcpAgent`
  (session lifecycle + streaming `prompt`).
- **Acceptance:** From Zed's agent panel, "new DiracQ thread" connects; a prompt
  streams a plan and tool calls; two threads run in parallel; cancellation honored.
- **TODO:** ACP server scaffold against `agent-client-protocol`, session lifecycle,
  streaming prompt, tool-call events.

### Workstream F — Document-to-circuit generation — *scaffolded*
- **Seam:** An Athena tool backed by the HF sidecar (parsing/embedding) and
  guppylang (validation). **Pipeline:** extract → identify circuit/algorithm →
  draft Guppy from validated templates → `check()` → emulate → self-repair.
- **Acceptance:** Given a paper describing Bell/teleportation, the tool returns
  Guppy that type-checks and reproduces the expected distribution on Selene; a
  generation that fails `check()` is repaired or rejected, never surfaced as "done".
- **TODO:** PDF/LaTeX extractor → structured circuit spec; spec→Guppy templates
  with the validation gate; self-repair feeding `check()` errors back to the model.

### Workstream G — Multimodal synthesis & HF inference — *scaffolded*
- **Seam:** Athena tools + the Python inference sidecar (`diracq_sidecar.inference`).
  **Interface:** `InferenceService` (`embed`, `relax_geometry`, `rank_candidates`,
  `predict_structure`) + the licence-enforcing model registry.
- **Acceptance:** A SMILES input is relaxed and ranked; only the top candidate is
  handed to a generated VQE program; the registry **refuses** a model used outside
  its licence (a governance check, not optional).
- **Status:** the registry + refusal path (`ModelNotAllowed`) and the molecular
  `mol.parse` entry are scaffolded. **TODO:** the FastAPI/JSON-RPC inference
  bodies, MLIP relaxation, pre-screen gating.

### Workstream H — TKET compile integration — *scaffolded*
- **Seam:** Rust service `crates/diracq_compile` over a pytket/tket2 Python
  worker + palette/Athena actions. **Domain passes:** `crates/dirac_passes`
  (`dirac.chem` HUGR extension + tket2 rewrites that slot *before* qsystem prep).
- **Acceptance:** Compiling a chemistry ansatz reduces entangling-gate count vs.
  the unoptimised circuit; the qsystem pass runs last; the diff view shows
  before/after metrics.
- **TODO:** the `tket.compile` worker body; pass-by-pass resource metrics; a CI
  check pinning the tket2/qsystem version against upstream renames.

---

## 4. Phases (delivery)

Build order is **M1 → M4**. The local edit/check/emulate loop and the agent are
front-loaded because they unlock the differentiating capabilities and need no
hardware. Each phase has an explicit exit gate; "not yet" is an acceptable,
documented outcome at any gate.

```
P1 Shell ──▶ P2 Quantum ──▶ P3 Agentic ──▶ P4 Hardware
(0–3 mo)     (3–9 mo)        (9–18 mo)       (18 mo+)
```

| Phase | Workstreams | Key deliverables | Exit criteria |
|-------|-------------|------------------|---------------|
| **P1 Shell** (0–3 mo) | (foundation) | Zed fork rebased as additive delta; Tauri shell; IPC bridge; sidecar supervisor; editor panels docked. | A **signed build that edits files and round-trips a JSON-RPC call**. |
| **P2 Quantum** (3–9 mo) | A, B, C, D, H | Guppy LSP + tree-sitter grammar; TKET compile; Selene emulate; graph/circuit viewer. | **Author → compile → emulate** a Bell/H₂ kernel in-IDE, with reproducible histograms. |
| **P3 Agentic** (9–18 mo) | E, F, G | LangGraph agents; DiracGPT RAG; FM sidecar; molecular pipeline; declarative experiments. | A **paper → validated emulated result with a cited report**. |
| **P4 Hardware** (18 mo+) | (Nexus) | Nexus submission; gated hardware runs; calibrated DiracNoise; CI benchmarking. | A **validated pilot run on Helios**, benchmarked vs. classical. |

### Milestones (each demonstrable on Selene, no hardware)

| Milestone | Workstreams | Demonstrable outcome |
|-----------|-------------|----------------------|
| **M1 Edit** | A, B | Guppy editing with live type/linearity diagnostics. |
| **M2 Run** | C, H | Compile + emulate from the editor; reproducible histograms. |
| **M3 See** | D | Interactive circuit & HUGR canvases bound to the buffer. |
| **M4 Augment** | E, F, G | Athena ACP agent: doc-to-circuit and multimodal synthesis with the validation gate. |

---

## 5. Performance budgets (measured in CI on reference hardware)

| Operation | Target | Method |
|-----------|--------|--------|
| Keystroke-to-glyph | < 16 ms (60 fps) | GPUI frame timing |
| LSP completion | < 120 ms p95 | Debounced; tree-sitter sync |
| LSP diagnostics | < 300 ms p95 | Incremental analyzer |
| HUGR compile (small) | < 1.5 s | tket2 wall-clock |
| Selene emulate (4q, 2k shots) | < 2 s | Stim backend |
| Model infer (embedding) | < 500 ms | Warm cache, GPU |
| Agent step overhead | < 200 ms | Graph transition, excl. tool |

Reproducibility is a **measured** property: the same seeded workload must produce
the same counts and resource profile across commits (G7). The benchmark harness
fails CI on regression beyond tolerance.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Upstream drift (Zed/Tauri/Quantinuum) | Additive deltas, pinned versions, CI against each bump; never fork. |
| Agent hallucination | Hard validation gate (types + emulate + baseline); citations; human approval. |
| Model licensing breach | Registry with licence/revision; inference refuses out-of-scope models. |
| Performance regressions | CI benchmark harness with per-op budgets and tolerances. |
| Security escalation | Capability model, sandboxed sidecar, keychain-only secrets, egress allowlist. |
| Over-claiming advantage | Maturity labels and mandatory classical baselines in every report. |

---

## 7. The roadmap in one sentence

> Build the shell, make the quantum stack feel native, layer agentic AI with a
> hard validation gate, and reserve scarce hardware for the final, approved,
> benchmarked step — **extending** the open Quantinuum stack throughout rather
> than forking it.
