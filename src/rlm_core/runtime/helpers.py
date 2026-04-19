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

_DEFAULT_GLOB_LIMIT = 200
_DEFAULT_GREP_LIMIT = 100
_DEFAULT_FIND_LIMIT = 100
_DEFAULT_READ_BATCH_LIMIT = 20
_DEFAULT_READ_MAX_LINES = 200
_DEFAULT_READ_MAX_CHARS = 12_000
_DEFAULT_TREE_ENTRIES = 200
_BROAD_SEARCH_FILE_THRESHOLD = 5_000


def _walk_files(root: pathlib.Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS and not name.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            yield pathlib.Path(dirpath) / filename


def _walk_dirs(root: pathlib.Path):
    if root.is_dir():
        yield root
    for dirpath, dirnames, _filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS and not name.startswith(".")]
        for dirname in dirnames:
            yield pathlib.Path(dirpath) / dirname


def _count_visible_files(root: pathlib.Path) -> int:
    count = 0
    for _ in _walk_files(root):
        count += 1
        if count > _BROAD_SEARCH_FILE_THRESHOLD:
            return count
    return count


def _shape_text_excerpt(
    content: str,
    *,
    start_line: int,
    max_lines: int,
    max_chars: int,
) -> str:
    if start_line < 1:
        raise ValueError("start_line must be >= 1")
    if max_lines < 1:
        raise ValueError("max_lines must be >= 1")
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")

    lines = content.splitlines()
    total_lines = len(lines)
    start_index = start_line - 1
    if start_index >= total_lines:
        return ""

    if start_line == 1 and total_lines <= max_lines and len(content) <= max_chars:
        return content

    selected_lines = lines[start_index : start_index + max_lines]
    excerpt = "\n".join(selected_lines)
    line_end = start_index + len(selected_lines)
    chars_truncated = False
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip()
        chars_truncated = True

    if start_index > 0 or line_end < total_lines or chars_truncated:
        footer = f"... [excerpt: lines {start_index + 1}-{line_end} of {total_lines}"
        if chars_truncated:
            footer += f", chars capped at {max_chars}"
        footer += "]"
        if excerpt:
            excerpt = excerpt.rstrip("\n") + "\n" + footer
        else:
            excerpt = footer
    return excerpt


def _summarize_grouped_matches(
    grouped: dict[str, list[dict[str, object]]],
    *,
    total_matches: int,
    truncated: bool,
    limit: int,
) -> str:
    if not grouped:
        return "No matches found."

    lines = [f"{total_matches} matches in {len(grouped)} files"]
    if truncated:
        lines[0] += f" (truncated to first {limit} matches)"
    lines[0] += ":"
    for file_path, matches in grouped.items():
        lines.append(f"\n  {file_path} ({len(matches)} matches):")
        for match in matches:
            lines.append(f"    L{match['line']}: {match['text']}")
    return "\n".join(lines)


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

    def read_text_file(target: pathlib.Path) -> str:
        relative_path = target.relative_to(base).as_posix()
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        if target.suffix.lower() in _BINARY_EXTENSIONS:
            raise ValueError(f"Refusing to read binary-looking file: {relative_path}")
        return target.read_text(encoding="utf-8-sig", errors="replace")

    def read_file(
        path: str,
        *,
        start_line: int = 1,
        max_lines: int = _DEFAULT_READ_MAX_LINES,
        max_chars: int = _DEFAULT_READ_MAX_CHARS,
    ) -> str:
        target = resolve_safe(path)
        content = read_text_file(target)
        return _shape_text_excerpt(content, start_line=start_line, max_lines=max_lines, max_chars=max_chars)

    def read_files(
        paths: list[str],
        *,
        start_line: int = 1,
        max_lines: int = _DEFAULT_READ_MAX_LINES,
        max_chars: int = _DEFAULT_READ_MAX_CHARS,
        max_files: int = _DEFAULT_READ_BATCH_LIMIT,
    ) -> dict[str, str]:
        if max_files < 1:
            raise ValueError("max_files must be >= 1")
        if len(paths) > max_files:
            raise ValueError(f"read_files accepts at most {max_files} paths per call")

        result: dict[str, str] = {}
        for path in paths:
            try:
                result[path] = read_file(path, start_line=start_line, max_lines=max_lines, max_chars=max_chars)
            except (OSError, PermissionError, ValueError) as exc:
                result[path] = f"[error: {exc}]"
        return result

    def glob_files(pattern: str, *, limit: int = _DEFAULT_GLOB_LIMIT) -> list[str]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        matches: list[str] = []
        for file_path in _walk_files(base):
            relative = file_path.relative_to(base).as_posix()
            if fnmatch.fnmatch(relative, pattern):
                matches.append(relative)
                if len(matches) >= limit:
                    break
        if matches:
            return sorted(matches)

        dir_matches = 0
        for dir_path in _walk_dirs(base):
            relative = dir_path.relative_to(base).as_posix() or "."
            if fnmatch.fnmatch(relative, pattern):
                dir_matches += 1
        if dir_matches:
            noun = "directory" if dir_matches == 1 else "directories"
            return [
                f"[hint: pattern '{pattern}' matched {dir_matches} {noun} but no files. "
                f"Add a file suffix or a recursive suffix such as '{pattern}/**']"
            ]
        return []

    def grep_matches(
        pattern: str,
        *,
        path: str = ".",
        limit: int = _DEFAULT_GREP_LIMIT,
    ) -> tuple[list[dict[str, object]], bool]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        target = resolve_safe(path)
        if target.is_dir() and _count_visible_files(target) > _BROAD_SEARCH_FILE_THRESHOLD:
            raise ValueError(
                f"grep on '{path}' would scan too many files. "
                "Narrow the path or use glob_files()/find_files() first."
            )

        compiled = re.compile(pattern)
        search_paths = [target] if target.is_file() else _walk_files(target)
        results: list[dict[str, object]] = []
        truncated = False

        for file_path in search_paths:
            if file_path.suffix.lower() in _BINARY_EXTENSIONS or not file_path.is_file():
                continue
            try:
                for line_number, line in enumerate(read_text_file(file_path).splitlines(), start=1):
                    if compiled.search(line):
                        results.append(
                            {
                                "file": file_path.relative_to(base).as_posix(),
                                "line": line_number,
                                "text": line.strip(),
                            }
                        )
                        if len(results) >= limit:
                            truncated = True
                            return results, truncated
            except OSError:
                continue
        return results, truncated

    def grep(pattern: str, path: str = ".", *, limit: int = _DEFAULT_GREP_LIMIT) -> list[dict[str, object]]:
        results, _truncated = grep_matches(pattern, path=path, limit=limit)
        return results

    def grep_summary(pattern: str, path: str = ".", *, limit: int = _DEFAULT_GREP_LIMIT) -> str:
        results, truncated = grep_matches(pattern, path=path, limit=limit)
        grouped: dict[str, list[dict[str, object]]] = {}
        for match in results:
            grouped.setdefault(str(match["file"]), []).append(match)
        return _summarize_grouped_matches(grouped, total_matches=len(results), truncated=truncated, limit=limit)

    def grep_read(
        pattern: str,
        path: str = ".",
        *,
        max_files: int = 10,
        context_lines: int = 0,
        limit: int = _DEFAULT_GREP_LIMIT,
        max_chars_per_file: int = _DEFAULT_READ_MAX_CHARS,
    ) -> dict[str, object]:
        if max_files < 1:
            raise ValueError("max_files must be >= 1")
        if context_lines < 0:
            raise ValueError("context_lines must be >= 0")

        results, truncated = grep_matches(pattern, path=path, limit=limit)
        if not results:
            return {"matches": {}, "files": {}, "summary": "No matches found."}

        grouped: dict[str, list[dict[str, object]]] = {}
        for match in results:
            grouped.setdefault(str(match["file"]), []).append(match)

        selected_paths = list(grouped)[:max_files]
        file_payloads: dict[str, str] = {}
        for relative_path in selected_paths:
            try:
                raw_content = read_text_file(resolve_safe(relative_path))
                if context_lines > 0:
                    content_lines = raw_content.splitlines()
                    visible_indexes: set[int] = set()
                    for match in grouped[relative_path]:
                        line_index = int(match["line"]) - 1
                        start_index = max(0, line_index - context_lines)
                        end_index = min(len(content_lines), line_index + context_lines + 1)
                        for candidate in range(start_index, end_index):
                            visible_indexes.add(candidate)
                    excerpt = "\n".join(f"L{index + 1}: {content_lines[index]}" for index in sorted(visible_indexes))
                    if len(excerpt) > max_chars_per_file:
                        excerpt = excerpt[:max_chars_per_file].rstrip() + f"\n... [excerpt capped at {max_chars_per_file} chars]"
                    file_payloads[relative_path] = excerpt
                else:
                    file_payloads[relative_path] = read_file(relative_path, max_chars=max_chars_per_file)
            except (OSError, PermissionError, ValueError) as exc:
                file_payloads[relative_path] = f"[error: {exc}]"

        summary = _summarize_grouped_matches(
            {relative_path: grouped[relative_path] for relative_path in selected_paths},
            total_matches=len(results),
            truncated=truncated,
            limit=limit,
        )
        omitted_files = len(grouped) - len(selected_paths)
        if omitted_files > 0:
            summary += f"\n... [showing {len(selected_paths)} files, {omitted_files} more omitted]"

        return {
            "matches": {relative_path: grouped[relative_path] for relative_path in selected_paths},
            "files": file_payloads,
            "summary": summary,
        }

    def find_files(name: str, *, limit: int = _DEFAULT_FIND_LIMIT) -> list[str]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        needle = name.strip().lower()
        if not needle:
            return []

        ranked: list[tuple[int, int, str]] = []
        for file_path in _walk_files(base):
            relative = file_path.relative_to(base).as_posix()
            relative_lower = relative.lower()
            file_name = file_path.name.lower()
            score = -1
            if file_name == needle:
                score = 0
            elif file_name.startswith(needle):
                score = 1
            elif needle in file_name:
                score = 2
            elif needle in relative_lower:
                score = 3
            if score >= 0:
                ranked.append((score, len(relative), relative))

        ranked.sort()
        return [relative for _score, _length, relative in ranked[:limit]]

    def tree(path: str = ".", max_depth: int = 3, *, max_entries: int = _DEFAULT_TREE_ENTRIES) -> str:
        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")

        target = resolve_safe(path)
        if target.is_file():
            return target.relative_to(base).as_posix()

        lines = [pathlib.Path(path).as_posix() if path != "." else "."]
        rendered_entries = 0
        truncated = False

        def render(current: pathlib.Path, prefix: str, depth: int) -> None:
            nonlocal rendered_entries, truncated
            if truncated or depth >= max_depth:
                return

            entries = [
                entry
                for entry in sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
                if entry.name not in _SKIP_DIRS and not entry.name.startswith(".")
            ]
            for index, entry in enumerate(entries):
                if rendered_entries >= max_entries:
                    truncated = True
                    return
                connector = "└── " if index == len(entries) - 1 else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                rendered_entries += 1
                if entry.is_dir():
                    child_prefix = f"{prefix}{'    ' if index == len(entries) - 1 else '│   '}"
                    render(entry, child_prefix, depth + 1)
                    if truncated:
                        return

        render(target, "", 0)
        if truncated:
            lines.append("... [tree truncated; narrow the path or reduce max_depth]")
        return "\n".join(lines)

    return {
        "find_files": find_files,
        "glob_files": glob_files,
        "grep": grep,
        "grep_read": grep_read,
        "grep_summary": grep_summary,
        "read_file": read_file,
        "read_files": read_files,
        "tree": tree,
    }, resolve_safe
