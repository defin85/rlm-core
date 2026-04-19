"""Core-owned orchestration for adapter-backed index lifecycle operations."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from rlm_core.adapters.registry import AdapterRegistry
from rlm_core.index.contracts import (
    IndexBuildRequest,
    IndexCapabilityMatrix,
    IndexLifecycleAction,
    IndexOperationResult,
    IndexOperationStatus,
    IndexStatus,
)
from rlm_core.workspace import WorkspaceRef


class IndexManagerError(RuntimeError):
    """Raised when lifecycle orchestration cannot proceed."""


@dataclass(frozen=True, slots=True)
class IndexJobStatus:
    """Status of a background lifecycle operation."""

    job_id: str
    workspace: WorkspaceRef
    action: IndexLifecycleAction
    status: IndexOperationStatus
    details: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))


class IndexManager:
    """Core-owned lifecycle service for adapter-backed indexes."""

    def __init__(self, adapter_registry: AdapterRegistry, *, max_workers: int = 4) -> None:
        self._adapter_registry = adapter_registry
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="rlm-index")
        self._workspace_locks: dict[str, Lock] = {}
        self._jobs: dict[str, Future[IndexOperationResult]] = {}
        self._job_status: dict[str, IndexJobStatus] = {}

    def build(self, workspace: WorkspaceRef, *, adapter_id: str | None = None, background: bool = False) -> IndexOperationResult:
        adapter = self._adapter_registry.select(workspace, adapter_id=adapter_id)
        return self._start_or_run(
            workspace,
            action=IndexLifecycleAction.BUILD,
            adapter_id=adapter.adapter_id,
            capabilities=adapter.capabilities,
            background=background,
            sync_runner=lambda: adapter.get_index_hooks().build_index(IndexBuildRequest(workspace=workspace, background=False)),
            async_runner=lambda: adapter.get_index_hooks().build_index(IndexBuildRequest(workspace=workspace, background=True)),
        )

    def update(self, workspace: WorkspaceRef, *, adapter_id: str | None = None, background: bool = False) -> IndexOperationResult:
        adapter = self._adapter_registry.select(workspace, adapter_id=adapter_id)
        return self._start_or_run(
            workspace,
            action=IndexLifecycleAction.UPDATE,
            adapter_id=adapter.adapter_id,
            capabilities=adapter.capabilities,
            background=background,
            sync_runner=lambda: adapter.get_index_hooks().update_index(IndexBuildRequest(workspace=workspace, background=False)),
            async_runner=lambda: adapter.get_index_hooks().update_index(IndexBuildRequest(workspace=workspace, background=True)),
        )

    def drop(self, workspace: WorkspaceRef, *, adapter_id: str | None = None) -> IndexOperationResult:
        adapter = self._adapter_registry.select(workspace, adapter_id=adapter_id)
        hooks = adapter.get_index_hooks()
        if hooks is None or not adapter.capabilities.supports_action(IndexLifecycleAction.DROP):
            return self._unsupported(IndexLifecycleAction.DROP, adapter.capabilities, adapter_id=adapter.adapter_id)
        return self._run_locked(workspace, IndexLifecycleAction.DROP, lambda: hooks.drop_index(workspace))

    def info(self, workspace: WorkspaceRef, *, adapter_id: str | None = None) -> IndexStatus:
        adapter = self._adapter_registry.select(workspace, adapter_id=adapter_id)
        hooks = adapter.get_index_hooks()
        if hooks is None or not adapter.capabilities.supports_action(IndexLifecycleAction.INFO):
            return self._unsupported_status(
                IndexLifecycleAction.INFO,
                adapter.capabilities,
                adapter_id=adapter.adapter_id,
            )
        return hooks.get_index_status(workspace)

    def check(self, workspace: WorkspaceRef, *, adapter_id: str | None = None) -> IndexStatus:
        adapter = self._adapter_registry.select(workspace, adapter_id=adapter_id)
        hooks = adapter.get_index_hooks()
        if hooks is None or not adapter.capabilities.supports_action(IndexLifecycleAction.CHECK):
            return self._unsupported_status(
                IndexLifecycleAction.CHECK,
                adapter.capabilities,
                adapter_id=adapter.adapter_id,
            )
        return hooks.get_index_status(workspace)

    def get_job_status(self, job_id: str) -> IndexJobStatus | None:
        return self._job_status.get(job_id)

    def wait_for_job(self, job_id: str, *, timeout: float | None = None) -> IndexJobStatus:
        future = self._jobs.get(job_id)
        if future is None:
            raise IndexManagerError(f"Unknown index job: {job_id}")
        try:
            future.result(timeout=timeout)
        except TimeoutError as exc:
            raise IndexManagerError(f"Timed out while waiting for job {job_id}") from exc
        status = self.get_job_status(job_id)
        if status is None:
            raise IndexManagerError(f"Job {job_id} finished without a recorded status")
        return status

    def _start_or_run(
        self,
        workspace: WorkspaceRef,
        *,
        action: IndexLifecycleAction,
        adapter_id: str,
        capabilities: IndexCapabilityMatrix,
        background: bool,
        sync_runner,
        async_runner,
    ) -> IndexOperationResult:
        if not capabilities.supports_action(action):
            return self._unsupported(action, capabilities, adapter_id=adapter_id)

        if background and not capabilities.supports_background_build:
            return self._unsupported(action, capabilities, reason="background_unsupported", adapter_id=adapter_id)

        if background:
            return self._start_background_job(workspace, action, async_runner)
        return self._run_locked(workspace, action, sync_runner)

    def _start_background_job(self, workspace: WorkspaceRef, action: IndexLifecycleAction, runner) -> IndexOperationResult:
        lock = self._acquire_lock(workspace)
        job_id = uuid4().hex
        self._job_status[job_id] = IndexJobStatus(
            job_id=job_id,
            workspace=workspace,
            action=action,
            status=IndexOperationStatus.STARTED,
        )

        def run() -> IndexOperationResult:
            try:
                result = runner()
                self._job_status[job_id] = IndexJobStatus(
                    job_id=job_id,
                    workspace=workspace,
                    action=action,
                    status=result.status,
                    details=result.details,
                )
                return result
            finally:
                lock.release()

        self._jobs[job_id] = self._executor.submit(run)
        return IndexOperationResult(
            action=action,
            status=IndexOperationStatus.STARTED,
            details={"job_id": job_id},
        )

    def _run_locked(self, workspace: WorkspaceRef, action: IndexLifecycleAction, runner) -> IndexOperationResult:
        lock = self._acquire_lock(workspace)
        try:
            return runner()
        finally:
            lock.release()

    def _acquire_lock(self, workspace: WorkspaceRef) -> Lock:
        key = str(workspace.root_path)
        lock = self._workspace_locks.setdefault(key, Lock())
        if not lock.acquire(blocking=False):
            raise IndexManagerError(f"Index lifecycle already in progress for workspace {workspace.root_path}")
        return lock

    @staticmethod
    def _unsupported(
        action: IndexLifecycleAction,
        capabilities: IndexCapabilityMatrix,
        *,
        reason: str = "capability_unsupported",
        adapter_id: str | None = None,
    ) -> IndexOperationResult:
        details: dict[str, object] = {
            "reason": reason,
            "supported_actions": sorted(item.value for item in capabilities.supported_actions),
        }
        if adapter_id is not None:
            details["adapter_id"] = adapter_id
        return IndexOperationResult(
            action=action,
            status=IndexOperationStatus.UNSUPPORTED,
            details=details,
        )

    @staticmethod
    def _unsupported_status(
        action: IndexLifecycleAction,
        capabilities: IndexCapabilityMatrix,
        *,
        reason: str = "capability_unsupported",
        adapter_id: str | None = None,
    ) -> IndexStatus:
        details: dict[str, object] = {
            "reason": reason,
            "unsupported_action": action.value,
            "supported_actions": sorted(item.value for item in capabilities.supported_actions),
        }
        if adapter_id is not None:
            details["adapter_id"] = adapter_id
        return IndexStatus(
            available=False,
            details=details,
        )
