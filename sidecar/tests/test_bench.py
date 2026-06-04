"""Tests for the benchmark harness (§14)."""

from diracq_sidecar import bench


def test_percentile_nearest_rank():
    xs = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert bench.percentile(xs, 50) == 30.0
    assert bench.percentile(xs, 95) == 50.0
    assert bench.percentile(xs, 0) == 10.0
    assert bench.percentile([], 95) == 0.0


def test_run_case_collects_samples():
    calls = {"n": 0}

    @bench.case(name="_unit_probe", warmups=2, runs=4)
    def _probe():
        calls["n"] += 1

    c = next(c for c in bench.registry() if c.name == "_unit_probe")
    r = bench.run_case(c)
    assert r.runs == 4
    assert len(r.samples_ms) == 4
    assert calls["n"] == 2 + 4  # warmups + runs
    assert r.p95_ms >= r.p50_ms >= 0.0


def test_budget_violation_detected():
    results = [bench.CaseResult(name="slow", p50_ms=10.0, p95_ms=120.0, runs=3)]
    violations = bench.check_budgets(results, {"slow": 100.0})
    assert len(violations) == 1 and violations[0].name == "slow"

    none = bench.check_budgets(results, {"slow": 200.0})
    assert none == []


def test_report_flags_failures():
    results = [bench.CaseResult(name="x", p50_ms=1.0, p95_ms=9.0, runs=2)]
    v = bench.check_budgets(results, {"x": 5.0})
    report = bench.format_report(results, v)
    assert "FAIL" in report and "budget" in report


def test_reference_suite_runs_and_meets_budgets():
    """The shipped reference cases run and stay within their (padded) budgets
    on the mock path — the reproducibility/CI gate in miniature."""
    from diracq_sidecar import benchmarks  # noqa: F401 (registers cases)

    results = bench.run_all()
    names = {r.name for r in results}
    assert {"bell_smoke", "emulate_4q_2k", "hugr_compile_small"} <= names
    budgets = bench.load_budgets("benchmarks/budgets.json")
    assert bench.check_budgets(results, budgets) == []
