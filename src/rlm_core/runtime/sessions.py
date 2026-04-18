"""Session management for the core runtime surface."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from rlm_core.adapters.contracts import HelperMap, RepositoryDescriptor
from rlm_core.index.contracts import IndexCapabilityMatrix
from rlm_core.workspace import WorkspaceRef

from .sandbox import RuntimeSandbox


class RuntimeSessionError(RuntimeError):
    """Raised when a runtime session cannot be resolved."""


@dataclass(frozen=True, slots=True)
class RuntimeSession:
    """Runtime session state exposed through the core API."""

    session_id: str
    workspace: WorkspaceRef
    adapter_id: str
    descriptor: RepositoryDescriptor
    capabilities: IndexCapabilityMatrix
    helpers: dict[str, object]
    strategy: str
    sandbox: RuntimeSandbox | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "helpers", dict(self.helpers))


class RuntimeSessionManager:
    """In-memory session registry for early runtime wiring."""

    def __init__(self) -> None:
        self._sessions: dict[str, RuntimeSession] = {}

    def create(
        self,
        *,
        workspace: WorkspaceRef,
        adapter_id: str,
        descriptor: RepositoryDescriptor,
        capabilities: IndexCapabilityMatrix,
        helpers: HelperMap,
        strategy: str,
        sandbox: RuntimeSandbox | None = None,
    ) -> RuntimeSession:
        session = RuntimeSession(
            session_id=uuid4().hex,
            workspace=workspace,
            adapter_id=adapter_id,
            descriptor=descriptor,
            capabilities=capabilities,
            helpers=dict(helpers),
            strategy=strategy,
            sandbox=sandbox,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> RuntimeSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise RuntimeSessionError(f"Unknown runtime session: {session_id}") from exc

    def end(self, session_id: str) -> RuntimeSession:
        try:
            return self._sessions.pop(session_id)
        except KeyError as exc:
            raise RuntimeSessionError(f"Unknown runtime session: {session_id}") from exc
