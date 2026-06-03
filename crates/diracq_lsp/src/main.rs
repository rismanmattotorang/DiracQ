//! `diracq-guppy-lsp` — the binary the Guppy WASM extension launches on PATH
//! (`worktree.which("diracq-guppy-lsp")`, see extensions/guppy/src/guppy.rs).
//!
//! M1 milestone (Workstream A+B): a working stdio LSP loop that publishes
//! linear-type diagnostics via the heuristic analyzer. Workstream B swaps the
//! analyzer for the debounced `guppylang` worker (authoritative ground truth)
//! without changing the protocol loop.

use std::io::{self, BufReader, BufWriter};

use diracq_lsp::{server, HeuristicAnalyzer};

fn main() -> anyhow::Result<()> {
    eprintln!(
        "diracq-guppy-lsp {} starting (stdio; heuristic analyzer — guppylang worker pending in Workstream B)",
        env!("CARGO_PKG_VERSION")
    );
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut reader = BufReader::new(stdin.lock());
    let mut writer = BufWriter::new(stdout.lock());
    server::run(HeuristicAnalyzer, &mut reader, &mut writer)
}
