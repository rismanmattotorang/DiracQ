# Compatibility Matrix & Pinned Versions

Every external dependency is pinned. CI rebuilds against each upstream bump and
treats a break as a *managed upgrade*, never a silent drift (G4). **These
versions are a snapshot at authoring time** — re-verify against the live sources
before any procurement or release decision.

| Component | Pinned | Notes |
|-----------|--------|-------|
| Rust toolchain | 1.95.0 (stable) | Per `rust-toolchain.toml`; profile minimal. Matches the Zed fork base. |
| Tauri | 2.x | v2 capability model required. |
| Zed (fork base) | tracked | Additive delta; **rebased per upstream tag**. Vendored under `third_party/zed`. |
| GPUI | via Zed | Not a separate crate pin. |
| `zed_extension_api` | 0.6.0 | WASM extension ABI; check Zed compat on rebase. |
| WASM target | wasm32-wasip2 | Extension compile target. |
| ACP | ProtocolVersion::V1 | Min. version for the Athena agent. |
| Python | 3.11–3.12 | Sidecar interpreter. |
| guppylang | ≥ 0.21 | Bundles Selene; LSP ground truth. |
| selene-sim | matched | To guppylang; QuEST/Stim backends. |
| tket2 / hugr | pinned **pair** | Renames are managed upgrades — upgrade together (ADR-05). |
| pytket | current | Bridge for legacy circuits. |
| LangGraph | pinned | Orchestration graph. |
| transformers | pinned | HF inference runtime. |
| RDKit | pinned | Molecular parsing. |

## Build & packaging

- **Rust:** Cargo workspace. The additive `crates/*` build standalone (no GPUI);
  the GPU fork crates link GPUI only with `--features gpui` after Zed is vendored.
- **Python:** `uv` or Poetry; the sidecar ships as a frozen environment alongside
  the binary.
- **Optional:** a Nix flake for hermetic developer environments.
- **Tauri** bundles the signed desktop artefacts per platform.

## Three extra Rust targets (matching Zed)

- `wasm32-wasip2` — WASM extensions
- `wasm32-unknown-unknown` — GPUI on the web
- `x86_64-unknown-linux-musl` — the remote server

## Upgrade procedure (managed, never silent)

1. Bump the pin here and in the relevant manifest (`Cargo.toml`, `pyproject.toml`,
   `rust-toolchain.toml`, `extensions/guppy/extension.toml`).
2. Run `scripts/vendor-zed.sh` with the new `ZED_REF` for a Zed rebase.
3. Re-run CI (incl. the benchmark harness). Treat the (tket2, hugr) pair and any
   qsystem rename as a single coordinated change.
