//! DiracQ L4 integration-service contracts.
//!
//! These are the small, stable Rust traits the core process (Zed fork + Tauri)
//! binds the integration services behind, plus the serde payload types carried
//! over the JSON-RPC 2.0 sidecar bridge (§5, §12 of the spec). The transport is
//! intentionally swappable so each service is independently testable; the
//! reference transport is a length-prefixed stdio pipe to the Python sidecar.
//!
//! Nothing here depends on GPUI, Tauri or the Quantinuum stack — the contracts
//! compile standalone so they can be unit-tested without the editor binary.

pub mod agent;
pub mod compile;
pub mod emulate;
pub mod error;
pub mod framing;
pub mod model;
pub mod molecular;
pub mod transport;

pub use error::ServiceError;

use async_trait::async_trait;

/// The quantum half of the integration layer: compile Guppy→HUGR via tket2 and
/// emulate the result on Selene. Implemented over the JSON-RPC sidecar.
#[async_trait]
pub trait QuantumService: Send + Sync {
    async fn compile(
        &self,
        req: compile::CompileRequest,
    ) -> Result<compile::CompileResult, ServiceError>;

    async fn emulate(
        &self,
        req: emulate::EmulateRequest,
    ) -> Result<emulate::EmulateResult, ServiceError>;

    /// Resource metrics only (cheap; powers the editor gutter badge).
    async fn resources(&self, hugr_b64: &str) -> Result<emulate::ResourceMetrics, ServiceError>;
}

/// The agentic half: start an Athena experiment run and satisfy the human gate.
/// Progress is delivered out-of-band via the event bus, not the return value.
#[async_trait]
pub trait AgentService: Send + Sync {
    async fn run(&self, spec: agent::ExperimentSpec) -> Result<agent::RunHandle, ServiceError>;
    async fn approve(&self, run: agent::RunHandle, gate: agent::GateId)
        -> Result<(), ServiceError>;
    async fn cancel(&self, run: agent::RunHandle) -> Result<(), ServiceError>;
}
