"""Molecular I/O pipeline (§11, ADR-07). Parses SMILES/PDB/.xyz (RDKit-centred),
sanitises, optionally relaxes via an MLIP, and emits a canonical Molecule.
No code execution from file content — malicious-molecule defence (Table 7).

The ``.xyz`` reader is a plain, dependency-free parser (xyz carries no bonds and
no embedded logic), so it works without RDKit. SMILES/PDB/MOL parsing requires
RDKit (the sanitiser of record) and is gated behind the `inference` extra.
"""

from __future__ import annotations

import hashlib
from typing import Any

from diracq_sidecar import __version__

_PARSER_VERSION = f"diracq-mol/{__version__}"


def register(dispatcher) -> None:
    dispatcher.register("mol.parse", parse)


def parse(params: dict) -> dict[str, Any]:
    """Parse and sanitise a molecular input into a canonical Molecule record.

    params: data, fmt ("smiles"|"pdb"|"xyz"|"mol").
    """
    fmt = params.get("fmt")
    data = params.get("data", "")
    if fmt == "xyz":
        return _parse_xyz(data)
    if fmt in ("smiles", "pdb", "mol"):
        _require_rdkit()
        # TODO(Workstream G): RDKit parse/sanitise (SMILES/MOL) + PDB parser.
        raise NotImplementedError(f"mol.parse({fmt}): Workstream G (RDKit)")
    raise ValueError(f"unsupported molecular format: {fmt!r}")


def _parse_xyz(data: str) -> dict[str, Any]:
    """Parse the standard XYZ format:

        line 1: <atom count>
        line 2: <comment>
        next N: <element> <x> <y> <z>
    """
    lines = data.splitlines()
    if len(lines) < 2:
        raise ValueError("xyz: too short (need a count line and a comment line)")
    try:
        n = int(lines[0].strip())
    except ValueError as exc:
        raise ValueError("xyz: first line must be the atom count") from exc

    body = lines[2 : 2 + n]
    if len(body) != n:
        raise ValueError(f"xyz: declared {n} atoms but found {len(body)}")

    atoms = []
    for i, line in enumerate(body):
        parts = line.split()
        if len(parts) < 4:
            raise ValueError(f"xyz: malformed atom line {i + 3}: {line!r}")
        element = parts[0]
        try:
            xyz = (float(parts[1]), float(parts[2]), float(parts[3]))
        except ValueError as exc:
            raise ValueError(f"xyz: bad coordinates on line {i + 3}") from exc
        atoms.append({"element": element, "xyz": xyz})

    digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return {
        "atoms": atoms,
        "bonds": [],  # xyz carries no connectivity
        "charge": 0,
        "multiplicity": 1,
        "source_format": "xyz",
        "provenance": {"sha256": digest, "parser": _PARSER_VERSION, "n_atoms": n},
    }


def _require_rdkit() -> None:
    try:
        import rdkit  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "rdkit not installed; `pip install diracq-sidecar[inference]`"
        ) from exc
