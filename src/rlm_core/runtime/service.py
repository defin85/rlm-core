"""Core-owned public runtime API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from rlm_core.adapters import AdapterRegistry, HelperContext, StrategyContext
from rlm_core.index.contracts import IndexCapabilityMatrix, IndexLifecycleAction
from rlm_core.index.manager import IndexManager
from rlm_core.workspace import InMemoryWorkspaceRegistry, WorkspaceRef, WorkspaceRegistry, WorkspaceSource

from .sessions import RuntimeSessionManager

_MUTATING_ACTIONS = frozenset(
    {
        IndexLifecycleAction.BUILD,
        IndexLifecycleAction.UPDATE,
        IndexLifecycleAction.DROP,
    }
)


class MutationPolicyError(RuntimeError):
    """Raised when a registry-backed mutation is forbidden by policy."""


class MutationConfirmationError(MutationPolicyError):
    """Raised when a mutating action requires explicit confirmation."""


@dataclass(frozen=True, slots=True)
class RlmStartResponse:
    """Response returned by `rlm_start`."""

    session_id: str
    workspace: WorkspaceRef
    adapter_id: str
    descriptor: Mapping[str, object]
    capabilities: IndexCapabilityMatrix
    helper_names: tuple[str, ...]
    strategy: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "descriptor", dict(self.descriptor))
        object.__setattr__(self, "helper_names", tuple(self.helper_names))


@dataclass(frozen=True, slots=True)
class RlmExecuteResponse:
    """Response returned by `rlm_execute`."""

    session_id: str
    helper_name: str
    result: object


@dataclass(frozen=True, slots=True)
class RlmEndResponse:
    """Response returned by `rlm_end`."""

    session_id: str
    workspace: WorkspaceRef
    adapter_id: str


class CoreRuntime:
    """Thin public surface that routes API calls through core-owned services."""

    def __init__(
        self,
        *,
        adapter_registry: AdapterRegistry,
        workspace_registry: WorkspaceRegistry | None = None,
        index_manager: IndexManager | None = None,
        session_manager: RuntimeSessionManager | None = None,
    ) -> None:
        self._adapter_registry = adapter_registry
        self._workspace_registry = workspace_registry or InMemoryWorkspaceRegistry()
        self._index_manager = index_manager or IndexManager(adapter_registry)
        self._session_manager = session_manager or RuntimeSessionManager()

    def rlm_start(
        self,
        *,
        workspace_id: str | None = None,
        root_path: str | None = None,
        adapter_id: str | None = None,
        display_name: str | None = None,
        metadata: Mapping[str, str] | None = None,
        query: str = "",
    ) -> RlmStartResponse:
        workspace = self._resolve_workspace(
            workspace_id=workspace_id,
            root_path=root_path,
            display_name=display_name,
            adapter_id=adapter_id,
            metadata=metadata,
        )
        selected_adapter = self._adapter_registry.select(workspace, adapter_id=self._preferred_adapter_id(workspace, adapter_id))
        descriptor = selected_adapter.describe_repo(workspace)
        helpers = selected_adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))
        strategy = selected_adapter.build_strategy(
            query,
            StrategyContext(workspace=workspace, descriptor=descriptor, capabilities=selected_adapter.capabilities),
        )
        session = self._session_manager.create(
            workspace=workspace,
            adapter_id=selected_adapter.adapter_id,
            descriptor=descriptor,
            capabilities=selected_adapter.capabilities,
            helpers=helpers,
            strategy=strategy,
        )
        return RlmStartResponse(
            session_id=session.session_id,
            workspace=workspace,
            adapter_id=selected_adapter.adapter_id,
            descriptor=descriptor.details,
            capabilities=selected_adapter.capabilities,
            helper_names=tuple(sorted(helpers)),
            strategy=strategy,
        )

    def rlm_execute(
        self,
        session_id: str,
        helper_name: str,
        arguments: Mapping[str, object] | Sequence[object] | object | None = None,
    ) -> RlmExecuteResponse:
        session = self._session_manager.get(session_id)
        helper = session.helpers.get(helper_name)
        if helper is None:
            raise RuntimeError(f"Unknown helper for session {session_id}: {helper_name}")

        if isinstance(arguments, Mapping):
            result = helper(**arguments)
        elif isinstance(arguments, Sequence) and not isinstance(arguments, (str, bytes, bytearray)):
            result = helper(*arguments)
        elif arguments is None:
            result = helper()
        else:
            result = helper(arguments)

        return RlmExecuteResponse(session_id=session_id, helper_name=helper_name, result=result)

    def rlm_end(self, session_id: str) -> RlmEndResponse:
        session = self._session_manager.end(session_id)
        return RlmEndResponse(session_id=session_id, workspace=session.workspace, adapter_id=session.adapter_id)

    def rlm_projects(self) -> tuple[WorkspaceRef, ...]:
        return tuple(self._workspace_registry.list_workspaces())

    def rlm_index(
        self,
        action: IndexLifecycleAction | str,
        *,
        workspace_id: str | None = None,
        root_path: str | None = None,
        adapter_id: str | None = None,
        display_name: str | None = None,
        metadata: Mapping[str, str] | None = None,
        background: bool = False,
        confirm: bool = False,
    ):
        workspace = self._resolve_workspace(
            workspace_id=workspace_id,
            root_path=root_path,
            display_name=display_name,
            adapter_id=adapter_id,
            metadata=metadata,
        )
        normalized_action = self._coerce_action(action)
        self._ensure_mutation_allowed(workspace, normalized_action, confirm=confirm)
        selected_adapter = self._preferred_adapter_id(workspace, adapter_id)

        if normalized_action is IndexLifecycleAction.BUILD:
            return self._index_manager.build(workspace, adapter_id=selected_adapter, background=background)
        if normalized_action is IndexLifecycleAction.UPDATE:
            return self._index_manager.update(workspace, adapter_id=selected_adapter, background=background)
        if normalized_action is IndexLifecycleAction.DROP:
            return self._index_manager.drop(workspace, adapter_id=selected_adapter)
        if normalized_action is IndexLifecycleAction.INFO:
            return self._index_manager.info(workspace, adapter_id=selected_adapter)
        if normalized_action is IndexLifecycleAction.CHECK:
            return self._index_manager.check(workspace, adapter_id=selected_adapter)
        raise RuntimeError(f"Unsupported lifecycle action: {normalized_action}")

    def _resolve_workspace(
        self,
        *,
        workspace_id: str | None,
        root_path: str | None,
        display_name: str | None,
        adapter_id: str | None,
        metadata: Mapping[str, str] | None,
    ) -> WorkspaceRef:
        return self._workspace_registry.resolve(
            workspace_id=workspace_id,
            root_path=root_path,
            display_name=display_name,
            adapter_hint=adapter_id,
            metadata=metadata,
        )

    @staticmethod
    def _preferred_adapter_id(workspace: WorkspaceRef, adapter_id: str | None) -> str | None:
        return adapter_id or workspace.adapter_hint

    @staticmethod
    def _coerce_action(action: IndexLifecycleAction | str) -> IndexLifecycleAction:
        if isinstance(action, IndexLifecycleAction):
            return action
        return IndexLifecycleAction(action)

    @staticmethod
    def _ensure_mutation_allowed(
        workspace: WorkspaceRef,
        action: IndexLifecycleAction,
        *,
        confirm: bool,
    ) -> None:
        if action not in _MUTATING_ACTIONS or workspace.source is not WorkspaceSource.REGISTRY:
            return

        policy = workspace.metadata.get("mutation_policy", "allow").strip().lower()
        if policy == "deny":
            raise MutationPolicyError(f"Mutating action {action.value} is forbidden for workspace {workspace.workspace_id}")
        if policy == "confirm" and not confirm:
            raise MutationConfirmationError(
                f"Mutating action {action.value} for workspace {workspace.workspace_id} requires confirmation"
            )
