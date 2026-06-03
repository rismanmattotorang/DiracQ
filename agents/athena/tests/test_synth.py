"""Tests for multimodal synthesis / pre-screen gating (Workstream G)."""

from athena.synth import multimodal_synthesis


def test_only_top_candidate_proceeds_to_quantum():
    scores = {"A": 0.9, "B": 0.8, "C": 0.2}
    r = multimodal_synthesis(
        candidates=["A", "B", "C"],
        keep_top=1,
        active_space_qubits=4,
        pre_screen=lambda cs: scores,
    )
    assert r.status == "ok"
    assert r.survivors == ["A"]  # highest score, capped at keep_top=1
    assert "def vqe_ansatz" in r.guppy_src
    assert "q3" in r.guppy_src  # 4-qubit active space


def test_no_survivors_skips_quantum_step():
    scores = {"A": 0.1, "B": 0.2}  # all below threshold
    r = multimodal_synthesis(
        candidates=["A", "B"],
        pre_screen=lambda cs: scores,
        score_threshold=0.5,
    )
    assert r.status == "no_survivors"
    assert r.guppy_src == ""  # quantum spend avoided (G3)


def test_keep_top_caps_survivors():
    scores = {"A": 0.9, "B": 0.85, "C": 0.7}
    r = multimodal_synthesis(
        candidates=["A", "B", "C"],
        keep_top=2,
        pre_screen=lambda cs: scores,
    )
    assert r.survivors == ["A", "B"]


def test_prompt_only_synthesizes_default_active_space():
    r = multimodal_synthesis(prompt="ground-state energy of H2", active_space_qubits=2)
    assert r.status == "ok"
    assert "q1" in r.guppy_src and "q2" not in r.guppy_src  # 2-qubit ansatz
