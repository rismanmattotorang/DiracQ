"""Reference benchmark workloads (§14.2).

These drive the real sidecar services with fixed seeds. With the quantum stack
installed they exercise real guppylang/Selene; without it they run the
deterministic mocks — either way the harness measures the same call path and the
seeds make results reproducible across commits (G7).

Run the suite:  python -m diracq_sidecar.benchmarks
"""

from __future__ import annotations

import sys

from diracq_sidecar import bench
from diracq_sidecar import compile_service, selene_service

# A real Guppy Bell kernel (used when the stack is present; the mock path ignores
# the body and uses n_qubits/shots/seed).
_BELL = (
    "from guppylang import guppy\n"
    "from guppylang.std.quantum import qubit, h, cx, measure\n"
    "from guppylang.std.builtins import result\n"
    "@guppy\n"
    "def main() -> None:\n"
    "    a = qubit()\n    b = qubit()\n    h(a)\n    cx(a, b)\n"
    "    result('c0', measure(a))\n    result('c1', measure(b))\n"
)


@bench.case(name="bell_smoke", warmups=1, runs=5)
def _bell_smoke() -> None:
    selene_service.emulate(
        {"guppy_src": _BELL, "entrypoint": "main", "n_qubits": 2,
         "shots": 200, "seed": 12478, "simulator": "stim"}
    )


@bench.case(name="emulate_4q_2k", warmups=1, runs=5)
def _emulate_4q_2k() -> None:
    # Budgeted at <2s (Stim backend) in Table 8. Mock path is sub-ms.
    selene_service.emulate({"n_qubits": 4, "shots": 2000, "seed": 7, "simulator": "stim"})


@bench.case(name="hugr_compile_small", warmups=1, runs=5)
def _compile_small() -> None:
    compile_service.compile_guppy(
        {"guppy_src": _BELL, "opt_level": 2, "target": "helios", "dirac_passes": True}
    )


def main() -> int:
    budgets_path = __file__.rsplit("/", 2)[0] + "/benchmarks/budgets.json"
    results = bench.run_all()
    try:
        budgets = bench.load_budgets(budgets_path)
    except OSError:
        budgets = {}
    violations = bench.check_budgets(results, budgets)
    print(bench.format_report(results, violations))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
