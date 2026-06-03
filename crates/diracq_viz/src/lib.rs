//! Render models for the DiracQ visualisation pipeline (§16, Fig. 9).
//!
//! The viewer is a shell over upstream output, never a re-implementation:
//! circuits reuse the Mermaid string tket2 already emits; HUGR graphs are laid
//! out (rank/port assignment) here and drawn natively through GPUI/WGPU by the
//! fork crates. These types are immutable layouts produced off-thread from a
//! compiled HUGR, so they carry no GPUI dependency and are unit-testable.

use serde::{Deserialize, Serialize};

/// A laid-out, GPUI-drawable circuit/graph model.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct RenderModel {
    pub nodes: Vec<RNode>,
    pub edges: Vec<REdge>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RNode {
    pub id: u64,
    pub label: String,
    /// Layout position assigned by the layout engine.
    pub col: u32,
    pub row: u32,
    /// Source span in the editor buffer (byte offsets), for bidirectional
    /// selection mapping (Workstream D acceptance criterion).
    pub span: Option<(usize, usize)>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct REdge {
    pub from: u64,
    pub to: u64,
    /// Carried across collapsed-region boundaries so edges are preserved.
    pub crosses_region: bool,
}

/// Circuit-specific layout: qubit/classical wires and gate glyphs by column.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CircuitLayout {
    pub wires: Vec<Wire>,
    pub gates: Vec<GateGlyph>,
    pub measures: Vec<MeasureGlyph>,
    pub width_cols: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wire {
    pub index: u32,
    pub classical: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateGlyph {
    pub name: String,
    pub col: u32,
    /// Wires this gate touches (controls + targets).
    pub wires: Vec<u32>,
    pub span: Option<(usize, usize)>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeasureGlyph {
    pub col: u32,
    pub qubit: u32,
    pub classical_bit: u32,
}

/// HUGR graph layout: rank/port-assigned, with collapsible hierarchical regions.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GraphLayout {
    pub model: RenderModel,
    /// Region id → child node ids (for collapse/expand).
    pub regions: Vec<(u64, Vec<u64>)>,
}

/// Off-thread layout engine contract. Implementations consume a compiled HUGR
/// (the fork crates pass the real `HugrProgram`; here it is opaque bytes).
pub trait LayoutEngine {
    fn layout_circuit(&self, hugr_b64: &str) -> CircuitLayout;
    fn layout_hugr(&self, hugr_b64: &str) -> GraphLayout;
}
