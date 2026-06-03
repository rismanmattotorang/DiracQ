"""Tests for the dependency-free XYZ molecular parser (Workstream G)."""

import pytest

from diracq_sidecar import molecular as mol

# H2 at ~0.74 Å separation.
_H2_XYZ = "2\nH2 molecule\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n"


def test_parse_xyz_h2():
    m = mol.parse({"fmt": "xyz", "data": _H2_XYZ})
    assert m["source_format"] == "xyz"
    assert len(m["atoms"]) == 2
    assert m["atoms"][0]["element"] == "H"
    assert m["atoms"][1]["xyz"] == (0.0, 0.0, 0.74)
    assert m["bonds"] == []


def test_provenance_records_hash_and_parser():
    m = mol.parse({"fmt": "xyz", "data": _H2_XYZ})
    prov = m["provenance"]
    assert prov["n_atoms"] == 2
    assert prov["parser"].startswith("diracq-mol/")
    assert len(prov["sha256"]) == 64  # G7 provenance


def test_parse_xyz_is_deterministic():
    a = mol.parse({"fmt": "xyz", "data": _H2_XYZ})
    b = mol.parse({"fmt": "xyz", "data": _H2_XYZ})
    assert a == b


def test_atom_count_mismatch_is_rejected():
    with pytest.raises(ValueError):
        mol.parse({"fmt": "xyz", "data": "3\ncomment\nH 0 0 0\n"})


def test_unsupported_format_raises():
    with pytest.raises(ValueError):
        mol.parse({"fmt": "cif", "data": ""})
