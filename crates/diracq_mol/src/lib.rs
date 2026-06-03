//! DiracQ molecule viewer (§11, Workstream G — fork crate).
//!
//! A WGPU-backed 3D viewer for the canonical [`diracq_services::molecular::Molecule`]
//! records emitted by the molecular I/O pipeline (RDKit-parsed, MLIP-relaxed).
//! Renders atoms/bonds and feeds the chemistry path (active space → Hamiltonian
//! → Guppy).

use diracq_services::molecular::Molecule;

/// Viewer state holding the molecule currently displayed.
#[derive(Default)]
pub struct MoleculeViewer {
    pub molecule: Option<Molecule>,
}

impl MoleculeViewer {
    pub fn set_molecule(&mut self, mol: Molecule) {
        self.molecule = Some(mol);
    }
}

#[cfg(feature = "gpui")]
mod view {
    // TODO(Workstream G): WGPU ball-and-stick rendering inside a GPUI Element.
}
