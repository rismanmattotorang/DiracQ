"""HuggingFace inference sidecar (§10) with a licence/revision-enforcing model
registry. The registry is a *governance* boundary: inference refuses any model
that is absent, unpinned, or used outside its licensed scope (enforced in code).
"""

from __future__ import annotations

from typing import Any


# Seed registry (Table 4). Production loads this from a checked-in manifest with
# checksum-verified weights; every entry pins a revision and records its licence.
_REGISTRY: dict[str, dict[str, Any]] = {
    "facebook/esm2_t33_650M_UR50D": {
        "domain": "biology",
        "task": "embedding",
        "licence": "MIT",
        "revision": "main",
        "commercial_ok": True,
    },
    "mace-off": {
        "domain": "chemistry",
        "task": "potential",
        "licence": "ASL",  # non-commercial — refused for commercial scope
        "revision": "v0.1",
        "commercial_ok": False,
    },
}


class ModelNotAllowed(RuntimeError):
    """Raised when a model is absent, unpinned, or out of licence scope."""


def register(dispatcher) -> None:
    dispatcher.register("model.list", lambda _p: list_models())
    dispatcher.register("model.infer", infer)


def list_models() -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in _REGISTRY.items()]


def infer(params: dict) -> dict[str, Any]:
    """Run inference after enforcing the registry guard.

    Expected params: model_id, inputs, revision, [commercial].
    """
    model_id = params.get("model_id", "")
    revision = params.get("revision")
    commercial = bool(params.get("commercial", False))
    card = _check_allowed(model_id, revision, commercial)

    _require_transformers()
    # TODO(Workstream G): load cached weights at the pinned revision and run on
    # the available device; return a task-specific payload.
    raise NotImplementedError(f"model.infer for {card['domain']}/{card['task']}: Workstream G")


def _check_allowed(model_id: str, revision: str | None, commercial: bool) -> dict[str, Any]:
    card = _REGISTRY.get(model_id)
    if card is None:
        raise ModelNotAllowed(f"model not in registry: {model_id}")
    if revision is None:
        raise ModelNotAllowed(f"model used unpinned (no revision): {model_id}")
    if commercial and not card["commercial_ok"]:
        raise ModelNotAllowed(f"model out of licence scope for commercial use: {model_id}")
    return card


def _require_transformers() -> None:
    try:
        import transformers  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "transformers not installed; `pip install diracq-sidecar[inference]`"
        ) from exc
