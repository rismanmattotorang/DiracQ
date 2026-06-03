//! DiracQ Selene emulation panel (§7, Workstream C — fork crate).
//!
//! A dockable GPUI view that runs the active program on Selene (ideal and
//! noisy), streams shot histograms and resource metrics, and pins a random seed
//! for reproducibility (G7). Emulation runs off-thread on Zed's
//! `BackgroundExecutor` via `cx.spawn` and reports back by updating the entity,
//! so the UI holds 120 fps while a 16–20 qubit statevector run proceeds (G6).
//!
//! The L4 service contract and panel state are GPUI-free so they unit-test
//! without the editor; the `Render` impl lives behind the `gpui` feature.

use async_trait::async_trait;
use diracq_services::emulate::{EmulateRequest, EmulateResult};

/// L4 service contract the panel (L6 view) talks to, implemented over the
/// Python sidecar that drives selene-sim.
#[async_trait]
pub trait EmulationService: Send + Sync {
    async fn run(&self, req: EmulateRequest) -> anyhow::Result<EmulateResult>;
}

/// Panel state. Holds a handle to the emulation service and the last result.
pub struct EmulationPanel {
    pub running: bool,
    pub last: Option<EmulateResult>,
    /// Seed pinned in the toolbar; defaults are reproducible.
    pub seed: u64,
    pub shots: u32,
}

impl Default for EmulationPanel {
    fn default() -> Self {
        Self {
            running: false,
            last: None,
            seed: 12478,
            shots: 2000,
        }
    }
}

#[cfg(feature = "gpui")]
mod view {
    // TODO(Workstream C): once Zed is vendored, implement:
    //
    //   impl gpui::Render for super::EmulationPanel {
    //       fn render(&mut self, _w: &mut Window, cx: &mut Context<Self>)
    //           -> impl IntoElement
    //       {
    //           div().flex().flex_col().gap_2().p_3()
    //               .child(self.toolbar(cx))       // run / stop / seed / shots
    //               .child(match &self.last {
    //                   Some(r) => self.histogram(r, cx),
    //                   None    => self.placeholder(cx),
    //               })
    //       }
    //   }
    //
    // with `cx.spawn` calling `EmulationService::run` on the BackgroundExecutor
    // and updating the entity on completion.
}
