"""Selene emulation service (§7, Workstream C / M2). Wraps ``selene-sim`` behind
the JSON-RPC bridge and streams shots and resource metrics to the emulation
panel. A fixed seed makes every run reproducible (G7).

Real path: when ``guppylang``/``selene-sim`` are installed and a ``guppy_src`` +
``entrypoint`` are supplied, the program is compiled and run on Selene
(Stim/Quest, optional depolarizing noise) via the guppy emulator builder, which
records ``result(...)`` outcomes into bitstring counts.

Fallback: a deterministic mock backend answers when selene-sim is absent (or no
source is given). It does not model real dynamics — provenance is stamped
``selene = "mock"`` — but identical seeds yield identical counts, satisfying the
M2 reproducibility property so the panel and CI work before the stack is present.
"""

from __future__ import annotations

import random
from typing import Any

from diracq_sidecar import __version__


def register(dispatcher) -> None:
    dispatcher.register("selene.emulate", emulate)
    dispatcher.register("selene.resources", resources)


def emulate(params: dict, notify=None) -> dict[str, Any]:
    """Run a program on Selene.

    params: guppy_src, entrypoint (default "main"), n_qubits, shots, seed,
    simulator ("stim"|"quest"), error_model {kind,p_1q,p_2q}. Falls back to the
    deterministic mock when selene-sim or guppy_src is unavailable.

    `notify`, when provided, streams `selene.shot` progress notifications
    (running tallies) so the emulation panel updates live (§12.2).
    """
    if params.get("guppy_src") and _selene_available():
        return _emulate_real(params, notify)
    return _emulate_mock(params, notify)


def resources(params: dict) -> dict[str, Any]:
    n = int(params.get("n_qubits", 0))
    return {"n_qubits": n, "gate_count": 0, "two_qubit_gates": 0, "depth": 0}


def _emulate_real(params: dict, notify=None) -> dict[str, Any]:
    import guppylang
    import selene_sim

    from diracq_sidecar import _guppy_runtime as rt

    n_qubits = max(1, int(params.get("n_qubits", 1)))
    shots = int(params.get("shots", 0))
    seed = int(params.get("seed", 0))
    entrypoint = params.get("entrypoint", "main")
    sim = selene_sim.Quest() if str(params.get("simulator", "stim")) == "quest" else selene_sim.Stim()

    loaded = rt.load_guppy_module(params["guppy_src"])
    try:
        fn = getattr(loaded.module, entrypoint)
        builder = (
            fn.emulator(n_qubits=n_qubits)
            .with_simulator(sim)
            .with_shots(shots)
            .with_seed(seed)
        )
        error_model = _build_error_model(params.get("error_model") or {})
        if error_model is not None:
            builder = builder.with_error_model(error_model)
        result = builder.run()
        counts = _collate_bitstrings(result)
        if notify is not None:
            notify("selene.shot", {"done": int(sum(counts.values())), "total": shots, "counts": counts})
        return {
            "counts": counts,
            "metrics": {"n_qubits": n_qubits, "gate_count": 0, "two_qubit_gates": 0, "depth": 0},
            "seed": seed,
            "stack_versions": {
                "guppylang": guppylang.__version__,
                "selene_sim": getattr(selene_sim, "__version__", "unknown"),
                "diracq_sidecar": __version__,
            },
        }
    finally:
        loaded.cleanup()


# DiracNoise (§7.2): the calibrated operating point DiracQ targets on Helios-class
# hardware, so a validator "pass" is a fair rehearsal of a real run. Built on
# Selene's documented DepolarizingErrorModel plugin point — no Selene internals
# are modified.
DIRACNOISE_CALIBRATION = {"p_1q": 1e-3, "p_2q": 1e-2}


def _build_error_model(em: dict):
    """Map an ErrorModelSpec to a Selene error-model plugin (or None for ideal)."""
    import selene_sim

    kind = em.get("kind", "none")
    if kind == "none":
        return None
    if kind == "depolarizing":
        return selene_sim.DepolarizingErrorModel(
            p_1q=float(em.get("p_1q", 0.0)), p_2q=float(em.get("p_2q", 0.0))
        )
    if kind == "dirac_calibrated":
        # Calibrated defaults, overridable per-request.
        return selene_sim.DepolarizingErrorModel(
            p_1q=float(em.get("p_1q", DIRACNOISE_CALIBRATION["p_1q"])),
            p_2q=float(em.get("p_2q", DIRACNOISE_CALIBRATION["p_2q"])),
        )
    return None


def _collate_bitstrings(result) -> dict[str, int]:
    """Turn Selene's collated digit-string counts into bitstring -> frequency,
    ordering bits by register name for stable keys."""
    out: dict[str, int] = {}
    for entries, n in result.collated_digitstring_counts().items():
        # entries is a tuple like (('c0','1'), ('c1','0')); order by register name.
        bits = "".join(v for _k, v in sorted(entries, key=lambda kv: kv[0]))
        out[bits] = out.get(bits, 0) + int(n)
    return out


def _emulate_mock(params: dict, notify=None) -> dict[str, Any]:
    n = max(1, min(int(params.get("n_qubits", 1)), 20))
    shots = int(params.get("shots", 0))
    seed = int(params.get("seed", 0))
    rng = random.Random(seed ^ (n << 32) ^ shots)
    counts: dict[str, int] = {}
    # Stream progress in ~10 batches so the panel histogram fills live.
    batch = max(1, shots // 10)
    for i in range(shots):
        bits = "".join("1" if rng.getrandbits(1) else "0" for _ in range(n))
        counts[bits] = counts.get(bits, 0) + 1
        if notify is not None and (i + 1) % batch == 0:
            notify("selene.shot", {"done": i + 1, "total": shots, "counts": dict(counts)})
    return {
        "counts": counts,
        "metrics": {"n_qubits": n, "gate_count": 0, "two_qubit_gates": 0, "depth": 0},
        "seed": seed,
        "stack_versions": {"selene": "mock", "diracq_sidecar": __version__},
    }


def _selene_available() -> bool:
    try:
        import guppylang  # noqa: F401
        import selene_sim  # noqa: F401

        return True
    except ImportError:
        return False
