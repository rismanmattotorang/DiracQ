"""Guppy analysis worker (§6, ADR-03). Wraps ``guppylang``'s own checker for
ground-truth diagnostics; called by the Rust ``diracq_lsp`` server over a typed
length-prefixed JSON-RPC bridge. Runs out-of-process so the moving upstream type
system is never re-implemented (G4).

Run as a module to serve the bridge::

    python -m diracq_sidecar.guppy_worker          # uses guppylang (ground truth)
    python -m diracq_sidecar.guppy_worker --mock   # heuristic, for dev/CI without guppylang

The Rust side spawns this and speaks 4-byte-length-prefixed JSON frames
(``{"method","params"}`` -> ``{"result"}`` / ``{"error"}``).
"""

from __future__ import annotations

import re
import sys
from typing import Any

from diracq_sidecar.server import read_message, write_message

# Force the pure-Python heuristic instead of guppylang (set by --mock).
_MOCK = False

_QUANTUM_OPS = {
    "h", "x", "y", "z", "s", "t", "sdg", "tdg", "cx", "cz", "rx", "ry", "rz", "measure", "reset",
}
_CALL = re.compile(r"\b([a-zA-Z_]\w*)\s*\(([^)]*)\)")
_ASSIGN = re.compile(r"\b([a-zA-Z_]\w*)\s*=(?!=)")


def check(uri: str, src: str) -> list[dict[str, Any]]:
    """Type-check a buffer; return LSP-shaped diagnostics
    (message, severity, start, end byte offsets)."""
    if _use_real():
        return _real_check(src)
    return _heuristic_check(src)


def compile_summary(uri: str, src: str) -> dict[str, int]:
    """Compile to HUGR and return node/edge/qubit counts."""
    if _use_real():
        return _real_compile_summary(src)
    return {"nodes": 0, "edges": 0, "qubits": src.count("qubit(")}


def resources(uri: str, src: str) -> dict[str, int]:
    summary = compile_summary(uri, src)
    return {
        "n_qubits": summary.get("qubits", 0),
        "gate_count": summary.get("nodes", 0),
        "two_qubit_gates": 0,
        "depth": 0,
    }


# --- real guppylang path -----------------------------------------------------


def _use_real() -> bool:
    if _MOCK:
        return False
    from diracq_sidecar import _guppy_runtime as rt

    return rt.guppylang_available()


def _real_check(src: str) -> list[dict[str, Any]]:
    """Compile every Guppy definition in the buffer and map the first
    guppylang error per definition to an LSP diagnostic with a precise range."""
    from guppylang_internals.error import GuppyError  # type: ignore
    from guppylang_internals.span import to_span  # type: ignore

    from diracq_sidecar import _guppy_runtime as rt

    try:
        loaded = rt.load_guppy_module(src)
    except SyntaxError as exc:  # a plain Python syntax error in the buffer
        line = (exc.lineno or 1)
        col = max((exc.offset or 1) - 1, 0)
        off = rt.line_col_to_offset(src, line, col)
        return [{"message": f"syntax error: {exc.msg}", "severity": "error", "start": off, "end": off + 1}]
    except Exception as exc:  # NameError etc. while importing the buffer
        return [{"message": f"load error: {exc}", "severity": "error", "start": 0, "end": 1}]

    diags: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    try:
        for _name, defn in rt.iter_guppy_defs(loaded.module, src):
            try:
                defn.compile()
            except GuppyError as exc:
                err = getattr(exc, "error", exc)
                try:
                    sp = to_span(err.span)
                    start = rt.line_col_to_offset(src, sp.start.line, sp.start.column)
                    end = rt.line_col_to_offset(src, sp.end.line, sp.end.column)
                except Exception:
                    start, end = 0, 1
                if (start, end) in seen:
                    continue
                seen.add((start, end))
                title = getattr(err, "rendered_title", None) or "Guppy error"
                detail = getattr(err, "rendered_message", None)
                message = f"{title}: {detail}" if detail else title
                diags.append({"message": message, "severity": "error", "start": start, "end": end})
            except Exception:
                # Non-Guppy compile failure; skip this def (others may report).
                continue
    finally:
        loaded.cleanup()
    return diags


def _real_compile_summary(src: str) -> dict[str, int]:
    from diracq_sidecar import _guppy_runtime as rt

    loaded = rt.load_guppy_module(src)
    try:
        entry = rt.select_entrypoint(loaded.module, src)
        if entry is None:
            return {"nodes": 0, "edges": 0, "qubits": 0}
        pkg = entry.compile()
        module0 = pkg.modules[0]
        nodes = sum(1 for _ in module0)
        edges = sum(1 for _ in module0.links()) if hasattr(module0, "links") else 0
        return {"nodes": nodes, "edges": edges, "qubits": src.count("qubit(")}
    finally:
        loaded.cleanup()


# --- pure-Python heuristic (mock / fallback) ---------------------------------


def _heuristic_check(src: str) -> list[dict[str, Any]]:
    """A Python mirror of the Rust heuristic: flag use-after-measure /
    double-measure. Used in --mock mode and when guppylang is unavailable."""
    stripped = re.sub(r"#[^\n]*", lambda m: " " * len(m.group(0)), src)
    diags: list[dict[str, Any]] = []
    measured: dict[str, int] = {}
    for kind, name, s, e in _iter_tokens(stripped):
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
