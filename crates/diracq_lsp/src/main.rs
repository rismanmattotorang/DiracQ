//! `diracq-guppy-lsp` — the binary the Guppy WASM extension launches on PATH
//! (`worktree.which("diracq-guppy-lsp")`, see extensions/guppy/src/guppy.rs).
//!
//! M1 milestone: this is a stdio stub that announces itself. The full LSP loop
//! (initialize → didOpen/didChange → debounced check via the guppy worker →
//! publishDiagnostics) is implemented in Workstream B.

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    eprintln!(
        "diracq-guppy-lsp {} starting (args: {:?}) — stdio LSP loop is a Workstream-B stub",
        env!("CARGO_PKG_VERSION"),
        &args[1..]
    );
    // TODO(Workstream B): drive the LSP protocol over stdio and bridge to the
    // Python guppy worker via `diracq_lsp::GuppyAnalysis`.
    Ok(())
}
