//! DiracQ GPUI views — the actual GPU product surfaces (§4.2, §16).
//!
//! These are real `gpui::Render` implementations docked into the Zed workspace:
//!
//! - [`EmulationPanelView`] — the Selene emulation panel: a toolbar line plus a
//!   shot-count **histogram** drawn from an [`EmulateResult`].
//! - [`CircuitCanvasView`] — the circuit diagram: a wire/column **grid** laid
//!   out by [`diracq_circuit`]/[`diracq_viz`], gate glyphs positioned by column.
//! - [`HugrGraphView`] — the HUGR graph: nodes positioned by rank (col) and row.
//!
//! Rendering uses GPUI's Tailwind-style element API. Layout is computed off the
//! UI thread by the pure-Rust engines in the sibling crates; these views only
//! draw. The crate links the vendored GPUI and therefore builds only after
//! `scripts/vendor-zed.sh` (see this crate's Cargo.toml).

use gpui::{div, prelude::*, px, rgb, Context, SharedString, Window};

use diracq_selene::EmulationPanel;
use diracq_services::emulate::EmulateResult;
use diracq_viz::CircuitLayout;

// --- palette (RGB) -----------------------------------------------------------
const BG: u32 = 0x1e1e2e;
const FG: u32 = 0xcdd6f4;
const ACCENT: u32 = 0x89b4fa;
const WIRE: u32 = 0x585b70;
const GATE: u32 = 0x313244;
const BAR: u32 = 0x89b4fa;

/// The Selene emulation panel (L6 surface).
pub struct EmulationPanelView {
    pub state: EmulationPanel,
}

impl EmulationPanelView {
    pub fn new(state: EmulationPanel) -> Self {
        Self { state }
    }

    pub fn set_result(&mut self, result: EmulateResult) {
        self.state.running = false;
        self.state.last = Some(result);
    }

    fn toolbar(&self) -> impl IntoElement {
        let status = if self.state.running { "running…" } else { "idle" };
        div()
            .flex()
            .gap_3()
            .items_center()
            .text_color(rgb(FG))
            .child(div().font_weight(gpui::FontWeight::BOLD).child("Selene"))
            .child(SharedString::from(format!("seed {}", self.state.seed)))
            .child(SharedString::from(format!("shots {}", self.state.shots)))
            .child(div().text_color(rgb(ACCENT)).child(SharedString::from(status)))
    }

    fn histogram(&self, result: &EmulateResult) -> impl IntoElement {
        let max = result.counts.values().copied().max().unwrap_or(1).max(1);
        let mut rows: Vec<(String, u64)> =
            result.counts.iter().map(|(k, v)| (k.clone(), *v)).collect();
        rows.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));

        div().flex().flex_col().gap_1().children(rows.into_iter().map(move |(bits, n)| {
            let frac = n as f32 / max as f32;
            div()
                .flex()
                .gap_2()
                .items_center()
                .text_color(rgb(FG))
                .child(div().w(px(64.0)).child(SharedString::from(bits)))
                .child(
                    div()
                        .h(px(14.0))
                        .w(px(8.0 + frac * 280.0))
                        .bg(rgb(BAR))
                        .rounded_sm(),
                )
                .child(SharedString::from(n.to_string()))
        }))
    }

    fn placeholder(&self) -> impl IntoElement {
        div()
            .text_color(rgb(WIRE))
            .child("No results yet — run a kernel on Selene.")
    }
}

impl Render for EmulationPanelView {
    fn render(&mut self, _window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        let body = match &self.state.last {
            Some(r) => self.histogram(r).into_any_element(),
            None => self.placeholder().into_any_element(),
        };
        div()
            .flex()
            .flex_col()
            .gap_3()
            .p_3()
            .bg(rgb(BG))
            .size_full()
            .child(self.toolbar())
            .child(body)
    }
}

/// The circuit diagram canvas: a wire × column grid of gate glyphs.
pub struct CircuitCanvasView {
    pub layout: CircuitLayout,
}

impl CircuitCanvasView {
    pub fn new(layout: CircuitLayout) -> Self {
        Self { layout }
    }

    /// Build a [wire][col] label grid from the laid-out gates and measures.
    fn grid(&self) -> Vec<Vec<Option<String>>> {
        let n_wires = self.layout.wires.len().max(1);
        let cols = self.layout.width_cols.max(1) as usize;
        let mut cells = vec![vec![None; cols]; n_wires];
        for g in &self.layout.gates {
            for &w in &g.wires {
                if let Some(row) = cells.get_mut(w as usize) {
                    if let Some(cell) = row.get_mut(g.col as usize) {
                        *cell = Some(g.name.clone());
                    }
                }
            }
        }
        for m in &self.layout.measures {
            if let Some(row) = cells.get_mut(m.qubit as usize) {
                if let Some(cell) = row.get_mut(m.col as usize) {
                    *cell = Some("M".to_string());
                }
            }
        }
        cells
    }
}

impl Render for CircuitCanvasView {
    fn render(&mut self, _window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        let cells = self.grid();
        div()
            .flex()
            .flex_col()
            .gap_2()
            .p_3()
            .bg(rgb(BG))
            .size_full()
            .children(cells.into_iter().enumerate().map(|(w, row)| {
                div()
                    .flex()
                    .gap_1()
                    .items_center()
                    .child(div().w(px(28.0)).text_color(rgb(WIRE)).child(SharedString::from(format!("q{w}"))))
                    .children(row.into_iter().map(|cell| {
                        let base = div().w(px(40.0)).h(px(28.0)).flex().items_center().justify_center();
                        match cell {
                            Some(name) => base
                                .bg(rgb(GATE))
                                .rounded_md()
                                .text_color(rgb(FG))
                                .child(SharedString::from(name)),
                            None => base
                                .child(div().h(px(2.0)).w(px(40.0)).bg(rgb(WIRE))),
                        }
                    }))
            }))
    }
}

/// The HUGR graph canvas: nodes placed by rank (col) and row.
pub struct HugrGraphView {
    pub layout: diracq_viz::GraphLayout,
}

impl HugrGraphView {
    pub fn new(layout: diracq_viz::GraphLayout) -> Self {
        Self { layout }
    }
}

impl Render for HugrGraphView {
    fn render(&mut self, _window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        // Group nodes by column (rank); render each rank as a column of boxes.
        let max_col = self.layout.model.nodes.iter().map(|n| n.col).max().unwrap_or(0);
        let nodes = self.layout.model.nodes.clone();
        div()
            .flex()
            .gap_4()
            .p_3()
            .bg(rgb(BG))
            .size_full()
            .children((0..=max_col).map(move |col| {
                let mut rank: Vec<_> = nodes.iter().filter(|n| n.col == col).cloned().collect();
                rank.sort_by_key(|n| n.row);
                div().flex().flex_col().gap_2().children(rank.into_iter().map(|n| {
                    div()
                        .px_2()
                        .py_1()
                        .bg(rgb(GATE))
                        .rounded_md()
                        .text_color(rgb(FG))
                        .border_1()
                        .border_color(rgb(ACCENT))
                        .child(SharedString::from(n.label))
                }))
            }))
    }
}
