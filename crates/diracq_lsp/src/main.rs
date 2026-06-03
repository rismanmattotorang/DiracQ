//! `diracq-guppy-lsp` — the binary the Guppy WASM extension launches on PATH
//! (`worktree.which("diracq-guppy-lsp")`, see extensions/guppy/src/guppy.rs).
//!
//! M1 milestone (Workstream A+B): a working stdio LSP loop that publishes
//! linear-type diagnostics. It prefers the authoritative `guppylang` worker
//! (ADR-03) and falls back to the pure-Rust heuristic analyzer when the worker
//! is unavailable or errors, so the editor always has diagnostics.
//!
//! The worker command is configured via env vars (set by the editor/extension):
//! `DIRACQ_GUPPY_WORKER` (program to launch, e.g. `python3`),
//! `DIRACQ_GUPPY_WORKER_ARGS` (space-separated args), and
//! `DIRACQ_GUPPY_WORKER_CWD` (working directory). If `DIRACQ_GUPPY_WORKER` is
//! unset, the heuristic analyzer is used directly.

use std::io::{self, BufReader, BufWriter};

use diracq_lsp::{server, FallbackAnalyzer, HeuristicAnalyzer, WorkerAnalyzer};

fn main() -> anyhow::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut reader = BufReader::new(stdin.lock());
    let mut writer = BufWriter::new(stdout.lock());

    match try_spawn_worker() {
        Some(worker) => {
            eprintln!(
                "diracq-guppy-lsp {} starting (guppylang worker → heuristic fallback)",
                env!("CARGO_PKG_VERSION")
            );
            server::run(
                FallbackAnalyzer::new(worker, HeuristicAnalyzer),
                &mut reader,
                &mut writer,
            )
        }
        None => {
            eprintln!(
                "diracq-guppy-lsp {} starting (heuristic analyzer; set DIRACQ_GUPPY_WORKER to enable guppylang)",
                env!("CARGO_PKG_VERSION")
            );
            server::run(HeuristicAnalyzer, &mut reader, &mut writer)
        }
    }
}

fn try_spawn_worker() -> Option<WorkerAnalyzer> {
    let program = std::env::var("DIRACQ_GUPPY_WORKER").ok()?;
    let args_str = std::env::var("DIRACQ_GUPPY_WORKER_ARGS").unwrap_or_default();
    let args: Vec<&str> = args_str.split_whitespace().collect();
    let cwd = std::env::var("DIRACQ_GUPPY_WORKER_CWD").ok();
    match WorkerAnalyzer::spawn(&program, &args, cwd.as_deref()) {
        Ok(w) => Some(w),
        Err(e) => {
            eprintln!("diracq-guppy-lsp: failed to spawn worker ({e}); using heuristic analyzer");
            None
        }
    }
}
