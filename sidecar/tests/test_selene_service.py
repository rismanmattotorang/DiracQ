"""Tests for the Selene mock emulation backend (no selene-sim needed)."""

from diracq_sidecar import selene_service as ss


def _params(seed, shots, n):
    return {"hugr_b64": "AA==", "n_qubits": n, "shots": shots, "seed": seed, "simulator": "stim"}


def test_same_seed_reproduces_counts():
    a = ss.emulate(_params(12478, 2000, 2))
    b = ss.emulate(_params(12478, 2000, 2))
    assert a["counts"] == b["counts"]  # G7 reproducibility
    assert a["stack_versions"]["selene"] == "mock"


def test_shots_conserved_and_bitstring_width():
    r = ss.emulate(_params(7, 1500, 3))
    assert sum(r["counts"].values()) == 1500
    assert all(len(k) == 3 for k in r["counts"])


def test_different_seed_changes_distribution():
    a = ss.emulate(_params(1, 2000, 2))
    b = ss.emulate(_params(2, 2000, 2))
    assert a["counts"] != b["counts"]
