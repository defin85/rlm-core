"""Generic helper functions for direct-path repository exploration."""

from __future__ import annotations

import fnmatch
import os
import pathlib
import re
from typing import Callable

_SKIP_DIRS = {
    ".git",
    ".beads",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    "coverage",
}

_BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".xz",
    ".bz2",
    ".sqlite",
    ".db",
    ".bin",
}


def make_runtime_helpers(base_path: str | pathlib.Path) -> tuple[dict[str, Callable[..., object]], Callable[[str], pathlib.Path]]:
    """Build a generic helper set for direct-path sandbox exploration."""
    base = pathlib.Path(base_path).expanduser().resolve()

    def resolve_safe(path: str) -> pathlib.Path:
        resolved = (base / path).resolve()
        try:
            resolved.relative_to(base)
        except ValueError as exc:
            raise PermissionError(f"Access denied: path '{path}' escapes sandbox root") from exc
        return resolved

    def walk_files(root: pathlib.Path):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS and not name.startswith(".")]
            for filename in filenames:
                if filename.startswith("."):
                    continue
                yield pathlib.Path(dirpath) / filename

    def read_file(path: str) -> str:
        target = resolve_safe(path)
        if target.suffix.lower() in _BINARY_EXTENSIONS:
            raise ValueError(f"Refusing to read binary-looking file: {path}")
        return target.read_text(encoding="utf-8-sig", errors="replace")

    def read_files(paths: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for path in paths:
            try:
                result[path] = read_file(path)
            except (OSError, PermissionError, ValueError) as exc:
                result[path] = f"[error: {exc}]"
        return result

    def glob_files(pattern: str) -> list[str]:
        matches: list[str] = []
        for file_path in walk_files(base):
            relative = file_path.relative_to(base).as_posix()
            if fnmatch.fnmatch(relative, pattern):
                matches.append(relative)
        return sorted(matches)

    def grep(pattern: str, path: str = ".") -> list[dict[str, object]]:
        target = resolve_safe(path)
        compiled = re.compile(pattern)
        search_paths = [target] if target.is_file() else walk_files(target)
        results: list[dict[str, object]] = []
        for file_path in search_paths:
            if file_path.suffix.lower() in _BINARY_EXTENSIONS or not file_path.is_file():
                continue
            try:
                for line_number, line in enumerate(
                    file_path.read_text(encoding="utf-8-sig", errors="replace").splitlines(),
                    start=1,
                ):
                    if compiled.search(line):
                        results.append(
                            {
                                "file": file_path.relative_to(base).as_posix(),
                                "line": line_number,
                                "text": line.strip(),
                            }
                        )
            except OSError:
                continue
        return results

    def tree(path: str = ".", max_depth: int = 3) -> str:
        target = resolve_safe(path)
        if target.is_file():
            return target.relative_to(base).as_posix()

        lines = [pathlib.Path(path).as_posix() if path != "." else "."]

        def render(current: pathlib.Path, prefix: str, depth: int) -> None:
            if depth >= max_depth:
                return
            entries = [
                entry
                for entry in sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
                if entry.name not in _SKIP_DIRS and not entry.name.startswith(".")
            ]
            for index, entry in enumerate(entries):
                connector = "└── " if index == len(entries) - 1 else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    child_prefix = f"{prefix}{'    ' if index == len(entries) - 1 else '│   '}"
                    render(entry, child_prefix, depth + 1)

        render(target, "", 0)
        return "\n".join(lines)

    return {
        "glob_files": glob_files,
        "grep": grep,
        "read_file": read_file,
        "read_files": read_files,
        "tree": tree,
    }, resolve_safe
