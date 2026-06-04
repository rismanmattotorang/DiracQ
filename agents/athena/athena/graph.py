"""The LangGraph state graph (§9.1, §9.5, ADR-06).

A planner decomposes the brief; a retriever grounds it in the literature; a
pre-screen step calls foundation models; a code-gen agent emits Guppy from
validated templates; a validator type-checks, emulates and compares to a
classical baseline, looping back to repair on failure; and a reporter writes the
cited result. The single human gate guards the optional hardware run (Fig. 4).
"""

from __future__ import annotations

from typing import TypedDict


class DiracQState(TypedDict, total=False):
    brief: str
    plan: list[str]
    passages: list[dict]      # retriever output (with citations)
    candidates: list[dict]    # pre-screen ranking
    guppy_src: str
    validation: dict          # check + emulate + baseline verdict
    approved: bool            # set only at the human gate


# Node names, in execution order. Edges: plan -> retrieve -> pre_screen ->
# code_gen -> validate; validate loops to code_gen on failure, else -> report.
NODES = ("plan", "retrieve", "pre_screen", "code_gen", "validate", "report")


def build_graph(node_fns: dict):
    """Assemble and compile the explicit state graph from node callables
    (`name -> fn(state) -> state-update`). Requires `langgraph` at runtime.

    Mirrors the spec's `build_graph()`: plan → retrieve → pre_screen → code_gen →
    validate; validate loops to code_gen on failure (repair), else → report → END.
    """
    from langgraph.graph import END, StateGraph

    g = StateGraph(DiracQState)
    for node in NODES:
        g.add_node(node, node_fns[node])
    g.set_entry_point("plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "pre_screen")
    g.add_edge("pre_screen", "code_gen")
    g.add_edge("code_gen", "validate")
    # Nothing is trusted until it passes a type check, a Selene emulation and a
    # comparison to a classical baseline; otherwise repair.
    g.add_conditional_edges(
        "validate",
        lambda s: "report" if s.get("validation", {}).get("passed") else "code_gen",
        {"report": "report", "code_gen": "code_gen"},
    )
    g.add_edge("report", END)
    return g.compile()


def run_with_langgraph(spec: dict, agents=None, *, max_repairs: int = 3) -> dict:
    """Run the experiment on the real LangGraph runtime, returning the final
    state plus a derived ``status`` ("reported" | "rejected"). The repair loop is
    bounded by a recursion limit derived from ``max_repairs``; exceeding it (a
    program that never validates) yields ``rejected`` — never "done"."""
    from langgraph.errors import GraphRecursionError

    from athena.orchestrator import DefaultAgents

    agents = agents or DefaultAgents()

    def wrap(method):
        # Agent methods mutate+return the full state; returning it updates all
        # channels. `dict(state)` decouples from langgraph's internal mapping.
        return lambda state: method(dict(state))

    node_fns = {name: wrap(getattr(agents, name)) for name in NODES}
    app = build_graph(node_fns)

    initial: DiracQState = {"brief": spec.get("goal", ""), "approved": False}
    # plan/retrieve/pre_screen/report run once; code_gen/validate run up to
    # (max_repairs+1) times — budget the recursion limit accordingly.
    limit = 4 + 2 * (max_repairs + 1) + 2
    try:
        final = app.invoke(initial, {"recursion_limit": limit})
    except GraphRecursionError:
        return {"status": "rejected", "reason": "validation never passed"}
    passed = bool(final.get("validation", {}).get("passed"))
    return {**final, "status": "reported" if passed else "rejected"}
