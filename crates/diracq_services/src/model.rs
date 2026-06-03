//! HuggingFace inference-sidecar payloads (§10). The model registry records
//! each model's licence and revision; inference refuses any model used outside
//! its licensed scope — a governance requirement enforced in code, not convention.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Domain {
    Chemistry,
    Biology,
    Physics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCard {
    /// e.g. "facebook/esm2_t33_650M_UR50D".
    pub id: String,
    pub domain: Domain,
    /// "embedding" | "structure" | "potential" | ...
    pub task: String,
    /// Enforced before use.
    pub licence: String,
    /// Pinned commit/tag (provenance).
    pub revision: String,
    pub commercial_ok: bool,
}
