"""Selene emulation service (§7). Wraps ``selene-sim`` behind the JSON-RPC
bridge and streams shots and resource metrics to the emulation panel. A fixed
seed makes every run reproducible (G7).

Heavy import (``selene``/``guppylang``) is lazy so the dispatcher loads without
the quantum stack installed; the handler raises a clear error if called.
"""

from __future__ import annotations

from typing import Any


def register(dispatcher) -> None:
    dispatcher.register("selene.emulate", emulate)
    dispatcher.register("selene.resources", resources)


def emulate(params: dict) -> dict[str, Any]:
    """Run a compiled HUGR on Selene under the requested simulator/error model.

    Expected params: hugr_b64, n_qubits, shots, seed, simulator, error_model.
    """
    _require_selene()
    # TODO(Workstream C): drive selene-sim with the DiracNoise plugin and stream
    # `selene.shot` notifications; return EmulationResult (counts/metrics/seed/
    # stack_versions).
    raise NotImplementedError("selene.emulate: Workstream C")


def resources(params: dict) -> dict[str, Any]:
    _require_selene()
    raise NotImplementedError("selene.resources: Workstream C")


def _require_selene() -> None:
    try:
        import selene_sim  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on extras
        raise RuntimeError(
            "selene-sim not installed; `pip install diracq-sidecar[quantum]`"
        ) from exc
