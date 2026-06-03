"""Tests for the Athena orchestration loop and ACP session lifecycle.

Run with: PYTHONPATH=. python -m pytest agents/athena/tests
"""

from pathlib import Path

from athena.orchestrator import DefaultAgents, run_experiment
from athena.server import AthenaAgent


def test_default_run_reports_on_emulator_path():
    spec = {"goal": "rank antioxidants", "quantum": {"backend": "selene"}}
    result = run_experiment(spec)
    assert result.status == "reported"
    assert result.repairs == 0
    assert "candidate" in result.state["report"].lower()


def test_validation_gate_repairs_then_reports():
    """A validator that fails twice then passes must loop code_gen→validate."""

    class FlakyAgents(DefaultAgents):
        def __init__(self):
            self.attempts = 0

        def validate(self, state):
            self.attempts += 1
            passed = self.attempts >= 3  # fail #1, #2; pass #3
            state["validation"] = {"passed": passed}
            return state

    result = run_experiment({"goal": "x"}, FlakyAgents(), max_repairs=3)
    assert result.status == "reported"
    assert result.repairs == 2  # two repairs before the third attempt passed


def test_validation_gate_rejects_when_never_passes():
    class AlwaysFail(DefaultAgents):
        def validate(self, state):
            state["validation"] = {"passed": False}
            return state

    result = run_experiment({"goal": "x"}, AlwaysFail(), max_repairs=2)
    assert result.status == "rejected"
    assert "report" not in result.state  # never surfaced as done


def test_human_gate_blocks_hardware_until_approved():
    spec = {"goal": "x", "quantum": {"backend": "helios"}}  # non-emulator → gated
    result = run_experiment(spec)
    assert result.status == "awaiting_approval"
    assert any(e["type"] == "awaiting_approval" and e["gate"] == "hw:submit" for e in result.events)


def test_approved_hardware_run_reports():
    class Approving(DefaultAgents):
        def pre_screen(self, state):
            state = super().pre_screen(state)
            state["approved"] = True  # human approved the gate
            return state

    result = run_experiment({"goal": "x", "quantum": {"backend": "helios"}}, Approving())
    assert result.status == "reported"


def test_acp_session_lifecycle_and_streaming_prompt():
    agent = AthenaAgent()
    s1 = agent.new_session(Path("/tmp/ws"))
    s2 = agent.new_session(Path("/tmp/ws"))
    assert s1 != s2  # parallel threads get distinct sessions

    events: list[dict] = []
    out = agent.prompt(s1, {"goal": "rank antioxidants"}, events.append)
    assert out["status"] == "reported"
    kinds = [e["type"] for e in events]
    assert kinds[0] == "plan" and "report" in kinds and kinds[-1] == "done"

    agent.close_session(s1)
    agent.close_session(s2)


def test_cancellation_is_honored():
    agent = AthenaAgent()
    sid = agent.new_session(Path("."))
    agent.cancel(sid)
    events: list[dict] = []
    out = agent.prompt(sid, {"goal": "x"}, events.append)
    assert out["status"] == "cancelled"
    assert events == [{"type": "cancelled", "session": sid}]
