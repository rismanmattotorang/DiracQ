//! DiracQ TKET compile service (§8, Workstream H).
//!
//! Wraps tket2 (Rust + Python bindings) and pytket behind the JSON-RPC sidecar.
//! Drives the Guppy→HUGR→rebase→optimise→schedule→dirac.chem→qsystem pipeline
//! (Fig. 3) and reports resource metrics before/after optimisation so the win
//! is visible in the circuit-diff view.

use async_trait::async_trait;
use diracq_services::{
    compile::{CompileRequest, CompileResult},
    ServiceError,
};

/// A `QuantumService::compile` implementation that relays to the sidecar's
/// `tket.compile` JSON-RPC method.
#[async_trait]
pub trait CompileBackend: Send + Sync {
    async fn compile(&self, req: CompileRequest) -> Result<CompileResult, ServiceError>;
    /// Returns the Mermaid string tket2 emits (`circ.mermaid_string()`).
    async fn render_mermaid(&self, hugr_b64: &str) -> Result<String, ServiceError>;
}

/// Placeholder backend that errors until the sidecar transport is wired (M2).
pub struct UnboundBackend;

#[async_trait]
impl CompileBackend for UnboundBackend {
    async fn compile(&self, _req: CompileRequest) -> Result<CompileResult, ServiceError> {
        Err(ServiceError::Transport(
            "compile sidecar not bound (Workstream H, M2)".into(),
        ))
    }
    async fn render_mermaid(&self, _hugr_b64: &str) -> Result<String, ServiceError> {
        Err(ServiceError::Transport(
            "compile sidecar not bound (Workstream H, M2)".into(),
        ))
    }
}
