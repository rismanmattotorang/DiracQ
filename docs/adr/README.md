# Architecture Decision Records

These ADRs are carried over from the ParaQ specification and rebranded for
DiracQ. They capture *why* the architecture is what it is, and the alternatives
considered. All are **Accepted**.

---

## ADR-00 — Integrate at the lightest seam (extension > ACP > fork)
**Decision.** For each capability, choose the lightest Zed integration seam that
suffices, in order: WASM extension, then ACP agent server, then fork crate.
**Context.** Source analysis shows three seams with very different maintenance
costs against a fast-moving upstream (37k+ commits).
**Alternatives.** (a) Everything in the fork — maximal control, maximal drift and
merge cost. (b) Everything as extensions — zero fork, but WASM cannot host GPU
canvases or deep editor surfaces.
**Consequences.** A small, reviewable fork delta plus independently-versioned
extensions and one ACP agent; capabilities ship on their own cadence.
*Supersedes the framing of ADR-01.*

## ADR-01 — Fork Zed for the editor core
**Decision.** Use a fork of Zed (GPUI) as the editor core rather than
VS Code/Electron, a CodeMirror/Monaco web editor, or a from-scratch editor.
**Context.** DiracQ needs native performance (G6), a Rust-native extension surface
that matches the Rust-heavy quantum stack, and a GPU renderer for circuit/graph views.
**Consequences.** Inherit Zed's velocity and GPUI; accept tracking a fast-moving
upstream (mitigated by the additive-delta rule); standardise on Rust across the core.

## ADR-02 — Tauri v2 shell with a Python JSON-RPC sidecar
**Decision.** Package with Tauri v2 and run Python work (LangGraph, HF inference,
pytket/Selene) in a supervised sidecar addressed by JSON-RPC 2.0.
**Alternatives.** (a) PyO3 in-process — lowest latency but GIL-bound Python in the
editor process risks blocking the UI (G6) and weakens the sandbox (G5). (b) gRPC —
strong typing/streaming but adds protobuf complexity. (c) REST — simplest but
awkward for bidirectional streaming.
**Consequences.** Process isolation gives the security model of §13 and keeps
Python off the UI thread; serialisation overhead is mitigated by length-prefixed
binary framing for large HUGR/array payloads.

## ADR-03 — Out-of-process LSP reusing guppylang
**Decision.** Implement the Guppy LSP as a Python process wrapping `guppylang`'s
own checker for ground-truth diagnostics, with a tree-sitter front-end for fast
highlighting/structure.
**Alternatives.** (a) Pure-Rust re-implementation — fastest/in-process but
duplicates a moving upstream type system (violates G4). (b) Tree-sitter only —
trivial but cannot catch linear-type errors (fails G1).
**Consequences.** Authoritative diagnostics that track upstream automatically, at
the cost of a process hop hidden by debouncing and synchronous tree-sitter structure.

## ADR-04 — Wrap Selene as a service; extend via plugins
**Decision.** Treat Selene as an out-of-process service and extend it only through
its documented simulator/error-model/runtime plugin points.
**Alternatives.** (a) Bespoke statevector emulator in Rust — reimplements Helios
runtime semantics Selene already models faithfully (fails G1/G4). (b) Hardware
only — far too slow/costly for iteration (fails G6).
**Consequences.** Free, fast, reproducible local emulation that tracks upstream;
cost is serialising HUGR/count maps, mitigated by binary framing.

## ADR-05 — Extend HUGR/tket2, never fork the compiler
**Decision.** Add domain optimisation as namespaced HUGR extensions and tket2
passes (`dirac.chem`) that slot before qsystem prep.
**Alternatives.** (a) Fork tket2 — full control but guaranteed drift (breaks G4).
(b) Post-process compiled output — brittle, no IR access.
**Consequences.** Passes compose cleanly and upgrade with the stack; cost is
pinning the (tket2, hugr) pair and treating upstream renames (e.g. the qsystem
rename) as managed dependency upgrades.

## ADR-06 — LangGraph for orchestration
**Decision.** Build the agentic subsystem on LangGraph (explicit state graph)
rather than AutoGen (conversational) or a bespoke loop.
**Alternatives.** (a) AutoGen — fast for free-form chat but implicit control flow
is harder to make inspectable/reproducible (tension with G1/G7). (b) Bespoke
orchestrator — reinvents checkpointing, retries, tool routing.
**Consequences.** Deterministic edges, checkpointed state for provenance, and a
single place to enforce the human gate; accept a dependency on LangGraph's API.

## ADR-07 — RDKit-centred parsing with MLIP relaxation
**Decision.** Use RDKit as the primary chemical parser/sanitiser and relax
geometries with an MLIP from the inference sidecar before the quantum step.
**Alternatives.** (a) Hand-rolled parsers — re-implement decades of edge cases.
(b) Classical force-field relaxation only — cheaper but worse VQE starting geometries.
**Consequences.** Robust parsing and good initial geometries at the cost of an
RDKit dependency (permissively licensed) in the sidecar.

## ADR-08 — Capability-scoped, sandboxed sidecar over in-process Python
**Decision.** Run untrusted/heavy work in a sandboxed sidecar behind Tauri
capabilities rather than embedding Python in the core.
**Alternatives.** (a) In-process (PyO3) — fastest but a compromise in any Python
dependency would run with the core's privileges. (b) Full container/VM per
sidecar — strongest isolation but heavy for a desktop app and awkward for GPU passthrough.
**Consequences.** Process-level isolation plus a capability gate is a strong,
practical boundary; accept IPC cost and a coarser-than-VM sandbox, hardened by the
egress allowlist and keychain-only secrets.

---

> ADRs below were adopted during implementation (they record decisions made while
> wiring the real stack, the GPUI surfaces and the CI gates).

## ADR-09 — Deterministic mock backends with provenance + graceful fallback
**Decision.** Every service that fronts a heavy dependency (guppylang, selene-sim,
tket2, transformers, RDKit) ships a **deterministic mock backend** and selects the
real driver only when the dependency is importable; otherwise it falls back to the
mock. Mock outputs are **provenance-stamped** (e.g. `stack_versions.selene = "mock"`)
so a mock result is never mistaken for a real one, and they are **seeded** so the
same inputs reproduce the same outputs.
**Context.** The full Quantinuum/ML stack is large and not always present (fresh
checkouts, fast CI, contributor laptops). We still want every layer buildable,
testable and demoable end-to-end.
**Alternatives.** (a) Require the full stack everywhere — slow, brittle CI, high
barrier to entry. (b) Skip tests when deps are missing — leaves the integration
logic unexercised.
**Consequences.** Default CI is fast and hermetic; real integrations are verified
in an opt-in job (`test_real_quantum.py`, `quantum` CI job). The cost is keeping
mock and real shapes in sync, enforced by shared payload contracts. **Accepted.**

## ADR-10 — GPUI surfaces as an excluded crate staged into the vendored Zed workspace
**Decision.** Keep the real `gpui::Render` views in `crates/diracq_gpui`, *excluded*
from the DiracQ workspace, and build them by staging the crate into the vendored
Zed workspace (`scripts/build-gpui.sh`).
**Context.** `gpui` uses Zed's workspace-inherited dependencies, so it only
resolves inside Zed's workspace; Cargo also requires workspace members to live
under the workspace root, so an out-of-tree member is rejected. Meanwhile the
standalone `cargo check --workspace` must keep working with no Zed and no GPU.
**Alternatives.** (a) Make `diracq_gpui` its own workspace with a path dep on gpui
— fails: gpui's inherited deps can't resolve. (b) Add `diracq_gpui` to the main
workspace with an optional gpui path dep — forces `third_party/zed` to exist for
any `cargo check`. (c) Fork gpui to drop inheritance — violates G4.
**Consequences.** The default build needs nothing extra; the GPU build is a
documented, reproducible opt-in (verified: `gpui` and `diracq_gpui` both check
against the vendored Zed at Rust 1.95.0). The cost is a small staging step. **Accepted.**

## ADR-11 — Benchmark harness as a CI gate; reproducibility is a measured property
**Decision.** Ship a fixed, seeded benchmark suite (`diracq_sidecar.bench` +
`benchmarks.py`) that records latency percentiles and **fails CI when a case's p95
exceeds its budget** (`benchmarks/budgets.json`, Table 8).
**Context.** Performance is goal G6 and reproducibility is G7; both are only real
if measured continuously. Seeded workloads make results comparable across commits.
**Alternatives.** (a) Ad-hoc manual timing — not enforceable. (b) Wall-clock
assertions inside unit tests — noisy and host-dependent without percentiles.
**Consequences.** Regressions are caught automatically; budgets are padded for CI
hardware and cold real-stack runs and tightened over time. Runs mock-backed in CI
(fast/hermetic) and against the real stack on demand. **Accepted.**
