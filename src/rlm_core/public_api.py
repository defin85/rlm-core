"""Stable transport-neutral public API surface for runtime and lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping

from rlm_core.adapters import AdapterRegistry, AdapterSelectionError
from rlm_core.adapters.bsl import BslRepositoryAdapter
from rlm_core.adapters.go import GoRepositoryAdapter
from rlm_core.index.contracts import IndexCapabilityMatrix, IndexLifecycleAction, IndexOperationResult, IndexStatus
from rlm_core.index.manager import IndexManagerError
from rlm_core.runtime import (
    CoreRuntime,
    MutationConfirmationError,
    MutationPolicyError,
    RlmEndResponse,
    RlmExecuteResponse,
    RlmIndexJobResponse,
    RlmStartResponse,
    RuntimeSessionError,
)
from rlm_core.workspace import WorkspaceRef, WorkspaceRegistry, WorkspaceResolutionError

PUBLIC_TOOL_NAMES = (
    "rlm_projects",
    "rlm_start",
    "rlm_execute",
    "rlm_end",
    "rlm_index",
    "rlm_index_job",
    "rlm_wait_for_index_job",
)


@dataclass(frozen=True, slots=True)
class PublicError:
    """Structured public error payload."""

    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))

    def to_payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "details": _normalize_json_value(self.details),
        }


@dataclass(frozen=True, slots=True)
class PublicToolResponse:
    """Stable top-level envelope used by CLI and future MCP routing."""

    tool_name: str
    ok: bool
    data: object | None = None
    error: PublicError | None = None

    @classmethod
    def success(cls, tool_name: str, data: object) -> "PublicToolResponse":
        return cls(tool_name=tool_name, ok=True, data=data)

    @classmethod
    def failure(cls, tool_name: str, error: PublicError) -> "PublicToolResponse":
        return cls(tool_name=tool_name, ok=False, error=error)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "tool_name": self.tool_name,
            "ok": self.ok,
        }
        if self.data is not None:
            payload["data"] = _normalize_json_value(self.data)
        if self.error is not None:
            payload["error"] = self.error.to_payload()
        return payload


@dataclass(frozen=True, slots=True)
class PublicStartRequest:
    """Public request contract for `rlm_start`."""

    workspace_id: str | None = None
    root_path: str | None = None
    adapter_id: str | None = None
    display_name: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    query: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class PublicExecuteRequest:
    """Public request contract for `rlm_execute`."""

    session_id: str
    helper_name: str | None = None
    arguments: object | None = None
    code: str | None = None


@dataclass(frozen=True, slots=True)
class PublicEndRequest:
    """Public request contract for `rlm_end`."""

    session_id: str


@dataclass(frozen=True, slots=True)
class PublicIndexRequest:
    """Public request contract for `rlm_index`."""

    action: IndexLifecycleAction | str
    workspace_id: str | None = None
    root_path: str | None = None
    adapter_id: str | None = None
    display_name: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    background: bool = False
    confirm: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class PublicIndexJobRequest:
    """Public request contract for `rlm_index_job`."""

    job_id: str


@dataclass(frozen=True, slots=True)
class PublicWaitForIndexJobRequest:
    """Public request contract for `rlm_wait_for_index_job`."""

    job_id: str
    timeout_seconds: float | None = None


def build_default_runtime(*, workspace_registry: WorkspaceRegistry | None = None) -> CoreRuntime:
    """Build the default runtime with the production adapter set."""

    return CoreRuntime(
        adapter_registry=AdapterRegistry([BslRepositoryAdapter(), GoRepositoryAdapter()]),
        workspace_registry=workspace_registry,
    )


class PublicApiSurface:
    """Stable external surface layered over the shared runtime and lifecycle services."""

    tool_names = PUBLIC_TOOL_NAMES

    def __init__(self, *, runtime: CoreRuntime | None = None) -> None:
        self._runtime = runtime or build_default_runtime()

    def rlm_projects(self) -> PublicToolResponse:
        return self._call(
            "rlm_projects",
            lambda: {
                "response_type": "rlm_projects",
                "projects": [_serialize_workspace(item) for item in self._runtime.rlm_projects()],
            },
        )

    def rlm_start(self, request: PublicStartRequest) -> PublicToolResponse:
        return self._call(
            "rlm_start",
            lambda: _serialize_start(
                self._runtime.rlm_start(
                    workspace_id=request.workspace_id,
                    root_path=request.root_path,
                    adapter_id=request.adapter_id,
                    display_name=request.display_name,
                    metadata=request.metadata,
                    query=request.query,
                )
            ),
        )

    def rlm_execute(self, request: PublicExecuteRequest) -> PublicToolResponse:
        return self._call(
            "rlm_execute",
            lambda: _serialize_execute(
                self._runtime.rlm_execute(
                    request.session_id,
                    helper_name=request.helper_name,
                    arguments=request.arguments,
                    code=request.code,
                )
            ),
        )

    def rlm_end(self, request: PublicEndRequest) -> PublicToolResponse:
        return self._call(
            "rlm_end",
            lambda: _serialize_end(self._runtime.rlm_end(request.session_id)),
        )

    def rlm_index(self, request: PublicIndexRequest) -> PublicToolResponse:
        def call_index() -> dict[str, object]:
            result = self._runtime.rlm_index(
                request.action,
                workspace_id=request.workspace_id,
                root_path=request.root_path,
                adapter_id=request.adapter_id,
                display_name=request.display_name,
                metadata=request.metadata,
                background=request.background,
                confirm=request.confirm,
            )
            return _serialize_index_response(result)

        return self._call("rlm_index", call_index)

    def rlm_index_job(self, request: PublicIndexJobRequest) -> PublicToolResponse:
        return self._call(
            "rlm_index_job",
            lambda: _serialize_index_job(self._runtime.rlm_index_job(request.job_id)),
        )

    def rlm_wait_for_index_job(self, request: PublicWaitForIndexJobRequest) -> PublicToolResponse:
        return self._call(
            "rlm_wait_for_index_job",
            lambda: _serialize_index_job(
                self._runtime.rlm_wait_for_index_job(
                    request.job_id,
                    timeout=request.timeout_seconds,
                )
            ),
        )

    def _call(self, tool_name: str, callback) -> PublicToolResponse:
        try:
            return PublicToolResponse.success(tool_name, callback())
        except Exception as exc:  # pragma: no cover - exercised through public contract tests
            return PublicToolResponse.failure(tool_name, _map_public_error(exc))


def _serialize_workspace(workspace: WorkspaceRef) -> dict[str, object]:
    return {
        "root_path": str(workspace.root_path),
        "source": workspace.source.value,
        "workspace_id": workspace.workspace_id,
        "display_name": workspace.display_name,
        "adapter_hint": workspace.adapter_hint,
        "metadata": dict(workspace.metadata),
    }


def _serialize_capabilities(capabilities: IndexCapabilityMatrix) -> dict[str, object]:
    return {
        "supports_prebuilt_index": capabilities.supports_prebuilt_index,
        "supports_incremental_update": capabilities.supports_incremental_update,
        "supports_background_build": capabilities.supports_background_build,
        "generic_only": capabilities.generic_only,
        "adapter_features": sorted(capabilities.adapter_features),
        "supported_actions": sorted(action.value for action in capabilities.supported_actions),
    }


def _serialize_start(response: RlmStartResponse) -> dict[str, object]:
    return {
        "response_type": "rlm_start",
        "session_id": response.session_id,
        "workspace": _serialize_workspace(response.workspace),
        "adapter_id": response.adapter_id,
        "descriptor": _normalize_json_value(response.descriptor),
        "capabilities": _serialize_capabilities(response.capabilities),
        "helper_names": list(response.helper_names),
        "strategy": response.strategy,
    }


def _serialize_execute(response: RlmExecuteResponse) -> dict[str, object]:
    return {
        "response_type": "rlm_execute",
        "session_id": response.session_id,
        "helper_name": response.helper_name,
        "result": _normalize_json_value(response.result),
    }


def _serialize_end(response: RlmEndResponse) -> dict[str, object]:
    return {
        "response_type": "rlm_end",
        "session_id": response.session_id,
        "workspace": _serialize_workspace(response.workspace),
        "adapter_id": response.adapter_id,
    }


def _serialize_index_operation(response: IndexOperationResult) -> dict[str, object]:
    return {
        "response_type": "index_operation",
        "action": response.action.value,
        "status": response.status.value,
        "details": _normalize_json_value(response.details),
    }


def _serialize_index_status(response: IndexStatus) -> dict[str, object]:
    return {
        "response_type": "index_status",
        "available": response.available,
        "stale": response.stale,
        "details": _normalize_json_value(response.details),
    }


def _serialize_index_job(response: RlmIndexJobResponse) -> dict[str, object]:
    return {
        "response_type": "index_job",
        "job_id": response.job_id,
        "workspace": _serialize_workspace(response.workspace),
        "action": response.action.value,
        "status": response.status.value,
        "details": _normalize_json_value(response.details),
    }


def _serialize_index_response(response: IndexOperationResult | IndexStatus) -> dict[str, object]:
    if isinstance(response, IndexOperationResult):
        return _serialize_index_operation(response)
    if isinstance(response, IndexStatus):
        return _serialize_index_status(response)
    raise TypeError(f"Unsupported index response: {type(response)!r}")


def _map_public_error(exc: Exception) -> PublicError:
    mappings: tuple[tuple[type[Exception], str], ...] = (
        (MutationConfirmationError, "mutation_confirmation_required"),
        (MutationPolicyError, "mutation_forbidden"),
        (WorkspaceResolutionError, "workspace_resolution_error"),
        (AdapterSelectionError, "adapter_selection_error"),
        (RuntimeSessionError, "runtime_session_error"),
        (IndexManagerError, "index_manager_error"),
        (PermissionError, "permission_denied"),
        (FileNotFoundError, "file_not_found"),
        (ValueError, "invalid_request"),
        (RuntimeError, "runtime_error"),
    )
    for error_type, code in mappings:
        if isinstance(exc, error_type):
            return PublicError(code=code, message=str(exc), details={"type": exc.__class__.__name__})
    return PublicError(code="internal_error", message=str(exc), details={"type": exc.__class__.__name__})


def _normalize_json_value(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized = [_normalize_json_value(item) for item in value]
        return sorted(normalized, key=repr)
    return value


__all__ = [
    "PUBLIC_TOOL_NAMES",
    "PublicApiSurface",
    "PublicEndRequest",
    "PublicError",
    "PublicExecuteRequest",
    "PublicIndexJobRequest",
    "PublicIndexRequest",
    "PublicStartRequest",
    "PublicToolResponse",
    "PublicWaitForIndexJobRequest",
    "build_default_runtime",
]
