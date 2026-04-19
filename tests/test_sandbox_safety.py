from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event

from rlm_core.adapters import AdapterRegistry
from rlm_core.index.contracts import (
    IndexBuildRequest,
    IndexCapabilityMatrix,
    IndexLifecycleAction,
    IndexOperationResult,
    IndexOperationStatus,
    IndexStatus,
)
from rlm_core.public_api import PublicApiSurface, PublicIndexRequest, PublicWaitForIndexJobRequest
from rlm_core.runtime import CoreRuntime
from rlm_core.runtime.helpers import make_runtime_helpers
from rlm_core.runtime.sandbox import RuntimeSandbox
from rlm_core.workspace import WorkspaceRef


class BackgroundHooks:
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
class BackgroundAdapter:
    adapter_id: str = "background"
    display_name: str = "Background"
    capabilities: IndexCapabilityMatrix = IndexCapabilityMatrix(
        supports_prebuilt_index=True,
        supports_incremental_update=True,
        supports_background_build=True,
    )
    hooks: BackgroundHooks = field(default_factory=BackgroundHooks)

    def detect(self, workspace: WorkspaceRef) -> bool:
        return True

    def describe_repo(self, workspace: WorkspaceRef):
        raise NotImplementedError

    def register_helpers(self, context):
        return {}

    def build_strategy(self, query: str, context) -> str:
        return query

    def get_index_hooks(self) -> BackgroundHooks:
        return self.hooks


def test_sandbox_blocks_non_whitelisted_imports(tmp_path):
    helpers, resolve_safe = make_runtime_helpers(tmp_path)
    sandbox = RuntimeSandbox(base_path=tmp_path, helpers=helpers, resolve_safe=resolve_safe)

    result = sandbox.execute("import os")

    assert result.error is not None
    assert "ImportError" in result.error
    assert "Only a small standard-library subset is allowed" in result.error


def test_sandbox_blocks_write_access_and_path_escapes(tmp_path):
    helpers, resolve_safe = make_runtime_helpers(tmp_path)
    sandbox = RuntimeSandbox(base_path=tmp_path, helpers=helpers, resolve_safe=resolve_safe)
    outside_file = tmp_path.parent / "outside.txt"
    outside_file.write_text("secret\n", encoding="utf-8")

    write_result = sandbox.execute("open('note.txt', 'w')")
    escape_result = sandbox.execute("print(read_file('../outside.txt'))")

    assert write_result.error is not None
    assert "PermissionError" in write_result.error
    assert "Write access denied" in write_result.error
    assert "blocks writes" in write_result.error
    assert escape_result.error is not None
    assert "PermissionError" in escape_result.error
    assert "escapes sandbox root" in escape_result.error


def test_sandbox_timeout_is_enforced_and_runtime_recovers(tmp_path):
    helpers, resolve_safe = make_runtime_helpers(tmp_path)
    sandbox = RuntimeSandbox(
        base_path=tmp_path,
        helpers=helpers,
        resolve_safe=resolve_safe,
        execution_timeout_seconds=0.05,
    )

    timed_out = sandbox.execute("while True:\n    pass")
    recovered = sandbox.execute("print('ok')")

    assert timed_out.error is not None
    assert "TimeoutError" in timed_out.error
    assert recovered.error is None
    assert recovered.stdout.strip() == "ok"


def test_public_api_wait_timeout_surfaces_structured_error_and_job_can_finish(tmp_path):
    workspace_root = tmp_path / "background"
    workspace_root.mkdir()
    gate = Event()
    surface = PublicApiSurface(
        runtime=CoreRuntime(
            adapter_registry=AdapterRegistry([BackgroundAdapter(hooks=BackgroundHooks(gate=gate))]),
        )
    )

    started = surface.rlm_index(
        PublicIndexRequest(
            action=IndexLifecycleAction.BUILD,
            root_path=str(workspace_root),
            background=True,
        )
    )
    started_payload = started.to_payload()
    job_id = started_payload["data"]["details"]["job_id"]

    timed_out = surface.rlm_wait_for_index_job(
        PublicWaitForIndexJobRequest(job_id=job_id, timeout_seconds=0.01)
    )
    timed_out_payload = timed_out.to_payload()

    assert timed_out.ok is False
    assert timed_out_payload["error"]["code"] == "index_manager_error"
    assert "Timed out while waiting for job" in timed_out_payload["error"]["message"]

    gate.set()
    completed = surface.rlm_wait_for_index_job(
        PublicWaitForIndexJobRequest(job_id=job_id, timeout_seconds=1.0)
    )
    completed_payload = completed.to_payload()

    assert completed.ok is True
    assert completed_payload["data"]["response_type"] == "index_job"
    assert completed_payload["data"]["status"] == "completed"
    assert completed_payload["data"]["details"]["background"] is True
