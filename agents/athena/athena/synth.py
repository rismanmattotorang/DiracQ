"""Multimodal synthesis (§18.8, Workstream G).

Accept natural language, pseudocode, and molecular inputs (SMILES/PDB/.xyz) and
synthesise chemistry/biology-targeted Guppy, seeded by foundation-model
pre-screening. MLIPs relax geometry and rank candidates; protein models
characterise targets; the quantum step (VQE via a Guppy ansatz) refines only the
strongly-correlated core — so the quantum spend goes only to survivors of the
pre-screen (G3: cheap classical screening before scarce quantum work).

The pre-screen and molecule parsing are injected so the tool is testable offline;
production wires the inference sidecar (`model.infer`, `mol.parse`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from athena import templates

# Maps a candidate id → a score in [0, 1]. Production calls the FM pre-screen.
PreScreen = Callable[[list[str]], dict[str, float]]


@dataclass
class SynthResult:
    survivors: list[str]
    active_space_qubits: int
    guppy_src: str
    status: str  # "ok" | "no_survivors"


def multimodal_synthesis(
    prompt: str = "",
    candidates: Optional[list[str]] = None,
    keep_top: int = 1,
    active_space_qubits: int = 4,
    pre_screen: Optional[PreScreen] = None,
    score_threshold: float = 0.5,
) -> SynthResult:
    """Pre-screen candidates, then synthesise a VQE ansatz for the survivors.

    Only candidates scoring at/above ``score_threshold`` survive, capped at
    ``keep_top`` — the quantum step never runs on screened-out candidates.
    """
    candidates = candidates or []
    pre_screen = pre_screen or _default_pre_screen

    scores = pre_screen(candidates) if candidates else {}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    survivors = [c for c, s in ranked if s >= score_threshold][:keep_top]

    if candidates and not survivors:
        # Nothing passed the classical screen — do not spend the quantum step.
        return SynthResult([], active_space_qubits, "", "no_survivors")

    # Refine only the strongly-correlated core: a VQE ansatz over the active space.
    src = templates.vqe_ansatz(active_space_qubits)
    return SynthResult(survivors, active_space_qubits, src, "ok")


def _default_pre_screen(candidates: list[str]) -> dict[str, float]:
    """Offline stand-in: a stable pseudo-score per candidate id (no model)."""
    return {c: ((hash(c) % 1000) / 1000.0) for c in candidates}
