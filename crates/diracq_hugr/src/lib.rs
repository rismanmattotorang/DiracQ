//! DiracQ HUGR graph canvas (§16, Workstream D — fork crate).
//!
//! An interactive, GPU-accelerated canvas: hierarchical, collapsible regions,
//! pannable/zoomable at 120 fps. The HUGR is consumed from `guppy.compile()`
//! and laid out (rank/port assignment) into a [`diracq_viz::GraphLayout`]
//! off-thread; this crate's custom GPUI `Element` virtualises and draws it.
//! Selecting a node highlights the source span in the editor (bidirectional
//! mapping via the project API).

use diracq_viz::{GraphLayout, LayoutEngine};

/// Lays a compiled HUGR out for the canvas. The real engine assigns ranks and
/// ports; this stub produces an empty layout until Workstream D.
#[derive(Default)]
pub struct HugrLayoutEngine;

impl LayoutEngine for HugrLayoutEngine {
    fn layout_circuit(&self, _hugr_b64: &str) -> diracq_viz::CircuitLayout {
        diracq_viz::CircuitLayout::default()
    }
    fn layout_hugr(&self, _hugr_b64: &str) -> GraphLayout {
        // TODO(Workstream D): rank/port assignment + region detection.
        GraphLayout::default()
    }
}

#[cfg(feature = "gpui")]
mod element {
    // TODO(Workstream D): implement a custom `gpui::Element` with hit-testing
    // for selection, virtualised drawing, and pan/zoom transforms.
}
