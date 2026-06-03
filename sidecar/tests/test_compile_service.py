"""Tests for the TKET compile mock backend (no pytket/tket2 needed)."""

import base64

from diracq_sidecar import compile_service as cs


def _params(src, dirac_passes=True):
    return {"guppy_src": src, "opt_level": 2, "target": "helios", "dirac_passes": dirac_passes}


def test_dirac_passes_reduce_two_qubit_gates():
    src = "cx(a,b)\ncx(b,c)\ncx(c,d)\ncx(d,e)\n"  # 4 entangling gates
    with_passes = cs.compile_guppy(_params(src, True))
    without = cs.compile_guppy(_params(src, False))
    assert without["metrics_after"]["two_qubit_gates"] == 4
    assert with_passes["metrics_after"]["two_qubit_gates"] == 3
    assert (
        with_passes["metrics_after"]["two_qubit_gates"]
        < with_passes["metrics_before"]["two_qubit_gates"]
    )


def test_deterministic_and_hugr_payload():
    a = cs.compile_guppy(_params("cx(a,b)\nqubit()\n"))
    b = cs.compile_guppy(_params("cx(a,b)\nqubit()\n"))
    assert a == b
    assert base64.b64decode(a["hugr_b64"]) == b"mock-hugr"
    assert a["metrics_before"]["n_qubits"] == 1
    assert a["mermaid"].startswith("graph")
