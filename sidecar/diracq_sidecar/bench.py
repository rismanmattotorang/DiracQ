"""DiracQ benchmark harness (§14.2).

A fixed suite of reference workloads, each run with deterministic seeds so
results are comparable across commits. The harness records latency percentiles
and fails CI on regression beyond a per-operation budget (Table 8). Treating
reproducibility as a *measured* property (G7) is what lets emulated quantum
programs sit under ordinary CI (§14.3).

The harness itself is dependency-free (stdlib only); the concrete cases live in
`benchmarks.py` and drive the sidecar services (mock-backed when the quantum
stack is absent, so CI is fast and hermetic).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

BenchFn = Callable[[], None]


@dataclass
class Case:
    name: str
    fn: BenchFn
    warmups: int = 2
    runs: int = 10


_REGISTRY: list[Case] = []


def case(name: str, warmups: int = 2, runs: int = 10) -> Callable[[BenchFn], BenchFn]:
    """Register a benchmark case. Mirrors the spec's `@case(...)` decorator."""

    def deco(fn: BenchFn) -> BenchFn:
        _REGISTRY.append(Case(name=name, fn=fn, warmups=warmups, runs=runs))
        return fn

    return deco


def registry() -> list[Case]:
    return list(_REGISTRY)


def percentile(samples_ms: list[float], p: float) -> float:
    """Nearest-rank percentile (p in [0, 100]). Empty -> 0.0."""
    import math

    if not samples_ms:
        return 0.0
    ordered = sorted(samples_ms)
    if p <= 0:
        return ordered[0]
    rank = max(1, min(len(ordered), math.ceil((p / 100.0) * len(ordered))))
    return ordered[rank - 1]


@dataclass
class CaseResult:
    name: str
    p50_ms: float
    p95_ms: float
    runs: int
    samples_ms: list[float] = field(default_factory=list)


def run_case(c: Case) -> CaseResult:
    for _ in range(c.warmups):
        c.fn()
    samples: list[float] = []
    for _ in range(c.runs):
        t0 = time.perf_counter()
        c.fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return CaseResult(
        name=c.name,
        p50_ms=percentile(samples, 50),
        p95_ms=percentile(samples, 95),
        runs=c.runs,
        samples_ms=samples,
    )


def run_all() -> list[CaseResult]:
    return [run_case(c) for c in _REGISTRY]


@dataclass
class Violation:
    name: str
    p95_ms: float
    budget_ms: float


def check_budgets(results: list[CaseResult], budgets: dict[str, float]) -> list[Violation]:
    """A case violates its budget if p95 exceeds it. Cases without a budget are
    informational. Budgets without a matching case are ignored here."""
    violations: list[Violation] = []
    by_name = {r.name: r for r in results}
    for name, budget_ms in budgets.items():
        r = by_name.get(name)
        if r is not None and r.p95_ms > budget_ms:
            violations.append(Violation(name, r.p95_ms, budget_ms))
    return violations


def load_budgets(path: str | Path) -> dict[str, float]:
    data = json.loads(Path(path).read_text())
    # budgets file maps name -> {"p95_ms": N}
    return {k: float(v["p95_ms"]) for k, v in data.items()}


def format_report(results: list[CaseResult], violations: list[Violation]) -> str:
    lines = ["DiracQ benchmark report", "=" * 40]
    bad = {v.name for v in violations}
    for r in sorted(results, key=lambda r: r.name):
        flag = "FAIL" if r.name in bad else "ok"
        lines.append(f"[{flag:>4}] {r.name:<28} p50={r.p50_ms:7.2f}ms  p95={r.p95_ms:7.2f}ms  (n={r.runs})")
    for v in violations:
        lines.append(f"  ! {v.name}: p95 {v.p95_ms:.2f}ms > budget {v.budget_ms:.2f}ms")
    return "\n".join(lines)
