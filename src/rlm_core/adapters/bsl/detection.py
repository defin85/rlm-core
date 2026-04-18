"""Detection helpers for BSL repositories."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .contracts import BslConfigRole, BslRepositoryDetails, BslSourceFormat

_CF_NAMESPACE = "http://v8.1c.ru/8.3/MDClasses"


def inspect_bsl_workspace(workspace_root: Path) -> BslRepositoryDetails | None:
    """Detect a BSL workspace and return adapter-owned repository details."""
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


def _inspect_candidate(workspace_root: Path, candidate: Path) -> BslRepositoryDetails | None:
    config_xml = candidate / "Configuration.xml"
    if config_xml.is_file():
        return _parse_cf_configuration(workspace_root, candidate, config_xml)

    config_mdo = candidate / "Configuration" / "Configuration.mdo"
    if config_mdo.is_file():
        return _parse_edt_configuration(workspace_root, candidate, config_mdo)
    return None


def _parse_cf_configuration(workspace_root: Path, config_root: Path, config_file: Path) -> BslRepositoryDetails | None:
    try:
        tree = ET.parse(config_file)
    except (ET.ParseError, OSError):
        return None

    ns = {"md": _CF_NAMESPACE}
    root = tree.getroot()
    configuration = root.find("md:Configuration", ns)
    if configuration is None:
        return None
    properties = configuration.find("md:Properties", ns)
    if properties is None:
        return None

    config_name = _find_text(properties, "Name", ns)
    extension_prefix = _find_text(properties, "NamePrefix", ns)
    extension_purpose = _find_text(properties, "ConfigurationExtensionPurpose", ns)

    return BslRepositoryDetails(
        source_format=BslSourceFormat.CF,
        config_role=BslConfigRole.EXTENSION if extension_purpose else BslConfigRole.MAIN,
        config_root=_relative_path(config_root, workspace_root),
        config_file=_relative_path(config_file, workspace_root),
        config_name=config_name or None,
        extension_prefix=extension_prefix or None,
        extension_purpose=extension_purpose or None,
    )


def _parse_edt_configuration(workspace_root: Path, config_root: Path, config_file: Path) -> BslRepositoryDetails | None:
    try:
        tree = ET.parse(config_file)
    except (ET.ParseError, OSError):
        return None

    root = tree.getroot()
    config_name = _direct_child_text(root, "name")
    extension_prefix = _direct_child_text(root, "namePrefix")
    extension_purpose = _direct_child_text(root, "configurationExtensionPurpose")
    has_extension_element = any(_local_name(child.tag) == "extension" for child in root)

    return BslRepositoryDetails(
        source_format=BslSourceFormat.EDT,
        config_role=BslConfigRole.EXTENSION if extension_purpose or has_extension_element else BslConfigRole.MAIN,
        config_root=_relative_path(config_root, workspace_root),
        config_file=_relative_path(config_file, workspace_root),
        config_name=config_name or None,
        extension_prefix=extension_prefix or None,
        extension_purpose=extension_purpose or None,
    )


def _find_text(parent: ET.Element, local_name: str, ns: dict[str, str]) -> str:
    node = parent.find(f"md:{local_name}", ns)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _direct_child_text(parent: ET.Element, local_name: str) -> str:
    for child in parent:
        if _local_name(child.tag) == local_name and child.text:
            return child.text.strip()
    return ""


def _local_name(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _relative_path(path: Path, workspace_root: Path) -> str:
    relative = path.relative_to(workspace_root)
    if relative == Path("."):
        return "."
    return relative.as_posix()
