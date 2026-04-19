from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event

import pytest

from rlm_core.adapters import AdapterRegistry
from rlm_core.index.contracts import (
    IndexBuildRequest,
    IndexCapabilityMatrix,
    IndexLifecycleAction,
    IndexOperationResult,
    IndexOperationStatus,
    IndexStatus,
)
from rlm_core.index.manager import IndexManager, IndexManagerError
from rlm_core.workspace import WorkspaceRef, WorkspaceSource


class ControllableHooks:
    def __init__(self, *, gate: Event | None = None) -> None:
        self._gate = gate

    def build_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        if self._gate is not None:
            self._gate.wait(timeout=1.0)
        return IndexOperationResult(
            action=IndexLifecycleAction.BUILD,
            status=IndexOperationStatus.COMPLETED,
            details={"background": request.background},
        )

    def update_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        return IndexOperationResult(
            action=IndexLifecycleAction.UPDATE,
            status=IndexOperationStatus.COMPLETED,
            details={"background": request.background},
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
class ManagerAdapter:
    adapter_id: str
    capabilities: IndexCapabilityMatrix
    hooks: ControllableHooks | None
    display_name: str = "ManagerAdapter"

    def detect(self, workspace: WorkspaceRef) -> bool:
        return True

    def describe_repo(self, workspace: WorkspaceRef):
        raise NotImplementedError

    def register_helpers(self, context):
        return {}

    def build_strategy(self, query: str, context) -> str:
        return query

    def get_index_hooks(self):
        return self.hooks


def test_index_manager_runs_sync_build(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    adapter = ManagerAdapter(
        adapter_id="bsl",
        capabilities=IndexCapabilityMatrix(supports_prebuilt_index=True, supports_incremental_update=True),
        hooks=ControllableHooks(),
    )
    manager = IndexManager(AdapterRegistry([adapter]))

    result = manager.build(workspace)

    assert result.status is IndexOperationStatus.COMPLETED
    assert result.action is IndexLifecycleAction.BUILD
    assert result.details["background"] is False


def test_index_manager_reports_unsupported_actions(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    adapter = ManagerAdapter(
        adapter_id="live-only",
        capabilities=IndexCapabilityMatrix(),
        hooks=None,
    )
    manager = IndexManager(AdapterRegistry([adapter]))

    result = manager.build(workspace)
    info = manager.info(workspace)

    assert result.status is IndexOperationStatus.UNSUPPORTED
    assert result.details["adapter_id"] == "live-only"
    assert result.details["reason"] == "capability_unsupported"
    assert result.details["supported_actions"] == []
    assert info.available is False
    assert info.details["adapter_id"] == "live-only"
    assert info.details["reason"] == "capability_unsupported"
    assert info.details["unsupported_action"] == "info"


def test_index_manager_tracks_background_jobs(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    adapter = ManagerAdapter(
        adapter_id="bsl",
        capabilities=IndexCapabilityMatrix(
            supports_prebuilt_index=True,
            supports_incremental_update=True,
            supports_background_build=True,
        ),
        hooks=ControllableHooks(),
    )
    manager = IndexManager(AdapterRegistry([adapter]))

    started = manager.build(workspace, background=True)
    job_id = started.details["job_id"]
    completed = manager.wait_for_job(job_id, timeout=1.0)

    assert started.status is IndexOperationStatus.STARTED
    assert completed.status is IndexOperationStatus.COMPLETED
    assert completed.details["background"] is True


def test_index_manager_rejects_concurrent_operations_for_same_workspace(tmp_path):
    workspace = WorkspaceRef(root_path=tmp_path, source=WorkspaceSource.DIRECT_PATH)
    gate = Event()
    adapter = ManagerAdapter(
        adapter_id="bsl",
        capabilities=IndexCapabilityMatrix(
            supports_prebuilt_index=True,
            supports_incremental_update=True,
            supports_background_build=True,
        ),
        hooks=ControllableHooks(gate=gate),
    )
    manager = IndexManager(AdapterRegistry([adapter]))

    started = manager.build(workspace, background=True)
    time.sleep(0.05)

    with pytest.raises(IndexManagerError):
        manager.drop(workspace)

    gate.set()
    manager.wait_for_job(started.details["job_id"], timeout=1.0)
