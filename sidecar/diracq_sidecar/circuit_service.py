"""Circuit extraction service (Workstream D). Turns a compiled Guppy program
into the structured circuit the GPU canvas lays out: qubit count, gate glyphs
(name + wire indices) and measurements.

Real path: run one shot on Selene with a CircuitExtractor and read the lowered
pytket Circuit (Helios-native gates). Fallback: a lightweight source parse so the
canvas shows something without the quantum stack.
"""

from __future__ import annotations

import re
from typing import Any

_TWO_Q = {"cx", "cz", "zzphase", "zzmax", "rzz"}


def register(dispatcher) -> None:
    dispatcher.register("circuit.extract", extract)


def extract(params: dict) -> dict[str, Any]:
    """params: guppy_src, entrypoint (default "main"), n_qubits.

    Returns {n_qubits, gates:[{name, qubits:[i,...]}], measures:[{qubit, classical_bit}]}.
    """
    src = params.get("guppy_src", "")
    entry = params.get("entrypoint", "main")
    n_qubits = int(params.get("n_qubits", 2))
    if src and _stack_available():
        return _extract_real(src, entry, n_qubits)
    return _extract_mock(src, n_qubits)


def _extract_real(src: str, entry: str, n_qubits: int) -> dict[str, Any]:
    from diracq_sidecar import _guppy_runtime as rt

    circ = rt.extract_user_circuit(src, entry, n_qubits)
    gates: list[dict[str, Any]] = []
    measures: list[dict[str, Any]] = []
    for cmd in circ.get_commands():
        name = str(cmd.op.type).rsplit(".", 1)[-1].lower()
        qubits = [q.index[0] for q in cmd.qubits]
        if name == "measure":
            bit = cmd.bits[0].index[0] if cmd.bits else (qubits[0] if qubits else 0)
            measures.append({"qubit": qubits[0] if qubits else 0, "classical_bit": bit})
        elif name == "reset":
            continue  # implicit qubit init; not drawn
        else:
            gates.append({"name": name, "qubits": qubits})
    return {"n_qubits": circ.n_qubits, "gates": gates, "measures": measures}


def _extract_mock(src: str, n_qubits: int) -> dict[str, Any]:
    """Parse `name(args)` calls from the source into a rough gate list so the
    canvas renders without the stack. Qubit identifiers are mapped to indices in
    first-seen order."""
    order: dict[str, int] = {}

    def idx(tok: str) -> int:
        return order.setdefault(tok, len(order))

    gates: list[dict[str, Any]] = []
    measures: list[dict[str, Any]] = []
    ops = {"h", "x", "y", "z", "s", "t", "rx", "ry", "rz", "cx", "cz", "measure", "reset"}
    for m in re.finditer(r"\b([a-zA-Z_]\w*)\s*\(([^)]*)\)", src):
        op = m.group(1).lower()
        if op not in ops:
            continue
        args = [a for a in re.findall(r"[a-zA-Z_]\w*", m.group(2))]
        qubits = [idx(a) for a in args]
        if op == "measure" and qubits:
            measures.append({"qubit": qubits[0], "classical_bit": qubits[0]})
        elif op != "reset" and qubits:
            gates.append({"name": op, "qubits": qubits})
    n = max(n_qubits, len(order), 1)
    return {"n_qubits": n, "gates": gates, "measures": measures}


def _stack_available() -> bool:
    try:
        import guppylang  # noqa: F401
        import selene_sim  # noqa: F401

        return True
    except ImportError:
        return False
