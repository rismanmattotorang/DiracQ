"""Tests for the validation gate (type-check → emulate → baseline)."""

from athena.orchestrator import DefaultAgents, run_experiment
from athena.validation import validate_program


class FakeServices:
    """Injectable Services double: scripted diagnostics + counts."""

    def __init__(self, diagnostics=None, counts=None):
        self._diags = diagnostics or []
        self._counts = counts if counts is not None else {"00": 500, "11": 500}

    def check(self, guppy_src):
        return self._diags

    def emulate(self, guppy_src, n_qubits, shots, seed):
        return {"counts": self._counts, "seed": seed}


def test_gate_passes_clean_program_with_counts():
    v = validate_program("src", FakeServices())
    assert v["passed"] is True
    assert v["stage"] == "report"
    assert v["shots"] == 1000


def test_gate_fails_on_type_error():
    diags = [{"message": "use-after-measure", "severity": "error", "start": 1, "end": 2}]
    v = validate_program("src", FakeServices(diagnostics=diags))
    assert v["passed"] is False and v["stage"] == "check"
    assert v["diagnostics"] == diags


def test_gate_fails_when_no_shots_recorded():
    v = validate_program("src", FakeServices(counts={}))
    assert v["passed"] is False and v["stage"] == "emulate"


def test_gate_fails_baseline_mismatch():
    # Emulator says all 00, baseline expects a balanced Bell distribution.
    v = validate_program(
        "src",
        FakeServices(counts={"00": 1000}),
        baseline={"00": 0.5, "11": 0.5},
        tolerance=0.1,
    )
    assert v["passed"] is False and v["stage"] == "baseline"


def test_gate_passes_baseline_within_tolerance():
    v = validate_program(
        "src",
        FakeServices(counts={"00": 520, "11": 480}),
        baseline={"00": 0.5, "11": 0.5},
        tolerance=0.1,
    )
    assert v["passed"] is True


def test_orchestrator_uses_injected_services_and_reports():
    # A type error must drive the loop to repair, then (since the fake always
    # reports a diagnostic) end rejected — never "done".
    bad = FakeServices(diagnostics=[{"message": "x", "severity": "error", "start": 0, "end": 1}])
    result = run_experiment({"goal": "x"}, DefaultAgents(services=bad), max_repairs=1)
    assert result.status == "rejected"


def test_orchestrator_reports_when_gate_passes():
    ok = FakeServices()  # clean + balanced counts
    result = run_experiment({"goal": "x"}, DefaultAgents(services=ok))
    assert result.status == "reported"
    assert result.state["validation"]["passed"] is True
