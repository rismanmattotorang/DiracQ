//! DiracQ TKET compile service (§8, Workstream H).
//!
//! Wraps tket2 (Rust + Python bindings) and pytket behind the JSON-RPC sidecar.
//! Drives the Guppy→HUGR→rebase→optimise→schedule→dirac.chem→qsystem pipeline
//! (Fig. 3) and reports resource metrics before/after optimisation so the win
//! is visible in the circuit-diff view.
//!
//! Two backends implement [`CompileBackend`]:
//! - [`SidecarCompileBackend`] relays `tket.compile` over a [`Transport`] (the
//!   real pytket/tket2 path).
//! - [`MockCompileBackend`] returns a deterministic result before tket2 is
//!   wired, so the editor's compile action and the circuit-diff view work in
//!   development. It estimates the two-qubit-gate count from the source and
//!   shows a plausible optimisation win; provenance is implicit (no real HUGR).

use async_trait::async_trait;
use diracq_services::compile::{CompileRequest, CompileResult};
use diracq_services::emulate::ResourceMetrics;
use diracq_services::transport::Transport;
use diracq_services::ServiceError;

/// A `compile`/`render_mermaid` backend.
#[async_trait]
pub trait CompileBackend: Send + Sync {
    async fn compile(&self, req: CompileRequest) -> Result<CompileResult, ServiceError>;
    /// Returns the Mermaid string tket2 emits (`circ.mermaid_string()`).
    async fn render_mermaid(&self, hugr_b64: &str) -> Result<String, ServiceError>;
}

/// Placeholder backend that errors until a backend is selected.
pub struct UnboundBackend;

#[async_trait]
impl CompileBackend for UnboundBackend {
    async fn compile(&self, _req: CompileRequest) -> Result<CompileResult, ServiceError> {
        Err(ServiceError::Transport("compile backend not bound".into()))
    }
    async fn render_mermaid(&self, _hugr_b64: &str) -> Result<String, ServiceError> {
        Err(ServiceError::Transport("compile backend not bound".into()))
    }
}

/// Relays compilation to the Python sidecar's `tket.compile` method.
pub struct SidecarCompileBackend<T: Transport> {
    transport: T,
}

impl<T: Transport> SidecarCompileBackend<T> {
    pub fn new(transport: T) -> Self {
        Self { transport }
    }
}

#[async_trait]
impl<T: Transport> CompileBackend for SidecarCompileBackend<T> {
    async fn compile(&self, req: CompileRequest) -> Result<CompileResult, ServiceError> {
        let params =
            serde_json::to_value(&req).map_err(|e| ServiceError::Transport(e.to_string()))?;
        let resp = self
            .transport
            .call("tket.compile", params)
            .map_err(|e| ServiceError::Upstream(e.to_string()))?;
        serde_json::from_value(resp).map_err(|e| ServiceError::Transport(e.to_string()))
    }
    async fn render_mermaid(&self, hugr_b64: &str) -> Result<String, ServiceError> {
        let resp = self
            .transport
            .call(
                "tket.render_mermaid",
                serde_json::json!({ "hugr_b64": hugr_b64 }),
            )
            .map_err(|e| ServiceError::Upstream(e.to_string()))?;
        Ok(resp.as_str().unwrap_or_default().to_string())
    }
}

/// Deterministic mock compiler (development stand-in).
#[derive(Default)]
pub struct MockCompileBackend;

#[async_trait]
impl CompileBackend for MockCompileBackend {
    async fn compile(&self, req: CompileRequest) -> Result<CompileResult, ServiceError> {
        Ok(mock_compile(&req))
    }
    async fn render_mermaid(&self, _hugr_b64: &str) -> Result<String, ServiceError> {
        Ok(MOCK_MERMAID.to_string())
    }
}

const MOCK_MERMAID: &str = "graph LR; q0--H-->q0; q0--CX-->q1; q1--M-->c1;";

/// Pure, deterministic mock compile. Estimates the entangling-gate count from
/// the source and applies a fixed optimisation ratio so the before/after win is
/// visible in the circuit-diff view (Workstream H acceptance criterion).
pub fn mock_compile(req: &CompileRequest) -> CompileResult {
    let two_qubit_before =
        (req.guppy_src.matches("cx").count() + req.guppy_src.matches("cz").count()) as u32;
    // dirac.chem fuses UCC rotations / groups Pauli measurements → fewer 2q gates.
    let two_qubit_after = if req.dirac_passes {
        two_qubit_before - two_qubit_before / 4 // ~25% reduction
    } else {
        two_qubit_before
    };
    let qubits = req.guppy_src.matches("qubit(").count() as u32;

    CompileResult {
        hugr_b64: "bW9jay1odWdy".into(), // base64("mock-hugr")
        mermaid: MOCK_MERMAID.to_string(),
        metrics_before: ResourceMetrics {
            n_qubits: qubits,
            two_qubit_gates: two_qubit_before,
            gate_count: two_qubit_before,
            depth: two_qubit_before,
        },
        metrics_after: ResourceMetrics {
            n_qubits: qubits,
            two_qubit_gates: two_qubit_after,
            gate_count: two_qubit_after,
            depth: two_qubit_after,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use diracq_services::compile::Target;

    fn req(src: &str, dirac_passes: bool) -> CompileRequest {
        CompileRequest {
            guppy_src: src.into(),
            opt_level: 2,
            target: Target::Helios,
            dirac_passes,
        }
    }

    #[test]
    fn dirac_passes_reduce_two_qubit_gate_count() {
        let src = "cx(a,b)\ncx(b,c)\ncx(c,d)\ncx(d,e)\n"; // 4 entangling gates
        let with = mock_compile(&req(src, true));
        let without = mock_compile(&req(src, false));
        assert_eq!(without.metrics_after.two_qubit_gates, 4);
        assert!(
            with.metrics_after.two_qubit_gates < with.metrics_before.two_qubit_gates,
            "dirac.chem passes should reduce entangling gates"
        );
        assert_eq!(with.metrics_after.two_qubit_gates, 3);
    }

    #[test]
    fn mock_is_deterministic() {
        let a = mock_compile(&req("cx(a,b)\nqubit()\n", true));
        let b = mock_compile(&req("cx(a,b)\nqubit()\n", true));
        assert_eq!(a.hugr_b64, b.hugr_b64);
        assert_eq!(a.metrics_after, b.metrics_after);
        assert_eq!(a.metrics_before.n_qubits, 1);
    }
}
