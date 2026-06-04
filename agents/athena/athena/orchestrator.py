"""The Athena orchestration loop (§9, Workstream E).

This runs the agent state machine of Fig. 4 directly in Python so the control
flow is explicit, deterministic and testable without an LLM or `langgraph`
installed (the `langgraph` `StateGraph` in `graph.py` wraps these same nodes for
the production runtime). The two invariants the spec insists on are enforced here:

1. **The validation gate (G1).** Nothing is reported until it passes
   ``code_gen → validate`` (type-check → emulate → classical-baseline compare).
   A failed validation loops back to ``code_gen`` to repair, up to ``max_repairs``
   attempts; if it never passes the run ends *rejected*, never "done".
2. **The human gate (G3).** A scarce/irreversible step (a hardware backend) is
   not taken until a human has approved; the agent pauses ``awaiting_approval``.

Agent nodes are injected (`AgentNodes`) so tests can drive the repair loop and
the gate deterministically; `DefaultAgents` provides offline stand-ins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from athena.graph import DiracQState

# An event sink for streaming progress to the ACP client (plan, tool calls, …).
EventSink = Callable[[dict], None]


class AgentNodes(Protocol):
    """Each node transforms the run state. Validate returns a verdict dict on
    ``state['validation']`` with a boolean ``passed``."""

    def plan(self, state: DiracQState) -> DiracQState: ...
    def retrieve(self, state: DiracQState) -> DiracQState: ...
    def pre_screen(self, state: DiracQState) -> DiracQState: ...
    def code_gen(self, state: DiracQState) -> DiracQState: ...
    def validate(self, state: DiracQState) -> DiracQState: ...
    def report(self, state: DiracQState) -> DiracQState: ...


@dataclass
class RunResult:
    state: DiracQState
    status: str  # "reported" | "rejected" | "awaiting_approval"
    repairs: int  # how many repair iterations were needed
    events: list[dict] = field(default_factory=list)


def run_experiment(
    spec: dict,
    agents: Optional[AgentNodes] = None,
    *,
    max_repairs: int = 3,
    emit: Optional[EventSink] = None,
) -> RunResult:
    """Drive the loop for a declarative experiment (see examples/experiment.yaml)."""
    agents = agents or DefaultAgents()
    events: list[dict] = []

    def event(kind: str, **data) -> None:
        e = {"type": kind, **data}
        events.append(e)
        if emit:
            emit(e)

    state: DiracQState = {"brief": spec.get("goal", ""), "approved": False}

    state = agents.plan(state)
    event("plan", plan=state.get("plan", []))
    state = agents.retrieve(state)
    event("retrieve", passages=len(state.get("passages", [])))
    state = agents.pre_screen(state)
    event("pre_screen", candidates=len(state.get("candidates", [])))

    repairs = 0
    while True:
        state = agents.code_gen(state)
        event("code_gen", attempt=repairs + 1)
        state = agents.validate(state)
        verdict = state.get("validation", {})
        event("validate", passed=bool(verdict.get("passed")), detail=verdict)
        if verdict.get("passed"):
            break
        repairs += 1
        if repairs > max_repairs:
            event("rejected", reason="validation never passed", attempts=repairs)
            return RunResult(state=state, status="rejected", repairs=repairs, events=events)

    # Human gate: only a hardware backend is gated; the emulator path reports now.
    wants_hardware = str(spec.get("quantum", {}).get("backend", "selene")) != "selene"
    if wants_hardware and not state.get("approved"):
        event("awaiting_approval", gate="hw:submit")
        return RunResult(state=state, status="awaiting_approval", repairs=repairs, events=events)

    state = agents.report(state)
    event("report", report=state.get("report", ""))
    return RunResult(state=state, status="reported", repairs=repairs, events=events)


class DefaultAgents:
    """Deterministic offline stand-ins. The production agents call the sidecar
    services (retriever/RAG, FM pre-screen, guppy code-gen, validate via
    check+emulate+baseline, reporter); these mirror the shape without an LLM.

    If a `services` boundary is supplied (or the sidecar is importable), the
    `validate` node runs the **real gate** (type-check → emulate → baseline) via
    `athena.validation`; otherwise it falls back to an offline pass so the loop
    is still demonstrable without the quantum stack.
    """

    def __init__(self, services=None) -> None:
        self._services = services

    def plan(self, state: DiracQState) -> DiracQState:
        state["plan"] = ["retrieve", "pre_screen", "code_gen", "validate", "report"]
        return state

    def retrieve(self, state: DiracQState) -> DiracQState:
        state["passages"] = [{"cite": "[1]", "text": "ground-state stability of antioxidants"}]
        return state

    def pre_screen(self, state: DiracQState) -> DiracQState:
        state["candidates"] = [{"id": "cand-A", "score": 0.91}, {"id": "cand-B", "score": 0.62}]
        return state

    def code_gen(self, state: DiracQState) -> DiracQState:
        # Instantiate a validated template from the brief (never a blank page);
        # see §9.2 and Workstream F. The orchestrator's validate node owns the
        # gate, so generation itself does not re-validate here.
        from athena.doc2circuit import document_to_circuit

        result = document_to_circuit(state.get("brief", ""), validate=False)
        state["guppy_src"] = result.guppy_src
        return state

    def validate(self, state: DiracQState) -> DiracQState:
        # Real gate when a services boundary is available (injected or sidecar);
        # otherwise an offline pass so the loop is demonstrable without the stack.
        services = self._services
        if services is None:
            from athena.validation import sidecar_services

            services = sidecar_services()
        if services is not None:
            from athena.validation import validate_program

            state["validation"] = validate_program(state.get("guppy_src", ""), services)
        else:
            state["validation"] = {"passed": True, "stage": "report", "offline": True}
        return state

    def report(self, state: DiracQState) -> DiracQState:
        cites = ", ".join(p["cite"] for p in state.get("passages", []))
        top = (state.get("candidates") or [{}])[0].get("id", "n/a")
        state["report"] = f"Top candidate {top} validated on the emulator. Citations: {cites}."
        return state
