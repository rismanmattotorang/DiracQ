"""Athena tool schemas (Workstreams F & G).

Each agent node is dispatched a JSON-schema'd function by the LangGraph runtime.
The two differentiating tools are document-to-circuit generation and multimodal
synthesis; both end in the hard validation gate (check -> emulate -> baseline).
"""

from __future__ import annotations

# Workstream F: parse an arXiv paper / chapter / brief and emit an annotated,
# type-checked Guppy program. A generation that fails check() is repaired or
# rejected — never surfaced as "done".
DOCUMENT_TO_CIRCUIT = {
    "name": "document_to_circuit",
    "description": "Generate a type-checked Guppy program from a document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "path or arXiv id"},
            "target": {"enum": ["circuit", "vqe", "qpe", "custom"]},
            "max_qubits": {"type": "integer"},
            "validate": {"type": "boolean", "default": True},
        },
        "required": ["source"],
    },
}

# Workstream G: accept NL / pseudocode / molecular inputs (SMILES/PDB/.xyz) and
# synthesise chemistry/biology-targeted Guppy, seeded by FM pre-screening.
MULTIMODAL_SYNTHESIS = {
    "name": "multimodal_synthesis",
    "description": "Synthesise Guppy from text/pseudocode/molecular inputs, pre-screened by foundation models.",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "molecule": {"type": "string", "description": "SMILES/PDB/.xyz"},
            "method": {"enum": ["vqe", "qpe", "custom"], "default": "vqe"},
            "validate": {"type": "boolean", "default": True},
        },
        "required": [],
    },
}

ALL_TOOLS = [DOCUMENT_TO_CIRCUIT, MULTIMODAL_SYNTHESIS]
