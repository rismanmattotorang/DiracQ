//! Molecular I/O payloads (§11). Molecular inputs (SMILES/PDB/.xyz) are parsed
//! and sanitised by RDKit in the sandbox (ADR-07), optionally relaxed by an
//! MLIP, and normalised to this canonical `Molecule` record.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum SourceFormat {
    Smiles,
    Pdb,
    Xyz,
    Mol,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Atom {
    pub element: String,
    pub xyz: [f64; 3],
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Molecule {
    pub atoms: Vec<Atom>,
    /// (i, j, order)
    pub bonds: Vec<(usize, usize, u8)>,
    #[serde(default)]
    pub charge: i32,
    #[serde(default = "one")]
    pub multiplicity: u32,
    pub source_format: SourceFormat,
    /// hash + parser version (G7).
    #[serde(default)]
    pub provenance: serde_json::Value,
}

fn one() -> u32 {
    1
}
