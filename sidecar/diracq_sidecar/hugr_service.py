"""HUGR graph extraction service (Workstream D). Decodes a compiled Guppy
program's HUGR into the node/edge/region model the GPU graph canvas lays out.

Real path: compile to a HUGR Package and walk the module's nodes, links and
parent relationships. Fallback: a small source-derived chain so the canvas shows
something without the quantum stack.
"""

from __future__ import annotations

import re
from typing import Any


def register(dispatcher) -> None:
    dispatcher.register("hugr.graph", graph)


def graph(params: dict) -> dict[str, Any]:
    """params: guppy_src, entrypoint (default "main").

    Returns {nodes:[{id,label}], edges:[{from,to}], regions:[[parent,[child,...]]]}.
    """
    src = params.get("guppy_src", "")
    if src and _stack_available():
        return _graph_real(src)
    return _graph_mock(src)


def _graph_real(src: str) -> dict[str, Any]:
    from diracq_sidecar import _guppy_runtime as rt

    loaded = rt.load_guppy_module(src)
    try:
        entry = rt.select_entrypoint(loaded.module, src)
        if entry is None:
            return _graph_mock(src)
        hg = entry.compile().modules[0]

        nodes = []
        children: dict[int, list[int]] = {}
        for node in hg:
            data = hg[node]
            nodes.append({"id": node.idx, "label": type(data.op).__name__})
            parent = data.parent
            if parent is not None:
                children.setdefault(parent.idx, []).append(node.idx)

        seen: set[tuple[int, int]] = set()
        edges = []
        for out_port, in_port in hg.links():
            a, b = out_port.node.idx, in_port.node.idx
            if a == b or (a, b) in seen:
                continue
            seen.add((a, b))
            edges.append({"from": a, "to": b})

        # Regions = container nodes that have children (for collapse/expand).
        regions = [[pid, kids] for pid, kids in children.items() if len(kids) > 1]
        return {"nodes": nodes, "edges": edges, "regions": regions}
    finally:
        loaded.cleanup()


def _graph_mock(src: str) -> dict[str, Any]:
    """Build a rough dataflow chain per qubit from the source so the graph view
    renders without the stack: qubit -> each op touching it -> measure."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, int]] = []
    nid = 0

    def add(label: str) -> int:
        nonlocal nid
        nodes.append({"id": nid, "label": label})
        nid += 1
        return nid - 1

    ops = {"h", "x", "y", "z", "s", "t", "rx", "ry", "rz", "cx", "cz", "measure"}
    last: dict[str, int] = {}
    for m in re.finditer(r"\b([a-zA-Z_]\w*)\s*\(([^)]*)\)", src):
        op = m.group(1).lower()
        if op not in ops:
            continue
        node = add(op)
        for arg in re.findall(r"[a-zA-Z_]\w*", m.group(2)):
            if arg in last:
                edges.append({"from": last[arg], "to": node})
            last[arg] = node
    return {"nodes": nodes, "edges": edges, "regions": []}


def _stack_available() -> bool:
    try:
        import guppylang  # noqa: F401

        return True
    except ImportError:
        return False
