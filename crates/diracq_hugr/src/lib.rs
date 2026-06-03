//! DiracQ HUGR graph canvas (§16, Workstream D — fork crate).
//!
//! An interactive, GPU-accelerated canvas: hierarchical, collapsible regions,
//! pannable/zoomable. The GPU drawing is gated behind the `gpui` feature; the
//! **layout** — a layered (rank) assignment over the HUGR dataflow DAG — is pure
//! Rust and unit-testable. A node's `col` is its rank (longest path from a
//! source), and its `row` is its order within that rank, which yields the
//! familiar left-to-right dataflow layering. Region membership is preserved so
//! the canvas can collapse a region while keeping edges that cross its boundary.

use diracq_viz::{GraphLayout, LayoutEngine, REdge, RNode, RenderModel};

/// A HUGR node to lay out (decoded from the compiled program).
#[derive(Debug, Clone)]
pub struct GraphNode {
    pub id: u64,
    pub label: String,
    /// Source span for bidirectional selection (optional).
    pub span: Option<(usize, usize)>,
}

/// A directed dataflow edge `from -> to` (by node id).
#[derive(Debug, Clone, Copy)]
pub struct GraphEdge {
    pub from: u64,
    pub to: u64,
}

/// Lays a compiled HUGR out for the canvas. `layout_dag` is the tested core;
/// decoding a real HUGR into nodes/edges/regions is the Workstream-D TODO.
#[derive(Default)]
pub struct HugrLayoutEngine;

impl LayoutEngine for HugrLayoutEngine {
    fn layout_circuit(&self, _hugr_b64: &str) -> diracq_viz::CircuitLayout {
        diracq_viz::CircuitLayout::default()
    }
    fn layout_hugr(&self, _hugr_b64: &str) -> GraphLayout {
        // TODO(Workstream D): decode the HUGR into nodes/edges/regions.
        GraphLayout::default()
    }
}

impl HugrLayoutEngine {
    /// Lay out a dataflow DAG. `regions` maps a region (container) node id to the
    /// ids of its children, used for collapse/expand on the canvas.
    pub fn layout_dag(
        &self,
        nodes: &[GraphNode],
        edges: &[GraphEdge],
        regions: &[(u64, Vec<u64>)],
    ) -> GraphLayout {
        layout_dag(nodes, edges, regions)
    }
}

/// Longest-path rank assignment. Ranks are computed by relaxing edges in
/// topological order; nodes with no incoming edges start at rank 0. Cycles (a
/// malformed DAG) are tolerated — any node not reached keeps rank 0.
pub fn layout_dag(
    nodes: &[GraphNode],
    edges: &[GraphEdge],
    regions: &[(u64, Vec<u64>)],
) -> GraphLayout {
    use std::collections::{HashMap, VecDeque};

    let index: HashMap<u64, usize> = nodes.iter().enumerate().map(|(i, n)| (n.id, i)).collect();
    let n = nodes.len();

    // Build adjacency + indegree over valid edges only.
    let mut adj: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut indeg = vec![0usize; n];
    for e in edges {
        if let (Some(&u), Some(&v)) = (index.get(&e.from), index.get(&e.to)) {
            adj[u].push(v);
            indeg[v] += 1;
        }
    }

    // Kahn topological order; relax ranks along the way (longest path).
    let mut rank = vec![0u32; n];
    let mut remaining = indeg.clone();
    let mut queue: VecDeque<usize> = (0..n).filter(|&i| remaining[i] == 0).collect();
    while let Some(u) = queue.pop_front() {
        for &v in &adj[u] {
            rank[v] = rank[v].max(rank[u] + 1);
            remaining[v] -= 1;
            if remaining[v] == 0 {
                queue.push_back(v);
            }
        }
    }

    // Row = order within a rank (stable by node order).
    let mut row_cursor: std::collections::HashMap<u32, u32> = std::collections::HashMap::new();
    let rnodes: Vec<RNode> = nodes
        .iter()
        .enumerate()
        .map(|(i, node)| {
            let col = rank[i];
            let row = row_cursor.entry(col).or_insert(0);
            let this_row = *row;
            *row += 1;
            RNode {
                id: node.id,
                label: node.label.clone(),
                col,
                row: this_row,
                span: node.span,
            }
        })
        .collect();

    // An edge "crosses a region" if its endpoints fall in different region sets.
    let region_of: HashMap<u64, u64> = regions
        .iter()
        .flat_map(|(rid, kids)| kids.iter().map(move |k| (*k, *rid)))
        .collect();
    let redges: Vec<REdge> = edges
        .iter()
        .filter(|e| index.contains_key(&e.from) && index.contains_key(&e.to))
        .map(|e| REdge {
            from: e.from,
            to: e.to,
            crosses_region: region_of.get(&e.from) != region_of.get(&e.to),
        })
        .collect();

    GraphLayout {
        model: RenderModel {
            nodes: rnodes,
            edges: redges,
        },
        regions: regions.to_vec(),
    }
}

#[cfg(feature = "gpui")]
mod element {
    // TODO(Workstream D): custom `gpui::Element` with hit-testing for selection,
    // virtualised drawing, pan/zoom, and region collapse/expand.
}

#[cfg(test)]
mod tests {
    use super::*;

    fn node(id: u64, label: &str) -> GraphNode {
        GraphNode {
            id,
            label: label.into(),
            span: None,
        }
    }

    #[test]
    fn linear_chain_gets_increasing_ranks() {
        // 1 -> 2 -> 3
        let nodes = [node(1, "a"), node(2, "b"), node(3, "c")];
        let edges = [GraphEdge { from: 1, to: 2 }, GraphEdge { from: 2, to: 3 }];
        let g = layout_dag(&nodes, &edges, &[]);
        let col = |id: u64| g.model.nodes.iter().find(|n| n.id == id).unwrap().col;
        assert_eq!(col(1), 0);
        assert_eq!(col(2), 1);
        assert_eq!(col(3), 2);
    }

    #[test]
    fn longest_path_wins_for_diamond() {
        // 1 -> 2 -> 4 and 1 -> 4 ; node 4 should rank after the longer path.
        let nodes = [node(1, "a"), node(2, "b"), node(4, "d")];
        let edges = [
            GraphEdge { from: 1, to: 2 },
            GraphEdge { from: 2, to: 4 },
            GraphEdge { from: 1, to: 4 },
        ];
        let g = layout_dag(&nodes, &edges, &[]);
        let col = |id: u64| g.model.nodes.iter().find(|n| n.id == id).unwrap().col;
        assert_eq!(
            col(4),
            2,
            "rank must follow the longest path, not the short edge"
        );
    }

    #[test]
    fn rows_disambiguate_nodes_at_the_same_rank() {
        // Two sources at rank 0 → distinct rows.
        let nodes = [node(1, "a"), node(2, "b")];
        let g = layout_dag(&nodes, &[], &[]);
        let rows: Vec<u32> = g.model.nodes.iter().map(|n| n.row).collect();
        assert_eq!(rows, vec![0, 1]);
        assert!(g.model.nodes.iter().all(|n| n.col == 0));
    }

    #[test]
    fn region_crossing_edges_are_flagged() {
        // region 10 contains {1,2}; edge 2->3 leaves the region.
        let nodes = [node(1, "a"), node(2, "b"), node(3, "c")];
        let edges = [
            GraphEdge { from: 1, to: 2 }, // inside region 10
            GraphEdge { from: 2, to: 3 }, // crosses out
        ];
        let regions = [(10u64, vec![1u64, 2u64])];
        let g = layout_dag(&nodes, &edges, &regions);
        let e = |f: u64, t: u64| {
            g.model
                .edges
                .iter()
                .find(|e| e.from == f && e.to == t)
                .unwrap()
                .crosses_region
        };
        assert!(!e(1, 2), "1->2 stays within region 10");
        assert!(e(2, 3), "2->3 leaves region 10");
        assert_eq!(g.regions.len(), 1);
    }
}
