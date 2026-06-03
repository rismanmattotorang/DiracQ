//! Selene emulation-service payloads (§7). A fixed `seed` makes every run
//! reproducible (G7) — the precondition for putting emulated kernels under CI.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum SimulatorKind {
    Quest,
    Stim,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ErrorModelKind {
    #[default]
    None,
    Depolarizing,
    /// Calibrated to the operating point DiracQ targets on Helios-class
    /// hardware (the DiracNoise plugin, registered through selene-core).
    DiracCalibrated,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ErrorModelSpec {
    #[serde(default)]
    pub kind: ErrorModelKind,
    #[serde(default)]
    pub p_1q: f64,
    #[serde(default)]
    pub p_2q: f64,
    #[serde(default)]
    pub seed: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmulateRequest {
    /// Base64-encoded compiled HUGR program.
    pub hugr_b64: String,
    pub n_qubits: u32,
    pub shots: u32,
    /// Reproducibility (G7): identical seeds must reproduce identical counts.
    pub seed: u64,
    #[serde(default)]
    pub error_model: Option<ErrorModelSpec>,
    pub simulator: SimulatorKind,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ResourceMetrics {
    pub n_qubits: u32,
    pub gate_count: u32,
    pub two_qubit_gates: u32,
    pub depth: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmulateResult {
    /// bitstring → frequency.
    pub counts: BTreeMap<String, u64>,
    pub metrics: ResourceMetrics,
    pub seed: u64,
    /// Provenance (G7): the resolved version of each stack component.
    pub stack_versions: BTreeMap<String, String>,
}
