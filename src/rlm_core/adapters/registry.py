"""Runtime-owned adapter registration and selection."""

from __future__ import annotations

from typing import Iterable

from rlm_core.adapters.contracts import RepositoryAdapter
from rlm_core.workspace import WorkspaceRef


class AdapterSelectionError(RuntimeError):
    """Raised when adapter selection is impossible or ambiguous."""


class AdapterRegistry:
    """Runtime-owned registry for adapter discovery and selection."""

    def __init__(self, adapters: Iterable[RepositoryAdapter] = ()) -> None:
        self._adapters: dict[str, RepositoryAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: RepositoryAdapter) -> None:
        if adapter.adapter_id in self._adapters:
            raise AdapterSelectionError(f"Adapter already registered: {adapter.adapter_id}")
        self._adapters[adapter.adapter_id] = adapter

    def get(self, adapter_id: str) -> RepositoryAdapter | None:
        return self._adapters.get(adapter_id)

    def list(self) -> tuple[RepositoryAdapter, ...]:
        return tuple(self._adapters.values())

    def matching(self, workspace: WorkspaceRef) -> tuple[RepositoryAdapter, ...]:
        return tuple(adapter for adapter in self._adapters.values() if adapter.detect(workspace))

    def select(self, workspace: WorkspaceRef, *, adapter_id: str | None = None) -> RepositoryAdapter:
        if adapter_id is not None:
            adapter = self.get(adapter_id)
            if adapter is None:
                raise AdapterSelectionError(f"Unknown adapter: {adapter_id}")
            if not adapter.detect(workspace):
                raise AdapterSelectionError(f"Adapter {adapter_id} does not match workspace {workspace.root_path}")
            return adapter

        matches = self.matching(workspace)
        if not matches:
            raise AdapterSelectionError(f"No adapter matched workspace {workspace.root_path}")
        if len(matches) > 1:
            adapter_ids = ", ".join(adapter.adapter_id for adapter in matches)
            raise AdapterSelectionError(f"Multiple adapters matched workspace {workspace.root_path}: {adapter_ids}")
        return matches[0]
