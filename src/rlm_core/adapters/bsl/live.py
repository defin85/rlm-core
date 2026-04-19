"""Live and indexed helper set for BSL repository exploration."""

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
}

_METADATA_CATEGORIES = frozenset(
    {
        "AccumulationRegisters",
        "AccountingRegisters",
        "BusinessProcesses",
        "CalculationRegisters",
        "Catalogs",
        "ChartsOfAccounts",
        "ChartsOfCalculationTypes",
        "ChartsOfCharacteristicTypes",
        "CommonCommands",
        "CommonForms",
        "CommonModules",
        "Constants",
        "DataProcessors",
        "DocumentJournals",
        "Documents",
        "Enums",
        "ExchangePlans",
        "ExternalDataSources",
        "FilterCriteria",
        "HTTPServices",
        "InformationRegisters",
        "Reports",
        "Roles",
        "SettingsStorages",
        "Subsystems",
        "Tasks",
        "WebServices",
        "XDTOPackages",
    }
)
_METADATA_CATEGORY_KEYS = frozenset(item.lower() for item in _METADATA_CATEGORIES)

_MODULE_TYPE_MAP: dict[str, str] = {
    "CommandModule.bsl": "CommandModule",
    "ExternalConnectionModule.bsl": "ExternalConnectionModule",
    "ManagedApplicationModule.bsl": "ManagedApplicationModule",
    "ManagerModule.bsl": "ManagerModule",
    "Module.bsl": "Module",
    "ObjectModule.bsl": "ObjectModule",
    "OrdinaryApplicationModule.bsl": "OrdinaryApplicationModule",
    "RecordSetModule.bsl": "RecordSetModule",
    "SessionModule.bsl": "SessionModule",
    "ValueManagerModule.bsl": "ValueManagerModule",
}

_CATEGORY_ALIASES: dict[str, str] = {
    "accumulationregister": "accumulationregisters",
    "accountingregister": "accountingregisters",
    "businessprocess": "businessprocesses",
    "calculationregister": "calculationregisters",
    "catalog": "catalogs",
    "commoncommand": "commoncommands",
    "commonform": "commonforms",
    "commonmodule": "commonmodules",
    "constant": "constants",
    "dataprocessor": "dataprocessors",
    "document": "documents",
    "documentjournal": "documentjournals",
    "enum": "enums",
    "exchangeplan": "exchangeplans",
    "externaldatasource": "externaldatasources",
    "httpservice": "httpservices",
    "informationregister": "informationregisters",
    "report": "reports",
    "settingstorage": "settingsstorages",
    "subsystem": "subsystems",
    "task": "tasks",
    "webservice": "webservices",
    "xdtopackage": "xdtopackages",
    "бизнеспроцесс": "businessprocesses",
    "документ": "documents",
    "журналдокументов": "documentjournals",
    "задача": "tasks",
    "константа": "constants",
    "обработка": "dataprocessors",
    "общаякоманда": "commoncommands",
    "общаяформа": "commonforms",
    "общиймодуль": "commonmodules",
    "отчет": "reports",
    "перечисление": "enums",
    "планобмена": "exchangeplans",
    "плансчетов": "chartsofaccounts",
    "планвидоврасчета": "chartsofcalculationtypes",
    "планвидовхарактеристик": "chartsofcharacteristictypes",
    "регистринакопления": "accumulationregisters",
    "регистрнакопления": "accumulationregisters",
    "регистрбухгалтерии": "accountingregisters",
    "регистррасчета": "calculationregisters",
    "регистрсведений": "informationregisters",
    "роль": "roles",
    "справочник": "catalogs",
    "подсистема": "subsystems",
    "httpсервис": "httpservices",
    "webсервис": "webservices",
    "пакетxdto": "xdtopackages",
}

_META_TYPE_PREFIXES = (
    "AccumulationRegister.",
    "AccountingRegister.",
    "BusinessProcess.",
    "CalculationRegister.",
    "Catalog.",
    "CatalogObject.",
    "CatalogRef.",
    "CommonForm.",
    "Constant.",
    "DataProcessor.",
    "Document.",
    "DocumentObject.",
    "DocumentRef.",
    "Enum.",
    "ExchangePlan.",
    "InformationRegister.",
    "Report.",
    "Task.",
    "Документ.",
    "ДокументОбъект.",
    "ДокументСсылка.",
    "Обработка.",
    "ОбщаяФорма.",
    "Перечисление.",
    "ПланОбмена.",
    "РегистрБухгалтерии.",
    "РегистрНакопления.",
    "РегистрРасчета.",
    "РегистрСведений.",
    "Справочник.",
    "СправочникОбъект.",
    "СправочникСсылка.",
    "Отчет.",
    "БизнесПроцесс.",
    "Задача.",
    "Константа.",
)

_PROC_START_RE = re.compile(
    r"^\s*(Процедура|Функция)\s+([A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]*)\s*\((.*?)\)\s*(Экспорт)?\s*$",
    re.IGNORECASE,
)
_PROC_END_RE = re.compile(r"^\s*Конец(Процедуры|Функции)\s*;?\s*$", re.IGNORECASE)
_STRING_LITERAL_RE = re.compile(r'"(?:[^"]|"")*"')
_CALL_RE = re.compile(r"(?<![A-Za-zА-Яа-яЁё0-9_])([A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_\.]*)\s*\(")
_CALL_KEYWORDS = frozenset(
    {
        "если",
        "иначеесли",
        "для",
        "длякаждого",
        "пока",
        "попытка",
        "процедура",
        "функция",
        "конецпроцедуры",
        "конецфункции",
        "новый",
    }
)


@dataclass(frozen=True, slots=True)
class BslModuleInfo:
    """Discovered BSL module location."""

    relative_path: str
    category: str | None
    object_name: str | None
    module_type: str | None
    form_name: str | None = None
    command_name: str | None = None

    @property
    def is_form_module(self) -> bool:
        return self.form_name is not None

    def as_mapping(self) -> dict[str, object]:
        return {
            "path": self.relative_path,
            "category": self.category,
            "object_name": self.object_name,
            "module_type": self.module_type,
            "form_name": self.form_name,
            "command_name": self.command_name,
            "is_form_module": self.is_form_module,
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "BslModuleInfo":
        return cls(
            relative_path=str(payload["path"]),
            category=_optional_str(payload.get("category")),
            object_name=_optional_str(payload.get("object_name")),
            module_type=_optional_str(payload.get("module_type")),
            form_name=_optional_str(payload.get("form_name")),
            command_name=_optional_str(payload.get("command_name")),
        )


@dataclass(frozen=True, slots=True)
class BslProcedureInfo:
    """Parsed BSL procedure or function."""

    name: str
    proc_type: str
    line: int
    end_line: int
    is_export: bool
    params: str

    def as_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "type": self.proc_type,
            "line": self.line,
            "end_line": self.end_line,
            "is_export": self.is_export,
            "params": self.params,
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "BslProcedureInfo":
        return cls(
            name=str(payload["name"]),
            proc_type=str(payload["type"]),
            line=int(payload["line"]),
            end_line=int(payload["end_line"]),
            is_export=bool(payload.get("is_export", False)),
            params=str(payload.get("params", "")),
        )


@dataclass(frozen=True, slots=True)
class BslCallerInfo:
    """Indexed caller context for a specific BSL procedure name."""

    file: str
    caller_name: str
    caller_is_export: bool
    line: int
    object_name: str | None
    category: str | None
    module_type: str | None

    def as_mapping(self) -> dict[str, object]:
        return {
            "file": self.file,
            "caller_name": self.caller_name,
            "caller_is_export": self.caller_is_export,
            "line": self.line,
            "object_name": self.object_name,
            "category": self.category,
            "module_type": self.module_type,
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "BslCallerInfo":
        return cls(
            file=str(payload["file"]),
            caller_name=str(payload["caller_name"]),
            caller_is_export=bool(payload.get("caller_is_export", False)),
            line=int(payload["line"]),
            object_name=_optional_str(payload.get("object_name")),
            category=_optional_str(payload.get("category")),
            module_type=_optional_str(payload.get("module_type")),
        )


@dataclass(frozen=True, slots=True)
class BslIndexSnapshot:
    """Persisted read-model used for indexed helper acceleration."""

    modules: tuple[BslModuleInfo, ...]
    procedures_by_path: dict[str, tuple[BslProcedureInfo, ...]]
    callers_by_name: dict[str, tuple[BslCallerInfo, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "modules", tuple(self.modules))
        object.__setattr__(
            self,
            "procedures_by_path",
            {path: tuple(items) for path, items in self.procedures_by_path.items()},
        )
        object.__setattr__(
            self,
            "callers_by_name",
            {name: tuple(items) for name, items in self.callers_by_name.items()},
        )

    @property
    def module_count(self) -> int:
        return len(self.modules)

    @property
    def procedure_count(self) -> int:
        return sum(len(items) for items in self.procedures_by_path.values())

    @property
    def call_count(self) -> int:
        return sum(len(items) for items in self.callers_by_name.values())

    def to_payload(self) -> dict[str, object]:
        return {
            "modules": [item.as_mapping() for item in self.modules],
            "procedures_by_path": {
                path: [item.as_mapping() for item in items]
                for path, items in sorted(self.procedures_by_path.items())
            },
            "callers_by_name": {
                name: [item.as_mapping() for item in items]
                for name, items in sorted(self.callers_by_name.items())
            },
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BslIndexSnapshot":
        procedures_by_path = {
            str(path): tuple(BslProcedureInfo.from_mapping(item) for item in items)
            for path, items in dict(payload.get("procedures_by_path", {})).items()
        }
        callers_by_name = {
            str(name): tuple(BslCallerInfo.from_mapping(item) for item in items)
            for name, items in dict(payload.get("callers_by_name", {})).items()
        }
        return cls(
            modules=tuple(BslModuleInfo.from_mapping(item) for item in list(payload.get("modules", []))),
            procedures_by_path=procedures_by_path,
            callers_by_name=callers_by_name,
        )


def resolve_workspace_path(base_path: str | Path, path: str) -> Path:
    """Resolve a workspace-relative path and forbid escaping the workspace root."""

    base = Path(base_path).expanduser().resolve()
    candidate = (base / path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise PermissionError(f"Access denied: path '{path}' escapes workspace root") from exc
    return candidate


def iter_bsl_files(base_path: str | Path) -> list[str]:
    """Return all BSL files under a workspace as sorted POSIX-relative paths."""

    base = Path(base_path).expanduser().resolve()
    results: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS and not name.startswith(".")]
        for filename in filenames:
            if filename.startswith(".") or not filename.endswith(".bsl"):
                continue
            file_path = Path(dirpath, filename)
            results.append(file_path.relative_to(base).as_posix())
    return sorted(results)


def normalize_category(category: str) -> str:
    """Normalize category aliases used by helper calls."""

    key = category.lower().replace(" ", "").replace("_", "")
    resolved = _CATEGORY_ALIASES.get(key)
    if resolved is not None:
        return resolved
    if not key.endswith("s"):
        candidate = key + "s"
        if candidate in _METADATA_CATEGORY_KEYS:
            return candidate
    return key


def strip_meta_prefix(name: str) -> str:
    """Strip common metadata prefixes from names passed by the model."""

    for prefix in _META_TYPE_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def normalize_proc_name(name: str) -> str:
    """Normalize a procedure name or qualified reference for lookups."""

    cleaned = strip_meta_prefix(name.strip())
    if "." in cleaned:
        cleaned = cleaned.rsplit(".", 1)[-1]
    return cleaned.lower()


def parse_bsl_path(relative_path: str) -> BslModuleInfo:
    """Infer BSL module metadata from a repository-relative path."""

    parts = relative_path.split("/")
    category: str | None = None
    object_name: str | None = None
    form_name: str | None = None
    command_name: str | None = None

    for index, part in enumerate(parts):
        if part in _METADATA_CATEGORIES:
            category = part
            if index + 1 < len(parts) - 1:
                object_name = parts[index + 1]
            break

    if "Forms" in parts:
        forms_index = parts.index("Forms")
        if forms_index + 1 < len(parts):
            form_name = parts[forms_index + 1].removesuffix(".bsl")

    if "Commands" in parts:
        commands_index = parts.index("Commands")
        if commands_index + 1 < len(parts):
            command_name = parts[commands_index + 1].removesuffix(".bsl")

    filename = parts[-1]
    module_type = _MODULE_TYPE_MAP.get(filename)
    if form_name is not None and filename == "Module.bsl":
        module_type = "FormModule"
    elif command_name is not None and filename == "Module.bsl":
        module_type = "CommandModule"

    return BslModuleInfo(
        relative_path=relative_path,
        category=category,
        object_name=object_name,
        module_type=module_type,
        form_name=form_name,
        command_name=command_name,
    )


def parse_procedures_from_text(content: str) -> tuple[list[str], list[BslProcedureInfo]]:
    """Parse procedures and functions from BSL source text."""

    lines = content.splitlines()
    procedures: list[BslProcedureInfo] = []
    current: dict[str, object] | None = None

    for line_index, line in enumerate(lines, start=1):
        if current is None:
            match = _PROC_START_RE.match(line)
            if match:
                current = {
                    "name": match.group(2),
                    "type": match.group(1),
                    "line": line_index,
                    "end_line": None,
                    "is_export": bool(match.group(4)),
                    "params": (match.group(3) or "").strip(),
                }
            continue

        if _PROC_END_RE.match(line):
            current["end_line"] = line_index
            procedures.append(
                BslProcedureInfo(
                    name=str(current["name"]),
                    proc_type=str(current["type"]),
                    line=int(current["line"]),
                    end_line=int(current["end_line"]),
                    is_export=bool(current["is_export"]),
                    params=str(current["params"]),
                )
            )
            current = None

    if current is not None:
        procedures.append(
            BslProcedureInfo(
                name=str(current["name"]),
                proc_type=str(current["type"]),
                line=int(current["line"]),
                end_line=len(lines),
                is_export=bool(current["is_export"]),
                params=str(current["params"]),
            )
        )

    return lines, procedures


def build_bsl_index_snapshot(base_path: str | Path) -> BslIndexSnapshot:
    """Build a minimal indexed snapshot for BSL helper acceleration."""

    base = Path(base_path).expanduser().resolve()
    modules: list[BslModuleInfo] = []
    procedures_by_path: dict[str, tuple[BslProcedureInfo, ...]] = {}
    callers_by_name: dict[str, list[BslCallerInfo]] = {}

    for relative_path in iter_bsl_files(base):
        module = parse_bsl_path(relative_path)
        modules.append(module)

        file_path = resolve_workspace_path(base, relative_path)
        content = file_path.read_text(encoding="utf-8-sig", errors="replace")
        lines, procedures = parse_procedures_from_text(content)
        procedures_by_path[relative_path] = tuple(procedures)

        for procedure in procedures:
            for line_number in range(procedure.line + 1, procedure.end_line):
                line = lines[line_number - 1]
                callees = _extract_call_names(line)
                if not callees:
                    continue
                for callee_name in callees:
                    callers_by_name.setdefault(callee_name, []).append(
                        BslCallerInfo(
                            file=relative_path,
                            caller_name=procedure.name,
                            caller_is_export=procedure.is_export,
                            line=line_number,
                            object_name=module.object_name,
                            category=module.category,
                            module_type=module.module_type,
                        )
                    )

    normalized_callers = {
        name: tuple(sorted(items, key=lambda item: (item.file, item.line, item.caller_name)))
        for name, items in callers_by_name.items()
    }
    return BslIndexSnapshot(
        modules=tuple(sorted(modules, key=lambda item: item.relative_path)),
        procedures_by_path=procedures_by_path,
        callers_by_name=normalized_callers,
    )


def make_bsl_live_helpers(
    base_path: str | Path,
    *,
    index_snapshot: BslIndexSnapshot | None = None,
) -> dict[str, Callable[..., object]]:
    """Build BSL helpers with optional prebuilt indexed acceleration."""

    base = Path(base_path).expanduser().resolve()
    module_index: list[BslModuleInfo] | None = list(index_snapshot.modules) if index_snapshot is not None else None
    procedure_cache: dict[str, tuple[str, list[str], list[dict[str, object]]]] = {}
    callers_cache: dict[str, list[dict[str, object]]] = {}

    def ensure_modules() -> list[BslModuleInfo]:
        nonlocal module_index
        if module_index is None:
            module_index = [parse_bsl_path(path) for path in iter_bsl_files(base)]
        return module_index

    def parse_procedures(path: str) -> tuple[str, list[str], list[dict[str, object]]]:
        cached = procedure_cache.get(path)
        if cached is not None:
            return cached

        target = resolve_workspace_path(base, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        content = target.read_text(encoding="utf-8-sig", errors="replace")
        lines = content.splitlines()
        indexed_procedures = None if index_snapshot is None else index_snapshot.procedures_by_path.get(path)
        if indexed_procedures is None:
            _parsed_lines, procedures = parse_procedures_from_text(content)
            procedure_payload = [item.as_mapping() for item in procedures]
        else:
            procedure_payload = [item.as_mapping() for item in indexed_procedures]

        cached = (content, lines, procedure_payload)
        procedure_cache[path] = cached
        return cached

    def scan_callers(name: str) -> list[dict[str, object]]:
        normalized_name = normalize_proc_name(name)
        cached = callers_cache.get(normalized_name)
        if cached is not None:
            return cached

        indexed_callers = None if index_snapshot is None else index_snapshot.callers_by_name.get(normalized_name)
        if indexed_callers is not None:
            results = [item.as_mapping() for item in indexed_callers]
            callers_cache[normalized_name] = results
            return results

        results: list[dict[str, object]] = []
        module_by_path = {item.relative_path: item for item in ensure_modules()}
        for relative_path in sorted(module_by_path):
            module = module_by_path[relative_path]
            _content, lines, procedures = parse_procedures(relative_path)
            for procedure in procedures:
                start_line = int(procedure["line"]) + 1
                end_line = int(procedure["end_line"])
                for line_number in range(start_line, end_line):
                    if normalized_name not in _extract_call_names(lines[line_number - 1]):
                        continue
                    results.append(
                        {
                            "file": relative_path,
                            "caller_name": str(procedure["name"]),
                            "caller_is_export": bool(procedure["is_export"]),
                            "line": line_number,
                            "object_name": module.object_name,
                            "category": module.category,
                            "module_type": module.module_type,
                        }
                    )

        ordered_results = sorted(results, key=lambda item: (str(item["file"]), int(item["line"]), str(item["caller_name"])))
        callers_cache[normalized_name] = ordered_results
        return ordered_results

    def bsl_find_modules(name: str, *, category: str = "", limit: int = 50) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        needle = strip_meta_prefix(name.strip()).lower()
        if not needle:
            raise ValueError("name must not be empty")

        normalized_category = normalize_category(category) if category else ""
        results: list[dict[str, object]] = []
        for item in ensure_modules():
            if normalized_category and (item.category or "").lower() != normalized_category:
                continue
            haystacks = (
                item.relative_path.lower(),
                (item.object_name or "").lower(),
                (item.form_name or "").lower(),
                (item.command_name or "").lower(),
            )
            if any(needle in haystack for haystack in haystacks):
                results.append(item.as_mapping())
                if len(results) >= limit:
                    break
        return results

    def bsl_find_by_type(category: str, *, name: str = "", limit: int = 50) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        normalized_category = normalize_category(category)
        needle = strip_meta_prefix(name.strip()).lower()
        results: list[dict[str, object]] = []
        for item in ensure_modules():
            if (item.category or "").lower() != normalized_category:
                continue
            if needle and needle not in (item.object_name or "").lower():
                continue
            results.append(item.as_mapping())
            if len(results) >= limit:
                break
        return results

    def bsl_extract_procedures(path: str) -> list[dict[str, object]]:
        _content, _lines, procedures = parse_procedures(path)
        return [dict(item) for item in procedures]

    def bsl_read_procedure(path: str, name: str) -> str | None:
        _content, lines, procedures = parse_procedures(path)
        needle = normalize_proc_name(name)
        if not needle:
            raise ValueError("name must not be empty")

        for procedure in procedures:
            if normalize_proc_name(str(procedure["name"])) != needle:
                continue
            start = int(procedure["line"]) - 1
            end = int(procedure["end_line"])
            return "\n".join(lines[start:end])
        return None

    def bsl_find_callers(
        name: str,
        *,
        module_hint: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, object]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        needle = normalize_proc_name(name)
        if not needle:
            raise ValueError("name must not be empty")

        hint = strip_meta_prefix(module_hint.strip()).lower()
        callers = scan_callers(needle)
        if hint:
            callers = [
                item
                for item in callers
                if hint in (str(item.get("object_name") or "").lower()) or hint in str(item.get("file") or "").lower()
            ]
        total_callers = len(callers)
        page = callers[offset : offset + limit]
        return {
            "callers": [dict(item) for item in page],
            "_meta": {
                "total_callers": total_callers,
                "returned": len(page),
                "offset": offset,
                "has_more": (offset + limit) < total_callers,
            },
        }

    return {
        "bsl_extract_procedures": bsl_extract_procedures,
        "bsl_find_by_type": bsl_find_by_type,
        "bsl_find_callers": bsl_find_callers,
        "bsl_find_modules": bsl_find_modules,
        "bsl_read_procedure": bsl_read_procedure,
    }


def _extract_call_names(line: str) -> set[str]:
    sanitized = _STRING_LITERAL_RE.sub('""', line)
    sanitized = sanitized.split("//", 1)[0]
    results: set[str] = set()
    for match in _CALL_RE.finditer(sanitized):
        candidate = match.group(1)
        normalized = normalize_proc_name(candidate)
        if not normalized or normalized in _CALL_KEYWORDS:
            continue
        results.add(normalized)
    return results


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
