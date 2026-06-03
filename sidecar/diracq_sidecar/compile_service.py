"""TKET compile service (§8). Wraps pytket/tket2; drives the
Guppy->HUGR->...->qsystem pipeline and returns the Mermaid string tket2 emits.
"""

from __future__ import annotations

from typing import Any


def register(dispatcher) -> None:
    dispatcher.register("tket.compile", compile_guppy)


def compile_guppy(params: dict) -> dict[str, Any]:
    """Compile Guppy source to a runnable HUGR.

    Expected params mirror CompileRequest (guppy_src, opt_level, target,
    dirac_passes). Returns CompileResult (hugr_b64, mermaid, metrics_before,
    metrics_after).
    """
    _require_tket()
    # TODO(Workstream H): guppy.compile -> tket2 passes (rebase, optimise,
    # schedule) -> dirac.chem passes -> tket2-qsystem prep; emit mermaid +
    # before/after ResourceMetrics.
    raise NotImplementedError("tket.compile: Workstream H")


def _require_tket() -> None:
    try:
        import pytket  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pytket/tket2 not installed; `pip install diracq-sidecar[quantum]`"
        ) from exc
