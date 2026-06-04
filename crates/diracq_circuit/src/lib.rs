//! DiracQ circuit canvas (§16, Workstream D — fork crate).
//!
//! Draws a circuit diagram natively through GPUI/WGPU. The drawing is gated
//! behind the `gpui` feature; the **layout** — a column-assignment over a
//! circuit's gate sequence — is pure Rust so it is unit-testable without the
//! editor. Selecting a gate highlights the source span in the editor via the
//! `span` carried on each glyph (bidirectional mapping).
//!
//! The column-assignment rule is the standard one: each gate is placed in the
//! earliest column at or after the last column used by any wire it touches, and
//! then advances those wires past it. Gates on disjoint wires therefore pack
//! into the same column, which is what makes a circuit read left-to-right by
//! depth.

use diracq_viz::{CircuitLayout, GateGlyph, MeasureGlyph, Wire};

/// One operation in a circuit, independent of HUGR encoding. The circuit canvas
/// lays these out; a HUGR dataflow region is lowered to a `Vec<GateOp>` by the
/// compile service (the real lowering is the Workstream-H/D TODO).
#[derive(Debug, Clone)]
pub struct GateOp {
    pub name: String,
    /// Qubit wire indices this op touches (controls + targets, in order).
    pub qubits: Vec<u32>,
    /// For `measure`, the classical bit it writes (else ignored).
    pub classical_bit: Option<u32>,
    /// Source span in the editor buffer, for bidirectional selection.
    pub span: Option<(usize, usize)>,
}

impl GateOp {
    pub fn new(name: &str, qubits: impl Into<Vec<u32>>) -> Self {
        Self {
            name: name.to_string(),
            qubits: qubits.into(),
            classical_bit: None,
            span: None,
        }
    }
    pub fn with_span(mut self, span: (usize, usize)) -> Self {
        self.span = Some(span);
        self
    }
    pub fn measure(qubit: u32, classical_bit: u32) -> Self {
        Self {
            name: "measure".to_string(),
            qubits: vec![qubit],
            classical_bit: Some(classical_bit),
            span: None,
        }
    }
    fn is_measure(&self) -> bool {
        self.name == "measure"
    }
}

/// Lays circuits out by column assignment. `from_hugr` (decoding a real HUGR)
/// is the remaining Workstream-D work; [`layout_ops`] is the tested core.
#[derive(Default)]
pub struct CircuitLayoutEngine;

impl CircuitLayoutEngine {
    pub fn layout(&self, _hugr_b64: &str) -> CircuitLayout {
        // TODO(Workstream D/H): decode the HUGR dataflow region into GateOps.
        CircuitLayout::default()
    }
    pub fn layout_ops(&self, ops: &[GateOp], n_wires: u32) -> CircuitLayout {
        layout_ops(ops, n_wires)
    }
}

/// The column-assignment algorithm. `n_wires` is the number of qubit lines.
pub fn layout_ops(ops: &[GateOp], n_wires: u32) -> CircuitLayout {
    // `cursor[w]` = the first free column on wire `w`.
    let mut cursor = vec![0u32; n_wires as usize];
    let mut gates = Vec::new();
    let mut measures = Vec::new();
    let mut width_cols = 0u32;

    for op in ops {
        if op.qubits.is_empty() {
            continue;
        }
        // Earliest column where all touched wires are free.
        let col = op
            .qubits
            .iter()
            .map(|&q| cursor.get(q as usize).copied().unwrap_or(0))
            .max()
            .unwrap_or(0);
        // Occupy that column on every touched wire; advance their cursors.
        for &q in &op.qubits {
            if let Some(c) = cursor.get_mut(q as usize) {
                *c = col + 1;
            }
        }
        width_cols = width_cols.max(col + 1);

        if op.is_measure() {
            measures.push(MeasureGlyph {
                col,
                qubit: op.qubits[0],
                classical_bit: op.classical_bit.unwrap_or(op.qubits[0]),
            });
        } else {
            gates.push(GateGlyph {
                name: op.name.clone(),
                col,
                wires: op.qubits.clone(),
                span: op.span,
            });
        }
    }

    let wires = (0..n_wires)
        .map(|index| Wire {
            index,
            classical: false,
        })
        .collect();

    CircuitLayout {
        wires,
        gates,
        measures,
        width_cols,
    }
}

/// Build a circuit from the sidecar's `circuit.extract` payload
/// (`{n_qubits, gates:[{name, qubits:[..]}], measures:[{qubit, classical_bit}]}`),
/// returning the gate ops and the wire count. This is how the canvas turns a
/// real compiled program into a [`CircuitLayout`] (via [`layout_ops`]).
pub fn ops_from_extracted(v: &serde_json::Value) -> (Vec<GateOp>, u32) {
    let n_wires = v.get("n_qubits").and_then(|x| x.as_u64()).unwrap_or(0) as u32;
    let mut ops = Vec::new();
    if let Some(gates) = v.get("gates").and_then(|g| g.as_array()) {
        for g in gates {
            let name = g.get("name").and_then(|n| n.as_str()).unwrap_or("?");
            let qubits: Vec<u32> = g
                .get("qubits")
                .and_then(|q| q.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_u64().map(|n| n as u32))
                        .collect()
                })
                .unwrap_or_default();
            ops.push(GateOp::new(name, qubits));
        }
    }
    if let Some(measures) = v.get("measures").and_then(|m| m.as_array()) {
        for m in measures {
            let q = m.get("qubit").and_then(|x| x.as_u64()).unwrap_or(0) as u32;
            let bit = m
                .get("classical_bit")
                .and_then(|x| x.as_u64())
                .unwrap_or(q as u64) as u32;
            ops.push(GateOp::measure(q, bit));
        }
    }
    let wires = n_wires.max(
        ops.iter()
            .flat_map(|o| o.qubits.iter().copied())
            .max()
            .map(|m| m + 1)
            .unwrap_or(0),
    );
    (ops, wires)
}

#[cfg(feature = "gpui")]
mod element {
    // TODO(Workstream D): custom `gpui::Element`; pan/zoom; gate hit-testing →
    // editor span selection (using GateGlyph.span).
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn independent_gates_share_a_column() {
        // h(0) and h(1) touch disjoint wires → both in column 0.
        let ops = [GateOp::new("h", [0]), GateOp::new("h", [1])];
        let layout = layout_ops(&ops, 2);
        assert_eq!(layout.gates.len(), 2);
        assert!(layout.gates.iter().all(|g| g.col == 0));
        assert_eq!(layout.width_cols, 1);
    }

    #[test]
    fn dependent_gates_serialize_into_columns() {
        // h(0); cx(0,1); measure(0) — each depends on the previous on wire 0.
        let ops = [
            GateOp::new("h", [0]),
            GateOp::new("cx", [0, 1]),
            GateOp::measure(0, 0),
        ];
        let layout = layout_ops(&ops, 2);
        assert_eq!(layout.gates[0].col, 0); // h
        assert_eq!(layout.gates[1].col, 1); // cx waits for h on wire 0
        assert_eq!(layout.measures[0].col, 2); // measure waits for cx
        assert_eq!(layout.width_cols, 3);
    }

    #[test]
    fn two_qubit_gate_blocks_both_wires() {
        // cx(0,1) then h(1): h must wait for the cx column.
        let ops = [GateOp::new("cx", [0, 1]), GateOp::new("h", [1])];
        let layout = layout_ops(&ops, 2);
        assert_eq!(layout.gates[0].col, 0);
        assert_eq!(layout.gates[1].col, 1);
    }

    #[test]
    fn spans_are_preserved_for_selection_mapping() {
        let ops = [GateOp::new("h", [0]).with_span((10, 14))];
        let layout = layout_ops(&ops, 1);
        assert_eq!(layout.gates[0].span, Some((10, 14)));
    }

    #[test]
    fn builds_ops_from_extracted_payload() {
        let v = serde_json::json!({
            "n_qubits": 2,
            "gates": [
                {"name": "h", "qubits": [0]},
                {"name": "cx", "qubits": [0, 1]}
            ],
            "measures": [
                {"qubit": 0, "classical_bit": 0},
                {"qubit": 1, "classical_bit": 1}
            ]
        });
        let (ops, wires) = ops_from_extracted(&v);
        assert_eq!(wires, 2);
        assert_eq!(ops.len(), 4); // h, cx, 2 measures
                                  // Lay it out: h@0, cx@1, measures@2 → depth 3, 2 measures.
        let layout = layout_ops(&ops, wires);
        assert_eq!(layout.width_cols, 3);
        assert_eq!(layout.measures.len(), 2);
        assert_eq!(layout.gates.iter().find(|g| g.name == "cx").unwrap().col, 1);
    }

    #[test]
    fn extracted_wire_count_grows_to_fit_qubit_indices() {
        let v = serde_json::json!({"n_qubits": 0, "gates": [{"name":"cx","qubits":[0,3]}], "measures": []});
        let (_ops, wires) = ops_from_extracted(&v);
        assert_eq!(wires, 4); // max index 3 → 4 wires
    }

    #[test]
    fn bell_circuit_has_depth_three() {
        let ops = [
            GateOp::new("h", [0]),
            GateOp::new("cx", [0, 1]),
            GateOp::measure(0, 0),
            GateOp::measure(1, 1),
        ];
        let layout = layout_ops(&ops, 2);
        // h@0, cx@1, measure(0)@2, measure(1)@2 → depth 3.
        assert_eq!(layout.width_cols, 3);
        assert_eq!(layout.measures.len(), 2);
    }
}
