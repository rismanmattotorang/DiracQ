"""Pydantic payload models shared by the sidecar services (§7, §8, §10, §11).

These mirror the Rust serde types in ``crates/diracq_services`` one-to-one so
the JSON-RPC envelope round-trips losslessly across the bridge.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


# --- Selene emulation (§7) ----------------------------------------------------


class ErrorModelSpec(BaseModel):
    kind: Literal["none", "depolarizing", "dirac_calibrated"] = "none"
    p_1q: float = 0.0
    p_2q: float = 0.0
    seed: Optional[int] = None


class ResourceMetrics(BaseModel):
    n_qubits: int = 0
    gate_count: int = 0
    two_qubit_gates: int = 0
    depth: int = 0


class EmulationResult(BaseModel):
    counts: dict[str, int]  # bitstring -> frequency
    metrics: ResourceMetrics
    seed: int
    stack_versions: dict[str, str]  # provenance (G7)


# --- TKET compile (§8) --------------------------------------------------------


class CompileRequest(BaseModel):
    guppy_src: str
    opt_level: Literal[0, 1, 2] = 2
    target: Literal["helios", "generic"] = "helios"
    dirac_passes: bool = True  # apply dirac.chem rewrites


class CompileResult(BaseModel):
    hugr_b64: str
    mermaid: str  # circuit diagram for the viewer
    metrics_before: ResourceMetrics
    metrics_after: ResourceMetrics


# --- HuggingFace inference (§10) ---------------------------------------------


class ModelCard(BaseModel):
    id: str
    domain: Literal["chemistry", "biology", "physics"]
    task: str
    licence: str  # enforced before use
    revision: str  # pinned commit/tag (provenance)
    commercial_ok: bool


# --- Molecular I/O (§11) ------------------------------------------------------


class Atom(BaseModel):
    element: str
    xyz: tuple[float, float, float]


class Molecule(BaseModel):
    atoms: list[Atom]
    bonds: list[tuple[int, int, int]]  # (i, j, order)
    charge: int = 0
    multiplicity: int = 1
    source_format: Literal["smiles", "pdb", "xyz", "mol"]
    provenance: dict = {}  # hash, parser version (G7)
