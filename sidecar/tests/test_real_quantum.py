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


def test_real_compile_emits_hugr_bytes_and_metrics():
    from diracq_sidecar import compile_service as cs

    r = cs.compile_guppy({"guppy_src": _BELL, "opt_level": 2, "target": "helios"})
    import base64

    raw = base64.b64decode(r["hugr_b64"])
    assert len(raw) > 0  # a real serialised HUGR package
    assert r["metrics_before"]["n_qubits"] == 2
    assert r["metrics_before"]["gate_count"] > 0
