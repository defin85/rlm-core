"""Adapter SPI definitions for language-specific repository integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Protocol

from rlm_core.index.contracts import AdapterIndexHooks, IndexCapabilityMatrix
from rlm_core.workspace import WorkspaceRef

HelperMap = Mapping[str, Callable[..., object]]


@dataclass(frozen=True, slots=True)
class RepositoryDescriptor:
    """Language-aware description returned after adapter detection."""

    adapter_id: str
    workspace_root: Path
    language: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", Path(self.workspace_root).expanduser().resolve())
        object.__setattr__(self, "details", dict(self.details))


@dataclass(frozen=True, slots=True)
class HelperContext:
    """Context passed to adapter helper registration."""

    workspace: WorkspaceRef
    descriptor: RepositoryDescriptor


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Context passed to adapter strategy generation."""

    workspace: WorkspaceRef
    descriptor: RepositoryDescriptor
    capabilities: IndexCapabilityMatrix


class RepositoryAdapter(Protocol):
    """Shared SPI implemented by every language adapter."""

    adapter_id: str
    display_name: str
    capabilities: IndexCapabilityMatrix

    def detect(self, workspace: WorkspaceRef) -> bool:
        """Return True when this adapter should handle the workspace."""

    def describe_repo(self, workspace: WorkspaceRef) -> RepositoryDescriptor:
        """Return adapter-specific description of the workspace."""

    def register_helpers(self, context: HelperContext) -> HelperMap:
        """Register adapter-specific sandbox helpers for the workspace."""

    def build_strategy(self, query: str, context: StrategyContext) -> str:
        """Return adapter-specific exploration or prompting guidance."""

    def get_index_hooks(self) -> AdapterIndexHooks | None:
        """Return lifecycle hooks for adapter-owned prebuilt indexes."""
