"""Guppy analysis worker (§6, ADR-03). Wraps ``guppylang``'s own checker for
ground-truth diagnostics; called by the Rust ``diracq_lsp`` server over a typed
length-prefixed JSON-RPC bridge. Runs out-of-process so the moving upstream type
system is never re-implemented (G4).

Run as a module to serve the bridge::

    python -m diracq_sidecar.guppy_worker          # uses guppylang (ground truth)
    python -m diracq_sidecar.guppy_worker --mock   # heuristic, for dev/CI without guppylang

The Rust side spawns this and speaks 4-byte-length-prefixed JSON frames
(``{"method","params"}`` → ``{"result"}`` / ``{"error"}``).
"""

from __future__ import annotations

import re
import sys
from typing import Any

from diracq_sidecar.server import read_message, write_message

# Whether to answer with the pure-Python heuristic instead of guppylang.
_MOCK = False

_QUANTUM_OPS = {
    "h", "x", "y", "z", "s", "t", "sdg", "tdg", "cx", "cz", "rx", "ry", "rz", "measure", "reset",
}
_CALL = re.compile(r"\b([a-zA-Z_]\w*)\s*\(([^)]*)\)")
_ASSIGN = re.compile(r"\b([a-zA-Z_]\w*)\s*=(?!=)")


def check(uri: str, src: str) -> list[dict[str, Any]]:
    """Type-check a buffer; return LSP-shaped diagnostics
    (message, severity, start, end byte offsets)."""
    if _MOCK:
        return _heuristic_check(src)
    _require_guppylang()
    # TODO(Workstream B): call guppy.check(); map error objects to ranges,
    # surfacing linear-type/ownership errors (use-after-measure, implicit
    # discard, aliasing).
    raise NotImplementedError("guppy_worker.check: Workstream B (guppylang mapping)")


def compile_summary(uri: str, src: str) -> dict[str, int]:
    """Compile to HUGR and return node/edge/qubit counts."""
    if _MOCK:
        return {"nodes": 0, "edges": 0, "qubits": src.count("qubit(")}
    _require_guppylang()
    raise NotImplementedError("guppy_worker.compile_summary: Workstream B")


def resources(uri: str, src: str) -> dict[str, int]:
    if _MOCK:
        return {
            "n_qubits": src.count("qubit("),
            "gate_count": 0,
            "two_qubit_gates": 0,
            "depth": 0,
        }
    _require_guppylang()
    raise NotImplementedError("guppy_worker.resources: Workstream B")


def _heuristic_check(src: str) -> list[dict[str, Any]]:
    """A Python mirror of the Rust heuristic: flag use-after-measure /
    double-measure. Used in --mock mode so the bridge is testable end-to-end
    without guppylang installed."""
    # Strip comments to byte-aligned spaces so offsets stay correct.
    stripped = re.sub(r"#[^\n]*", lambda m: " " * len(m.group(0)), src)
    diags: list[dict[str, Any]] = []
    measured: dict[str, int] = {}
    for m in _iter_tokens(stripped):
        kind, name, start, end = m
        if kind == "assign":
            measured.pop(name, None)
        elif kind == "call":
            op, args = name
            for arg_name, a_start, a_end in args:
                if arg_name in measured and a_start > measured[arg_name]:
                    diags.append({
                        "message": (
                            f"use-after-measure: qubit `{arg_name}` is used in "
                            f"`{op}(...)` after it was measured "
                            f"(no-cloning / linear-type violation)"
                        ),
                        "severity": "error",
                        "start": a_start,
                        "end": a_end,
                    })
                if op == "measure":
                    measured[arg_name] = a_start
    return diags


def _iter_tokens(src: str):
    """Yield ('assign', name, s, e) and ('call', (op, [args]), s, e) in order."""
    events = []
    for m in _ASSIGN.finditer(src):
        events.append((m.start(1), "assign", m.group(1), m.start(1), m.end(1)))
    for m in _CALL.finditer(src):
        op = m.group(1)
        if op not in _QUANTUM_OPS:
            continue
        args = []
        arg_region_start = m.start(2)
        for am in re.finditer(r"[a-zA-Z_]\w*", m.group(2)):
            args.append((am.group(0), arg_region_start + am.start(), arg_region_start + am.end()))
        events.append((m.start(1), "call", (op, args), m.start(1), m.end()))
    events.sort(key=lambda e: e[0])
    for _, kind, name, s, e in events:
        yield kind, name, s, e


def _require_guppylang() -> None:
    try:
        import guppylang  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "guppylang not installed; `pip install diracq-sidecar[quantum]` "
            "(or run the worker with --mock)"
        ) from exc


_METHODS = {"check": check, "compile_summary": compile_summary, "resources": resources}


def serve() -> int:
    """Serve the length-prefixed JSON-RPC bridge over stdio."""
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        req = read_message(stdin)
        if req is None:
            break
        method = req.get("method")
        params = req.get("params") or {}
        fn = _METHODS.get(method)
        if fn is None:
            write_message(stdout, {"error": f"unknown method: {method}"})
            continue
        try:
            result = fn(params.get("uri", ""), params.get("src", ""))
            write_message(stdout, {"result": _wrap(method, result)})
        except Exception as exc:  # surface as an error; Rust falls back
            write_message(stdout, {"error": str(exc)})
    return 0


def _wrap(method: str, result: Any) -> Any:
    # `check` returns a list; the Rust side expects {"diagnostics": [...]}.
    if method == "check":
        return {"diagnostics": result}
    return result


def main(argv: list[str] | None = None) -> int:
    global _MOCK
    argv = sys.argv[1:] if argv is None else argv
    _MOCK = "--mock" in argv
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
