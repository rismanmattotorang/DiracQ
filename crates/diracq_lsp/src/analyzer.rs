//! A lightweight, dependency-free **heuristic** linear-type analyzer.
//!
//! This is *not* the ground truth — the authoritative analyzer delegates to
//! `guppylang`'s own checker over the Python worker (Workstream B, ADR-03). But
//! a pure-Rust heuristic lets DiracQ surface the most important class of bug —
//! **use-after-measure** (reusing a qubit that has already been measured) —
//! inline, synchronously, before the worker is wired. It is enough to satisfy
//! the M1 acceptance test and gives instant feedback while typing.
//!
//! The heuristic tokenises the buffer, tracks which qubit identifiers have been
//! consumed by `measure(...)`, and flags any later use of a measured qubit in a
//! quantum operation. Re-assignment (`q = ...`) clears the measured state. It is
//! intentionally conservative; the guppylang worker remains the source of truth.

use crate::{Diagnostic, GuppyAnalysis, HugrSummary, Severity};
use diracq_services::emulate::ResourceMetrics;
use std::collections::HashMap;

/// Quantum operations whose qubit arguments must be *live* (not yet measured).
const QUANTUM_OPS: &[&str] = &[
    "h", "x", "y", "z", "s", "t", "sdg", "tdg", "cx", "cz", "rx", "ry", "rz", "measure", "reset",
];

#[derive(Debug, Clone, PartialEq, Eq)]
enum Tok {
    /// An identifier with its byte range `[start, end)`.
    Ident {
        text: String,
        start: usize,
        end: usize,
    },
    /// A single punctuation char with its byte offset.
    Punct { ch: char, at: usize },
}

/// Tokenise into identifiers and the punctuation that matters for our scan.
fn tokenize(src: &str) -> Vec<Tok> {
    let mut toks = Vec::new();
    let bytes = src.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        let c = bytes[i] as char;
        if c == '#' {
            // Skip to end of line (Guppy/Python comment).
            while i < bytes.len() && bytes[i] != b'\n' {
                i += 1;
            }
            continue;
        }
        if c.is_alphabetic() || c == '_' {
            let start = i;
            while i < bytes.len() {
                let d = bytes[i] as char;
                if d.is_alphanumeric() || d == '_' {
                    i += 1;
                } else {
                    break;
                }
            }
            toks.push(Tok::Ident {
                text: src[start..i].to_string(),
                start,
                end: i,
            });
            continue;
        }
        if matches!(c, '(' | ')' | ',' | '=') {
            toks.push(Tok::Punct { ch: c, at: i });
        }
        i += 1;
    }
    toks
}

/// The heuristic analyzer. Stateless; safe to share across the LSP server.
#[derive(Default)]
pub struct HeuristicAnalyzer;

impl HeuristicAnalyzer {
    fn scan(&self, src: &str) -> Vec<Diagnostic> {
        let toks = tokenize(src);
        let mut diags = Vec::new();
        // qubit name -> byte offset where it was measured.
        let mut measured: HashMap<String, usize> = HashMap::new();

        let mut idx = 0;
        while idx < toks.len() {
            // Re-assignment: `name =` (a single '=', not the start of '==').
            if let Tok::Ident { text, .. } = &toks[idx] {
                if let Some(Tok::Punct { ch: '=', .. }) = toks.get(idx + 1) {
                    let is_eq_eq = matches!(toks.get(idx + 2), Some(Tok::Punct { ch: '=', .. }));
                    if !is_eq_eq {
                        measured.remove(text); // qubit rebound; it is live again
                    }
                }
            }

            // Call: `op (` ... `)`.
            if let Tok::Ident { text: op, .. } = &toks[idx] {
                if QUANTUM_OPS.contains(&op.as_str()) {
                    if let Some(Tok::Punct { ch: '(', .. }) = toks.get(idx + 1) {
                        let op = op.clone();
                        // Walk arguments until the matching ')'.
                        let mut j = idx + 2;
                        while j < toks.len() {
                            match &toks[j] {
                                Tok::Punct { ch: ')', .. } => break,
                                Tok::Ident {
                                    text: arg,
                                    start,
                                    end,
                                } => {
                                    if let Some(&mpos) = measured.get(arg) {
                                        if *start > mpos {
                                            diags.push(Diagnostic {
                                                message: format!(
                                                    "use-after-measure: qubit `{arg}` is used in `{op}(...)` after it was measured (no-cloning / linear-type violation)"
                                                ),
                                                severity: Severity::Error,
                                                range: (*start, *end),
                                            });
                                        }
                                    }
                                    // `measure(q)` consumes q from here on.
                                    if op == "measure" {
                                        measured.insert(arg.clone(), *start);
                                    }
                                }
                                _ => {}
                            }
                            j += 1;
                        }
                    }
                }
            }
            idx += 1;
        }
        diags
    }
}

impl GuppyAnalysis for HeuristicAnalyzer {
    fn check(&self, _uri: &str, src: &str) -> anyhow::Result<Vec<Diagnostic>> {
        Ok(self.scan(src))
    }

    fn compile_summary(&self, _uri: &str, src: &str) -> anyhow::Result<HugrSummary> {
        // Rough proxy: count distinct qubit() allocations as the qubit width.
        let qubits = src.matches("qubit(").count() as u32;
        Ok(HugrSummary {
            nodes: 0,
            edges: 0,
            qubits,
        })
    }

    fn resources(&self, _uri: &str, src: &str) -> anyhow::Result<ResourceMetrics> {
        Ok(ResourceMetrics {
            n_qubits: src.matches("qubit(").count() as u32,
            ..Default::default()
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clean_program_has_no_diagnostics() {
        let src = "q = qubit()\nh(q)\nmeasure(q)\n";
        let diags = HeuristicAnalyzer.check("test", src).unwrap();
        assert!(diags.is_empty(), "unexpected: {diags:?}");
    }

    #[test]
    fn use_after_measure_is_flagged() {
        let src = "q = qubit()\nmeasure(q)\nh(q)\n";
        let diags = HeuristicAnalyzer.check("test", src).unwrap();
        assert_eq!(diags.len(), 1);
        assert!(diags[0].message.contains("use-after-measure"));
        // The flagged range must point at the reuse `q` inside `h(q)`.
        let (s, e) = diags[0].range;
        assert_eq!(&src[s..e], "q");
        assert!(s > src.find("measure").unwrap());
    }

    #[test]
    fn double_measure_is_flagged() {
        let src = "q = qubit()\nmeasure(q)\nmeasure(q)\n";
        let diags = HeuristicAnalyzer.check("test", src).unwrap();
        assert_eq!(diags.len(), 1);
    }

    #[test]
    fn reassignment_clears_measured_state() {
        let src = "q = qubit()\nmeasure(q)\nq = qubit()\nh(q)\n";
        let diags = HeuristicAnalyzer.check("test", src).unwrap();
        assert!(
            diags.is_empty(),
            "rebinding q should make it live again: {diags:?}"
        );
    }

    #[test]
    fn comments_are_ignored() {
        let src = "q = qubit()\n# measure(q) in a comment\nh(q)\nmeasure(q)\n";
        let diags = HeuristicAnalyzer.check("test", src).unwrap();
        assert!(diags.is_empty(), "comment should not consume q: {diags:?}");
    }

    #[test]
    fn two_qubit_gate_args_are_checked() {
        let src = "a = qubit()\nb = qubit()\nmeasure(a)\ncx(a, b)\n";
        let diags = HeuristicAnalyzer.check("test", src).unwrap();
        assert_eq!(diags.len(), 1);
        assert!(diags[0].message.contains('a'));
    }
}
