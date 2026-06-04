"""Tests for server-initiated streaming notifications (§12.2)."""

from diracq_sidecar.server import Dispatcher, build_dispatcher


def test_dispatcher_passes_notify_to_streaming_handlers():
    seen = []

    def streamer(params, notify):
        notify("progress", {"step": 1})
        notify("progress", {"step": 2})
        return {"ok": True}

    d = Dispatcher()
    d.register("stream", streamer)
    resp = d.handle({"jsonrpc": "2.0", "id": 1, "method": "stream", "params": {}},
                    notify=lambda m, p: seen.append((m, p)))
    assert resp["result"] == {"ok": True}
    assert seen == [("progress", {"step": 1}), ("progress", {"step": 2})]


def test_non_streaming_handler_unaffected():
    d = Dispatcher()
    d.register("plain", lambda p: {"echo": p})
    # notify supplied, but handler doesn't accept it → still works.
    resp = d.handle({"jsonrpc": "2.0", "id": 2, "method": "plain", "params": {"x": 1}},
                    notify=lambda m, p: None)
    assert resp["result"] == {"echo": {"x": 1}}


def test_selene_mock_streams_shot_progress():
    d = build_dispatcher()
    events = []
    resp = d.handle(
        {"jsonrpc": "2.0", "id": 3, "method": "selene.emulate",
         "params": {"n_qubits": 2, "shots": 100, "seed": 5}},
        notify=lambda m, p: events.append((m, p)),
    )
    # Final result present and shots conserved.
    assert sum(resp["result"]["counts"].values()) == 100
    # selene.shot notifications streamed, monotonic, ending at the total.
    shots = [p for (m, p) in events if m == "selene.shot"]
    assert len(shots) >= 1
    assert shots[-1]["done"] == 100 and shots[-1]["total"] == 100
    assert [s["done"] for s in shots] == sorted(s["done"] for s in shots)
