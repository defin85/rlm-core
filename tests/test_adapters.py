from __future__ import annotations

from dataclasses import dataclass

import pytest

from rlm_core.adapters import AdapterRegistry, AdapterSelectionError, HelperContext, RepositoryDescriptor, StrategyContext
from rlm_core.index.contracts import (
    IndexBuildRequest,
    IndexCapabilityMatrix,
    IndexLifecycleAction,
    IndexOperationResult,
    IndexOperationStatus,
    IndexStatus,
)
from rlm_core.workspace import WorkspaceRef, WorkspaceSource


class DummyIndexHooks:
    def build_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        return IndexOperationResult(
            action=IndexLifecycleAction.BUILD,
            status=IndexOperationStatus.COMPLETED,
            details={"workspace": str(request.workspace.root_path)},
        )

    def update_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        return IndexOperationResult(
            action=IndexLifecycleAction.UPDATE,
            status=IndexOperationStatus.COMPLETED,
            details={"workspace": str(request.workspace.root_path)},
        )

    def drop_index(self, workspace: WorkspaceRef) -> IndexOperationResult:
        return IndexOperationResult(
            action=IndexLifecycleAction.DROP,
            status=IndexOperationStatus.COMPLETED,
            details={"workspace": str(workspace.root_path)},
        )

    def get_index_status(self, workspace: WorkspaceRef) -> IndexStatus:
        return IndexStatus(available=True, stale=False, details={"workspace": str(workspace.root_path)})


@dataclass
class DummyAdapter:
    adapter_id: str
    matches: bool
    capabilities: IndexCapabilityMatrix
    display_name: str = "Dummy"

    def detect(self, workspace: WorkspaceRef) -> bool:
        return self.matches

    def describe_repo(self, workspace: WorkspaceRef) -> RepositoryDescriptor:
        return RepositoryDescriptor(
            adapter_id=self.adapter_id,
            workspace_root=workspace.root_path,
            language=self.adapter_id,
            details={"source": workspace.source.value},
        )

    def register_helpers(self, context: HelperContext):
        return {"ping": lambda: "pong"}

    def build_strategy(self, query: str, context: StrategyContext) -> str:
        return f"{self.adapter_id}:{query}"

    def get_index_hooks(self):
        return DummyIndexHooks() if self.capabilities.supports_prebuilt_index else None


def test_capabilities_report_supported_actions_and_features():
    capabilities = IndexCapabilityMatrix(
        supports_prebuilt_index=True,
        supports_incremental_update=True,
        supports_background_build=True,
        adapter_features={"forms", "overrides"},
    )

    assert capabilities.supports_action(IndexLifecycleAction.BUILD)
    assert capabilities.supports_action(IndexLifecycleAction.UPDATE)
    assert capabilities.supports_action(IndexLifecycleAction.INFO)
    assert capabilities.supports_feature("forms")
    assert not capabilities.supports_feature("missing")


def test_adapter_registry_selects_matching_adapter(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    registry = AdapterRegistry(
        [
            DummyAdapter("bsl", matches=True, capabilities=IndexCapabilityMatrix()),
            DummyAdapter("go", matches=False, capabilities=IndexCapabilityMatrix()),
        ]
    )

    selected = registry.select(workspace)

    assert selected.adapter_id == "bsl"
    descriptor = selected.describe_repo(workspace)
    helpers = selected.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))
    strategy = selected.build_strategy(
        "find callers",
        StrategyContext(workspace=workspace, descriptor=descriptor, capabilities=selected.capabilities),
    )
    assert descriptor.language == "bsl"
    assert helpers["ping"]() == "pong"
    assert strategy == "bsl:find callers"


def test_adapter_registry_rejects_ambiguous_matches(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    registry = AdapterRegistry(
        [
            DummyAdapter("bsl", matches=True, capabilities=IndexCapabilityMatrix()),
            DummyAdapter("go", matches=True, capabilities=IndexCapabilityMatrix()),
        ]
    )

    with pytest.raises(AdapterSelectionError):
        registry.select(workspace)


def test_adapter_registry_rejects_unknown_adapter_hint(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    registry = AdapterRegistry([DummyAdapter("bsl", matches=True, capabilities=IndexCapabilityMatrix())])

    with pytest.raises(AdapterSelectionError):
        registry.select(workspace, adapter_id="missing")
