"""Selene emulation service (§7, Workstream C / M2). Wraps ``selene-sim`` behind
the JSON-RPC bridge and streams shots and resource metrics to the emulation
panel. A fixed seed makes every run reproducible (G7).

When ``selene-sim`` is not installed, a **deterministic mock backend** answers
instead: it does not model real quantum dynamics (provenance is stamped
``selene = "mock"`` so a result is never mistaken for a physical emulation) but
it satisfies the M2 reproducibility property — identical seeds yield identical
counts — so the panel and CI work before the real emulator is wired.
"""

from __future__ import annotations

import random
from typing import Any

from diracq_sidecar import __version__


def register(dispatcher) -> None:
    dispatcher.register("selene.emulate", emulate)
    dispatcher.register("selene.resources", resources)


def emulate(params: dict) -> dict[str, Any]:
    """Run a compiled HUGR on Selene under the requested simulator/error model.

    params: hugr_b64, n_qubits, shots, seed, simulator, error_model.
    Returns an EmulationResult (counts / metrics / seed / stack_versions).
    """
    if _selene_available():
        return _emulate_real(params)
    return _emulate_mock(params)


def resources(params: dict) -> dict[str, Any]:
    if _selene_available():
        _require_selene()  # delegate to real resource estimation (TODO)
        raise NotImplementedError("selene.resources: Workstream C (real selene-sim)")
    n = int(params.get("n_qubits", 0))
    return {"n_qubits": n, "gate_count": 0, "two_qubit_gates": 0, "depth": 0}


def _emulate_mock(params: dict) -> dict[str, Any]:
    n = max(1, min(int(params.get("n_qubits", 1)), 20))
    shots = int(params.get("shots", 0))
    seed = int(params.get("seed", 0))
    rng = random.Random(seed ^ (n << 32) ^ shots)
    counts: dict[str, int] = {}
    for _ in range(shots):
        bits = "".join("1" if rng.getrandbits(1) else "0" for _ in range(n))
        counts[bits] = counts.get(bits, 0) + 1
    return {
        "counts": counts,
        "metrics": {"n_qubits": n, "gate_count": 0, "two_qubit_gates": 0, "depth": 0},
        "seed": seed,
        "stack_versions": {"selene": "mock", "diracq_sidecar": __version__},
    }


def _emulate_real(params: dict) -> dict[str, Any]:
    _require_selene()
    # TODO(Workstream C): drive selene-sim with the DiracNoise plugin, stream
    # `selene.shot` notifications, and return real counts/metrics/versions.
    raise NotImplementedError("selene.emulate: Workstream C (real selene-sim)")


def _selene_available() -> bool:
    try:
        import selene_sim  # noqa: F401

        return True
    except ImportError:
        return False


def _require_selene() -> None:
    try:
        import selene_sim  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "selene-sim not installed; `pip install diracq-sidecar[quantum]`"
        ) from exc
