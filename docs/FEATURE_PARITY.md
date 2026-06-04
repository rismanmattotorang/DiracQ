# DiracQ vs. Zed — Feature Parity & QC Superiority

**Verdict: DiracQ is a strict superset of Zed.** It inherits *every* Zed feature
unchanged (parity by construction) and adds a quantum-computing layer Zed has no
equivalent for. This is guaranteed by the architecture, not by re-implementation.

Reproduce the evidence in this document with:

```bash
./scripts/vendor-zed.sh && ./scripts/zed-feature-audit.sh
```

---

## 1. Assessment of upstream Zed

Audited from the vendored source tree (`third_party/zed`):

| Property | Value |
| --- | --- |
| Version | **1.7.0** |
| Crates | **235** (single Cargo workspace, ~97% Rust) |
| Editor crate | **~151,000 LOC** |
| UI runtime | **GPUI** (own GPU-accelerated framework; Metal / Vulkan / DirectX) |
| Targets | native + `wasm32-wasip2` (extensions), `wasm32-unknown-unknown` (web), `x86_64-unknown-linux-musl` (remote server) |

Zed is a best-in-class, GPU-native code editor. Its strengths — and exactly what
DiracQ must not lose — are: a sub-frame-latency multi-buffer editor, Tree-sitter
syntax, a full LSP/DAP stack, Vim mode, integrated terminal, Git (inline blame,
diffs, staging), real-time collaboration (calls, channels, shared projects), an
extension host (WASM), themes, tasks, a Jupyter-style REPL, an AI agent panel
with the **Agent Client Protocol (ACP)** for external agents, and edit-prediction.

### Zed features verified present (40/40 crates, inherited unchanged)

`vim` · `terminal` · `terminal_view` · `git` · `git_ui` · `collab` · `call` ·
`channel` · `project_panel` · `outline_panel` · `search` · `task` · `tasks_ui` ·
`dap` · `debugger_ui` · `diagnostics` · `editor` · `multi_buffer` · `language` ·
`lsp` · `languages` · `extension` · `extension_host` · `theme` · `theme_selector` ·
`agent` · `agent_ui` · `acp_thread` · `agent_servers` · `copilot` ·
`edit_prediction` · `repl` · `markdown_preview` · `command_palette` ·
`file_finder` · `go_to_line` · `settings_ui` · `journal` · `feedback` · `onboarding`

---

## 2. Why DiracQ has *all* of Zed's features (parity by construction)

DiracQ is an **additive-delta fork** (ADR-00, ADR-01, design goal **G4**). The
DiracQ editor binary **is** the upstream Zed Cargo workspace, built together with
the additive `crates/diracq_*` crates that register into Zed's `Workspace`:

```
DiracQ editor  =  Zed workspace (all 235 crates, unchanged)  ⊕  diracq_* crates
```

The audit confirms the invariant: **0 Zed crate sources are modified or deleted**
by DiracQ — the delta is purely additive (new crates, a Guppy WASM extension, a
Python sidecar, an ACP agent). Therefore there is no Zed feature DiracQ can lack:
Vim, Git, collaboration, the debugger, the terminal, the extension ecosystem,
themes and edit-prediction are all present exactly as upstream.

> Contrast with the alternatives we rejected (ADR-01): a VS Code fork would
> inherit Electron's latency; a from-scratch editor would lose a decade of editor
> work. Building *on* Zed is what lets DiracQ match the best editor on day one.

### Parity matrix

| Zed capability | DiracQ status |
| --- | --- |
| GPU multi-buffer editor, Tree-sitter | **Inherited unchanged** |
| LSP (completion, hover, diagnostics, code actions) | Inherited **+ extended** for Guppy (linear types) |
| DAP debugger | Inherited unchanged |
| Vim mode | Inherited unchanged |
| Integrated terminal | Inherited unchanged |
| Git (blame, diff, stage, branches) | Inherited unchanged |
| Real-time collaboration (calls, channels) | Inherited unchanged |
| Extension host (WASM) | Inherited **+** the Guppy extension |
| Themes / theme selector | Inherited unchanged |
| Tasks / runnables | Inherited unchanged |
| Jupyter-style REPL | Inherited unchanged |
| AI agent panel + ACP external agents | Inherited **+** the Athena ACP agent |
| Edit prediction / Copilot | Inherited unchanged |
| Command palette, file finder, settings UI | Inherited **+** DiracQ palette actions |
| Remote server, web (wasm) targets | Inherited unchanged |

---

## 3. Why DiracQ is *superior for QC* (the delta Zed has no equivalent for)

These are first-class in DiracQ and **absent from Zed**. Each is implemented and
verified against the real Quantinuum stack (guppylang 0.21.15, selene-sim 0.2.16,
tket/pytket, hugr 0.16) — see `DEVELOPMENT_ROADMAP.md` for per-item status.

| QC capability | DiracQ | Zed |
| --- | --- | --- |
| **Guppy language** (syntax, highlight, indent) | ✅ `extensions/guppy` (reuses tree-sitter-python) | ✗ |
| **Linear-type diagnostics** (use-after-measure, no-cloning) inline | ✅ real guppylang check → exact byte ranges (`diracq_lsp`) | ✗ |
| **Quantum emulation** (Selene, Stim/Quest) in-IDE | ✅ real Bell 00/11, seed-reproducible (`selene.emulate`) | ✗ |
| **Calibrated noise** (DiracNoise) | ✅ §7.2 — adds 01/10 error outcomes | ✗ |
| **Live shot streaming** | ✅ `selene.shot` notifications | ✗ |
| **TKET compile + optimisation** w/ before/after diff | ✅ real 16→5 gates, 2→0 two-qubit (`tket.compile`) | ✗ |
| **Helios qsystem prep** (always last) | ✅ real `QSystemPass` on HUGR | ✗ |
| **Circuit canvas** | ✅ `diracq_circuit` layout → `diracq_gpui` (real gpui) | ✗ |
| **HUGR graph canvas** (collapsible regions) | ✅ `diracq_hugr` rank layout → `diracq_gpui` | ✗ |
| **Molecule viewer** (SMILES/PDB/.xyz) | ✅ `diracq_mol` + xyz parser w/ provenance | ✗ |
| **Agentic orchestrator** (Athena) on ACP + LangGraph | ✅ plug into Zed's agent panel | ✗ (Zed hosts generic agents only) |
| **Hard validation gate** (type-check → emulate → baseline) | ✅ `athena.validation` | ✗ |
| **Document-to-circuit** from papers/briefs | ✅ `doc2circuit` + validated templates | ✗ |
| **Multimodal synthesis** w/ FM pre-screen gating | ✅ `athena.synth` | ✗ |
| **Reproducibility-as-CI-gate** (seeds, benchmarks) | ✅ `diracq_sidecar.bench` (§14) | ✗ |
| **Licence-enforcing model registry** | ✅ refuses out-of-scope models | ✗ |

### The DiracQ superiority loop (Zed cannot do this)

```
read a paper → generate type-checked Guppy → emulate on Selene (reproducibly)
   → compare to a classical baseline → human-approve → run on Helios → cited report
```

Zed gives you the world-class editor to *write* code. DiracQ gives you that same
editor **plus** the entire quantum toolchain — language intelligence, emulation,
compilation, visualization, and an agent that drives them — woven in as native,
first-class surfaces.

---

## 4. Keeping parity over time

Zed moves fast (the editor crate alone is ~151k LOC across 37k+ upstream commits).
Parity is maintained by the additive-delta rule plus the compatibility matrix:

- **Never patch Zed in place** — only add crates/extensions/agents (audited: 0
  modified Zed sources).
- **Rebase per upstream tag** via `scripts/vendor-zed.sh` (pinned in
  `docs/compatibility-matrix.md`); the additive crates track upstream with a
  small, reviewable delta.
- **CI** builds the standalone additive workspace on every push; `build-gpui.sh`
  builds the GPU surfaces against the vendored Zed; `zed-feature-audit.sh`
  re-verifies the superset invariant.

**Net:** DiracQ ⊇ Zed, always — same editor, plus quantum.
