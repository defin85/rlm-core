"""Lifecycle contracts used by core-owned index orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol

from rlm_core.workspace import WorkspaceRef


class IndexLifecycleAction(StrEnum):
    """Actions surfaced by core index orchestration."""

    BUILD = "build"
    UPDATE = "update"
    DROP = "drop"
    INFO = "info"
    CHECK = "check"


class IndexOperationStatus(StrEnum):
    """Common statuses for lifecycle results."""

    COMPLETED = "completed"
    STARTED = "started"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class IndexCapabilityMatrix:
    """Explicit capabilities exposed by an adapter to the core lifecycle layer."""

    supports_prebuilt_index: bool = False
    supports_incremental_update: bool = False
    supports_background_build: bool = False
    generic_only: bool = False
    adapter_features: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_features", frozenset(self.adapter_features))

    @property
    def supported_actions(self) -> frozenset[IndexLifecycleAction]:
        if not self.supports_prebuilt_index:
            return frozenset()

        actions = {
            IndexLifecycleAction.BUILD,
            IndexLifecycleAction.DROP,
            IndexLifecycleAction.INFO,
            IndexLifecycleAction.CHECK,
        }
        if self.supports_incremental_update:
            actions.add(IndexLifecycleAction.UPDATE)
        return frozenset(actions)

    def supports_action(self, action: IndexLifecycleAction) -> bool:
        return action in self.supported_actions

    def supports_feature(self, feature_name: str) -> bool:
        return feature_name in self.adapter_features


@dataclass(frozen=True, slots=True)
class IndexBuildRequest:
    """Lifecycle request passed from the core orchestrator to adapter hooks."""

    workspace: WorkspaceRef
    background: bool = False
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class IndexOperationResult:
    """Lifecycle result returned by adapter hooks."""

    action: IndexLifecycleAction
    status: IndexOperationStatus
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))


@dataclass(frozen=True, slots=True)
class IndexStatus:
    """Adapter-owned index status returned to the core lifecycle layer."""

    available: bool
    stale: bool | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))


class AdapterIndexHooks(Protocol):
    """Adapter-side lifecycle hooks called by core index orchestration."""

    def build_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        """Build a prebuilt index for a workspace."""

    def update_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        """Update an existing prebuilt index for a workspace."""

    def drop_index(self, workspace: WorkspaceRef) -> IndexOperationResult:
        """Drop a prebuilt index for a workspace."""

    def get_index_status(self, workspace: WorkspaceRef) -> IndexStatus:
        """Return availability and freshness details for a workspace index."""
