"""Validated Guppy templates the code-gen agent instantiates (§9.2, §9.3).

The code-gen agent never writes from a blank page — it fills *validated*
templates from a structured spec. Each template here is a known-good Guppy
program (no use-after-measure, every qubit measured once); the document-to-circuit
tool maps an extracted spec onto one of these and parameterises it.
"""

from __future__ import annotations

HEADER = "from guppylang import guppy, qubit\n\n"


def bell() -> str:
    return (
        HEADER + "@guppy\n"
        "def bell() -> tuple[bool, bool]:\n"
        "    a = qubit()\n"
        "    b = qubit()\n"
        "    h(a)\n"
        "    cx(a, b)\n"
        "    return measure(a), measure(b)\n"
    )


def ghz(n: int) -> str:
    n = max(2, min(n, 16))
    lines = [HEADER, "@guppy\n", f"def ghz() -> array[bool, {n}]:\n"]
    for i in range(n):
        lines.append(f"    q{i} = qubit()\n")
    lines.append("    h(q0)\n")
    for i in range(1, n):
        lines.append(f"    cx(q0, q{i})\n")
    results = ", ".join(f"measure(q{i})" for i in range(n))
    lines.append(f"    return array({results})\n")
    return "".join(lines)


def teleport() -> str:
    return (
        HEADER + "@guppy\n"
        "def teleport() -> bool:\n"
        "    msg = qubit()\n"
        "    a = qubit()\n"
        "    b = qubit()\n"
        "    h(a)\n"
        "    cx(a, b)\n"
        "    cx(msg, a)\n"
        "    h(msg)\n"
        "    m0 = measure(msg)\n"
        "    m1 = measure(a)\n"
        "    return measure(b)\n"
    )


def vqe_ansatz(n_qubits: int) -> str:
    n = max(1, min(n_qubits, 16))
    lines = [HEADER, "@guppy\n", f"def vqe_ansatz() -> array[bool, {n}]:\n"]
    for i in range(n):
        lines.append(f"    q{i} = qubit()\n")
    for i in range(n):
        lines.append(f"    rz(q{i}, 0.5)\n")
    for i in range(n - 1):
        lines.append(f"    cx(q{i}, q{i + 1})\n")
    results = ", ".join(f"measure(q{i})" for i in range(n))
    lines.append(f"    return array({results})\n")
    return "".join(lines)


# Maps a recognised circuit/algorithm kind to a template factory.
def render(kind: str, max_qubits: int | None) -> str:
    n = max_qubits or 2
    if kind == "bell":
        return bell()
    if kind == "ghz":
        return ghz(n)
    if kind == "teleport":
        return teleport()
    if kind == "vqe":
        return vqe_ansatz(n)
    raise KeyError(f"no validated template for kind: {kind!r}")
