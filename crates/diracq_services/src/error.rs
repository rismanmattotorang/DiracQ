//! One uniform error taxonomy across IPC and every L4 service (§12.3).

use thiserror::Error;

#[derive(Error, Debug)]
pub enum ServiceError {
    /// A capability the call requires was not granted by the Tauri shell.
    #[error("capability denied: {0}")]
    Denied(String),
    /// The JSON-RPC sidecar transport failed (spawn, framing, disconnect).
    #[error("sidecar transport: {0}")]
    Transport(String),
    /// The validator (type-check / emulate / baseline) rejected the program.
    #[error("validation failed: {0}")]
    Validation(String),
    /// An upstream Quantinuum/HF tool returned an error.
    #[error("upstream tool error: {0}")]
    Upstream(String),
}
