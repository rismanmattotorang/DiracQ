"""Integration tests against the REAL Quantinuum stack (guppylang + selene-sim).

Skipped automatically when the stack is not installed, so the default CI (which
installs only pydantic/pytest) stays green. Run inside the project venv:

    . .venv/bin/activate && pip install pytest && \
        PYTHONPATH=. pytest sidecar/tests/test_real_quantum.py -q
"""

import pytest

from diracq_sidecar import _guppy_runtime as rt

pytestmark = pytest.mark.skipif(
    not rt.guppylang_available(), reason="guppylang/selene-sim not installed"
)

from diracq_sidecar import guppy_worker as gw  # noqa: E402
from diracq_sidecar import selene_service as ss  # noqa: E402

_BELL = (
    "from guppylang import guppy\n"
    "from guppylang.std.quantum import qubit, h, cx, measure\n"
    "from guppylang.std.builtins import result\n"
    "@guppy\n"
    "def main() -> None:\n"
    "    a = qubit()\n"
    "    b = qubit()\n"
    "    h(a)\n"
    "    cx(a, b)\n"
    "    result('c0', measure(a))\n"
    "    result('c1', measure(b))\n"
)

_USE_AFTER_MEASURE = (
    "from guppylang import guppy\n"
    "from guppylang.std.quantum import qubit, h, measure\n"
    "@guppy\n"
    "def broken() -> bool:\n"
    "    q = qubit()\n"
    "    r = measure(q)\n"
    "    h(q)\n"
    "    return r\n"
)


def test_real_check_accepts_valid_bell():
    assert gw._real_check(_BELL) == []


def test_real_check_flags_use_after_measure_with_range():
    diags = gw._real_check(_USE_AFTER_MEASURE)
    assert len(diags) >= 1
    d = diags[0]
    # The span must point at the offending `q` in `h(q)` on the last guppy line.
    assert _USE_AFTER_MEASURE[d["start"] : d["end"]] == "q"
    assert d["start"] > _USE_AFTER_MEASURE.index("measure(q)")


def test_real_compile_summary_reports_nodes_and_qubits():
    s = gw._real_compile_summary(_BELL)
    assert s["qubits"] == 2
    assert s["nodes"] > 0


def test_real_emulation_bell_clusters_on_00_and_11():
    params = {
        "guppy_src": _BELL,
        "entrypoint": "main",
        "n_qubits": 2,
        "shots": 1000,
        "seed": 7,
        "simulator": "stim",
    }
    r = ss.emulate(params)
    counts = r["counts"]
    assert sum(counts.values()) == 1000
    # An ideal Bell state only ever measures 00 or 11.
    assert set(counts) <= {"00", "11"}
    assert "guppylang" in r["stack_versions"]  # real provenance, not "mock"


def test_real_emulation_is_reproducible_under_fixed_seed():
    params = {
        "guppy_src": _BELL, "entrypoint": "main",
        "n_qubits": 2, "shots": 500, "seed": 42, "simulator": "stim",
    }
    assert ss.emulate(params)["counts"] == ss.emulate(params)["counts"]


def test_diracnoise_introduces_error_outcomes():
    """An ideal Bell run only yields 00/11; under the calibrated DiracNoise model
    a small fraction of 01/10 (error) outcomes appears (§7.2)."""
    base = {"guppy_src": _BELL, "entrypoint": "main", "n_qubits": 2,
            "shots": 4000, "seed": 1, "simulator": "stim"}
    ideal = ss.emulate(base)
    assert set(ideal["counts"]) <= {"00", "11"}

    noisy = ss.emulate({**base, "error_model": {"kind": "dirac_calibrated", "p_2q": 0.1}})
    errors = noisy["counts"].get("01", 0) + noisy["counts"].get("10", 0)
    assert errors > 0  # DiracNoise produced error outcomes
    assert sum(noisy["counts"].values()) == 4000


def test_real_compile_emits_hugr_bytes_and_metrics():
    from diracq_sidecar import compile_service as cs

    r = cs.compile_guppy({"guppy_src": _BELL, "opt_level": 2, "target": "helios"})
    import base64

    raw = base64.b64decode(r["hugr_b64"])
    assert len(raw) > 0  # a real serialised HUGR package
    assert r["metrics_before"]["n_qubits"] == 2
    assert r["metrics_before"]["gate_count"] > 0
    assert r["mermaid"].startswith("graph LR")


# A circuit with a redundant pair of CX (identity) so optimisation has something
# real to remove.
_REDUNDANT = (
    "from guppylang import guppy\n"
    "from guppylang.std.quantum import qubit, h, cx, measure\n"
    "from guppylang.std.builtins import result\n"
    "@guppy\n"
    "def main() -> None:\n"
    "    a = qubit()\n    b = qubit()\n    h(a)\n    cx(a, b)\n    cx(a, b)\n"
    "    result('c0', measure(a))\n    result('c1', measure(b))\n"
)


def test_real_compile_optimisation_reduces_two_qubit_gates():
    from diracq_sidecar import compile_service as cs

    r = cs.compile_guppy({"guppy_src": _REDUNDANT, "dirac_passes": True})
    before = r["metrics_before"]["two_qubit_gates"]
    after = r["metrics_after"]["two_qubit_gates"]
    assert before >= 2
    assert after < before  # the redundant CX pair is removed by the real pass


def test_real_compile_runs_qsystem_prep_on_hugr():
    """The Helios target must run the real tket2 QSystemPass, which lowers/
    expands the HUGR — so the emitted (prepped) HUGR differs from raw compile."""
    import base64

    from diracq_sidecar import _guppy_runtime as rt
    from diracq_sidecar import compile_service as cs

    helios = cs.compile_guppy({"guppy_src": _BELL, "target": "helios"})
    generic = cs.compile_guppy({"guppy_src": _BELL, "target": "generic"})
    prepped = base64.b64decode(helios["hugr_b64"])
    raw = base64.b64decode(generic["hugr_b64"])
    assert len(prepped) != len(raw)  # qsystem prep transformed the HUGR

    # And QSystemPass genuinely runs on the package.
    loaded = rt.load_guppy_module(_BELL)
    try:
        pkg = rt.select_entrypoint(loaded.module, _BELL).compile()
        before_nodes = sum(1 for _ in pkg.modules[0])
        assert cs._qsystem_prepare(pkg) is True
        assert sum(1 for _ in pkg.modules[0]) != before_nodes
    finally:
        loaded.cleanup()


def test_real_circuit_extract_yields_gates_and_measures():
    from diracq_sidecar import circuit_service as cz

    out = cz.extract({"guppy_src": _BELL, "entrypoint": "main", "n_qubits": 2})
    assert out["n_qubits"] == 2
    assert len(out["measures"]) == 2
    # The lowered Helios circuit entangles the two qubits (a 2-qubit gate).
    assert any(len(g["qubits"]) == 2 for g in out["gates"])


def test_real_hugr_graph_has_nodes_and_edges():
    from diracq_sidecar import hugr_service as hz

    g = hz.graph({"guppy_src": _BELL, "entrypoint": "main"})
    assert len(g["nodes"]) > 3  # Module/FuncDefn/Input/Output + ops
    assert len(g["edges"]) > 0
    labels = {n["label"] for n in g["nodes"]}
    assert "Output" in labels  # a real HUGR structural node
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in g["edges"])
