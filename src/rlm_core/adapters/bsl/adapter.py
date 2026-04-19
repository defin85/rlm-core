"""BSL adapter implementation."""

from __future__ import annotations

from rlm_core.adapters.contracts import HelperContext, RepositoryDescriptor, StrategyContext
from rlm_core.index.contracts import IndexCapabilityMatrix
from rlm_core.workspace import WorkspaceRef

from .advanced import BslAdvancedExtension
from .contracts import BSL_INDEXED_FEATURES
from .detection import inspect_bsl_workspace
from .index import BslIndexHooks
from .live import make_bsl_live_helpers


class BslRepositoryAdapter:
    """Adapter for 1C/BSL repositories."""

    adapter_id = "bsl"
    display_name = "BSL"

    def __init__(
        self,
        *,
        advanced_extension: BslAdvancedExtension | None = None,
        index_hooks: BslIndexHooks | None = None,
    ) -> None:
        self._advanced_extension = advanced_extension or BslAdvancedExtension()
        self.capabilities = IndexCapabilityMatrix(
            supports_prebuilt_index=True,
            supports_incremental_update=True,
            supports_background_build=True,
            adapter_features=BSL_INDEXED_FEATURES,
        )
        self._index_hooks = index_hooks or BslIndexHooks(advanced_extension=self._advanced_extension)

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
        index_snapshot = self._index_hooks.load_snapshot(context.workspace)
        advanced_snapshot = self._index_hooks.load_advanced_snapshot(context.workspace)
        helpers = {
            "bsl_repo_details": lambda: dict(details),
            "bsl_index_features": lambda: list(features),
        }
        helpers.update(make_bsl_live_helpers(context.workspace.root_path, index_snapshot=index_snapshot))
        helpers.update(self._advanced_extension.register_helpers(context.workspace.root_path, snapshot=advanced_snapshot))
        return helpers

    def build_strategy(self, query: str, context: StrategyContext) -> str:
        feature_list = ", ".join(sorted(context.capabilities.adapter_features))
        normalized_query = query.strip() or "inspect bsl repository"
        index_ready = (
            self._index_hooks.load_snapshot(context.workspace) is not None
            and self._index_hooks.load_advanced_snapshot(context.workspace) is not None
        )
        workflow_label = "INDEXED WORKFLOW" if index_ready else "LIVE WORKFLOW"
        return (
            f"bsl:{normalized_query} [indexed_features={feature_list}]\n"
            f"{workflow_label}:\n"
            "- BROWSE: bsl_find_by_type('Documents'), bsl_find_by_type('CommonModules')\n"
            "- NAVIGATE: bsl_find_modules('ObjectName')\n"
            "- TRACE: bsl_find_callers('ProcedureName')\n"
            "- READ: bsl_extract_procedures(path), bsl_read_procedure(path, 'ProcedureName'), read_file(path)\n"
            "- ADVANCED: bsl_find_attributes(name='Организация'), bsl_find_predefined(name='РеализуемыеАктивы')\n"
        )

    def get_index_hooks(self) -> BslIndexHooks:
        return self._index_hooks
