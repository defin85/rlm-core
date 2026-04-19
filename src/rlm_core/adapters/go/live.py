"""Live helper set for Go repository exploration."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_SKIP_DIRS = {
    ".beads",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

_PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
_FUNC_RE = re.compile(
    r"^\s*func\s*(?:\((?P<receiver>[^)]*)\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)
_TYPE_RE = re.compile(r"^\s*type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b")
_VAR_CONST_RE = re.compile(r"^\s*(?P<kind>var|const)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b")
_IMPORT_RE = re.compile(r'"([^"]+)"')


@dataclass(frozen=True, slots=True)
class GoFileInfo:
    """Discovered Go source file."""

    relative_path: str
    directory: str
    package: str
    is_test: bool

    def as_mapping(self) -> dict[str, object]:
        return {
            "path": self.relative_path,
            "directory": self.directory,
            "package": self.package,
            "is_test": self.is_test,
        }


@dataclass(frozen=True, slots=True)
class GoPackageInfo:
    """Aggregated Go package information."""

    package: str
    directory: str
    file_count: int
    test_file_count: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "package": self.package,
            "directory": self.directory,
            "file_count": self.file_count,
            "test_file_count": self.test_file_count,
        }


@dataclass(frozen=True, slots=True)
class GoDeclarationInfo:
    """Top-level Go declaration."""

    name: str
    kind: str
    line: int
    end_line: int
    receiver: str | None = None

    def as_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "line": self.line,
            "end_line": self.end_line,
            "receiver": self.receiver,
        }


def make_go_live_helpers(
    workspace_root: str | Path,
    *,
    details: dict[str, object] | None = None,
) -> dict[str, Callable[..., object]]:
    """Return adapter-owned live helpers for Go repositories."""

    workspace_base = Path(workspace_root).expanduser().resolve()
    repo_details = dict(details or {})
    module_root = str(repo_details.get("module_root") or ".")
    scan_root = (workspace_base / module_root).resolve()

    def resolve_safe(path: str) -> Path:
        resolved = (workspace_base / path).resolve()
        try:
            resolved.relative_to(workspace_base)
        except ValueError as exc:
            raise PermissionError(f"Access denied: path '{path}' escapes workspace root") from exc
        return resolved

    def go_repo_details() -> dict[str, object]:
        return dict(repo_details)

    def go_list_packages(name: str = "", *, limit: int = 50) -> list[dict[str, object]]:
        normalized_name = name.strip().lower()
        results: list[dict[str, object]] = []
        for item in _discover_packages(scan_root, workspace_base):
            haystacks = (item.package.lower(), item.directory.lower())
            if normalized_name and not any(normalized_name in hay for hay in haystacks):
                continue
            results.append(item.as_mapping())
            if len(results) >= limit:
                break
        return results

    def go_find_go_files(
        *,
        package: str = "",
        name: str = "",
        include_tests: bool = False,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        normalized_package = package.strip().lower()
        normalized_name = name.strip().lower()
        results: list[dict[str, object]] = []
        for item in _discover_go_files(scan_root, workspace_base):
            if not include_tests and item.is_test:
                continue
            if normalized_package and item.package.lower() != normalized_package:
                continue
            if normalized_name and normalized_name not in item.relative_path.lower():
                continue
            results.append(item.as_mapping())
            if len(results) >= limit:
                break
        return results

    def go_extract_declarations(path: str) -> list[dict[str, object]]:
        target = resolve_safe(path)
        return [item.as_mapping() for item in _extract_declarations(target)]

    def go_read_declaration(path: str, name: str) -> str:
        target = resolve_safe(path)
        lines = _read_text(target).splitlines()
        for item in _extract_declarations(target):
            if item.name == name:
                return "\n".join(lines[item.line - 1 : item.end_line])
        raise ValueError(f"Declaration not found in {path}: {name}")

    def go_find_imports(
        *,
        path: str = "",
        package: str = "",
        import_path: str = "",
        limit: int = 50,
    ) -> list[dict[str, object]]:
        normalized_package = package.strip().lower()
        normalized_import = import_path.strip().lower()
        if path:
            files = [_file_from_path(workspace_base, resolve_safe(path))]
        else:
            files = _discover_go_files(scan_root, workspace_base)

        results: list[dict[str, object]] = []
        for item in files:
            if normalized_package and item.package.lower() != normalized_package:
                continue
            for imported in _extract_imports(resolve_safe(item.relative_path)):
                if normalized_import and normalized_import not in imported.lower():
                    continue
                results.append(
                    {
                        "path": item.relative_path,
                        "package": item.package,
                        "import": imported,
                    }
                )
                if len(results) >= limit:
                    return results
        return results

    return {
        "go_extract_declarations": go_extract_declarations,
        "go_find_go_files": go_find_go_files,
        "go_find_imports": go_find_imports,
        "go_list_packages": go_list_packages,
        "go_read_declaration": go_read_declaration,
        "go_repo_details": go_repo_details,
    }


def _discover_packages(scan_root: Path, workspace_base: Path) -> list[GoPackageInfo]:
    packages: dict[tuple[str, str], list[GoFileInfo]] = {}
    for item in _discover_go_files(scan_root, workspace_base):
        packages.setdefault((item.directory, item.package), []).append(item)

    results: list[GoPackageInfo] = []
    for (directory, package), files in sorted(packages.items()):
        results.append(
            GoPackageInfo(
                package=package,
                directory=directory,
                file_count=len([item for item in files if not item.is_test]),
                test_file_count=len([item for item in files if item.is_test]),
            )
        )
    return results


def _discover_go_files(scan_root: Path, workspace_base: Path) -> list[GoFileInfo]:
    results: list[GoFileInfo] = []
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = sorted(item for item in dirs if item not in _SKIP_DIRS and not item.startswith("."))
        root_path = Path(root)
        directory = _relative_path(root_path, workspace_base)
        for name in sorted(files):
            if not name.endswith(".go"):
                continue
            target = root_path / name
            package = _read_package_name(target)
            if package is None:
                continue
            results.append(
                GoFileInfo(
                    relative_path=_relative_path(target, workspace_base),
                    directory=directory,
                    package=package,
                    is_test=name.endswith("_test.go"),
                )
            )
    return results


def _extract_declarations(path: Path) -> list[GoDeclarationInfo]:
    lines = _read_text(path).splitlines()
    declarations: list[GoDeclarationInfo] = []
    in_block_comment = False
    current: dict[str, object] | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        clean_line, in_block_comment = _sanitize_go_line(raw_line, in_block_comment)

        if current is None:
            match = _FUNC_RE.match(clean_line)
            if match:
                receiver = (match.group("receiver") or "").strip() or None
                current = {
                    "name": match.group("name"),
                    "kind": "method" if receiver else "func",
                    "receiver": receiver,
                    "line": line_number,
                    "balance": _balance_delta(clean_line),
                }
                if current["balance"] <= 0:
                    declarations.append(
                        GoDeclarationInfo(
                            name=str(current["name"]),
                            kind=str(current["kind"]),
                            line=int(current["line"]),
                            end_line=line_number,
                            receiver=current["receiver"],
                        )
                    )
                    current = None
                continue

            match = _TYPE_RE.match(clean_line)
            if match:
                current = {
                    "name": match.group("name"),
                    "kind": "type",
                    "receiver": None,
                    "line": line_number,
                    "balance": _balance_delta(clean_line),
                }
                if current["balance"] <= 0:
                    declarations.append(
                        GoDeclarationInfo(
                            name=str(current["name"]),
                            kind="type",
                            line=line_number,
                            end_line=line_number,
                        )
                    )
                    current = None
                continue

            match = _VAR_CONST_RE.match(clean_line)
            if match:
                declarations.append(
                    GoDeclarationInfo(
                        name=match.group("name"),
                        kind=match.group("kind"),
                        line=line_number,
                        end_line=line_number,
                    )
                )
                continue

        if current is not None:
            current["balance"] = int(current["balance"]) + _balance_delta(clean_line)
            if int(current["balance"]) <= 0:
                declarations.append(
                    GoDeclarationInfo(
                        name=str(current["name"]),
                        kind=str(current["kind"]),
                        line=int(current["line"]),
                        end_line=line_number,
                        receiver=current["receiver"],
                    )
                )
                current = None

    return declarations


def _extract_imports(path: Path) -> list[str]:
    imports: list[str] = []
    in_import_block = False

    for raw_line in _read_text(path).splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        if in_import_block:
            if line == ")":
                in_import_block = False
                continue
            match = _IMPORT_RE.search(line)
            if match:
                imports.append(match.group(1))
            continue

        if line.startswith("import ("):
            in_import_block = True
            continue
        if line.startswith("import "):
            match = _IMPORT_RE.search(line)
            if match:
                imports.append(match.group(1))

    return imports


def _read_package_name(path: Path) -> str | None:
    for raw_line in _read_text(path).splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        match = _PACKAGE_RE.match(line)
        if match:
            return match.group(1)
        break
    return None


def _file_from_path(base: Path, path: Path) -> GoFileInfo:
    package = _read_package_name(path)
    if package is None:
        raise ValueError(f"Not a valid Go source file: {_relative_path(path, base)}")
    return GoFileInfo(
        relative_path=_relative_path(path, base),
        directory=_relative_path(path.parent, base),
        package=package,
        is_test=path.name.endswith("_test.go"),
    )


def _sanitize_go_line(line: str, in_block_comment: bool) -> tuple[str, bool]:
    chars: list[str] = []
    index = 0
    in_string = False
    in_raw_string = False
    in_rune = False

    while index < len(line):
        if in_block_comment:
            end_index = line.find("*/", index)
            if end_index == -1:
                return "".join(chars), True
            index = end_index + 2
            in_block_comment = False
            continue

        current = line[index]
        next_two = line[index : index + 2]

        if in_string:
            if current == "\\":
                index += 2
                chars.append(" ")
                continue
            if current == '"':
                in_string = False
            chars.append(" ")
            index += 1
            continue

        if in_raw_string:
            if current == "`":
                in_raw_string = False
            chars.append(" ")
            index += 1
            continue

        if in_rune:
            if current == "\\":
                index += 2
                chars.append(" ")
                continue
            if current == "'":
                in_rune = False
            chars.append(" ")
            index += 1
            continue

        if next_two == "//":
            break
        if next_two == "/*":
            in_block_comment = True
            index += 2
            continue
        if current == '"':
            in_string = True
            chars.append(" ")
            index += 1
            continue
        if current == "`":
            in_raw_string = True
            chars.append(" ")
            index += 1
            continue
        if current == "'":
            in_rune = True
            chars.append(" ")
            index += 1
            continue

        chars.append(current)
        index += 1

    return "".join(chars), in_block_comment


def _balance_delta(line: str) -> int:
    delta = 0
    for char in line:
        if char in "{[(":
            delta += 1
        elif char in "}])":
            delta -= 1
    return delta


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _relative_path(path: Path, base: Path) -> str:
    relative = path.relative_to(base)
    if relative == Path("."):
        return "."
    return relative.as_posix()
