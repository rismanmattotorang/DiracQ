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

### Workstream A — Guppy language extension (WASM) — *done (M1)*
- **Seam:** WASM extension via `zed_extension_api`. **Creates:** `extensions/guppy/`.
- **Acceptance:** Install as a dev extension; open a `.guppy` file; verify
  highlighting, that the LSP starts, and that a deliberate linear-type violation
  (reusing a measured qubit) surfaces a diagnostic.
- **Done:** `extension.toml`, language config, the `Extension` impl that locates
  `diracq-guppy-lsp` via the sandbox-safe `Worktree`, and the Guppy-aware
  `highlights/indents/injections.scm`. The grammar **reuses the pinned upstream
  `tree-sitter-python`** (v0.23.6) with Guppy queries layered on top — the G4/
  ADR-00 choice (adopt upstream; no forked parser, no reimplemented indentation
  scanner). See `extensions/guppy/README.md`.

### Workstream B — Guppy LSP and HUGR-aware analysis — *in progress (M1)*
- **Seam:** Native Rust service (`crates/diracq_lsp`) + a Python `guppylang`
  worker (`sidecar/.../guppy_worker.py`). **Interface:** `GuppyAnalysis` trait
  (`check` / `compile_summary` / `resources`).
- **Acceptance:** On the teleportation example, `check` returns zero diagnostics
  and `compile_summary` reports the expected qubit width; a buffer that drops a
  qubit yields a precise diagnostic with the offending range.
- **Done:** the **stdio LSP server loop** (`server.rs`: initialize →
  didOpen/didChange/didClose → `publishDiagnostics` → shutdown/exit), the
  dependency-free **LSP framing + byte-offset→position mapping** (`protocol.rs`),
  and a pure-Rust **heuristic linear-type analyzer** (`analyzer.rs`) that flags
  use-after-measure / double-measure inline. Verified end-to-end against the
  compiled `diracq-guppy-lsp` binary and by unit tests. This already satisfies
  the "deliberate linear-type violation surfaces a diagnostic" half of M1.
- **Real stack wired (verified):** the worker now runs **real `guppylang`** when
  installed — `_real_check` compiles each user `@guppy` function (found via the
  buffer AST) and maps guppylang errors to **precise byte-range diagnostics**
  (e.g. `AlreadyUsedError`/"Copy violation" → the offending `q`); `compile_summary`
  returns real HUGR node/qubit counts. Falls back to the heuristic when the stack
  is absent. Verified against guppylang 0.21.15 (`sidecar/tests/test_real_quantum.py`).
- **TODO:** idle-debounce on the background executor; hover/completion bodies.

### Workstream C — Selene emulation panel (fork crate) — *in progress (M2)*
- **Seam:** Fork crate `crates/diracq_selene` (GPUI view + entity); emulation
  off-thread on the `BackgroundExecutor`. **Interface:** `EmulationService` trait;
  `EmulateRequest`/`EmulateResult` payloads.
- **Acceptance:** A Bell program yields counts on `00`/`11`; the depolarizing
  model introduces a small `01`/`10` fraction; identical seeds reproduce
  identical counts; the UI stays at 120 fps during a 16–20 qubit run.
- **Done:** the emulation **service layer** (`service.rs`): `SidecarEmulationService`
  relays `selene.emulate` over an injected `Transport`, and a deterministic
  `MockEmulationService` (SplitMix64) provides reproducible counts before
  selene-sim is wired. The Python sidecar's `selene.emulate` answers with a real
  selene-sim run when installed, else the same deterministic mock (provenance
  stamped `selene = "mock"`). The shared length-prefixed JSON framing now lives
  in `diracq_services::framing`. Reproducibility (G7) is unit-tested on both sides.
- **Real stack wired (verified):** `selene.emulate` now compiles a supplied
  `guppy_src` and runs it on **real Selene** (Stim/Quest, optional depolarizing
  noise) via the guppy emulator builder — a Bell kernel clusters on `00`/`11`
  only and is reproducible under a fixed seed; provenance carries the real
  guppylang/selene versions. Falls back to the deterministic mock when the stack
  is absent. Verified against selene-sim 0.2.16.
- **TODO:** the `Render` impl + histogram element (behind `--features gpui`),
  `selene.shot` streaming notifications, the DiracNoise calibrated plugin.

### Workstream D — HUGR & circuit GPU canvases (fork crates) — *in progress (M3)*
- **Seam:** Fork crates `crates/diracq_hugr` + `crates/diracq_circuit`, each a
  custom GPUI `Element`. **Interface:** `LayoutEngine` → `CircuitLayout` / `GraphLayout`.
- **Acceptance:** A 20-gate circuit renders and pans/zooms without jank;
  collapsing a HUGR region hides children and preserves boundary edges; selecting
  a gate highlights the source span in the editor (bidirectional mapping).
- **Done:** the pure-Rust **layout algorithms** (unit-tested, no GPUI):
  `diracq_circuit::layout_ops` — column assignment (independent gates pack into a
  column; dependent gates serialise; 2-qubit gates block both wires) carrying
  per-gate `span` for selection mapping; and `diracq_hugr::layout_dag` —
  longest-path rank assignment with per-rank rows and region-crossing edge
  detection for collapse/expand.
- **GPUI views built (verified):** `crates/diracq_gpui` provides real
  `gpui::Render` implementations — `EmulationPanelView` (shot histogram),
  `CircuitCanvasView` (wire×column gate grid from `CircuitLayout`), and
  `HugrGraphView` (rank-positioned nodes from `GraphLayout`) — using GPUI 0.2.2's
  element API. They **type-check against the real vendored gpui** (Zed pinned to
  Rust 1.95.0) via `scripts/build-gpui.sh`, which stages the crate into the
  vendored Zed workspace (gpui needs Zed's workspace inheritance). The crate is
  excluded from the main workspace so `cargo check --workspace` still needs no GPU.
- **Real circuit decode (verified):** the sidecar `circuit.extract` runs one shot
  with Selene's `CircuitExtractor` and returns the lowered Helios-native circuit
  (`{n_qubits, gates, measures}`); `diracq_circuit::ops_from_extracted` turns that
  into `GateOp`s that `layout_ops` lays out for `CircuitCanvasView`. A source-parse
  mock serves the canvas without the stack. Verified against selene-sim 0.2.16.
- **Real HUGR graph decode (verified):** the sidecar `hugr.graph` walks the
  compiled HUGR Package (nodes/ops, links, parent→child regions) and returns
  `{nodes, edges, regions}`; `diracq_hugr::graph_from_payload` + `layout_dag`
  feed `HugrGraphView`. A source-derived mock serves the canvas without the stack.
  Verified against hugr 0.16.0.
- **TODO:** dock these views in the Zed `Workspace` (editor-binary integration);
  pan/zoom + hit-testing → editor-selection via a custom `Element`; `selene.shot`
  live streaming.

### Workstream E — Athena as an ACP agent server — *in progress (P3)*
- **Seam:** ACP agent server process `agents/athena` implementing the surface
  Zed's `AgentConnection` expects (no bespoke chat UI). **Interface:** `AcpAgent`
  (session lifecycle + streaming `prompt`).
- **Acceptance:** From Zed's agent panel, "new DiracQ thread" connects; a prompt
  streams a plan and tool calls; two threads run in parallel; cancellation honored.
- **Done:** the deterministic, dependency-injected **orchestration loop**
  (`orchestrator.py`, plan→retrieve→pre_screen→code_gen→validate→report) enforcing
  the two spec invariants — the **validation gate** (fail→repair up to N, else
  *rejected*, never "done") and the **human gate** (a hardware backend pauses
  `awaiting_approval` until approved). The **ACP `AthenaAgent`** supports parallel
  sessions, a streaming gate-aware `prompt`, and cancellation. Tested (7 cases)
  without langgraph/LLM.
- **Real validation gate (verified):** `athena.validation.validate_program` runs
  the gate over an injected `Services` boundary — **type-check → emulate →
  classical-baseline compare** — naming the failing stage so the repair loop
  knows what to fix. `sidecar_services()` wires it to the real guppylang check +
  Selene emulate. Verified end-to-end with the real stack: a Bell brief flows
  plan→…→code-gen→**real validate**→report with counts `{00: 497, 11: 503}`; a
  type-erroring program is driven to repair then *rejected*, never "done".
- **TODO:** bind to the `agent-client-protocol` stdio schema; wrap the nodes in
  the `langgraph` `StateGraph` (`graph.py`) for checkpointed runtime; replace the
  offline retriever/FM/code-gen/reporter stand-ins with real RAG/LLM calls.

### Workstream F — Document-to-circuit generation — *in progress (P3)*
- **Seam:** An Athena tool backed by the HF sidecar (parsing/embedding) and
  guppylang (validation). **Pipeline:** extract → identify circuit/algorithm →
  draft Guppy from validated templates → `check()` → emulate → self-repair.
- **Acceptance:** Given a paper describing Bell/teleportation, the tool returns
  Guppy that type-checks and reproduces the expected distribution on Selene; a
  generation that fails `check()` is repaired or rejected, never surfaced as "done".
- **Done:** the full pipeline (`doc2circuit.py`): a keyword `extract_spec`
  (recognises bell/ghz/teleport/vqe + qubit budget), `render` from **validated
  Guppy templates** (`templates.py`), and a self-repair loop that falls back to
  the simplest known-good template — ending **`rejected`** if nothing validates
  (never "done"). Wired into the orchestrator's `code_gen` so a brief drives
  generation. The validator is injected (default: a structural check that flags
  use-after-measure). Tested (7 cases).
- **TODO:** real PDF/LaTeX extractor; swap the structural validator for the
  guppylang worker + Selene; feed real `check()` errors back to a model.

### Workstream G — Multimodal synthesis & HF inference — *in progress (P3)*
- **Seam:** Athena tools + the Python inference sidecar (`diracq_sidecar.inference`).
  **Interface:** `InferenceService` (`embed`, `relax_geometry`, `rank_candidates`,
  `predict_structure`) + the licence-enforcing model registry.
- **Acceptance:** A SMILES input is relaxed and ranked; only the top candidate is
  handed to a generated VQE program; the registry **refuses** a model used outside
  its licence (a governance check, not optional).
- **Done:** the licence/revision registry + refusal path (`ModelNotAllowed`); a
  dependency-free **`.xyz` molecular parser** (`mol.parse`) producing the
  canonical `Molecule` record with G7 provenance (sha256 + parser version), with
  SMILES/PDB/MOL gated on RDKit; and `synth.py`'s `multimodal_synthesis` —
  **pre-screen gating** so only survivors (top-k above threshold) reach the VQE
  ansatz, skipping the quantum step entirely when nothing passes (G3). Tested.
- **TODO:** the real inference bodies (MLIP relaxation, ESM/Boltz), RDKit
  SMILES/PDB parsing, and wiring the pre-screen to the FM sidecar.

### Workstream H — TKET compile integration — *in progress (M2)*
- **Seam:** Rust service `crates/diracq_compile` over a pytket/tket2 Python
  worker + palette/Athena actions. **Domain passes:** `crates/dirac_passes`
  (`dirac.chem` HUGR extension + tket2 rewrites that slot *before* qsystem prep).
- **Acceptance:** Compiling a chemistry ansatz reduces entangling-gate count vs.
  the unoptimised circuit; the qsystem pass runs last; the diff view shows
  before/after metrics.
- **Done:** `CompileBackend` with `SidecarCompileBackend<T: Transport>` (relays
  `tket.compile`) and a deterministic `MockCompileBackend` that reports
  before/after `ResourceMetrics` showing the dirac.chem entangling-gate
  reduction, plus the Mermaid string for the circuit view. The sidecar
  `tket.compile` runs real pytket/tket2 when installed, else the same mock.
  Tested on both sides (the diff shows fewer two-qubit gates with passes on).
- **Real compile + optimisation (verified):** with the stack installed,
  `tket.compile` emits the **actual serialised HUGR bytes** (base64), extracts the
  lowered circuit for **real before/after metrics**, and applies a real tket pass
  (`FullPeepholeOptimise`) — on a redundant-CX kernel the diff is genuine:
  **16→5 gates, 2→0 two-qubit gates, depth 11→3**. A Mermaid string is generated
  from the optimised circuit for the viewer. The mock still serves dev/CI.
  Verified against pytket 2.18.0 / guppylang 0.21.15.
- **qsystem prep wired (verified):** the Helios target now runs the real
  `tket.passes.QSystemPass` on the compiled HUGR as the always-last step (Fig. 3);
  the emitted Helios HUGR is genuinely transformed vs the generic one
  (5648 B vs 3542 B on the Bell example). Guarded so non-qsystem programs still
  compile. Verified against tket 0.13.1.
- **TODO:** implement the namespaced `dirac.chem` rewrites (UCC fusion / Pauli
  grouping) as a HUGR extension slotting *before* qsystem prep; a CI check
  pinning tket2/qsystem against upstream renames.

> With Workstreams A, B, C and H landed (mock-backed where the heavy stack isn't
> installed), the **M2 "author → compile → emulate" loop is exercisable
> end-to-end and reproducibly** — the real selene-sim/tket2 drivers and the GPUI
> panels are the remaining work to make it physical and visual.

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

**Implemented (ADR-11):** `diracq_sidecar.bench` + `benchmarks.py` provide a
seeded reference suite (`bell_smoke`, `emulate_4q_2k`, `hugr_compile_small`) that
records p50/p95 and **fails on any p95 over budget** (`benchmarks/budgets.json`).
It runs mock-backed in CI (the `bench` job) and against the real stack on demand
(measured here: real Bell compile+emulate ≈ 158 ms p50, real HUGR compile ≈ 22 ms).
CI also runs a **toolchain matrix** (stable + the pinned 1.95.0) with fmt, clippy
`-D warnings`, check and the full test suite.

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
