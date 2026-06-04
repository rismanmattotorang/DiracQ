"""Tests for hugr.graph on the source-derived mock path (no stack needed)."""

from diracq_sidecar import hugr_service as hz


def test_mock_graph_builds_chain_per_qubit():
    src = (
        "@guppy\ndef main() -> None:\n"
        "    a = qubit()\n    h(a)\n    cx(a, b)\n    measure(a)\n"
    )
    g = hz._graph_mock(src)
    labels = [n["label"] for n in g["nodes"]]
    assert labels == ["h", "cx", "measure"]
    # h(a) -> cx(a,b) -> measure(a) chained along wire `a`.
    assert {"from": 0, "to": 1} in g["edges"]
    assert {"from": 1, "to": 2} in g["edges"]


def test_mock_graph_empty_without_ops():
    g = hz._graph_mock("def f():\n    pass\n")
    assert g["nodes"] == [] and g["edges"] == []
