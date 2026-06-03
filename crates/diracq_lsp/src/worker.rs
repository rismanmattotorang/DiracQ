//! Bridge to the out-of-process `guppylang` analysis worker (ADR-03).
//!
//! The authoritative diagnostics come from `guppylang`'s own checker, which runs
//! in a Python worker. This module speaks a small **length-prefixed JSON** RPC
//! to that worker (4-byte big-endian length + UTF-8 JSON body) — the same
//! framing the DiracQ sidecar uses internally, distinct from the editor-facing
//! LSP `Content-Length` framing in [`crate::protocol`].
//!
//! Two analyzers are provided:
//! - [`WorkerAnalyzer`] spawns the worker and maps its responses to LSP types.
//! - [`FallbackAnalyzer`] tries a primary analyzer and, on any error, falls back
//!   to a secondary one. The LSP binary wires `Fallback<Worker, Heuristic>` so a
//!   missing/erroring worker degrades to the pure-Rust heuristic instead of
//!   leaving the editor with no diagnostics.

use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;

use serde_json::{json, Value};

use crate::{Diagnostic, GuppyAnalysis, HugrSummary, Severity};
use diracq_services::emulate::ResourceMetrics;
use diracq_services::framing::{read_frame, write_frame};

/// Map a worker `check` result array into LSP [`Diagnostic`]s.
fn map_diagnostics(result: &Value) -> Vec<Diagnostic> {
    result
        .get("diagnostics")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(|d| {
                    let message = d.get("message")?.as_str()?.to_string();
                    let start = d.get("start")?.as_u64()? as usize;
                    let end = d.get("end")?.as_u64()? as usize;
                    let severity = match d.get("severity").and_then(Value::as_str) {
                        Some("warning") => Severity::Warning,
                        Some("information") => Severity::Information,
                        Some("hint") => Severity::Hint,
                        _ => Severity::Error,
                    };
                    Some(Diagnostic {
                        message,
                        severity,
                        range: (start, end),
                    })
                })
                .collect()
        })
        .unwrap_or_default()
}

struct Pipes {
    stdin: ChildStdin,
    stdout: ChildStdout,
    _child: Child,
}

/// An analyzer backed by a spawned `guppylang` worker process.
pub struct WorkerAnalyzer {
    pipes: Mutex<Pipes>,
}

impl WorkerAnalyzer {
    /// Spawn the worker. `program` + `args` typically launch
    /// `python3 -m diracq_sidecar.guppy_worker` (optionally `--mock`).
    pub fn spawn(program: &str, args: &[&str], cwd: Option<&str>) -> anyhow::Result<Self> {
        let mut cmd = Command::new(program);
        cmd.args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());
        if let Some(dir) = cwd {
            cmd.current_dir(dir);
        }
        let mut child = cmd.spawn()?;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| anyhow::anyhow!("no stdin"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| anyhow::anyhow!("no stdout"))?;
        Ok(Self {
            pipes: Mutex::new(Pipes {
                stdin,
                stdout,
                _child: child,
            }),
        })
    }

    fn request(&self, method: &str, params: Value) -> anyhow::Result<Value> {
        let mut p = self
            .pipes
            .lock()
            .map_err(|_| anyhow::anyhow!("worker mutex poisoned"))?;
        write_frame(&mut p.stdin, &json!({"method": method, "params": params}))?;
        let resp = read_frame(&mut p.stdout)?.ok_or_else(|| anyhow::anyhow!("worker closed"))?;
        if let Some(err) = resp.get("error") {
            anyhow::bail!("worker error: {err}");
        }
        Ok(resp.get("result").cloned().unwrap_or(Value::Null))
    }
}

impl GuppyAnalysis for WorkerAnalyzer {
    fn check(&self, uri: &str, src: &str) -> anyhow::Result<Vec<Diagnostic>> {
        let result = self.request("check", json!({"uri": uri, "src": src}))?;
        Ok(map_diagnostics(&result))
    }

    fn compile_summary(&self, uri: &str, src: &str) -> anyhow::Result<HugrSummary> {
        let r = self.request("compile_summary", json!({"uri": uri, "src": src}))?;
        Ok(HugrSummary {
            nodes: r.get("nodes").and_then(Value::as_u64).unwrap_or(0) as u32,
            edges: r.get("edges").and_then(Value::as_u64).unwrap_or(0) as u32,
            qubits: r.get("qubits").and_then(Value::as_u64).unwrap_or(0) as u32,
        })
    }

    fn resources(&self, uri: &str, src: &str) -> anyhow::Result<ResourceMetrics> {
        let r = self.request("resources", json!({"uri": uri, "src": src}))?;
        Ok(ResourceMetrics {
            n_qubits: r.get("n_qubits").and_then(Value::as_u64).unwrap_or(0) as u32,
            gate_count: r.get("gate_count").and_then(Value::as_u64).unwrap_or(0) as u32,
            two_qubit_gates: r
                .get("two_qubit_gates")
                .and_then(Value::as_u64)
                .unwrap_or(0) as u32,
            depth: r.get("depth").and_then(Value::as_u64).unwrap_or(0) as u32,
        })
    }
}

/// Tries `primary`; on any error falls back to `secondary`.
pub struct FallbackAnalyzer<P, S> {
    primary: P,
    secondary: S,
}

impl<P, S> FallbackAnalyzer<P, S> {
    pub fn new(primary: P, secondary: S) -> Self {
        Self { primary, secondary }
    }
}

impl<P: GuppyAnalysis, S: GuppyAnalysis> GuppyAnalysis for FallbackAnalyzer<P, S> {
    fn check(&self, uri: &str, src: &str) -> anyhow::Result<Vec<Diagnostic>> {
        match self.primary.check(uri, src) {
            Ok(d) => Ok(d),
            Err(_) => self.secondary.check(uri, src),
        }
    }
    fn compile_summary(&self, uri: &str, src: &str) -> anyhow::Result<HugrSummary> {
        match self.primary.compile_summary(uri, src) {
            Ok(s) => Ok(s),
            Err(_) => self.secondary.compile_summary(uri, src),
        }
    }
    fn resources(&self, uri: &str, src: &str) -> anyhow::Result<ResourceMetrics> {
        match self.primary.resources(uri, src) {
            Ok(r) => Ok(r),
            Err(_) => self.secondary.resources(uri, src),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::analyzer::HeuristicAnalyzer;
    use std::io::Cursor;

    #[test]
    fn frame_roundtrip() {
        let mut buf = Vec::new();
        write_frame(&mut buf, &json!({"method": "check"})).unwrap();
        let mut cur = Cursor::new(buf);
        assert_eq!(read_frame(&mut cur).unwrap().unwrap()["method"], "check");
        // A second read hits clean EOF.
        assert!(read_frame(&mut cur).unwrap().is_none());
    }

    #[test]
    fn maps_worker_diagnostics() {
        let result = json!({"diagnostics": [
            {"message": "use-after-measure: q", "severity": "error", "start": 12, "end": 13}
        ]});
        let diags = map_diagnostics(&result);
        assert_eq!(diags.len(), 1);
        assert_eq!(diags[0].range, (12, 13));
        assert_eq!(diags[0].severity, Severity::Error);
    }

    /// An always-failing analyzer to exercise the fallback path.
    struct Failing;
    impl GuppyAnalysis for Failing {
        fn check(&self, _u: &str, _s: &str) -> anyhow::Result<Vec<Diagnostic>> {
            anyhow::bail!("worker down")
        }
        fn compile_summary(&self, _u: &str, _s: &str) -> anyhow::Result<HugrSummary> {
            anyhow::bail!("worker down")
        }
        fn resources(&self, _u: &str, _s: &str) -> anyhow::Result<ResourceMetrics> {
            anyhow::bail!("worker down")
        }
    }

    #[test]
    fn fallback_uses_secondary_on_error() {
        let fb = FallbackAnalyzer::new(Failing, HeuristicAnalyzer);
        let diags = fb.check("t", "q = qubit()\nmeasure(q)\nh(q)\n").unwrap();
        assert_eq!(diags.len(), 1, "should fall back to the heuristic analyzer");
        assert!(diags[0].message.contains("use-after-measure"));
    }

    /// End-to-end through the real Python worker in mock mode. Ignored by
    /// default (needs python3 + the sidecar on PYTHONPATH); run with
    /// `cargo test -p diracq_lsp -- --ignored`.
    #[test]
    #[ignore]
    fn spawns_python_mock_worker() {
        let cwd = concat!(env!("CARGO_MANIFEST_DIR"), "/../../sidecar");
        let analyzer = WorkerAnalyzer::spawn(
            "python3",
            &["-m", "diracq_sidecar.guppy_worker", "--mock"],
            Some(cwd),
        )
        .expect("spawn worker");
        let diags = analyzer
            .check("file:///t.guppy", "q = qubit()\nmeasure(q)\nh(q)\n")
            .expect("worker check");
        assert!(diags
            .iter()
            .any(|d| d.message.contains("use-after-measure")));
    }
}
