//! Emulation service implementations (Workstream C / M2).
//!
//! Two backends implement [`crate::EmulationService`]:
//!
//! - [`SidecarEmulationService`] relays `selene.emulate` to the Python sidecar
//!   over an injected [`Transport`] (the real selene-sim path). The transport
//!   itself lives where stdio/process access is available; this crate stays
//!   runtime-agnostic.
//! - [`MockEmulationService`] is a deterministic, **reproducible** in-process
//!   backend used for development and tests before selene-sim is wired. It does
//!   not model real quantum dynamics — it stamps provenance `selene = "mock"`
//!   so a result is never mistaken for a physical emulation — but it satisfies
//!   the M2 reproducibility property (G7): identical seeds yield identical
//!   counts, which is what lets emulated kernels go under CI.

use std::collections::BTreeMap;

use async_trait::async_trait;
use serde_json::Value;

use crate::EmulationService;
use diracq_services::emulate::{EmulateRequest, EmulateResult, ResourceMetrics};

/// A synchronous JSON-RPC transport to the sidecar. Implemented by the host
/// (e.g. over the length-prefixed stdio bridge in `diracq_services::framing`).
pub trait Transport: Send + Sync {
    fn call(&self, method: &str, params: Value) -> anyhow::Result<Value>;
}

/// Relays emulation to the Python sidecar's `selene.emulate` method.
pub struct SidecarEmulationService<T: Transport> {
    transport: T,
}

impl<T: Transport> SidecarEmulationService<T> {
    pub fn new(transport: T) -> Self {
        Self { transport }
    }
}

#[async_trait]
impl<T: Transport> EmulationService for SidecarEmulationService<T> {
    async fn run(&self, req: EmulateRequest) -> anyhow::Result<EmulateResult> {
        let params = serde_json::to_value(&req)?;
        let resp = self.transport.call("selene.emulate", params)?;
        Ok(serde_json::from_value(resp)?)
    }
}

/// Deterministic, reproducible mock emulator (development/CI stand-in).
#[derive(Default)]
pub struct MockEmulationService;

#[async_trait]
impl EmulationService for MockEmulationService {
    async fn run(&self, req: EmulateRequest) -> anyhow::Result<EmulateResult> {
        Ok(mock_emulate(&req))
    }
}

/// Pure function so it is trivially testable and obviously seed-deterministic.
pub fn mock_emulate(req: &EmulateRequest) -> EmulateResult {
    let n = req.n_qubits.clamp(1, 20);
    let mut rng = SplitMix64::new(req.seed ^ ((n as u64) << 32) ^ (req.shots as u64));
    let mut counts: BTreeMap<String, u64> = BTreeMap::new();
    for _ in 0..req.shots {
        let bits = rng.next_u64();
        let mut s = String::with_capacity(n as usize);
        for q in 0..n {
            s.push(if (bits >> q) & 1 == 1 { '1' } else { '0' });
        }
        *counts.entry(s).or_insert(0) += 1;
    }

    let mut stack_versions = BTreeMap::new();
    // Provenance makes it unmistakable that this is not a physical emulation.
    stack_versions.insert("selene".to_string(), "mock".to_string());
    stack_versions.insert(
        "diracq_selene".to_string(),
        env!("CARGO_PKG_VERSION").to_string(),
    );

    EmulateResult {
        counts,
        metrics: ResourceMetrics {
            n_qubits: n,
            ..Default::default()
        },
        seed: req.seed,
        stack_versions,
    }
}

/// A tiny, dependency-free deterministic PRNG (SplitMix64). Used only by the
/// mock backend; reproducibility is the point, not cryptographic quality.
struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }
    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use diracq_services::emulate::SimulatorKind;

    fn req(seed: u64, shots: u32, n: u32) -> EmulateRequest {
        EmulateRequest {
            hugr_b64: "AA==".into(),
            n_qubits: n,
            shots,
            seed,
            error_model: None,
            simulator: SimulatorKind::Stim,
        }
    }

    #[test]
    fn same_seed_reproduces_identical_counts() {
        let a = mock_emulate(&req(12478, 2000, 2));
        let b = mock_emulate(&req(12478, 2000, 2));
        assert_eq!(
            a.counts, b.counts,
            "G7: identical seeds must reproduce counts"
        );
        assert_eq!(a.seed, 12478);
    }

    #[test]
    fn different_seed_changes_distribution() {
        let a = mock_emulate(&req(1, 2000, 2));
        let b = mock_emulate(&req(2, 2000, 2));
        assert_ne!(a.counts, b.counts);
    }

    #[test]
    fn shots_are_conserved_and_provenance_is_marked_mock() {
        let r = mock_emulate(&req(7, 1500, 3));
        assert_eq!(r.counts.values().sum::<u64>(), 1500);
        assert_eq!(
            r.stack_versions.get("selene").map(String::as_str),
            Some("mock")
        );
        // 3-qubit bitstrings only.
        assert!(r.counts.keys().all(|k| k.len() == 3));
    }

    #[test]
    fn mock_service_runs_through_the_async_trait() {
        let svc = MockEmulationService;
        let r = block_on(svc.run(req(99, 100, 2))).unwrap();
        assert_eq!(r.counts.values().sum::<u64>(), 100);
    }

    /// Minimal dependency-free executor: the mock future never yields, so a
    /// single poll with a no-op waker completes it.
    fn block_on<F: std::future::Future>(mut fut: F) -> F::Output {
        use std::pin::Pin;
        use std::task::{Context, Poll, RawWaker, RawWakerVTable, Waker};

        const VTABLE: RawWakerVTable = RawWakerVTable::new(
            |_| RawWaker::new(std::ptr::null(), &VTABLE),
            |_| {},
            |_| {},
            |_| {},
        );
        let waker = unsafe { Waker::from_raw(RawWaker::new(std::ptr::null(), &VTABLE)) };
        let mut cx = Context::from_waker(&waker);
        // Safety: `fut` is owned and not moved after pinning.
        let mut fut = unsafe { Pin::new_unchecked(&mut fut) };
        loop {
            match fut.as_mut().poll(&mut cx) {
                Poll::Ready(v) => return v,
                Poll::Pending => continue,
            }
        }
    }
}
