"""JSON-RPC 2.0 sidecar server over length-prefixed stdio (§5.2, §12.2).

Every method shares one envelope. Requests carry an ``id``; notifications carry
a ``method`` but no ``id`` and are streamed by the sidecar for progress
(``agent.progress``, ``selene.shot``, ``compile.metric``). The flat, versioned
namespace is ``selene.* tket.* agent.* model.* mol.*``.

The dispatcher is pure-stdlib so the framing/dispatch path is testable without
the quantum/ML stack. Service modules register handlers lazily; a service whose
heavy dependency is missing is skipped with a warning so the server still
starts.
"""

from __future__ import annotations

import json
import struct
import sys
from typing import Any, Callable, Dict

Handler = Callable[[dict], Any]


class Dispatcher:
    """Maps a JSON-RPC method name to a handler returning a JSON-able result."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}

    def register(self, method: str, handler: Handler) -> None:
        self._handlers[method] = handler

    def handle(self, request: dict) -> dict | None:
        """Process one request object; returns a response, or None for a
        notification (no ``id``)."""
        rpc_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if method not in self._handlers:
            if rpc_id is None:
                return None
            return _error(rpc_id, -32601, f"method not found: {method}")
        try:
            result = self._handlers[method](params)
        except Exception as exc:  # surface as a structured error, never crash
            if rpc_id is None:
                return None
            return _error(rpc_id, -32000, str(exc))
        if rpc_id is None:
            return None
        return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _error(rpc_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


# --- length-prefixed framing (4-byte big-endian length + UTF-8 JSON) ---------


def read_message(stream) -> dict | None:
    header = stream.read(4)
    if not header or len(header) < 4:
        return None
    (length,) = struct.unpack(">I", header)
    body = stream.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(stream, message: dict) -> None:
    body = json.dumps(message).encode("utf-8")
    stream.write(struct.pack(">I", len(body)))
    stream.write(body)
    stream.flush()


def build_dispatcher() -> Dispatcher:
    """Register every available service; skip those whose deps are missing."""
    d = Dispatcher()
    d.register("sidecar.ping", lambda _p: {"ok": True, "version": _version()})

    for module_name, register_name in (
        ("diracq_sidecar.selene_service", "register"),
        ("diracq_sidecar.compile_service", "register"),
        ("diracq_sidecar.circuit_service", "register"),
        ("diracq_sidecar.hugr_service", "register"),
        ("diracq_sidecar.inference", "register"),
        ("diracq_sidecar.molecular", "register"),
    ):
        try:
            module = __import__(module_name, fromlist=[register_name])
            getattr(module, register_name)(d)
        except Exception as exc:  # missing heavy dependency, etc.
            print(f"[diracq-sidecar] skipped {module_name}: {exc}", file=sys.stderr)
    return d


def _version() -> str:
    from diracq_sidecar import __version__

    return __version__


def main() -> int:
    dispatcher = build_dispatcher()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    print("[diracq-sidecar] ready (JSON-RPC 2.0 over length-prefixed stdio)", file=sys.stderr)
    while True:
        request = read_message(stdin)
        if request is None:
            break
        response = dispatcher.handle(request)
        if response is not None:
            write_message(stdout, response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
