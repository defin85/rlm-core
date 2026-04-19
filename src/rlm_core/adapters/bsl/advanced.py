"""Adapter-owned advanced BSL metadata extension layer."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .contracts import BSL_ADVANCED_FEATURES
from .live import normalize_category, strip_meta_prefix

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

_ATTRIBUTE_CATEGORIES = frozenset(
    {
        "AccumulationRegisters",
        "CalculationRegisters",
        "Catalogs",
        "ChartsOfAccounts",
        "ChartsOfCalculationTypes",
        "ChartsOfCharacteristicTypes",
        "Documents",
        "InformationRegisters",
    }
)
_PREDEFINED_CATEGORIES = frozenset(
    {
        "Catalogs",
        "ChartsOfAccounts",
        "ChartsOfCalculationTypes",
        "ChartsOfCharacteristicTypes",
    }
)
_CF_NS_URI = "http://v8.1c.ru/8.3/MDClasses"
_MDO_NS_URI = "http://g5.1c.ru/v8/dt/metadata/mdclass"
_XS_TYPE_MAP = {
    "xs:string": "String",
    "xs:decimal": "Number",
    "xs:boolean": "Boolean",
    "xs:dateTime": "DateTime",
    "xs:base64Binary": "ValueStorage",
}


@dataclass(frozen=True, slots=True)
class BslAttributeRecord:
    """Adapter-owned advanced metadata record for object attributes."""

    object_name: str
    category: str
    attr_name: str
    attr_synonym: str
    attr_type: tuple[str, ...]
    attr_kind: str
    ts_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attr_type", tuple(self.attr_type))

    def as_mapping(self) -> dict[str, object]:
        return {
            "object_name": self.object_name,
            "category": self.category,
            "attr_name": self.attr_name,
            "attr_synonym": self.attr_synonym,
            "attr_type": list(self.attr_type),
            "attr_kind": self.attr_kind,
            "ts_name": self.ts_name,
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "BslAttributeRecord":
        return cls(
            object_name=str(payload["object_name"]),
            category=str(payload["category"]),
            attr_name=str(payload["attr_name"]),
            attr_synonym=str(payload.get("attr_synonym", "")),
            attr_type=tuple(str(item) for item in list(payload.get("attr_type", []))),
            attr_kind=str(payload["attr_kind"]),
            ts_name=_optional_str(payload.get("ts_name")),
        )


@dataclass(frozen=True, slots=True)
class BslPredefinedItemRecord:
    """Adapter-owned advanced metadata record for predefined items."""

    object_name: str
    category: str
    item_name: str
    item_synonym: str
    item_code: str
    types: tuple[str, ...]
    is_folder: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "types", tuple(self.types))

    def as_mapping(self) -> dict[str, object]:
        return {
            "object_name": self.object_name,
            "category": self.category,
            "item_name": self.item_name,
            "item_synonym": self.item_synonym,
            "item_code": self.item_code,
            "types": list(self.types),
            "is_folder": self.is_folder,
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "BslPredefinedItemRecord":
        return cls(
            object_name=str(payload["object_name"]),
            category=str(payload["category"]),
            item_name=str(payload["item_name"]),
            item_synonym=str(payload.get("item_synonym", "")),
            item_code=str(payload.get("item_code", "")),
            types=tuple(str(item) for item in list(payload.get("types", []))),
            is_folder=bool(payload.get("is_folder", False)),
        )


@dataclass(frozen=True, slots=True)
class BslAdvancedSnapshot:
    """Persisted adapter-owned snapshot for advanced metadata helpers."""

    object_attributes: tuple[BslAttributeRecord, ...]
    predefined_items: tuple[BslPredefinedItemRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "object_attributes", tuple(self.object_attributes))
        object.__setattr__(self, "predefined_items", tuple(self.predefined_items))

    @property
    def object_attribute_count(self) -> int:
        return len(self.object_attributes)

    @property
    def predefined_item_count(self) -> int:
        return len(self.predefined_items)

    def to_payload(self) -> dict[str, object]:
        return {
            "object_attributes": [item.as_mapping() for item in self.object_attributes],
            "predefined_items": [item.as_mapping() for item in self.predefined_items],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BslAdvancedSnapshot":
        return cls(
            object_attributes=tuple(
                BslAttributeRecord.from_mapping(item) for item in list(payload.get("object_attributes", []))
            ),
            predefined_items=tuple(
                BslPredefinedItemRecord.from_mapping(item) for item in list(payload.get("predefined_items", []))
            ),
        )


class BslAdvancedExtension:
    """Adapter-owned extension layer for advanced metadata helpers."""

    feature_names = BSL_ADVANCED_FEATURES
    schema_extensions = BSL_ADVANCED_FEATURES

    def build_snapshot(self, base_path: str | Path) -> BslAdvancedSnapshot:
        return build_bsl_advanced_snapshot(base_path)

    def register_helpers(
        self,
        base_path: str | Path,
        *,
        snapshot: BslAdvancedSnapshot | None = None,
    ) -> dict[str, Callable[..., object]]:
        base = Path(base_path).expanduser().resolve()
        live_snapshot: BslAdvancedSnapshot | None = None

        def ensure_snapshot() -> BslAdvancedSnapshot:
            nonlocal live_snapshot
            if snapshot is not None:
                return snapshot
            if live_snapshot is None:
                live_snapshot = self.build_snapshot(base)
            return live_snapshot

        def bsl_advanced_features() -> list[str]:
            return sorted(self.feature_names)

        def bsl_find_attributes(
            *,
            name: str = "",
            object_name: str = "",
            category: str = "",
            kind: str = "",
            limit: int = 500,
        ) -> list[dict[str, object]]:
            if limit < 1:
                raise ValueError("limit must be >= 1")

            snapshot_data = ensure_snapshot()
            normalized_category = normalize_category(category) if category else ""
            normalized_kind = kind.strip().lower()
            normalized_name = name.strip().lower()
            object_category, object_value = _normalize_object_reference(object_name)

            results: list[dict[str, object]] = []
            for record in snapshot_data.object_attributes:
                if normalized_category and record.category.lower() != normalized_category:
                    continue
                if normalized_kind and record.attr_kind.lower() != normalized_kind:
                    continue
                if object_category and record.category.lower() != object_category:
                    continue
                if object_value and record.object_name.lower() != object_value:
                    continue
                if normalized_name:
                    haystacks = (record.attr_name.lower(), record.attr_synonym.lower())
                    if not any(normalized_name in haystack for haystack in haystacks):
                        continue
                results.append(record.as_mapping())
                if len(results) >= limit:
                    break
            return results

        def bsl_find_predefined(
            *,
            name: str = "",
            object_name: str = "",
            limit: int = 500,
        ) -> list[dict[str, object]]:
            if limit < 1:
                raise ValueError("limit must be >= 1")

            snapshot_data = ensure_snapshot()
            normalized_name = name.strip().lower()
            object_category, object_value = _normalize_object_reference(object_name)

            results: list[dict[str, object]] = []
            for record in snapshot_data.predefined_items:
                if object_category and record.category.lower() != object_category:
                    continue
                if object_value and record.object_name.lower() != object_value:
                    continue
                if normalized_name:
                    haystacks = (record.item_name.lower(), record.item_synonym.lower())
                    if not any(normalized_name in haystack for haystack in haystacks):
                        continue
                results.append(record.as_mapping())
                if len(results) >= limit:
                    break
            return results

        return {
            "bsl_advanced_features": bsl_advanced_features,
            "bsl_find_attributes": bsl_find_attributes,
            "bsl_find_predefined": bsl_find_predefined,
        }


def build_bsl_advanced_snapshot(base_path: str | Path) -> BslAdvancedSnapshot:
    """Build adapter-owned advanced metadata snapshot from 1C metadata files."""

    base = Path(base_path).expanduser().resolve()
    object_attributes: list[BslAttributeRecord] = []
    predefined_items: list[BslPredefinedItemRecord] = []

    for category, object_name, candidate in _iter_metadata_candidates(base):
        content = candidate.read_text(encoding="utf-8-sig", errors="replace")
        parsed = parse_metadata_xml(content)
        if parsed is None:
            continue
        object_attributes.extend(_attribute_records_from_parsed(parsed, category, object_name))
        if category in _PREDEFINED_CATEGORIES and candidate.suffix == ".mdo":
            items = parse_predefined_items(content) or []
            predefined_items.extend(_predefined_records_from_items(items, category, object_name))

    for category, object_name, candidate in _iter_predefined_candidates(base):
        content = candidate.read_text(encoding="utf-8-sig", errors="replace")
        items = parse_predefined_items(content) or []
        predefined_items.extend(_predefined_records_from_items(items, category, object_name))

    return BslAdvancedSnapshot(
        object_attributes=tuple(
            sorted(
                object_attributes,
                key=lambda item: (item.category, item.object_name, item.attr_kind, item.ts_name or "", item.attr_name),
            )
        ),
        predefined_items=tuple(
            sorted(predefined_items, key=lambda item: (item.category, item.object_name, item.item_name))
        ),
    )


def parse_metadata_xml(xml_content: str) -> dict[str, object] | None:
    """Parse a CF or EDT metadata object and extract advanced structural fields."""

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    if _is_mdo_root(root):
        return _parse_mdo_metadata(root)
    return _parse_cf_metadata(root)


def parse_predefined_items(xml_content: str) -> list[dict[str, object]] | None:
    """Parse predefined items from CF Predefined.xml or EDT .mdo metadata."""

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    if _is_mdo_root(root):
        return _parse_mdo_predefined(root)
    return _parse_cf_predefined(root)


def _attribute_records_from_parsed(
    parsed: dict[str, object],
    category: str,
    object_name: str,
) -> list[BslAttributeRecord]:
    results: list[BslAttributeRecord] = []
    for attr in list(parsed.get("attributes", [])):
        results.append(
            BslAttributeRecord(
                object_name=object_name,
                category=category,
                attr_name=str(attr.get("name", "")),
                attr_synonym=str(attr.get("synonym", "")),
                attr_type=tuple(normalize_type_list(attr.get("type", ""))),
                attr_kind="attribute",
            )
        )
    for dimension in list(parsed.get("dimensions", [])):
        results.append(
            BslAttributeRecord(
                object_name=object_name,
                category=category,
                attr_name=str(dimension.get("name", "")),
                attr_synonym=str(dimension.get("synonym", "")),
                attr_type=tuple(normalize_type_list(dimension.get("type", ""))),
                attr_kind="dimension",
            )
        )
    for resource in list(parsed.get("resources", [])):
        results.append(
            BslAttributeRecord(
                object_name=object_name,
                category=category,
                attr_name=str(resource.get("name", "")),
                attr_synonym=str(resource.get("synonym", "")),
                attr_type=tuple(normalize_type_list(resource.get("type", ""))),
                attr_kind="resource",
            )
        )
    for section in list(parsed.get("tabular_sections", [])):
        section_name = str(section.get("name", ""))
        for attr in list(section.get("attributes", [])):
            results.append(
                BslAttributeRecord(
                    object_name=object_name,
                    category=category,
                    attr_name=str(attr.get("name", "")),
                    attr_synonym=str(attr.get("synonym", "")),
                    attr_type=tuple(normalize_type_list(attr.get("type", ""))),
                    attr_kind="ts_attribute",
                    ts_name=section_name,
                )
            )
    return results


def _predefined_records_from_items(
    items: list[dict[str, object]],
    category: str,
    object_name: str,
) -> list[BslPredefinedItemRecord]:
    results: list[BslPredefinedItemRecord] = []
    for item in items:
        results.append(
            BslPredefinedItemRecord(
                object_name=object_name,
                category=category,
                item_name=str(item.get("name", "")),
                item_synonym=str(item.get("synonym", "")),
                item_code=str(item.get("code", "")),
                types=tuple(str(entry) for entry in list(item.get("types", []))),
                is_folder=bool(item.get("is_folder", False)),
            )
        )
    return results


def normalize_type_list(raw: str | list[str] | tuple[str, ...]) -> list[str]:
    """Normalize raw 1C type declarations into stable type names."""

    if isinstance(raw, (list, tuple)):
        parts = [str(item).strip() for item in raw if str(item).strip()]
    else:
        if not raw or not str(raw).strip():
            return []
        parts = [part.strip() for part in str(raw).split(",") if part.strip()]

    normalized: list[str] = []
    for part in parts:
        mapped = _XS_TYPE_MAP.get(part)
        if mapped is not None:
            normalized.append(mapped)
            continue
        if ":" in part:
            normalized.append(part.split(":", 1)[1])
            continue
        normalized.append(part)
    return normalized


def _iter_metadata_candidates(base: Path):
    for candidate in _iter_workspace_files(base):
        relative = candidate.relative_to(base)
        parts = relative.parts
        if len(parts) >= 4 and parts[0] in _ATTRIBUTE_CATEGORIES and parts[2] == "Ext" and candidate.suffix == ".xml":
            if candidate.name in {"Configuration.xml", "Predefined.xml"}:
                continue
            yield parts[0], parts[1], candidate
        elif len(parts) == 3 and parts[0] in _ATTRIBUTE_CATEGORIES and candidate.suffix == ".mdo":
            if candidate.stem != parts[1]:
                continue
            yield parts[0], parts[1], candidate


def _iter_predefined_candidates(base: Path):
    for candidate in _iter_workspace_files(base):
        relative = candidate.relative_to(base)
        parts = relative.parts
        if len(parts) >= 4 and parts[0] in _PREDEFINED_CATEGORIES and parts[2] == "Ext" and candidate.name == "Predefined.xml":
            yield parts[0], parts[1], candidate


def _iter_workspace_files(base: Path):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_DIRS and not name.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            candidate = Path(dirpath, filename)
            if candidate.suffix not in {".xml", ".mdo"}:
                continue
            yield candidate


def _parse_cf_metadata(root: ET.Element) -> dict[str, object] | None:
    meta_el = next((child for child in root if _find_direct_child(child, "Properties") is not None), None)
    if meta_el is None:
        return None

    props = _find_direct_child(meta_el, "Properties")
    assert props is not None
    search_root = _find_direct_child(meta_el, "ChildObjects")
    if search_root is None:
        search_root = meta_el

    result: dict[str, object] = {
        "object_type": _local_name(meta_el.tag),
        "name": _find_text(props, "Name"),
        "synonym": _cf_find_synonym(props),
        "attributes": _parse_cf_fields(search_root, "Attribute"),
        "dimensions": _parse_cf_fields(search_root, "Dimension"),
        "resources": _parse_cf_fields(search_root, "Resource"),
        "tabular_sections": [],
    }

    sections: list[dict[str, object]] = []
    for section_el in _find_children(search_root, "TabularSection"):
        section_props = _find_direct_child(section_el, "Properties")
        if section_props is None:
            continue
        section_root = _find_direct_child(section_el, "ChildObjects")
        if section_root is None:
            section_root = section_el
        sections.append(
            {
                "name": _find_text(section_props, "Name"),
                "synonym": _cf_find_synonym(section_props),
                "attributes": _parse_cf_fields(section_root, "Attribute"),
            }
        )
    result["tabular_sections"] = sections
    return result


def _parse_mdo_metadata(root: ET.Element) -> dict[str, object]:
    result: dict[str, object] = {
        "object_type": _local_name(root.tag),
        "name": _find_text(root, "name"),
        "synonym": _mdo_find_synonym(root),
        "attributes": _parse_mdo_fields(root, "attributes"),
        "dimensions": _parse_mdo_fields(root, "dimensions"),
        "resources": _parse_mdo_fields(root, "resources"),
        "tabular_sections": [],
    }

    sections: list[dict[str, object]] = []
    for section_el in _find_children(root, "tabularSections"):
        sections.append(
            {
                "name": _find_text(section_el, "name"),
                "synonym": _mdo_find_synonym(section_el),
                "attributes": _parse_mdo_fields(section_el, "attributes"),
            }
        )
    result["tabular_sections"] = sections
    return result


def _parse_cf_predefined(root: ET.Element) -> list[dict[str, object]] | None:
    predef_el = root if _local_name(root.tag) == "PredefinedData" else root.find(f".//{{{_CF_NS_URI}}}PredefinedData")
    if predef_el is None:
        predef_el = next((item for item in root.iter() if _local_name(item.tag) == "PredefinedData"), None)
    if predef_el is None:
        return None

    results: list[dict[str, object]] = []
    for item_el in _find_children(predef_el, "Item"):
        type_values = [child.text.strip() for child in item_el.iter() if _local_name(child.tag) == "Type" and child.text]
        results.append(
            {
                "name": _find_text(item_el, "Name"),
                "synonym": _find_text(item_el, "Description"),
                "code": _find_text(item_el, "Code"),
                "types": normalize_type_list(type_values),
                "is_folder": _find_text(item_el, "IsFolder").lower() == "true",
            }
        )
    return results or None


def _parse_mdo_predefined(root: ET.Element) -> list[dict[str, object]] | None:
    predef_el = _find_direct_child(root, "predefined")
    if predef_el is None:
        return None

    results: list[dict[str, object]] = []
    for item_el in _find_children(predef_el, "items"):
        type_values = [child.text.strip() for child in item_el.iter() if _local_name(child.tag) == "types" and child.text]
        results.append(
            {
                "name": _find_text(item_el, "name"),
                "synonym": _find_text(item_el, "description"),
                "code": _find_text(item_el, "code"),
                "types": normalize_type_list(type_values),
                "is_folder": _find_text(item_el, "isFolder").lower() == "true",
            }
        )
    return results or None


def _parse_cf_fields(parent: ET.Element, field_name: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for field_el in _find_children(parent, field_name):
        props = _find_direct_child(field_el, "Properties")
        if props is None:
            continue
        results.append(
            {
                "name": _find_text(props, "Name"),
                "synonym": _cf_find_synonym(props),
                "type": ", ".join(
                    child.text.strip() for child in props.iter() if _local_name(child.tag) == "Type" and child.text
                ),
            }
        )
    return results


def _parse_mdo_fields(parent: ET.Element, field_name: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for field_el in _find_children(parent, field_name):
        type_values = [child.text.strip() for child in field_el.iter() if _local_name(child.tag) == "types" and child.text]
        results.append(
            {
                "name": _find_text(field_el, "name"),
                "synonym": _mdo_find_synonym(field_el),
                "type": ", ".join(type_values),
            }
        )
    return results


def _cf_find_synonym(parent: ET.Element) -> str:
    synonym_el = _find_direct_child(parent, "Synonym")
    if synonym_el is None:
        return ""
    content_el = next((item for item in synonym_el.iter() if _local_name(item.tag) == "content" and item.text), None)
    return content_el.text.strip() if content_el is not None else ""


def _mdo_find_synonym(parent: ET.Element) -> str:
    synonym_el = _find_direct_child(parent, "synonym")
    if synonym_el is None:
        return ""
    value_el = _find_direct_child(synonym_el, "value")
    return value_el.text.strip() if value_el is not None and value_el.text else ""


def _normalize_object_reference(value: str) -> tuple[str, str]:
    cleaned = strip_meta_prefix(value.strip())
    if not cleaned:
        return "", ""
    if "/" in cleaned:
        category, object_name = cleaned.split("/", 1)
        return normalize_category(category), object_name.lower()
    return "", cleaned.lower()


def _find_children(parent: ET.Element, local_name: str) -> list[ET.Element]:
    return [child for child in parent if _local_name(child.tag) == local_name]


def _find_direct_child(parent: ET.Element, local_name: str) -> ET.Element | None:
    return next((child for child in parent if _local_name(child.tag) == local_name), None)


def _find_text(parent: ET.Element, local_name: str) -> str:
    child = _find_direct_child(parent, local_name)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _is_mdo_root(root: ET.Element) -> bool:
    if "}" not in root.tag:
        return False
    return root.tag.split("}")[0].lstrip("{") == _MDO_NS_URI


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
