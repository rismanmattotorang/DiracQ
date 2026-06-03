"""The ACP agent server surface (§18.6, Workstream E).

Athena implements the session lifecycle and interaction surface Zed's
``AgentConnection`` expects, so it plugs into the agent panel directly. Internally
it runs the plan->act->observe loop over the LangGraph graph, calling the
compile/emulate/infer services on the sidecar.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol


class AcpAgent(Protocol):
    """Mirrors Zed's AgentConnection (session lifecycle + streaming prompt)."""

    async def new_session(self, cwd: Path) -> str: ...
    async def load_session(self, session_id: str) -> None: ...
    async def resume_session(self, session_id: str) -> None: ...
    async def close_session(self, session_id: str) -> None: ...
    async def prompt(self, session_id: str, msg: dict, tx) -> None: ...
    async def cancel(self, session_id: str) -> None: ...
    async def authenticate(self, method: str) -> None: ...


class AthenaAgent:
    """Skeleton ACP agent. Workstream E fills in the protocol I/O and wires the
    LangGraph run; the human gate guards the single paid/irreversible step."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    async def new_session(self, cwd: Path) -> str:
        raise NotImplementedError("Athena ACP session lifecycle: Workstream E")


def main() -> int:
    print("[diracq-athena] ACP agent server (Workstream E stub) — not yet serving", file=sys.stderr)
    # TODO(Workstream E): scaffold an ACP server using the agent-client-protocol
    # schema; implement session lifecycle and a streaming prompt; register the
    # tools from athena.tools and emit tool-call events over ACP.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
