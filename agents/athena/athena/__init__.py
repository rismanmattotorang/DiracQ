"""Athena — the DiracQ agentic orchestrator (§9, Workstream E).

Implemented as an ACP-compatible agent server (a separate process) so it appears
in Zed's existing agent panel with thread history and parallel threads, rather
than a bespoke chat UI. The heavy Python (LangGraph, transformers, guppylang)
runs here and never blocks the editor.
"""

__version__ = "0.1.0"
