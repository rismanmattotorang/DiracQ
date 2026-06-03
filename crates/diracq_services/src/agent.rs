//! Agentic-subsystem payloads (§9). An experiment is *declared*, not coded; the
//! Athena orchestrator reads the declaration and runs the plan→retrieve→
//! pre-screen→code-gen→validate→report loop (Fig. 4) with a human gate before
//! any scarce/irreversible action (G3).

use serde::{Deserialize, Serialize};

/// Opaque handle to a running experiment graph.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunHandle(pub String);

/// Identifies a pending human-approval gate within a run.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateId(pub String);

/// Mirrors `diracq/experiment.yaml` — the declarative agentic experiment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentSpec {
    pub name: String,
    pub goal: String,
    #[serde(default)]
    pub retriever: serde_json::Value,
    #[serde(default)]
    pub pre_screen: serde_json::Value,
    #[serde(default)]
    pub quantum: serde_json::Value,
    #[serde(default)]
    pub validation: serde_json::Value,
    #[serde(default)]
    pub report: serde_json::Value,
}
