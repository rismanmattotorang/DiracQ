"""Molecular I/O pipeline (§11, ADR-07). Parses SMILES/PDB/.xyz (RDKit-centred),
sanitises, optionally relaxes via an MLIP, and emits a canonical Molecule.
No code execution from file content — malicious-molecule defence (Table 7).
"""

from __future__ import annotations

from typing import Any


def register(dispatcher) -> None:
    dispatcher.register("mol.parse", parse)


def parse(params: dict) -> dict[str, Any]:
    """Parse and sanitise a molecular input into a canonical Molecule record.

    Expected params: data, fmt ("smiles"|"pdb"|"xyz"|"mol").
    """
    fmt = params.get("fmt")
    if fmt not in ("smiles", "pdb", "xyz", "mol"):
        raise ValueError(f"unsupported molecular format: {fmt!r}")
    _require_rdkit()
    # TODO(Workstream G): RDKit parse/sanitise (SMILES/MOL), PDB parser for
    # structures, plain reader for .xyz; attach provenance (hash, parser ver).
    raise NotImplementedError("mol.parse: Workstream G")


def _require_rdkit() -> None:
    try:
        import rdkit  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "rdkit not installed; `pip install diracq-sidecar[inference]`"
        ) from exc
