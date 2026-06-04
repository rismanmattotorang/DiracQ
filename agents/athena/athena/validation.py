"""The validation gate (§9, Fig. 4) — the heart of "nothing is trusted until it
type-checks, emulates, and beats a classical baseline" (G1).

`validate_program` is pure logic over an injected `Services` boundary, so it is
testable without the quantum stack: tests pass a fake; production passes a
sidecar-backed implementation (`sidecar_services`) that calls the real
guppylang check + Selene emulate over the JSON-RPC bridge.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class Services(Protocol):
    """The two sidecar operations the gate needs."""

    def check(self, guppy_src: str) -> list[dict]:
        """Return LSP-shaped diagnostics (empty == type-checks)."""
        ...

    def emulate(self, guppy_src: str, n_qubits: int, shots: int, seed: int) -> dict:
        """Return an EmulationResult-shaped dict ({counts, ...})."""
        ...


def validate_program(
    guppy_src: str,
    services: Services,
    *,
    n_qubits: int = 2,
    shots: int = 1000,
    seed: int = 12478,
    baseline: Optional[dict[str, float]] = None,
    tolerance: float = 0.15,
) -> dict[str, Any]:
    """Run the gate: type-check → emulate → compare to a classical baseline.

    Returns ``{passed, stage, ...}``. A failure names the stage that rejected it
    so the repair loop (and the engineer) know what to fix — never "done" on
    failure.
    """
    # 1. Type-check (linear types, ownership). Any diagnostic fails the gate.
    diagnostics = services.check(guppy_src)
    if diagnostics:
        return {"passed": False, "stage": "check", "diagnostics": diagnostics}

    # 2. Emulate on Selene under a fixed seed (reproducible, G7).
    result = services.emulate(guppy_src, n_qubits=n_qubits, shots=shots, seed=seed)
    counts = result.get("counts", {})
    total = sum(counts.values())
    if total == 0:
        return {"passed": False, "stage": "emulate", "reason": "no shots recorded", "counts": counts}

    # 3. Classical-baseline compare (optional). When a baseline distribution is
    #    supplied, every shared outcome must be within `tolerance` of it.
    if baseline:
        probs = {k: v / total for k, v in counts.items()}
        for outcome, p_ref in baseline.items():
            if abs(probs.get(outcome, 0.0) - p_ref) > tolerance:
                return {
                    "passed": False,
                    "stage": "baseline",
                    "reason": f"{outcome}: {probs.get(outcome, 0.0):.3f} vs ref {p_ref:.3f}",
                    "counts": counts,
                }

    return {"passed": True, "stage": "report", "counts": counts, "shots": total}


def sidecar_services() -> Optional[Services]:
    """An in-process Services backed by the DiracQ sidecar, when importable.

    Production wires this over the JSON-RPC bridge; here it calls the sidecar
    modules directly (real guppylang/Selene when installed, mocks otherwise).
    Returns None if the sidecar package is not on the path.
    """
    try:
        from diracq_sidecar import guppy_worker, selene_service  # type: ignore
    except Exception:
        return None

    class _Sidecar:
        def check(self, guppy_src: str) -> list[dict]:
            return guppy_worker.check("athena://buffer", guppy_src)

        def emulate(self, guppy_src: str, n_qubits: int, shots: int, seed: int) -> dict:
            return selene_service.emulate(
                {
                    "guppy_src": guppy_src,
                    "entrypoint": "main",
                    "n_qubits": n_qubits,
                    "shots": shots,
                    "seed": seed,
                    "simulator": "stim",
                }
            )

    return _Sidecar()
