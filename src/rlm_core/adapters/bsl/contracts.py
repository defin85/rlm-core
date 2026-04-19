"""BSL-specific repository and index extension contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BslSourceFormat(StrEnum):
    """Supported 1C source layouts."""

    CF = "cf"
    EDT = "edt"


class BslConfigRole(StrEnum):
    """Role of the detected 1C configuration."""

    MAIN = "main"
    EXTENSION = "extension"


class BslIndexedFeature(StrEnum):
    """BSL-specific indexed features owned by the adapter."""

    METADATA = "metadata"
    CALLER_GRAPH = "caller_graph"
    OBJECT_ATTRIBUTES = "object_attributes"
    PREDEFINED_ITEMS = "predefined_items"


BSL_ADVANCED_FEATURES = frozenset(
    {
        BslIndexedFeature.OBJECT_ATTRIBUTES.value,
        BslIndexedFeature.PREDEFINED_ITEMS.value,
    }
)
BSL_SCHEMA_EXTENSIONS = frozenset(
    {
        BslIndexedFeature.METADATA.value,
        BslIndexedFeature.CALLER_GRAPH.value,
        *BSL_ADVANCED_FEATURES,
    }
)
BSL_INDEXED_FEATURES = frozenset(
    {
        BslIndexedFeature.METADATA.value,
        BslIndexedFeature.CALLER_GRAPH.value,
        *BSL_ADVANCED_FEATURES,
    }
)


@dataclass(frozen=True, slots=True)
class BslRepositoryDetails:
    """Adapter-owned repository details for 1C/BSL workspaces."""

    source_format: BslSourceFormat
    config_role: BslConfigRole
    config_root: str = "."
    config_file: str = ""
    config_name: str | None = None
    extension_prefix: str | None = None
    extension_purpose: str | None = None

    def as_mapping(self) -> dict[str, object]:
        """Return a serializable mapping stored in the generic descriptor."""
        details: dict[str, object] = {
            "source_format": self.source_format.value,
            "config_role": self.config_role.value,
            "config_root": self.config_root,
            "config_file": self.config_file,
        }
        if self.config_name:
            details["config_name"] = self.config_name
        if self.extension_prefix:
            details["extension_prefix"] = self.extension_prefix
        if self.extension_purpose:
            details["extension_purpose"] = self.extension_purpose
        return details
