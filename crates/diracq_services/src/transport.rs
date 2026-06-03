//! A synchronous JSON-RPC transport abstraction to the Python sidecar.
//!
//! Service bindings in the additive crates (emulate, compile, …) are written
//! against this trait so they stay runtime- and process-agnostic; the concrete
//! transport (length-prefixed stdio via [`crate::framing`], a localhost socket,
//! or an in-memory mock in tests) is injected by the host.

use serde_json::Value;

pub trait Transport: Send + Sync {
    /// Issue a request and return the `result` value, or an error.
    fn call(&self, method: &str, params: Value) -> anyhow::Result<Value>;
}
