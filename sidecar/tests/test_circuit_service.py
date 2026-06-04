"""Tests for circuit.extract on the source-parse mock path (no stack needed)."""

from diracq_sidecar import circuit_service as cz


def test_mock_extract_parses_gates_and_measures():
    src = (
        "@guppy\ndef main() -> None:\n"
        "    a = qubit()\n    b = qubit()\n    h(a)\n    cx(a, b)\n"
        "    measure(a)\n    measure(b)\n"
    )
    out = cz._extract_mock(src, 2)
    names = [g["name"] for g in out["gates"]]
    assert "h" in names and "cx" in names
    assert out["n_qubits"] == 2
    assert len(out["measures"]) == 2
    # cx touches two distinct wire indices (first-seen order: a=0, b=1).
    cx = next(g for g in out["gates"] if g["name"] == "cx")
    assert cx["qubits"] == [0, 1]


def test_mock_extract_unsupported_calls_ignored():
    out = cz._extract_mock("@guppy\ndef f():\n    print(x)\n    h(q)\n", 1)
    assert [g["name"] for g in out["gates"]] == ["h"]
