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


def build_graph(agents: dict):
    """Assemble the explicit state graph from the agent node implementations.

    Mirrors the spec's `build_graph()`; requires `langgraph` at runtime.
    """
    from langgraph.graph import StateGraph

    g = StateGraph(DiracQState)
    for node in NODES:
        g.add_node(node, agents[node])
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "pre_screen")
    g.add_edge("pre_screen", "code_gen")
    g.add_edge("code_gen", "validate")
    # Nothing is trusted until it passes a type check, a Selene emulation and a
    # comparison to a classical baseline; otherwise repair.
    g.add_conditional_edges(
        "validate",
        lambda s: "report" if s.get("validation", {}).get("passed") else "code_gen",
    )
    return g
