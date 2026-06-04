"""Helpers for running real ``guppylang`` over an editor buffer (Workstream B/C).

The Guppy compiler reads function source via ``inspect``, so a buffer must be
materialised as a real importable module. These helpers write the buffer to a
uniquely-named temp file, import it, and expose the Guppy definitions plus a
line/column → byte-offset mapper for diagnostic ranges.

All of this is gated by the caller on ``guppylang`` actually being importable;
nothing here is imported at module load time of the sidecar.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional


def guppylang_available() -> bool:
    try:
        import guppylang  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass
class LoadedModule:
    module: Any
    path: Path
    name: str

    def cleanup(self) -> None:
        sys.modules.pop(self.name, None)
        try:
            self.path.unlink()
        except OSError:
            pass


def load_guppy_module(src: str) -> LoadedModule:
    """Materialise `src` as a uniquely-named importable module."""
    name = f"diracq_buf_{uuid.uuid4().hex}"
    path = Path(tempfile.gettempdir()) / f"{name}.py"
    path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # may raise SyntaxError / NameError
    return LoadedModule(module=module, path=path, name=name)


def _guppy_decorated_names(src: str) -> list[str]:
    """Top-level function names decorated with `@guppy` / `@guppy.something`.

    Parsing the buffer's AST is the precise way to find *user* Guppy functions:
    imported builtins (``result``, ``h``, …) are GuppyFunctionDefinition objects
    too and can't be told apart by type, but they are never decorated here.
    """
    def is_guppy_decorator(dec: ast.expr) -> bool:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name):
            return target.id == "guppy"
        if isinstance(target, ast.Attribute):
            return isinstance(target.value, ast.Name) and target.value.id == "guppy"
        return False

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(is_guppy_decorator(d) for d in node.decorator_list):
                names.append(node.name)
    return names


def iter_guppy_defs(module: Any, src: str) -> Iterator[tuple[str, Any]]:
    """Yield (name, definition) for each user Guppy function in the buffer."""
    for name in _guppy_decorated_names(src):
        obj = getattr(module, name, None)
        if obj is not None and hasattr(obj, "compile"):
            yield name, obj


def select_entrypoint(module: Any, src: str) -> Optional[Any]:
    """Pick the program entrypoint: a function named main/circuit/ansatz if
    present, else the last user-defined Guppy function."""
    defs = dict(iter_guppy_defs(module, src))
    for preferred in ("main", "circuit", "ansatz"):
        if preferred in defs:
            return defs[preferred]
    return list(defs.values())[-1] if defs else None


def line_col_to_offset(src: str, line: int, column: int) -> int:
    """Convert a 1-based line + 0-based column to a byte offset into `src`."""
    lines = src.splitlines(keepends=True)
    offset = sum(len(lines[i]) for i in range(min(line - 1, len(lines))))
    return offset + column
