"""Tests for document-to-circuit generation (Workstream F)."""

from athena.doc2circuit import (
    default_validator,
    document_to_circuit,
    extract_spec,
)


def test_extracts_kind_and_qubits_from_brief():
    spec = extract_spec("Prepare a 4-qubit GHZ state and measure it")
    assert spec.kind == "ghz"
    assert spec.max_qubits == 4


def test_bell_paper_yields_validated_bell_program():
    r = document_to_circuit("Implements the Bell/EPR pair circuit")
    assert r.spec.kind == "bell"
    assert r.status == "ok"
    assert r.validation["passed"] is True
    assert "@guppy" in r.guppy_src and "measure(a)" in r.guppy_src


def test_teleportation_brief_is_recognized():
    r = document_to_circuit("A quantum teleportation protocol")
    assert r.spec.kind == "teleport"
    assert r.status == "ok"


def test_generated_templates_pass_the_structural_check():
    for brief in ["bell", "3-qubit ghz", "teleportation", "vqe ansatz 4 qubits"]:
        r = document_to_circuit(brief)
        assert r.validation["passed"], f"{brief} should validate: {r.validation}"


def test_validation_failure_repairs_to_bell():
    """A validator that rejects everything except a bell kernel forces repair."""

    def only_bell_ok(src: str):
        ok = "def bell" in src
        return ok, {"reason": "only bell accepted"} if not ok else {}

    r = document_to_circuit("a 5-qubit ghz state", validator=only_bell_ok)
    assert r.status == "repaired"
    assert r.spec.kind == "bell"
    assert r.attempts == 2


def test_never_reports_done_when_nothing_validates():
    r = document_to_circuit("bell", validator=lambda s: (False, {"reason": "nope"}))
    assert r.status == "rejected"
    assert r.guppy_src == ""
    assert r.validation["passed"] is False


def test_default_validator_flags_use_after_measure():
    bad = "@guppy\ndef f():\n    q = qubit()\n    r = measure(q)\n    h(q)\n"
    passed, detail = default_validator(bad)
    assert passed is False
    assert "use-after-measure" in detail["reason"]
