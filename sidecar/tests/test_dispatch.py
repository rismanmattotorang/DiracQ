"""Smoke tests for the stdlib JSON-RPC dispatcher (no quantum/ML deps needed)."""

import io

from diracq_sidecar.server import (
    Dispatcher,
    build_dispatcher,
    read_message,
    write_message,
)


def test_dispatch_result():
    d = Dispatcher()
    d.register("add", lambda p: p["a"] + p["b"])
    resp = d.handle({"jsonrpc": "2.0", "id": 1, "method": "add", "params": {"a": 2, "b": 3}})
    assert resp == {"jsonrpc": "2.0", "id": 1, "result": 5}


def test_method_not_found():
    d = Dispatcher()
    resp = d.handle({"jsonrpc": "2.0", "id": 7, "method": "nope", "params": {}})
    assert resp["error"]["code"] == -32601


def test_notification_has_no_response():
    d = Dispatcher()
    d.register("evt", lambda p: None)
    assert d.handle({"jsonrpc": "2.0", "method": "evt", "params": {}}) is None


def test_handler_error_is_structured():
    d = Dispatcher()

    def boom(_p):
        raise ValueError("kaboom")

    d.register("boom", boom)
    resp = d.handle({"jsonrpc": "2.0", "id": 9, "method": "boom", "params": {}})
    assert resp["error"]["code"] == -32000
    assert "kaboom" in resp["error"]["message"]


def test_framing_roundtrip():
    buf = io.BytesIO()
    write_message(buf, {"jsonrpc": "2.0", "id": 1, "method": "sidecar.ping"})
    buf.seek(0)
    assert read_message(buf)["method"] == "sidecar.ping"


def test_builtin_ping_registered():
    d = build_dispatcher()
    resp = d.handle({"jsonrpc": "2.0", "id": 1, "method": "sidecar.ping", "params": {}})
    assert resp["result"]["ok"] is True
