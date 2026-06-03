//! DiracQ circuit canvas (§16, Workstream D — fork crate).
//!
//! Draws a circuit diagram natively through GPUI/WGPU. A column-assignment
//! layout is computed from a HUGR dataflow region into a
//! [`diracq_viz::CircuitLayout`]; while the native canvas matures, circuits can
//! be rendered from tket2's Mermaid emission as a fallback. Selecting a gate
//! highlights the source span in the editor.

use diracq_viz::CircuitLayout;

/// Column-assignment layout for circuits, built from a HUGR dataflow region.
#[derive(Default)]
pub struct CircuitLayoutEngine;

impl CircuitLayoutEngine {
    /// Assign each gate to a column respecting wire dependencies.
    pub fn layout(&self, _hugr_b64: &str) -> CircuitLayout {
        // TODO(Workstream D): greedy column assignment over the dataflow region.
        CircuitLayout::default()
    }
}

#[cfg(feature = "gpui")]
mod element {
    // TODO(Workstream D): custom `gpui::Element`; pan/zoom; gate hit-testing →
    // editor span selection.
}
