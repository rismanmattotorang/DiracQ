"""Tests for the real LangGraph runtime (ADR-06). Skipped if langgraph absent."""

import pytest

langgraph = pytest.importorskip("langgraph")

from athena.graph import run_with_langgraph  # noqa: E402
from athena.orchestrator import DefaultAgents  # noqa: E402


class _Services:
    def __init__(self, diags=None, counts=None):
        self._d = diags or []
        self._c = counts if counts is not None else {"00": 500, "11": 500}

    def check(self, src):
        return self._d

    def emulate(self, src, n_qubits, shots, seed):
        return {"counts": self._c}


def test_langgraph_run_reaches_report():
    out = run_with_langgraph({"goal": "prepare a bell pair"}, DefaultAgents(services=_Services()))
    assert out["status"] == "reported"
    assert out["validation"]["passed"] is True
    # The graph executed every stage.
    assert out.get("plan") and "guppy_src" in out


def test_langgraph_repair_loop_rejects_when_never_valid():
    bad = _Services(diags=[{"message": "use-after-measure", "severity": "error", "start": 0, "end": 1}])
    out = run_with_langgraph({"goal": "x"}, DefaultAgents(services=bad), max_repairs=2)
    assert out["status"] == "rejected"
