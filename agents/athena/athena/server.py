"""The ACP agent server surface (§18.6, Workstream E).

Athena implements the session lifecycle and interaction surface Zed's
``AgentConnection`` expects, so it plugs into the agent panel directly. Internally
it runs the plan->act->observe loop (``orchestrator.run_experiment``) over the
tools of Workstreams F–G, calling the compile/emulate/infer services on the
sidecar. Because it is a separate process, the heavy Python never blocks the
editor.

The protocol I/O against the `agent-client-protocol` schema is the remaining
Workstream-E wiring; the session lifecycle and a streaming, gate-aware prompt
are implemented and tested here.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path
from typing import Callable, Optional, Protocol

from athena.orchestrator import AgentNodes, run_experiment

EventSink = Callable[[dict], None]


class AcpAgent(Protocol):
    """Mirrors Zed's AgentConnection (session lifecycle + streaming prompt)."""

    def new_session(self, cwd: Path) -> str: ...
    def load_session(self, session_id: str) -> None: ...
    def resume_session(self, session_id: str) -> None: ...
    def close_session(self, session_id: str) -> None: ...
    def prompt(self, session_id: str, msg: dict, tx: EventSink) -> None: ...
    def cancel(self, session_id: str) -> None: ...
    def authenticate(self, method: str) -> None: ...


class AthenaAgent:
    """An in-process ACP agent driving the orchestrator. Supports multiple
    concurrent sessions (Zed runs threads in parallel) and cancellation."""

    def __init__(self, agents: Optional[AgentNodes] = None) -> None:
        self._sessions: dict[str, dict] = {}
        self._ids = itertools.count(1)
        self._agents = agents  # injected for tests; None → DefaultAgents

    def new_session(self, cwd: Path) -> str:
        sid = f"athena-{next(self._ids)}"
        self._sessions[sid] = {"cwd": str(cwd), "cancelled": False, "last": None}
        return sid

    def load_session(self, session_id: str) -> None:
        self._sessions.setdefault(session_id, {"cancelled": False, "last": None})

    def resume_session(self, session_id: str) -> None:
        self._require(session_id)["cancelled"] = False

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def cancel(self, session_id: str) -> None:
        self._require(session_id)["cancelled"] = True

    def authenticate(self, method: str) -> None:
        # No external auth needed for the local sidecar path.
        return None

    def prompt(self, session_id: str, msg: dict, tx: EventSink) -> dict:
        """Run an experiment for this prompt, streaming events to `tx`.

        `msg` carries a declarative experiment under `experiment` (or a free-text
        `goal`). Returns the terminal RunResult-as-dict. If the session was
        cancelled, emits a `cancelled` event and stops.
        """
        sess = self._require(session_id)
        if sess.get("cancelled"):
            tx({"type": "cancelled", "session": session_id})
            return {"status": "cancelled"}

        spec = msg.get("experiment") or {"goal": msg.get("goal", "")}
        result = run_experiment(spec, self._agents, emit=tx)
        sess["last"] = result.status
        tx({"type": "done", "status": result.status, "repairs": result.repairs})
        return {"status": result.status, "repairs": result.repairs}

    def _require(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            raise KeyError(f"unknown session: {session_id}")
        return self._sessions[session_id]


def main() -> int:
    print(
        "[diracq-athena] ACP agent server (Workstream E) — session lifecycle + "
        "orchestrator ready; ACP stdio protocol wiring is the remaining TODO",
        file=sys.stderr,
    )
    # TODO(Workstream E): bridge AthenaAgent to the agent-client-protocol schema
    # over stdio (new/load/resume/close session, streaming prompt, cancel) and
    # register the tools from athena.tools.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
