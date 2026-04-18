"""Workspace resolution abstractions for direct-path and registry-backed execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Protocol, Sequence


class WorkspaceSource(StrEnum):
    """Source of workspace resolution."""

    DIRECT_PATH = "direct_path"
    REGISTRY = "registry"


class WorkspaceResolutionError(ValueError):
    """Raised when a workspace cannot be resolved."""


class DuplicateWorkspaceError(ValueError):
    """Raised when the registry already contains a workspace identifier."""


@dataclass(frozen=True, slots=True)
class WorkspaceRef:
    """Canonical workspace reference shared by direct-path and registry-backed flows."""

    root_path: Path
    source: WorkspaceSource
    workspace_id: str | None = None
    display_name: str | None = None
    adapter_hint: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        resolved_path = Path(self.root_path).expanduser().resolve()
        normalized_metadata = dict(self.metadata)
        object.__setattr__(self, "root_path", resolved_path)
        object.__setattr__(self, "metadata", normalized_metadata)

        if self.source is WorkspaceSource.REGISTRY and not self.workspace_id:
            raise WorkspaceResolutionError("Registry-backed workspaces must define workspace_id")

        if self.source is WorkspaceSource.DIRECT_PATH and self.workspace_id is not None:
            raise WorkspaceResolutionError("Direct-path workspaces must not define workspace_id")


class WorkspaceRegistry(Protocol):
    """Core-owned registry abstraction used by runtime and lifecycle services."""

    def list_workspaces(self) -> Sequence[WorkspaceRef]:
        """Return all registered workspaces."""

    def get(self, workspace_id: str) -> WorkspaceRef | None:
        """Return a registered workspace by identifier."""

    def resolve(
        self,
        *,
        workspace_id: str | None = None,
        root_path: str | Path | None = None,
        display_name: str | None = None,
        adapter_hint: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> WorkspaceRef:
        """Resolve either a registered workspace or a direct-path workspace."""


class InMemoryWorkspaceRegistry:
    """Simple registry implementation used for tests and early runtime wiring."""

    def __init__(self) -> None:
        self._workspaces: dict[str, WorkspaceRef] = {}

    def list_workspaces(self) -> Sequence[WorkspaceRef]:
        return tuple(self._workspaces.values())

    def get(self, workspace_id: str) -> WorkspaceRef | None:
        return self._workspaces.get(workspace_id)

    def register(
        self,
        workspace_id: str,
        root_path: str | Path,
        *,
        display_name: str | None = None,
        adapter_hint: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> WorkspaceRef:
        if workspace_id in self._workspaces:
            raise DuplicateWorkspaceError(f"Workspace already exists: {workspace_id}")

        workspace = WorkspaceRef(
            root_path=Path(root_path),
            source=WorkspaceSource.REGISTRY,
            workspace_id=workspace_id,
            display_name=display_name,
            adapter_hint=adapter_hint,
            metadata=metadata or {},
        )
        self._workspaces[workspace_id] = workspace
        return workspace

    def remove(self, workspace_id: str) -> WorkspaceRef:
        try:
            return self._workspaces.pop(workspace_id)
        except KeyError as exc:
            raise WorkspaceResolutionError(f"Unknown workspace: {workspace_id}") from exc

    def resolve(
        self,
        *,
        workspace_id: str | None = None,
        root_path: str | Path | None = None,
        display_name: str | None = None,
        adapter_hint: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> WorkspaceRef:
        if (workspace_id is None) == (root_path is None):
            raise WorkspaceResolutionError("Provide exactly one of workspace_id or root_path")

        if workspace_id is not None:
            workspace = self.get(workspace_id)
            if workspace is None:
                raise WorkspaceResolutionError(f"Unknown workspace: {workspace_id}")
            return workspace

        return WorkspaceRef(
            root_path=Path(root_path),
            source=WorkspaceSource.DIRECT_PATH,
            display_name=display_name,
            adapter_hint=adapter_hint,
            metadata=metadata or {},
        )
