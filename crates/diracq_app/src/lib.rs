//! DiracQ application glue (§4 — the entire fork delta against upstream Zed).
//!
//! Per ADR-00/ADR-01, the fork delta is four additive changes, all registered
//! from here so no upstream Zed file is edited in place:
//!   1. a language registration for Guppy (grammar + LSP adapter + queries);
//!   2. three new GPUI panel views — HUGR graph viewer, Selene emulation panel,
//!      agent chat (the last reuses Zed's ACP agent panel; see Workstream E);
//!   3. a molecular viewer view backed by WGPU;
//!   4. a set of palette actions that bridge to the integration services.
//!
//! The `gpui` feature wires these into Zed's `Workspace` once Zed is vendored.

/// The palette actions DiracQ adds (Table 5). Each is capability-gated by the
/// Tauri shell before its body runs.
pub mod actions {
    pub const COMPILE_GUPPY: &str = "diracq: compile"; // cap quantum:compile
    pub const EMULATE_GUPPY: &str = "diracq: emulate"; // cap quantum:emulate
    pub const SHOW_CIRCUIT: &str = "diracq: show circuit";
    pub const SHOW_HUGR: &str = "diracq: show hugr";
    pub const AGENT_RUN: &str = "diracq: run experiment"; // cap agent:run
    pub const AGENT_APPROVE: &str = "diracq: approve gate"; // cap agent:approve
    pub const SUBMIT_HARDWARE: &str = "diracq: submit hardware"; // cap hw:submit (gated)
}

/// Called from the Zed fork's `main`/init to register every DiracQ surface.
/// Without the `gpui` feature this is a no-op so the workspace checks standalone.
#[cfg(feature = "gpui")]
pub fn register(_cx: &mut ()) {
    // TODO(M1): register the Guppy language, dock the three panels, register the
    // molecular viewer, and bind the palette actions to the integration services.
    unimplemented!("wire DiracQ surfaces into the Zed Workspace (M1)")
}

/// Diagnostic banner so a standalone build can confirm the glue is present.
pub fn banner() -> String {
    format!("DiracQ app glue v{}", env!("CARGO_PKG_VERSION"))
}
