//! TKET compile-service payloads (§8). Drives the
//! Guppy→HUGR→rebase→optimise→schedule→dirac.chem→qsystem pipeline (Fig. 3).

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Target {
    #[default]
    Helios,
    Generic,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileRequest {
    pub guppy_src: String,
    /// Optimisation level 0..=2.
    #[serde(default = "default_opt_level")]
    pub opt_level: u8,
    #[serde(default)]
    pub target: Target,
    /// Apply the dirac.chem domain rewrite passes before qsystem prep.
    #[serde(default = "default_true")]
    pub dirac_passes: bool,
}

fn default_opt_level() -> u8 {
    2
}
fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileResult {
    /// Base64-encoded compiled HUGR program.
    pub hugr_b64: String,
    /// Circuit diagram Mermaid string (reused from tket2's `mermaid_string()`).
    pub mermaid: String,
    /// Resource metrics before optimisation.
    pub metrics_before: super::emulate::ResourceMetrics,
    /// Resource metrics after optimisation (so the win is visible).
    pub metrics_after: super::emulate::ResourceMetrics,
}
