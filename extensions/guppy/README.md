# Guppy language extension (DiracQ)

First-class Guppy editing for DiracQ, shipped as a sandboxed Zed WASM extension
(`zed_extension_api`) — no editor fork required (ADR-00, Workstream A).

## Grammar: reuse Python, don't fork a parser

Guppy is *syntactically* Python — `@guppy`-decorated functions with a linear
type discipline. Rather than author and maintain a Python-superset grammar
(including Python's tricky indentation scanner), DiracQ **reuses the upstream
`tree-sitter-python` grammar verbatim** (pinned in `extension.toml`) and layers
Guppy-aware queries on top:

- `languages/guppy/highlights.scm` — highlights the `@guppy` decorator family,
  the quantum builtin operations (`h`, `cx`, `rz`, `measure`, …), and Guppy
  builtin types (`qubit`, `array`, `angle`) on the Python parse tree.
- `languages/guppy/indents.scm` — block-based auto-indentation.
- `languages/guppy/injections.scm` — intentionally minimal (the whole buffer is
  already Python).

This is the G4 / ADR-00 choice: adopt upstream, extend through documented seams,
never carry a forked parser that drifts.

## Language server

The extension launches `diracq-guppy-lsp` (located on `PATH` via the sandbox-safe
`Worktree`, never `std::env`). That server provides linear-type diagnostics — the
authoritative `guppylang` worker when available, falling back to a fast pure-Rust
heuristic. See `crates/diracq_lsp`.

## Develop

Install as a dev extension in Zed (Extensions → Install Dev Extension → this
folder), then open a `.guppy` file (see `examples/guppy/`). Verify highlighting,
that the LSP starts, and that a deliberate linear-type violation (reusing a
measured qubit) surfaces a diagnostic.
