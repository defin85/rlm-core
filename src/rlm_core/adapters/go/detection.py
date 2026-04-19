"""Detection helpers for Go repositories."""

from __future__ import annotations

from pathlib import Path

from .contracts import GoRepositoryDetails


def inspect_go_workspace(workspace_root: Path) -> GoRepositoryDetails | None:
    """Detect a Go workspace and return adapter-owned repository details."""

    workspace_root = Path(workspace_root).expanduser().resolve()
    for candidate in _candidate_roots(workspace_root):
        detected = _inspect_candidate(workspace_root, candidate)
        if detected is not None:
            return detected
    return None


def _candidate_roots(workspace_root: Path) -> list[Path]:
    candidates = [workspace_root]
    try:
        for child in sorted(workspace_root.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                candidates.append(child)
    except FileNotFoundError:
        return [workspace_root]
    return candidates


def _inspect_candidate(workspace_root: Path, candidate: Path) -> GoRepositoryDetails | None:
    module_file = candidate / "go.mod"
    if not module_file.is_file():
        return None

    module_path = ""
    go_version = ""
    try:
        for raw_line in module_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if not line:
                continue
            if line.startswith("module "):
                module_path = line.removeprefix("module ").strip()
            elif line.startswith("go "):
                go_version = line.removeprefix("go ").strip()
    except OSError:
        return None

    return GoRepositoryDetails(
        module_root=_relative_path(candidate, workspace_root),
        module_file=_relative_path(module_file, workspace_root),
        module_path=module_path or None,
        go_version=go_version or None,
    )


def _relative_path(path: Path, workspace_root: Path) -> str:
    relative = path.relative_to(workspace_root)
    if relative == Path("."):
        return "."
    return relative.as_posix()
