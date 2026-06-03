"""Guppy analysis worker (§6, ADR-03). Wraps ``guppylang``'s own checker for
ground-truth diagnostics; called by the Rust ``diracq_lsp`` server over a typed
JSON-RPC bridge. Runs out-of-process so the moving upstream type system is never
re-implemented (G4).
"""

from __future__ import annotations

from typing import Any


def check(uri: str, src: str) -> list[dict[str, Any]]:
    """Type-check a buffer; map guppylang diagnostics to LSP-shaped dicts
    (message, severity, range)."""
    _require_guppylang()
    # TODO(Workstream B): call guppy.check(); map error objects to ranges,
    # surfacing linear-type/ownership errors (use-after-measure, implicit
    # discard, aliasing).
    raise NotImplementedError("guppy_worker.check: Workstream B")


def compile_summary(uri: str, src: str) -> dict[str, int]:
    """Compile to HUGR and return node/edge/qubit counts."""
    _require_guppylang()
    raise NotImplementedError("guppy_worker.compile_summary: Workstream B")


def _require_guppylang() -> None:
    try:
        import guppylang  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "guppylang not installed; `pip install diracq-sidecar[quantum]`"
        ) from exc
