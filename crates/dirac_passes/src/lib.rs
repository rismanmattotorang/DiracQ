//! `dirac.chem` — ParagonCorp domain HUGR extension and tket2 rewrite passes
//! (§8.2, ADR-05).
//!
//! These name chemistry macro-operations (a fermionic-excitation block, a UCC
//! ansatz layer, a Pauli-measurement-grouping op) and a small set of
//! chemistry-aware rewrite passes that run *before* tket2-qsystem preparation.
//! Because they are ordinary HUGR-to-HUGR passes they compose with the built-in
//! passes and need no compiler fork (G4); they are validated on Selene by
//! compiling with and without the pass and confirming identical results while
//! resource counts drop.
//!
//! The real passes link tket2 behind the `tket2` feature (see ADR-05 on pinning
//! the (tket2, hugr) pair together). Until then, the public surface is defined
//! against a local placeholder `Circuit` so the crate documents intent and
//! compiles standalone.

#[cfg(not(feature = "tket2"))]
mod stub {
    /// Placeholder standing in for `tket2::Circuit` until the pair is vendored.
    #[derive(Default)]
    pub struct Circuit {
        pub two_qubit_gate_count: u32,
    }
}
#[cfg(not(feature = "tket2"))]
use stub::Circuit;

#[cfg(feature = "tket2")]
use tket2::Circuit;

/// Domain pass: fuse UCC rotations and group commuting Pauli measurements,
/// reducing two-qubit-gate count before the vendor's Helios preparation.
///
/// Mirrors the spec's `dirac_chem_optimise`: reuse a tket2 rewrite, then apply
/// the two ParagonCorp-specific rewrites.
pub fn dirac_chem_optimise(circ: &mut Circuit) {
    apply_greedy_commutation(circ);
    fuse_ucc_rotations(circ);
    group_pauli_measurements(circ);
}

/// Reuse tket2's greedy commutation rewrite.
fn apply_greedy_commutation(_circ: &mut Circuit) {
    #[cfg(feature = "tket2")]
    tket2::passes::apply_greedy_commutation(_circ);
}

/// ParagonCorp-specific: fuse adjacent UCC rotation blocks.
fn fuse_ucc_rotations(_circ: &mut Circuit) {
    // TODO(Workstream H): implement against the real HUGR/tket2 IR.
}

/// ParagonCorp-specific: group commuting Pauli measurements into fewer
/// measurement settings.
fn group_pauli_measurements(_circ: &mut Circuit) {
    // TODO(Workstream H): implement against the real HUGR/tket2 IR.
}
