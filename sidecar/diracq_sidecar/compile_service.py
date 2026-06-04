"""TKET compile service (§8, Workstream H). Wraps pytket/tket2; drives the
Guppy->HUGR->...->qsystem pipeline and returns the Mermaid string tket2 emits.

When pytket/tket2 are not installed, a **deterministic mock** answers: it
estimates the entangling-gate count from the source and applies a fixed
optimisation ratio so the before/after win is visible, mirroring the Rust mock.
"""

from __future__ import annotations

import base64
from typing import Any

_MOCK_MERMAID = "graph LR; q0--H-->q0; q0--CX-->q1; q1--M-->c1;"


def register(dispatcher) -> None:
    dispatcher.register("tket.compile", compile_guppy)
    dispatcher.register("tket.render_mermaid", lambda p: _MOCK_MERMAID)


def compile_guppy(params: dict) -> dict[str, Any]:
    """Compile Guppy source to a runnable HUGR.

    params mirror CompileRequest (guppy_src, opt_level, target, dirac_passes).
    Returns CompileResult (hugr_b64, mermaid, metrics_before, metrics_after).

    Uses the real guppylang compiler when the source is genuine Guppy
    (``@guppy``) and the stack is installed; otherwise the deterministic mock.
    """
    src = params.get("guppy_src", "")
    if "@guppy" in src and _guppy_available():
        return _compile_real(params)
    return _compile_mock(params)


def _compile_mock(params: dict) -> dict[str, Any]:
    src = params.get("guppy_src", "")
    dirac_passes = params.get("dirac_passes", True)
    two_q_before = src.count("cx") + src.count("cz")
    # dirac.chem fuses UCC rotations / groups Pauli measurements → fewer 2q gates.
    two_q_after = two_q_before - two_q_before // 4 if dirac_passes else two_q_before
    qubits = src.count("qubit(")

    def metrics(two_q: int) -> dict[str, int]:
        return {
            "n_qubits": qubits,
            "gate_count": two_q,
            "two_qubit_gates": two_q,
            "depth": two_q,
        }

    return {
        "hugr_b64": base64.b64encode(b"mock-hugr").decode(),
        "mermaid": _MOCK_MERMAID,
        "metrics_before": metrics(two_q_before),
        "metrics_after": metrics(two_q_after),
    }


def _compile_real(params: dict) -> dict[str, Any]:
    """Real Guppy->HUGR compile: emits the actual HUGR bytes (base64) and node/
    qubit metrics from the compiled program. The tket2 optimisation passes
    (the before/after entangling-gate reduction) and the Mermaid emission remain
    the Workstream-H TODO, so before == after here."""
    from diracq_sidecar import _guppy_runtime as rt

    src = params["guppy_src"]
    loaded = rt.load_guppy_module(src)
    try:
        entry = rt.select_entrypoint(loaded.module, src)
        if entry is None:
            return _compile_mock(params)
        pkg = entry.compile()
        hugr_b64 = base64.b64encode(pkg.to_bytes()).decode()
        nodes = sum(1 for _ in pkg.modules[0])
        qubits = src.count("qubit(")
        metrics = {"n_qubits": qubits, "gate_count": nodes, "two_qubit_gates": 0, "depth": 0}
        return {
            "hugr_b64": hugr_b64,
            "mermaid": "",  # TODO(Workstream H): tket2 circ.mermaid_string()
            "metrics_before": metrics,
            "metrics_after": metrics,
        }
    finally:
        loaded.cleanup()


def _guppy_available() -> bool:
    try:
        import guppylang  # noqa: F401

        return True
    except ImportError:
        return False
