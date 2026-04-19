"""Live filesystem-based helper set for BSL repository exploration."""

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


@dataclass(frozen=True, slots=True)
class BslModuleInfo:
    """Live-discovered BSL module location."""

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


def make_bsl_live_helpers(base_path: str | Path) -> dict[str, Callable[..., object]]:
    """Build a lightweight live-analysis helper set for BSL repositories."""

    base = Path(base_path).expanduser().resolve()
    module_index: list[BslModuleInfo] | None = None
    procedure_cache: dict[str, tuple[str, list[str], list[dict[str, object]]]] = {}

    def resolve_safe(path: str) -> Path:
        candidate = (base / path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise PermissionError(f"Access denied: path '{path}' escapes workspace root") from exc
        return candidate

    def iter_bsl_files() -> list[str]:
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
        key = category.lower().replace(" ", "").replace("_", "")
        resolved = _CATEGORY_ALIASES.get(key)
        if resolved is not None:
            return resolved
        if not key.endswith("s"):
            candidate = key + "s"
            if candidate in {item.lower() for item in _METADATA_CATEGORIES}:
                return candidate
        return key

    def strip_meta_prefix(name: str) -> str:
        for prefix in _META_TYPE_PREFIXES:
            if name.startswith(prefix):
                return name[len(prefix) :]
        return name

    def parse_bsl_path(relative_path: str) -> BslModuleInfo:
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

    def ensure_index() -> list[BslModuleInfo]:
        nonlocal module_index
        if module_index is None:
            module_index = [parse_bsl_path(path) for path in iter_bsl_files()]
        return module_index

    def parse_procedures(path: str) -> tuple[str, list[str], list[dict[str, object]]]:
        cached = procedure_cache.get(path)
        if cached is not None:
            return cached

        target = resolve_safe(path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        content = target.read_text(encoding="utf-8-sig", errors="replace")
        lines = content.splitlines()
        procedures: list[dict[str, object]] = []
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
                procedures.append(current)
                current = None

        if current is not None:
            current["end_line"] = len(lines)
            procedures.append(current)

        cached = (content, lines, procedures)
        procedure_cache[path] = cached
        return cached

    def bsl_find_modules(name: str, *, category: str = "", limit: int = 50) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        needle = strip_meta_prefix(name.strip()).lower()
        if not needle:
            raise ValueError("name must not be empty")

        normalized_category = normalize_category(category) if category else ""
        results: list[dict[str, object]] = []
        for item in ensure_index():
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
        for item in ensure_index():
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
        needle = name.strip().lower()
        if not needle:
            raise ValueError("name must not be empty")

        for procedure in procedures:
            if str(procedure["name"]).lower() != needle:
                continue
            start = int(procedure["line"]) - 1
            end = int(procedure["end_line"])
            return "\n".join(lines[start:end])
        return None

    return {
        "bsl_extract_procedures": bsl_extract_procedures,
        "bsl_find_by_type": bsl_find_by_type,
        "bsl_find_modules": bsl_find_modules,
        "bsl_read_procedure": bsl_read_procedure,
    }
