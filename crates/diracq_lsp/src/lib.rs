//! DiracQ Guppy LSP (§6, Workstream B).
//!
//! Strategy (ADR-03): the server speaks the Microsoft LSP over stdio. Fast,
//! synchronous highlighting/structure comes from a tree-sitter front-end;
//! authoritative semantic diagnostics (linear types, qubit ownership,
//! use-after-measure) are delegated to a Python worker that wraps
//! `guppylang`'s own checker — ground truth that tracks upstream automatically.
//! Heavy checks run debounced on idle, off the editor's hot path.

use diracq_services::emulate::ResourceMetrics;

pub mod analyzer;
pub mod protocol;
pub mod server;

pub use analyzer::HeuristicAnalyzer;

/// A diagnostic mapped from a guppylang error object to an LSP range.
#[derive(Debug, Clone)]
pub struct Diagnostic {
    pub message: String,
    pub severity: Severity,
    /// (start_byte, end_byte) in the buffer.
    pub range: (usize, usize),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Error,
    Warning,
    Information,
    Hint,
}

/// Summary of a compiled HUGR (powers hovers and the gutter badge).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct HugrSummary {
    pub nodes: u32,
    pub edges: u32,
    pub qubits: u32,
}

/// Bridge from the Rust LSP server to the Python guppy worker.
///
/// `check` maps `guppylang` diagnostics to LSP; `compile_summary` returns a
/// HUGR shape summary; `resources` powers the gutter resource badge.
pub trait GuppyAnalysis: Send + Sync {
    fn check(&self, uri: &str, src: &str) -> anyhow::Result<Vec<Diagnostic>>;
    fn compile_summary(&self, uri: &str, src: &str) -> anyhow::Result<HugrSummary>;
    fn resources(&self, uri: &str, src: &str) -> anyhow::Result<ResourceMetrics>;
}

/// A stub analyzer used until the Python worker is wired (Workstream B, M1).
/// Returns no diagnostics — the real implementation calls `guppy.check()`.
#[derive(Default)]
pub struct StubAnalyzer;

impl GuppyAnalysis for StubAnalyzer {
    fn check(&self, _uri: &str, _src: &str) -> anyhow::Result<Vec<Diagnostic>> {
        Ok(Vec::new())
    }
    fn compile_summary(&self, _uri: &str, _src: &str) -> anyhow::Result<HugrSummary> {
        Ok(HugrSummary::default())
    }
    fn resources(&self, _uri: &str, _src: &str) -> anyhow::Result<ResourceMetrics> {
        Ok(ResourceMetrics::default())
    }
}
