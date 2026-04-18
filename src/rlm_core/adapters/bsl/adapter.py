"""BSL adapter implementation."""

from __future__ import annotations

from rlm_core.adapters.contracts import HelperContext, RepositoryDescriptor, StrategyContext
from rlm_core.index.contracts import IndexCapabilityMatrix
from rlm_core.workspace import WorkspaceRef

from .contracts import BSL_INDEXED_FEATURES
from .detection import inspect_bsl_workspace
from .index import BslIndexHooks


class BslRepositoryAdapter:
    """Adapter for 1C/BSL repositories."""

    adapter_id = "bsl"
    display_name = "BSL"

    def __init__(self, *, index_hooks: BslIndexHooks | None = None) -> None:
        self.capabilities = IndexCapabilityMatrix(
            supports_prebuilt_index=True,
            supports_incremental_update=True,
            supports_background_build=True,
            adapter_features=BSL_INDEXED_FEATURES,
        )
        self._index_hooks = index_hooks or BslIndexHooks()

    def detect(self, workspace: WorkspaceRef) -> bool:
        return inspect_bsl_workspace(workspace.root_path) is not None

    def describe_repo(self, workspace: WorkspaceRef) -> RepositoryDescriptor:
        details = inspect_bsl_workspace(workspace.root_path)
        if details is None:
            raise ValueError(f"Workspace {workspace.root_path} is not recognized as a BSL repository")
        return RepositoryDescriptor(
            adapter_id=self.adapter_id,
            workspace_root=workspace.root_path,
            language="bsl",
            details=details.as_mapping(),
        )

    def register_helpers(self, context: HelperContext):
        details = dict(context.descriptor.details)
        features = sorted(context.descriptor.details.get("indexed_features", []) or self.capabilities.adapter_features)
        return {
            "bsl_repo_details": lambda: dict(details),
            "bsl_index_features": lambda: list(features),
        }

    def build_strategy(self, query: str, context: StrategyContext) -> str:
        feature_list = ", ".join(sorted(context.capabilities.adapter_features))
        return f"bsl:{query} [indexed_features={feature_list}]"

    def get_index_hooks(self) -> BslIndexHooks:
        return self._index_hooks
