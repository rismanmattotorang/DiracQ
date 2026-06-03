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
